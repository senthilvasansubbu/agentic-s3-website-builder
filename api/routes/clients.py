"""
Clients API — app_users create and manage their client users.

A *client* is an end-business owner who has been onboarded by an app_user.
Each client is linked to exactly one website (client_website_id) and can:
  • View / edit their website content
  • Monitor their website stats and feedback
  • Manage products on their website

Clients CANNOT build new websites, manage billing, or see other clients.
"""
import json as _json
import logging
import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from api.routes.auth import get_current_user, require_app_user_or_above
from database.snowflake_client import db
from services.auth_service import hash_password

router = APIRouter(prefix="/clients", tags=["clients"])
logger = logging.getLogger("website_builder.clients")


# ── Schemas ────────────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    website_id: str                        # the website this client manages
    permissions: Optional[List[str]] = None  # e.g. ["products", "monitoring"]


class ClientUpdate(BaseModel):
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
async def list_clients(
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    current: dict = Depends(require_app_user_or_above),
):
    """List client users onboarded by the current app_user (paginated)."""
    offset = (page - 1) * limit
    user_id = current["sub"]

    total_row = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM users WHERE role = 'client' AND owner_id = %s",
        (user_id,),
    )
    total = total_row["cnt"] if total_row else 0

    rows = db.fetchall(
        """SELECT u.user_id, u.email, u.full_name, u.mobile,
                  u.client_website_id, u.permissions, u.is_active, u.created_at,
                  w.name AS website_name, w.domain
           FROM users u
           LEFT JOIN websites w ON w.website_id = u.client_website_id
           WHERE u.role = 'client' AND u.owner_id = %s
           ORDER BY u.created_at DESC LIMIT %s OFFSET %s""",
        (user_id, limit, offset),
    )
    items = rows or []
    for r in items:
        try:
            r["permissions"] = _json.loads(r.get("permissions") or "[]")
        except (_json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.debug("Invalid permissions JSON for client row %s: %s", r.get("user_id"), exc)
            r["permissions"] = []
    return {
        "items": items,
        "total": total,
        "page":  page,
        "pages": max(1, -(-total // limit)),  # ceil division
    }


@router.post("/", status_code=201)
async def create_client(
    body: ClientCreate,
    current: dict = Depends(require_app_user_or_above),
):
    """Onboard a new client user tied to a specific website."""
    # Verify the website belongs to this app_user
    website = db.fetchone(
        "SELECT website_id FROM websites WHERE website_id=? AND user_id=?",
        (body.website_id, current["sub"]),
    )
    if not website:
        raise HTTPException(status_code=404, detail="Website not found or not owned by you")

    if db.fetchone("SELECT user_id FROM users WHERE email=?", (body.email,)):
        raise HTTPException(status_code=409, detail="Email already registered")

    client_id = str(uuid.uuid4())
    perms = _json.dumps(body.permissions or ["monitoring", "feedback"])
    db.execute(
        """INSERT INTO users
               (user_id, email, password_hash, full_name, mobile,
                role, owner_id, client_website_id, permissions, is_verified, is_active)
           VALUES (?, ?, ?, ?, ?, 'client', ?, ?, ?, 1, 1)""",
        (client_id, body.email, hash_password(body.password),
         body.full_name or "", body.mobile or "",
         current["sub"], body.website_id, perms),
    )
    return {"client_id": client_id, "message": "Client user created"}


@router.get("/{client_id}")
async def get_client(
    client_id: str,
    current: dict = Depends(require_app_user_or_above),
):
    row = db.fetchone(
        """SELECT u.user_id, u.email, u.full_name, u.mobile,
                  u.client_website_id, u.permissions, u.is_active, u.created_at,
                  w.name AS website_name, w.domain
           FROM users u
           LEFT JOIN websites w ON w.website_id = u.client_website_id
           WHERE u.user_id=? AND u.role='client' AND u.owner_id=?""",
        (client_id, current["sub"]),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    try:
        row["permissions"] = _json.loads(row.get("permissions") or "[]")
    except (_json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.debug("Invalid permissions JSON for client %s: %s", client_id, exc)
        row["permissions"] = []
    return row


@router.patch("/{client_id}")
async def update_client(
    client_id: str,
    body: ClientUpdate,
    current: dict = Depends(require_app_user_or_above),
):
    if not db.fetchone(
        "SELECT user_id FROM users WHERE user_id=? AND role='client' AND owner_id=?",
        (client_id, current["sub"]),
    ):
        raise HTTPException(status_code=404, detail="Client not found")

    updates, params = [], []
    if body.full_name is not None:
        updates.append("full_name=?"); params.append(body.full_name)
    if body.mobile is not None:
        updates.append("mobile=?"); params.append(body.mobile)
    if body.permissions is not None:
        updates.append("permissions=?"); params.append(_json.dumps(body.permissions))
    if body.is_active is not None:
        updates.append("is_active=?"); params.append(1 if body.is_active else 0)

    if updates:
        params.append(client_id)
        db.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id=?", params)
    return {"message": "Client updated"}


# ── Platform service permissions ───────────────────────────────────────────────

# The 4 platform products an app_user can grant to a client
PLATFORM_SERVICES = ["build", "monitoring", "notifications", "feedback"]


class ServiceUpdate(BaseModel):
    service: str
    enabled: bool


@router.get("/{client_id}/services")
async def get_client_services(
    client_id: str,
    current: dict = Depends(require_app_user_or_above),
):
    """Return the current platform service permissions for a client."""
    row = db.fetchone(
        "SELECT permissions FROM users WHERE user_id=? AND role='client' AND owner_id=?",
        (client_id, current["sub"]),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    try:
        perms = _json.loads(row.get("permissions") or "[]")
    except (_json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.debug("Invalid permissions JSON for client %s: %s", client_id, exc)
        perms = []
    return {
        "client_id": client_id,
        "services": {s: s in perms for s in PLATFORM_SERVICES},
    }


@router.patch("/{client_id}/services")
async def update_client_service(
    client_id: str,
    body: ServiceUpdate,
    current: dict = Depends(require_app_user_or_above),
):
    """Enable or disable a single platform service for a client."""
    if body.service not in PLATFORM_SERVICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown service '{body.service}'. Valid: {PLATFORM_SERVICES}",
        )
    row = db.fetchone(
        "SELECT permissions FROM users WHERE user_id=? AND role='client' AND owner_id=?",
        (client_id, current["sub"]),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")

    try:
        perms: list = _json.loads(row.get("permissions") or "[]")
    except (_json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.debug("Invalid permissions JSON for client service update %s: %s", client_id, exc)
        perms = []

    if body.enabled and body.service not in perms:
        perms.append(body.service)
    elif not body.enabled and body.service in perms:
        perms.remove(body.service)

    db.execute(
        "UPDATE users SET permissions=? WHERE user_id=?",
        [_json.dumps(perms), client_id],
    )
    return {
        "client_id": client_id,
        "service": body.service,
        "enabled": body.enabled,
        "services": {s: s in perms for s in PLATFORM_SERVICES},
    }


@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    current: dict = Depends(require_app_user_or_above),
):
    if not db.fetchone(
        "SELECT user_id FROM users WHERE user_id=? AND role='client' AND owner_id=?",
        (client_id, current["sub"]),
    ):
        raise HTTPException(status_code=404, detail="Client not found")
    db.execute("DELETE FROM users WHERE user_id=?", [client_id])
    return {"message": "Client deleted"}
