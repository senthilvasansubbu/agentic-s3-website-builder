"""Console API — superuser-only admin endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid, datetime

from api.routes.auth import get_current_user, require_superuser as _require_superuser
from database.snowflake_client import db
from services.auth_service import hash_password, create_access_token

router = APIRouter(prefix="/admin", tags=["admin-console"])


# ── App-user management (superuser only) ──────────────────────────────────────

class AppUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    plan: str = "free"


@router.get("/app-users")
async def list_app_users(
    limit: int = Query(100, ge=1, le=1000),
    current=Depends(_require_superuser),
):
    """List all app_user accounts."""
    rows = db.execute(
        "SELECT user_id, email, full_name, mobile, plan, is_verified, is_active, created_at "
        "FROM users WHERE role='app_user' ORDER BY created_at DESC LIMIT ?",
        [limit],
    )
    return rows or []


@router.post("/app-users", status_code=201)
async def create_app_user(body: AppUserCreate, current=Depends(_require_superuser)):
    """Create a new app_user account (superuser-initiated)."""
    if db.fetchone("SELECT user_id FROM users WHERE email=?", (body.email,)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO users (user_id, email, password_hash, full_name, mobile,
                              role, plan, is_verified, is_active)
           VALUES (?, ?, ?, ?, ?, 'app_user', ?, 1, 1)""",
        (user_id, body.email, hash_password(body.password),
         body.full_name or "", body.mobile or "", body.plan),
    )
    return {"user_id": user_id, "message": "App user created"}


@router.patch("/app-users/{user_id}/deactivate")
async def deactivate_app_user(user_id: str, current=Depends(_require_superuser)):
    if not db.fetchone("SELECT user_id FROM users WHERE user_id=? AND role='app_user'", (user_id,)):
        raise HTTPException(status_code=404, detail="App user not found")
    db.execute("UPDATE users SET is_active=0 WHERE user_id=?", [user_id])
    return {"message": "App user deactivated"}


@router.patch("/app-users/{user_id}/activate")
async def activate_app_user(user_id: str, current=Depends(_require_superuser)):
    if not db.fetchone("SELECT user_id FROM users WHERE user_id=? AND role='app_user'", (user_id,)):
        raise HTTPException(status_code=404, detail="App user not found")
    db.execute("UPDATE users SET is_active=1 WHERE user_id=?", [user_id])
    return {"message": "App user activated"}


@router.delete("/app-users/{user_id}")
async def delete_app_user(user_id: str, current=Depends(_require_superuser)):
    if not db.fetchone("SELECT user_id FROM users WHERE user_id=? AND role='app_user'", (user_id,)):
        raise HTTPException(status_code=404, detail="App user not found")
    db.execute("DELETE FROM users WHERE user_id=? OR owner_id=?", [user_id, user_id])
    return {"message": "App user and their clients deleted"}


# ── Stats ─────────────────────────────────────────────────────────────────────
@router.get("/stats")
async def get_stats(current=Depends(_require_superuser)):
    users_row    = db.execute("SELECT COUNT(*) AS c FROM users WHERE plan != 'superuser'")
    websites_row = db.execute("SELECT COUNT(*) AS c FROM websites")
    live_row     = db.execute("SELECT COUNT(*) AS c FROM websites WHERE status='live'")
    pro_row      = db.execute("SELECT COUNT(*) AS c FROM users WHERE plan IN ('pro','enterprise')")
    return {
        "total_users":      (users_row    or [{}])[0].get("c", 0),
        "total_websites":   (websites_row or [{}])[0].get("c", 0),
        "live_websites":    (live_row     or [{}])[0].get("c", 0),
        "pro_plan_users":   (pro_row      or [{}])[0].get("c", 0),
    }


# ── Customers ─────────────────────────────────────────────────────────────────
@router.get("/customers")
async def list_customers(
    limit: int = Query(50, ge=1, le=500),
    current=Depends(_require_superuser),
):
    rows = db.execute(
        "SELECT user_id, email, full_name, plan, is_verified, created_at "
        "FROM users WHERE plan != 'superuser' ORDER BY created_at DESC LIMIT ?",
        [limit],
    )
    return rows or []


# ── Activity ──────────────────────────────────────────────────────────────────
@router.get("/activity")
async def list_activity(
    limit: int = Query(50, ge=1, le=500),
    current=Depends(_require_superuser),
):
    rows = db.execute(
        "SELECT event, user_id, website_id, ip_address, country, created_at "
        "FROM activity_log ORDER BY created_at DESC LIMIT ?",
        [limit],
    )
    return rows or []


# ── Websites (all) ────────────────────────────────────────────────────────────
@router.get("/websites")
async def list_all_websites(current=Depends(_require_superuser)):
    rows = db.execute(
        "SELECT website_id, user_id, name, title, theme, status, domain, s3_url, created_at "
        "FROM websites ORDER BY created_at DESC"
    )
    return rows or []


# ── Verify user ───────────────────────────────────────────────────────────────
@router.post("/verify-user/{user_id}")
async def admin_verify_user(user_id: str, current=Depends(_require_superuser)):
    db.execute(
        "UPDATE users SET is_verified=1 WHERE user_id=?", [user_id]
    )
    return {"message": "User verified"}


# ── Set plan ──────────────────────────────────────────────────────────────────
@router.post("/set-plan/{user_id}/{plan}")
async def set_user_plan(user_id: str, plan: str, current=Depends(_require_superuser)):
    allowed = ("free", "pro", "enterprise")
    if plan not in allowed:
        raise HTTPException(status_code=400, detail=f"Plan must be one of: {allowed}")
    db.execute("UPDATE users SET plan=? WHERE user_id=?", [plan, user_id])
    return {"message": f"Plan updated to {plan}"}


# ── Create workspace for user ─────────────────────────────────────────────────
class WorkspaceCreate(BaseModel):
    name: str
    title: Optional[str] = None
    theme: str = "modern"
    domain: Optional[str] = None
    hosting_env: str = "local"
    include_shopping_cart: bool = False
    content_depth: str = 'standard'


@router.post("/create-workspace/{user_id}")
async def create_workspace(
    user_id: str,
    body: WorkspaceCreate,
    current=Depends(_require_superuser),
):
    check = db.execute("SELECT user_id FROM users WHERE user_id=?", [user_id])
    if not check:
        raise HTTPException(status_code=404, detail="User not found")

    website_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO websites (website_id, user_id, name, title, theme, domain, status, hosting_env, content_depth, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [website_id, user_id, body.name, body.title or body.name, body.theme,
         body.domain, "draft", body.hosting_env, body.content_depth, now, now],
    )
    return {"website_id": website_id, "message": "Workspace created"}


# ── Change admin password ─────────────────────────────────────────────────────
class PasswordChange(BaseModel):
    new_password: str


@router.post("/change-password")
async def change_password(body: PasswordChange, current=Depends(get_current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    hashed = hash_password(body.new_password)
    db.execute(
        "UPDATE users SET password_hash=? WHERE user_id=?",
        [hashed, current["sub"]],
    )
    return {"message": "Password updated successfully"}


# ── All feedback ──────────────────────────────────────────────────────────────
@router.get("/feedback")
async def list_all_feedback(current=Depends(_require_superuser)):
    rows = db.execute(
        "SELECT feedback_id, website_id, name, email, rating, message, created_at "
        "FROM feedback ORDER BY created_at DESC LIMIT 200"
    )
    return rows or []
