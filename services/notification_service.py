"""
Notification Service — Email, SMS, and WhatsApp delivery.

Channels:
  email     → SMTP (SendGrid or any SMTP)
  sms       → Twilio SMS
  whatsapp  → Twilio WhatsApp (sandbox or production)

All sends are logged to the notification_log table.
"""
import os
import uuid
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from database.snowflake_client import db


# ── Config ────────────────────────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST",     "smtp.sendgrid.net")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER",     "apikey")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM",     "noreply@websitebuilder.ai")

TWILIO_SID    = os.getenv("TWILIO_ACCOUNT_SID",  "")
TWILIO_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN",   "")
TWILIO_FROM   = os.getenv("TWILIO_FROM_NUMBER",  "")
TWILIO_WA     = os.getenv("TWILIO_WHATSAPP_FROM", f"whatsapp:{TWILIO_FROM}" if TWILIO_FROM else "")


# ── Internal log helper ───────────────────────────────────────────────────────
def _log(user_id, channel, destination, subject, body, status, error=None):
    db.execute(
        "INSERT INTO notification_log "
        "(log_id, user_id, channel, destination, subject, body, status, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, channel, destination, subject, body, status, error),
    )


# ── Email ─────────────────────────────────────────────────────────────────────
def send_email(to: str, subject: str, html_body: str, user_id: str = None) -> bool:
    """Send HTML email via SMTP. Returns True on success."""
    if not SMTP_PASSWORD:
        print(f"[notify] SMTP not configured — skipping email to {to}")
        _log(user_id, "email", to, subject, html_body, "skipped")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SMTP_FROM
        msg["To"]      = to
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo()
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.sendmail(SMTP_FROM, [to], msg.as_string())

        _log(user_id, "email", to, subject, html_body, "sent")
        return True
    except Exception as e:
        print(f"[notify] Email error → {e}")
        _log(user_id, "email", to, subject, html_body, "failed", str(e))
        return False


# ── SMS ───────────────────────────────────────────────────────────────────────
def send_sms(to: str, body: str, user_id: str = None) -> bool:
    """Send SMS via Twilio. Returns True on success."""
    if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM):
        print(f"[notify] Twilio SMS not configured — skipping SMS to {to}")
        _log(user_id, "sms", to, None, body, "skipped")
        return False
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(to=to, from_=TWILIO_FROM, body=body)
        _log(user_id, "sms", to, None, body, "sent")
        return True
    except Exception as e:
        print(f"[notify] SMS error → {e}")
        _log(user_id, "sms", to, None, body, "failed", str(e))
        return False


# ── WhatsApp ──────────────────────────────────────────────────────────────────
def send_whatsapp(to: str, body: str, user_id: str = None) -> bool:
    """
    Send WhatsApp message via Twilio.
    'to' should be a phone number like +15551234567 (no whatsapp: prefix needed).
    """
    if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_WA):
        print(f"[notify] Twilio WhatsApp not configured — skipping WA to {to}")
        _log(user_id, "whatsapp", to, None, body, "skipped")
        return False
    try:
        from twilio.rest import Client
        wa_to = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(to=wa_to, from_=TWILIO_WA, body=body)
        _log(user_id, "whatsapp", to, None, body, "sent")
        return True
    except Exception as e:
        print(f"[notify] WhatsApp error → {e}")
        _log(user_id, "whatsapp", to, None, body, "failed", str(e))
        return False


# ── Multi-channel broadcast ───────────────────────────────────────────────────
def notify_user(
    user_id: str,
    email: str,
    subject: str,
    html_body: str,
    plain_body: str,
    mobile: Optional[str] = None,
    channels: list = None,   # default: all configured channels
):
    """
    Deliver a notification across all requested channels.
    channels: list of 'email', 'sms', 'whatsapp'
    """
    if channels is None:
        channels = ["email", "sms", "whatsapp"]

    results = {}
    if "email" in channels:
        results["email"] = send_email(email, subject, html_body, user_id)
    if mobile:
        if "sms" in channels:
            results["sms"] = send_sms(mobile, plain_body, user_id)
        if "whatsapp" in channels:
            results["whatsapp"] = send_whatsapp(mobile, plain_body, user_id)
    return results


