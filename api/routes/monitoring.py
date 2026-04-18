"""Monitoring API routes — superuser + website owner access."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import Optional

from api.routes.auth import get_current_user
from services.monitoring_service import (
    run_all_checks, get_latest_checks, get_open_incidents, get_escalation_report,
)
from services.payment_reminder_service import (
    run_payment_reminders, get_defaulters, get_reminder_history,
)
from database.snowflake_client import db

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


def _require_superuser(current=Depends(get_current_user)):
    if current.get("plan") not in ("superuser", "enterprise"):
        raise HTTPException(status_code=403, detail="Superuser access required")
    return current


# ── Trigger manual check ──────────────────────────────────────────────────────
@router.post("/run")
async def trigger_checks(bg: BackgroundTasks, current=Depends(_require_superuser)):
    """Manually trigger a full monitoring sweep (runs in background)."""
    bg.add_task(run_all_checks)
    return {"message": "Monitoring sweep started in background"}


# ── Platform-level checks ─────────────────────────────────────────────────────
@router.get("/platform")
async def platform_status(current=Depends(get_current_user)):
    """Latest status for all platform-wide checks (DB, email, SMS, Stripe, API)."""
    return get_latest_checks(website_id=None)


# ── Per-website checks ────────────────────────────────────────────────────────
@router.get("/website/{website_id}")
async def website_status(website_id: str, current=Depends(get_current_user)):
    """Latest check results for a single website. Owner or superuser only."""
    user_id = current["sub"]
    plan    = current.get("plan", "free")

    if plan not in ("superuser", "enterprise"):
        # Verify ownership
        site = db.fetchone(
            "SELECT user_id FROM websites WHERE website_id = ?", (website_id,)
        )
        if not site or site["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not your website")

    return get_latest_checks(website_id=website_id)


# ── Open incidents ────────────────────────────────────────────────────────────
@router.get("/incidents")
async def all_incidents(
    website_id: Optional[str] = Query(None),
    current=Depends(get_current_user),
):
    plan = current.get("plan", "free")
    if plan in ("superuser", "enterprise"):
        return get_open_incidents(website_id)
    # Regular users: only their own incidents
    user_id = current["sub"]
    sites = db.execute(
        "SELECT website_id FROM websites WHERE user_id = ?", (user_id,)
    ) or []
    result = []
    for s in sites:
        if website_id and s["website_id"] != website_id:
            continue
        result.extend(get_open_incidents(s["website_id"]))
    return result


# ── Resolve incident ──────────────────────────────────────────────────────────
@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str, current=Depends(_require_superuser)):
    import datetime
    db.execute(
        "UPDATE monitor_incidents SET status='resolved', resolved_at=? WHERE incident_id=?",
        (datetime.datetime.utcnow().isoformat(), incident_id),
    )
    return {"message": "Incident marked resolved"}


# ── Escalation report ─────────────────────────────────────────────────────────
@router.get("/escalation")
async def escalation_report(current=Depends(_require_superuser)):
    """
    All open incidents older than 1 hour — used on the monitoring console page
    to surface unresolved issues requiring admin attention.
    """
    return get_escalation_report()


# ── Payment defaulters ────────────────────────────────────────────────────────
@router.get("/defaulters")
async def payment_defaulters(current=Depends(_require_superuser)):
    """Users with 3 overdue payment reminders sent — escalated to 'defaulted'."""
    return get_defaulters()


# ── Reminder history ──────────────────────────────────────────────────────────
@router.get("/reminders")
async def reminder_history(
    user_id: Optional[str] = Query(None),
    current=Depends(_require_superuser),
):
    return get_reminder_history(user_id)


# ── Trigger manual payment reminder run ───────────────────────────────────────
@router.post("/reminders/run")
async def trigger_reminders(bg: BackgroundTasks, current=Depends(_require_superuser)):
    bg.add_task(run_payment_reminders)
    return {"message": "Payment reminder cycle started in background"}


# ── Check history (paginated) ─────────────────────────────────────────────────
@router.get("/history")
async def check_history(
    website_id: Optional[str] = Query(None),
    check_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current=Depends(_require_superuser),
):
    sql  = "SELECT * FROM monitor_checks WHERE 1=1"
    args = []
    if website_id:
        sql += " AND website_id = ?"
        args.append(website_id)
    if check_type:
        sql += " AND check_type = ?"
        args.append(check_type)
    sql += " ORDER BY checked_at DESC LIMIT ?"
    args.append(limit)
    return db.execute(sql, tuple(args)) or []


# ── Notification log ────────────────────────────────────────────────────────--
@router.get("/notifications")
async def notification_log(
    limit: int = Query(100, ge=1, le=500),
    current=Depends(_require_superuser),
):
    return db.execute(
        "SELECT * FROM notification_log ORDER BY sent_at DESC LIMIT ?", (limit,)
    ) or []
