"""
Analytics / activity-tracking service.
Logs every meaningful user/website event to Snowflake.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from database.snowflake_client import db


def log_event(
    event: str,
    user_id: Optional[str] = None,
    website_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    country: Optional[str] = None,
) -> None:
    """Insert an activity log row (best-effort, never raises)."""
    import json
    try:
        db.execute(
            """INSERT INTO activity_log
               (user_id, website_id, event, meta, ip_address, country)
               VALUES (%s, %s, %s, PARSE_JSON(%s), %s, %s)""",
            (
                user_id,
                website_id,
                event,
                json.dumps(meta or {}),
                ip_address,
                country,
            ),
        )
    except Exception as exc:
        print(f"[analytics] log_event failed silently: {exc}")


def get_user_activity(user_id: str, limit: int = 50):
    return db.execute(
        """SELECT event, website_id, ip_address, country, created_at
           FROM activity_log
           WHERE user_id = %s
           ORDER BY created_at DESC
           LIMIT %s""",
        (user_id, limit),
    )


def get_website_activity(website_id: str, limit: int = 100):
    return db.execute(
        """SELECT event, user_id, ip_address, country, meta, created_at
           FROM activity_log
           WHERE website_id = %s
           ORDER BY created_at DESC
           LIMIT %s""",
        (website_id, limit),
    )
