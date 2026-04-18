"""
Monitoring Service — health checks for all platform components.

Check types (runs per website):
  website_uptime       — HTTP GET the live URL, check 2xx response
  ssl_certificate      — TLS cert expiry days remaining
  response_time        — Page load latency (ms)
  shopping_cart        — Product listing API responds correctly
  payment_gateway      — Stripe API key validity
  database_health      — Platform DB query round-trip
  s3_hosting           — S3 bucket HEAD request
  email_service        — SMTP connectivity (EHLO only, no send)
  sms_service          — Twilio credentials validation
  api_health           — Platform API /health endpoint

Severity rules:
  critical  — website down, DB down, payment gateway auth failed
  warning   — SSL < 14 days, slow response > 5 s, service degraded
  info      — first-time pass or recovery
"""
import os
import ssl
import socket
import time
import uuid
import datetime
import smtplib
from typing import Optional
from urllib.request import urlopen, Request as UrlRequest
from urllib.error import URLError

from database.snowflake_client import db
from services.notification_service import (
    email_incident_alert, sms_incident_alert, email_resolved_alert,
)

PLATFORM_API = os.getenv("PLATFORM_API_URL", "http://localhost:8000")
CHECK_TIMEOUT = int(os.getenv("MONITOR_TIMEOUT_SEC", "10"))


# ─────────────────────────────────────────────────────────────────────────────
# Individual check functions — each returns dict: {status, latency_ms, detail}
# status: "ok" | "warning" | "critical"
# ─────────────────────────────────────────────────────────────────────────────

def check_website_uptime(url: str) -> dict:
    if not url or not url.startswith("http"):
        return {"status": "warning", "latency_ms": None, "detail": "No URL configured for this website"}
    try:
        req = UrlRequest(url, headers={"User-Agent": "WebBuilder-Monitor/1.0"})
        t0 = time.monotonic()
        with urlopen(req, timeout=CHECK_TIMEOUT) as resp:
            latency = int((time.monotonic() - t0) * 1000)
            if resp.status < 400:
                status = "warning" if latency > 5000 else "ok"
                return {"status": status, "latency_ms": latency,
                        "detail": f"HTTP {resp.status} in {latency}ms"}
            return {"status": "critical", "latency_ms": latency,
                    "detail": f"HTTP {resp.status}"}
    except URLError as e:
        return {"status": "critical", "latency_ms": None, "detail": f"Unreachable: {e.reason}"}
    except Exception as e:
        return {"status": "critical", "latency_ms": None, "detail": str(e)}


def check_ssl_certificate(url: str) -> dict:
    if not url or not url.startswith("https"):
        return {"status": "info", "latency_ms": None, "detail": "Not HTTPS — SSL check skipped"}
    try:
        hostname = url.split("/")[2]
        ctx = ssl.create_default_context()
        t0 = time.monotonic()
        with ctx.wrap_socket(socket.create_connection((hostname, 443), timeout=CHECK_TIMEOUT),
                             server_hostname=hostname) as s:
            latency = int((time.monotonic() - t0) * 1000)
            cert = s.getpeercert()
        expiry_str = cert["notAfter"]                             # e.g. "Apr 30 12:00:00 2025 GMT"
        expiry = datetime.datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
        days   = (expiry - datetime.datetime.utcnow()).days
        if days < 7:
            return {"status": "critical", "latency_ms": latency,
                    "detail": f"SSL cert expires in {days} day(s)!"}
        if days < 14:
            return {"status": "warning", "latency_ms": latency,
                    "detail": f"SSL cert expires in {days} day(s)"}
        return {"status": "ok", "latency_ms": latency,
                "detail": f"SSL valid — {days} days remaining"}
    except Exception as e:
        return {"status": "warning", "latency_ms": None, "detail": f"SSL check failed: {e}"}


def check_response_time(url: str) -> dict:
    """Re-uses uptime check but focuses on latency thresholds."""
    result = check_website_uptime(url)
    ms = result.get("latency_ms")
    if ms is None:
        return result
    if ms > 5000:
        result["status"] = "critical"
        result["detail"] += " — VERY SLOW (>5s)"
    elif ms > 2000:
        result["status"] = "warning"
        result["detail"] += " — slow (>2s)"
    return result


def check_shopping_cart(website_id: str) -> dict:
    try:
        url = f"{PLATFORM_API}/api/v1/shop/{website_id}/categories"
        req = UrlRequest(url, headers={"User-Agent": "WebBuilder-Monitor/1.0"})
        t0 = time.monotonic()
        with urlopen(req, timeout=CHECK_TIMEOUT) as resp:
            latency = int((time.monotonic() - t0) * 1000)
            if resp.status < 400:
                return {"status": "ok", "latency_ms": latency,
                        "detail": f"Shopping cart API responds in {latency}ms"}
            return {"status": "critical", "latency_ms": latency,
                    "detail": f"Shopping cart API returned HTTP {resp.status}"}
    except Exception as e:
        return {"status": "critical", "latency_ms": None,
                "detail": f"Shopping cart API unreachable: {e}"}


