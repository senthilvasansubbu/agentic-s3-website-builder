"""
Admin / analytics routes — customer overview, activity logs, platform stats.
"""
from fastapi import APIRouter, Depends, HTTPException
from api.routes.auth import get_current_user
from database.snowflake_client import db
from services.analytics_service import get_user_activity

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(current_user: dict = Depends(get_current_user)):
    """Only enterprise users can access admin routes."""
    user = db.fetchone("SELECT plan FROM users WHERE user_id = %s", (current_user["sub"],))
    if not user or user["plan"] not in ("enterprise",):
        raise HTTPException(status_code=403, detail="Admin access requires Enterprise plan")
    return current_user


@router.get("/customers")
async def list_customers(limit: int = 50, _=Depends(_require_admin)):
    return db.execute(
        "SELECT user_id, email, full_name, plan, is_verified, created_at FROM users ORDER BY created_at DESC LIMIT %s",
        (limit,),
    )


@router.get("/activity")
async def platform_activity(limit: int = 100, _=Depends(_require_admin)):
    return db.execute(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT %s", (limit,)
    )


@router.get("/stats")
async def platform_stats(_=Depends(_require_admin)):
    total_users = db.fetchone("SELECT COUNT(*) AS cnt FROM users")
    total_sites = db.fetchone("SELECT COUNT(*) AS cnt FROM websites")
    live_sites  = db.fetchone("SELECT COUNT(*) AS cnt FROM websites WHERE status = 'live'")
    free_users  = db.fetchone("SELECT COUNT(*) AS cnt FROM users WHERE plan = 'free'")
    pro_users   = db.fetchone("SELECT COUNT(*) AS cnt FROM users WHERE plan = 'pro'")
    ent_users   = db.fetchone("SELECT COUNT(*) AS cnt FROM users WHERE plan = 'enterprise'")
    return {
        "total_users":        total_users["cnt"] if total_users else 0,
        "total_websites":     total_sites["cnt"] if total_sites else 0,
        "live_websites":      live_sites["cnt"] if live_sites else 0,
        "free_plan_users":    free_users["cnt"] if free_users else 0,
        "pro_plan_users":     pro_users["cnt"] if pro_users else 0,
        "enterprise_users":   ent_users["cnt"] if ent_users else 0,
    }


@router.get("/my-activity")
async def my_activity(limit: int = 50, current_user: dict = Depends(get_current_user)):
    return get_user_activity(current_user["sub"], limit)
