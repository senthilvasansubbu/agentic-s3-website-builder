"""
Payment Reminder Service — automated billing notifications.

Reminder schedule:
  PRE-DUE   (days_until > 0)
    • 7 days before due date
    • 3 days before due date
    • 1 day before due date

  POST-DUE  (days_until <= 0, payment not received)
    • Reminder #1 — 1 day after due
    • Reminder #2 — 3 days after due
    • Reminder #3 — 7 days after due  →  escalation flagged

Channels: email + SMS + WhatsApp (where configured).

Escalation: users with 3 failed reminder cycles are surfaced in the
escalation report accessible from the monitoring page.
"""
import os
import uuid
import datetime
from typing import Optional

from database.snowflake_client import db
from services.notification_service import (
    notify_user, email_payment_reminder, send_sms, send_whatsapp,
)

# Map plan → USD monthly price  (keep in sync with payment service)
PLAN_PRICES = {
    "free":       0.00,
    "pro":       29.00,
    "enterprise": 99.00,
}

# Days before/after due to send reminders
PRE_DUE_DAYS  = [7, 3, 1]      # days_until_due > 0
POST_DUE_DAYS = [1, 3, 7]      # days_past_due > 0  →  reminders 1, 2, 3


def _reminder_already_sent(user_id: str, reminder_type: str) -> bool:
    """
    Prevent duplicate sends within the same calendar day.
    """
    today = datetime.date.today().isoformat()
    rows = db.execute(
        "SELECT reminder_id FROM payment_reminders "
        "WHERE user_id = ? AND reminder_type = ? AND sent_at >= ?",
        (user_id, reminder_type, today + "T00:00:00"),
    )
    return bool(rows)


def _log_reminder(user_id: str, reminder_type: str, channel: str,
                   due_date: str, amount: float, status: str):
    db.execute(
        "INSERT INTO payment_reminders "
        "(reminder_id, user_id, reminder_type, channel, status, due_date, amount) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, reminder_type, channel, status, due_date, amount),
    )


def _notify(user: dict, subject: str, html: str, sms_text: str,
             reminder_type: str, due_date: str, amount: float):
    """Send across all channels and log each."""
    uid    = user["user_id"]
    email  = user["email"]
    mobile = user.get("mobile")
    name   = user.get("full_name") or "Valued Customer"

    # Email
    ok = email_payment_reminder(
        email, uid, name, user.get("plan", "free"), due_date, amount,
        user.get("_days_until", 0), user.get("_reminder_num", 1),
    )
    _log_reminder(uid, reminder_type, "email", due_date, amount, "sent" if ok else "failed")

    # SMS
    if mobile:
        ok_sms = send_sms(mobile, sms_text, uid)
        _log_reminder(uid, reminder_type, "sms", due_date, amount, "sent" if ok_sms else "failed")
        ok_wa = send_whatsapp(mobile, sms_text, uid)
        _log_reminder(uid, reminder_type, "whatsapp", due_date, amount, "sent" if ok_wa else "failed")


def run_payment_reminders():
    """
    Called by the scheduler once per day.
    Iterates all active paid subscriptions and fires reminders as needed.
    """
    today = datetime.date.today()
    print(f"[reminders] Running payment reminder cycle — {today.isoformat()}")

    # Fetch paid subscribers with their renewal date stored in subscriptions table
    subs = db.execute(
        "SELECT s.subscription_id, s.user_id, s.plan, s.next_billing_date, "
        "       s.status, u.email, u.mobile, u.full_name "
        "FROM subscriptions s "
        "JOIN users u ON s.user_id = u.user_id "
        "WHERE s.plan IN ('pro','enterprise') AND s.status IN ('active','past_due')"
    ) or []

    sent_count = 0
    for sub in subs:
        if not sub.get("next_billing_date"):
            continue

        try:
            due = datetime.date.fromisoformat(str(sub["next_billing_date"])[:10])
        except ValueError:
            continue

        days_until = (due - today).days
        amount     = PLAN_PRICES.get(sub.get("plan", "free"), 0)
        due_str    = due.isoformat()
        user       = dict(sub)

        # ── Pre-due reminders ────────────────────────────────────────────────
        if days_until in PRE_DUE_DAYS:
            rtype = f"pre_due_{days_until}d"
            if not _reminder_already_sent(sub["user_id"], rtype):
                user["_days_until"]  = days_until
                user["_reminder_num"] = 0
                sms = (
                    f"💳 WebBuilder: Your {sub['plan']} plan payment of ${amount:.2f} "
                    f"is due in {days_until} day(s) on {due_str}. "
                    f"Manage billing at websitebuilder.ai/billing"
                )
                _notify(user, "", "", sms, rtype, due_str, amount)
                sent_count += 1
                print(f"[reminders] Pre-due notice ({days_until}d) → {sub['email']}")

        # ── Post-due follow-up reminders ─────────────────────────────────────
        elif days_until < 0:
            days_past = abs(days_until)
            for num, threshold in enumerate(POST_DUE_DAYS, start=1):
                if days_past == threshold:
                    rtype = f"overdue_reminder_{num}"
                    if not _reminder_already_sent(sub["user_id"], rtype):
                        user["_days_until"]  = days_until
                        user["_reminder_num"] = num
                        sms = (
                            f"⚠️ WebBuilder: Payment overdue! Your {sub['plan']} plan "
                            f"(${amount:.2f}) was due on {due_str}. "
                            f"Reminder {num}/3. Pay at websitebuilder.ai/billing"
                        )
                        _notify(user, "", "", sms, rtype, due_str, amount)
                        sent_count += 1
                        print(f"[reminders] Overdue reminder #{num} → {sub['email']}")

                        # After reminder #3: mark subscription as defaulted
                        if num == 3:
                            db.execute(
                                "UPDATE subscriptions SET status='defaulted' "
                                "WHERE subscription_id=?",
                                (sub["subscription_id"],),
                            )
                            print(f"[reminders] 🚨 Escalated to DEFAULT: {sub['email']}")

    print(f"[reminders] Done — {sent_count} reminder(s) sent.")


def get_defaulters() -> list:
    """Return users whose subscriptions have been escalated to 'defaulted'."""
    return db.execute(
        "SELECT s.subscription_id, s.user_id, s.plan, s.next_billing_date, "
        "       s.status, u.email, u.full_name, u.mobile, "
        "       COUNT(r.reminder_id) AS reminders_sent "
        "FROM subscriptions s "
        "JOIN users u ON s.user_id = u.user_id "
        "LEFT JOIN payment_reminders r ON r.user_id = s.user_id "
        "WHERE s.status = 'defaulted' "
        "GROUP BY s.subscription_id, s.user_id, s.plan, s.next_billing_date, "
        "         s.status, u.email, u.full_name, u.mobile "
        "ORDER BY s.next_billing_date ASC"
    ) or []


def get_reminder_history(user_id: Optional[str] = None) -> list:
    if user_id:
        return db.execute(
            "SELECT * FROM payment_reminders WHERE user_id = ? ORDER BY sent_at DESC LIMIT 100",
            (user_id,),
        ) or []
    return db.execute(
        "SELECT r.*, u.email, u.full_name "
        "FROM payment_reminders r JOIN users u ON r.user_id = u.user_id "
        "ORDER BY r.sent_at DESC LIMIT 500"
    ) or []