def check_payment_gateway() -> dict:
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return {"status": "warning", "latency_ms": None,
                "detail": "Stripe not configured (STRIPE_SECRET_KEY missing)"}
    try:
        import stripe
        stripe.api_key = stripe_key
        t0 = time.monotonic()
        stripe.Account.retrieve()
        latency = int((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency,
                "detail": f"Stripe API reachable in {latency}ms"}
    except Exception as e:
        err = str(e)
        if "AuthenticationError" in type(e).__name__ or "authentication" in err.lower():
            return {"status": "critical", "latency_ms": None,
                    "detail": f"Stripe authentication failed — check API key"}
        return {"status": "warning", "latency_ms": None,
                "detail": f"Stripe check failed: {err}"}


def check_database_health() -> dict:
    try:
        t0 = time.monotonic()
        db.execute("SELECT 1 AS ping")
        latency = int((time.monotonic() - t0) * 1000)
        if latency > 3000:
            return {"status": "warning", "latency_ms": latency,
                    "detail": f"DB responding but slow ({latency}ms)"}
        return {"status": "ok", "latency_ms": latency,
                "detail": f"Database healthy ({latency}ms)"}
    except Exception as e:
        return {"status": "critical", "latency_ms": None,
                "detail": f"Database unreachable: {e}"}


def check_s3_hosting(bucket: str, region: str = "us-east-1") -> dict:
    if not bucket:
        return {"status": "info", "latency_ms": None,
                "detail": "S3 not configured for this website"}
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
        s3 = boto3.client("s3", region_name=region)
        t0 = time.monotonic()
        s3.head_bucket(Bucket=bucket)
        latency = int((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency,
                "detail": f"S3 bucket '{bucket}' reachable in {latency}ms"}
    except Exception as e:
        err = str(e)
        if "NoCredentials" in err or "403" in err:
            return {"status": "critical", "latency_ms": None,
                    "detail": f"S3 auth failed for bucket '{bucket}'"}
        return {"status": "warning", "latency_ms": None,
                "detail": f"S3 check failed: {err}"}


def check_email_service() -> dict:
    host     = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
    port     = int(os.getenv("SMTP_PORT", "587"))
    password = os.getenv("SMTP_PASSWORD", "")
    if not password:
        return {"status": "warning", "latency_ms": None,
                "detail": "SMTP not configured — email notifications unavailable"}
    try:
        t0 = time.monotonic()
        with smtplib.SMTP(host, port, timeout=CHECK_TIMEOUT) as s:
            s.ehlo()
        latency = int((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency,
                "detail": f"SMTP server {host}:{port} reachable ({latency}ms)"}
    except Exception as e:
        return {"status": "critical", "latency_ms": None,
                "detail": f"SMTP unreachable: {e}"}


def check_sms_service() -> dict:
    sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    if not (sid and token):
        return {"status": "warning", "latency_ms": None,
                "detail": "Twilio not configured — SMS/WhatsApp notifications unavailable"}
    try:
        from twilio.rest import Client
        t0 = time.monotonic()
        Client(sid, token).api.accounts(sid).fetch()
        latency = int((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency,
                "detail": f"Twilio account verified ({latency}ms)"}
    except Exception as e:
        return {"status": "critical", "latency_ms": None,
                "detail": f"Twilio auth failed: {e}"}


def check_api_health() -> dict:
    try:
        t0 = time.monotonic()
        with urlopen(f"{PLATFORM_API}/health", timeout=CHECK_TIMEOUT) as r:
            latency = int((time.monotonic() - t0) * 1000)
            return {"status": "ok", "latency_ms": latency,
                    "detail": f"Platform API healthy ({latency}ms)"}
    except Exception as e:
        return {"status": "critical", "latency_ms": None,
                "detail": f"Platform API unreachable: {e}"}


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator — run all checks for all live websites
# ─────────────────────────────────────────────────────────────────────────────

PLATFORM_CHECKS = {
    "database_health":   lambda _: check_database_health(),
    "email_service":     lambda _: check_email_service(),
    "sms_service":       lambda _: check_sms_service(),
    "payment_gateway":   lambda _: check_payment_gateway(),
    "api_health":        lambda _: check_api_health(),
}

WEBSITE_CHECKS = {
    "website_uptime":    lambda w: check_website_uptime(w.get("domain") or w.get("s3_url") or ""),
    "ssl_certificate":   lambda w: check_ssl_certificate(w.get("domain") or w.get("s3_url") or ""),
    "response_time":     lambda w: check_response_time(w.get("domain") or w.get("s3_url") or ""),
    "shopping_cart":     lambda w: check_shopping_cart(w["website_id"]),
    "s3_hosting":        lambda w: check_s3_hosting(w.get("s3_bucket", ""), w.get("aws_region", "us-east-1")),
}


def _save_check(website_id: Optional[str], check_type: str, result: dict):
    db.execute(
        "INSERT INTO monitor_checks (check_id, website_id, check_type, status, latency_ms, detail) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), website_id, check_type,
         result["status"], result.get("latency_ms"), result.get("detail")),
    )
    return result


def _handle_incident(website_id: Optional[str], website_name: str,
                      check_type: str, result: dict,
                      owner_email: str, owner_mobile: Optional[str],
                      owner_user_id: str):
    status   = result["status"]
    severity = status  # "ok" | "warning" | "critical"

    # Check if there's already an open incident for this check
    existing = db.fetchone(
        "SELECT incident_id, status FROM monitor_incidents "
        "WHERE website_id IS ? AND check_type = ? AND status = 'open' "
        "ORDER BY created_at DESC LIMIT 1",
        (website_id, check_type),
    )

    if status in ("warning", "critical"):
        if not existing:
            # New incident — create and notify
            incident_id = str(uuid.uuid4())
            now = datetime.datetime.utcnow().isoformat()
            db.execute(
                "INSERT INTO monitor_incidents "
                "(incident_id, website_id, check_type, severity, status, detail, notified_at) "
                "VALUES (?, ?, ?, ?, 'open', ?, ?)",
                (incident_id, website_id, check_type, severity, result.get("detail"), now),
            )
            # Notify owner
            email_incident_alert(owner_email, owner_user_id, website_name,
                                   check_type, result.get("detail", ""), severity)
            if owner_mobile:
                sms_incident_alert(owner_mobile, owner_user_id, website_name,
                                    check_type, severity)
            print(f"[monitor] 🔴 NEW incident: {website_name} / {check_type} — {severity}")
    elif status == "ok" and existing:
        # Resolve the open incident
        db.execute(
            "UPDATE monitor_incidents SET status='resolved', resolved_at=? WHERE incident_id=?",
            (datetime.datetime.utcnow().isoformat(), existing["incident_id"]),
        )
        email_resolved_alert(owner_email, owner_user_id, website_name, check_type)
        print(f"[monitor] ✅ Resolved: {website_name} / {check_type}")


def run_all_checks():
    """Entry point called by the scheduler every N minutes."""
    print(f"[monitor] Starting check cycle at {datetime.datetime.utcnow().isoformat()}")

    # ── Platform-wide checks (not tied to a specific website) ────────────────
    for check_type, fn in PLATFORM_CHECKS.items():
        result = fn(None)
        _save_check(None, check_type, result)
        if result["status"] != "ok":
            print(f"[monitor] ⚠️  Platform / {check_type}: {result['detail']}")

    # ── Per-website checks ───────────────────────────────────────────────────
    websites = db.execute(
        "SELECT w.website_id, w.name, w.domain, w.s3_url, w.s3_bucket, w.status, "
        "       u.email, u.mobile, u.user_id "
        "FROM websites w JOIN users u ON w.user_id = u.user_id "
        "WHERE w.status IN ('live','built')"
    )
    for website in (websites or []):
        for check_type, fn in WEBSITE_CHECKS.items():
            result = fn(website)
            _save_check(website["website_id"], check_type, result)
            _handle_incident(
                website["website_id"], website["name"],
                check_type, result,
                website["email"], website.get("mobile"),
                website["user_id"],
            )

    print(f"[monitor] ✅ Check cycle complete. "
          f"Checked {len(websites or [])} website(s) × {len(WEBSITE_CHECKS)} checks "
          f"+ {len(PLATFORM_CHECKS)} platform checks.")


def get_latest_checks(website_id: Optional[str] = None) -> list:
    """Return most recent check per check_type for a website (or platform)."""
    if website_id:
        sql = (
            "SELECT check_type, status, latency_ms, detail, checked_at "
            "FROM monitor_checks WHERE website_id = ? "
            "ORDER BY checked_at DESC"
        )
        rows = db.execute(sql, (website_id,))
    else:
        sql = (
            "SELECT check_type, status, latency_ms, detail, checked_at "
            "FROM monitor_checks WHERE website_id IS NULL "
            "ORDER BY checked_at DESC"
        )
        rows = db.execute(sql)

    # Deduplicate: keep only latest per check_type
    seen, result = set(), []
    for row in (rows or []):
        if row["check_type"] not in seen:
            seen.add(row["check_type"])
            result.append(row)
    return result


def get_open_incidents(website_id: Optional[str] = None) -> list:
    if website_id:
        return db.execute(
            "SELECT * FROM monitor_incidents WHERE website_id = ? AND status = 'open' "
            "ORDER BY created_at DESC",
            (website_id,),
        ) or []
    return db.execute(
        "SELECT mi.*, w.name AS website_name "
        "FROM monitor_incidents mi "
        "LEFT JOIN websites w ON mi.website_id = w.website_id "
        "ORDER BY mi.created_at DESC LIMIT 200"
    ) or []


def get_escalation_report() -> list:
    """All unresolved incidents older than 1 hour, ordered by severity."""
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat()
    return db.execute(
        "SELECT mi.incident_id, mi.check_type, mi.severity, mi.detail, "
        "       mi.created_at, w.name AS website_name, u.email AS owner_email "
        "FROM monitor_incidents mi "
        "LEFT JOIN websites w ON mi.website_id = w.website_id "
        "LEFT JOIN users u ON w.user_id = u.user_id "
        "WHERE mi.status = 'open' AND mi.created_at < ? "
        "ORDER BY CASE mi.severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, "
        "mi.created_at ASC",
        (cutoff,),
    ) or []
