"""
Team / sub-user management.
The application owner can create sub-users with restricted page access.
Sub-users share the owner's website data but can only see permitted pages.
"""
import uuid
import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional

from api.routes.auth import get_current_user, require_app_user_or_above
from database.snowflake_client import db
from services.auth_service import hash_password

router = APIRouter(prefix="/team", tags=["team"])
logger = logging.getLogger("website_builder.team")

ALLOWED_PAGES = {
    "overview", "websites", "build", "cart-items", "billing",
    "monitoring", "feedback", "team", "notifications", "coupons",
}


# ── Schemas ────────────────────────────────────────────────────────────────────

class SubUserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str
    permissions: List[str] = ["overview", "websites", "cart-items"]


class SubUserPermissions(BaseModel):
    permissions: List[str]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _validate_permissions(perms: List[str]):
    invalid = set(perms) - ALLOWED_PAGES
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid permission(s): {sorted(invalid)}")


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("")
async def list_sub_users(current: dict = Depends(require_app_user_or_above)):
    rows = db.execute(
        "SELECT user_id, email, full_name, permissions, is_verified, created_at "
        "FROM users WHERE owner_id = ?",
        (current["sub"],),
    )
    for r in (rows or []):
        try:
            r["permissions"] = json.loads(r.get("permissions") or "[]")
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.debug("Invalid team permissions JSON for user_id=%s: %s", r.get("user_id"), exc)
            r["permissions"] = []
    return rows or []


@router.post("")
async def create_sub_user(body: SubUserCreate, current: dict = Depends(require_app_user_or_above)):
    _validate_permissions(body.permissions)
    existing = db.fetchone("SELECT user_id FROM users WHERE email = ?", (body.email,))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    sub_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users "
        "(user_id, email, password_hash, full_name, is_verified, plan, owner_id, permissions) "
        "VALUES (?, ?, ?, ?, 1, 'member', ?, ?)",
        (sub_id, body.email, hash_password(body.password),
         body.full_name or "", current["sub"], json.dumps(body.permissions)),
    )
    return {"user_id": sub_id, "message": "Team member created"}


@router.patch("/{user_id}/permissions")
async def update_permissions(user_id: str, body: SubUserPermissions,
                              current: dict = Depends(require_app_user_or_above)):
    _validate_permissions(body.permissions)
    sub = db.fetchone(
        "SELECT user_id FROM users WHERE user_id = ? AND owner_id = ?",
        (user_id, current["sub"]),
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Team member not found")
    db.execute(
        "UPDATE users SET permissions = ? WHERE user_id = ?",
        (json.dumps(body.permissions), user_id),
    )
    return {"message": "Permissions updated"}


@router.delete("/{user_id}")
async def remove_sub_user(user_id: str, current: dict = Depends(require_app_user_or_above)):
    sub = db.fetchone(
        "SELECT user_id FROM users WHERE user_id = ? AND owner_id = ?",
        (user_id, current["sub"]),
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Team member not found")
    db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    return {"message": "Team member removed"}