# ── Pre-built templates ───────────────────────────────────────────────────────
def _wrap_html(title: str, body_html: str) -> str:
    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto;padding:24px">
      <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:24px;border-radius:12px 12px 0 0">
        <h1 style="color:#fff;margin:0;font-size:1.4rem">🚀 Website Builder</h1>
      </div>
      <div style="background:#fff;padding:28px;border:1px solid #e2e8f0;border-radius:0 0 12px 12px">
        <h2 style="color:#2d3748">{title}</h2>
        {body_html}
        <hr style="margin:24px 0;border:none;border-top:1px solid #e2e8f0">
        <p style="color:#a0aec0;font-size:.8rem">Website Builder Platform · support@websitebuilder.ai</p>
      </div>
    </div>"""


def email_incident_alert(to: str, user_id: str, website_name: str,
                          check_type: str, detail: str, severity: str) -> bool:
    icon = "🔴" if severity == "critical" else "🟡"
    subject = f"{icon} Alert: {check_type} issue on {website_name}"
    body = _wrap_html(
        f"{icon} {check_type} — {severity.upper()}",
        f"<p>Your website <b>{website_name}</b> has a monitoring alert:</p>"
        f"<div style='background:#fff5f5;border-left:4px solid #fc8181;padding:16px;border-radius:4px'>"
        f"<b>{check_type}</b><br>{detail}</div>"
        f"<p>We are tracking this and will notify you when resolved.</p>",
    )
    return send_email(to, subject, body, user_id)


def sms_incident_alert(to: str, user_id: str, website_name: str,
                        check_type: str, severity: str) -> bool:
    icon = "🔴" if severity == "critical" else "🟡"
    return send_sms(
        to,
        f"{icon} WebBuilder Alert: {check_type} issue detected on '{website_name}'. "
        f"Login to your console for details.",
        user_id,
    )


def email_resolved_alert(to: str, user_id: str, website_name: str, check_type: str) -> bool:
    subject = f"✅ Resolved: {check_type} is back online — {website_name}"
    body = _wrap_html(
        f"✅ {check_type} — RESOLVED",
        f"<p>Good news! The <b>{check_type}</b> issue on <b>{website_name}</b> "
        f"has been resolved and is now operating normally.</p>",
    )
    return send_email(to, subject, body, user_id)


def email_payment_reminder(to: str, user_id: str, full_name: str,
                            plan: str, due_date: str, amount: float,
                            days_until: int, reminder_num: int) -> bool:
    if days_until > 0:
        urgency = "Payment Due Soon"
        icon = "💳"
        detail = f"<p>Your <b>{plan}</b> subscription payment of <b>${amount:.2f}</b> is due in <b>{days_until} day(s)</b> on {due_date}.</p>"
    else:
        overdue = abs(days_until)
        urgency = f"Payment Overdue — Reminder #{reminder_num}"
        icon = "⚠️"
        detail = (
            f"<p>Your <b>{plan}</b> subscription payment of <b>${amount:.2f}</b> was due on {due_date} "
            f"({overdue} day(s) ago). This is reminder <b>#{reminder_num} of 3</b>.</p>"
        )

    subject = f"{icon} {urgency} — Website Builder"
    body = _wrap_html(
        f"{icon} {urgency}",
        f"<p>Hi {full_name},</p>"
        + detail
        + "<p><a href='https://websitebuilder.ai/billing' "
        "style='background:#667eea;color:#fff;padding:12px 24px;border-radius:8px;"
        "text-decoration:none;font-weight:700'>Pay Now</a></p>"
        "<p>If you have questions, reply to this email or contact support.</p>",
    )
    return send_email(to, subject, body, user_id)
