"""
Auth API routes — register, verify OTP, login, get current user.

User hierarchy
──────────────
  superuser   Platform administrator. Can only create/manage app_users.
              Created once via scripts/create_superuser.py.
  app_user    Agency / SaaS operator. Builds & manages websites, onboards
              clients, manages billing.  Created via public registration.
  client      End-client user.  Created by an app_user for a specific website.
              Can customise their website content and view their own analytics.
  customer    Shopper on a client's website.  No dashboard access.
              Created via the storefront checkout flow.
"""
import json as _json
import uuid
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from database.snowflake_client import db
from services.auth_service import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
    create_otp, verify_otp,
)
from services.otp_service import deliver_otp
from services.analytics_service import log_event
from services.payment_service import create_stripe_customer

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

# Valid roles — ordered from most-privileged to least
ROLE_HIERARCHY = ["superuser", "app_user", "client", "customer"]

# Persistent website access exceptions for browser/testing workflows.
GLOBAL_WEBSITE_ACCESS_EMAILS = {"sayeesaran.s@gmail.com"}


# ── Dependencies ───────────────────────────────────────────────────────────────

def get_current_user(request: Request) -> dict:
    """Decode the Bearer JWT and return its payload dict.
    The payload always contains: sub, email, role."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    payload = decode_access_token(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    # Ensure role is always present (back-compat with tokens minted before role was added)
    if "role" not in payload:
        payload["role"] = "app_user"
    return payload


def has_global_website_access(current_user: dict) -> bool:
    email = str(current_user.get("email") or "").strip().lower()
    return current_user.get("role") == "superuser" or email in GLOBAL_WEBSITE_ACCESS_EMAILS


def require_roles(*allowed_roles: str):
    """
    FastAPI dependency factory.  Returns a dependency that raises 403 if the
    authenticated user's role is not in *allowed_roles*.

    Usage:
        current_user: dict = Depends(require_roles("superuser", "app_user"))
    """
    def _dep(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access restricted to {', '.join(allowed_roles)} roles.",
            )
        return current_user
    return _dep


# Convenience shorthands
def require_superuser(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "superuser":
        raise HTTPException(status_code=403, detail="Superuser access required.")
    return current_user


def require_app_user_or_above(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") not in ("superuser", "app_user"):
        raise HTTPException(status_code=403, detail="App-user access required.")
    return current_user


def require_client_or_above(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") not in ("superuser", "app_user", "client"):
        raise HTTPException(status_code=403, detail="Client access required.")
    return current_user


# ── Schemas ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    otp_channel: Literal["email", "sms"] = "email"


class VerifyOTPRequest(BaseModel):
    user_id: str
    otp_code: str
    channel: Literal["email", "sms"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register")
@limiter.limit("5/minute")
async def register(body: RegisterRequest, request: Request):
    """
    Public registration — creates an *app_user* account.
    Superusers are created via scripts/create_superuser.py.
    Clients are created by their app_user via POST /clients.
    Customers are created by the storefront checkout flow via POST /auth/register-customer.
    """
    existing = db.fetchone("SELECT user_id FROM users WHERE email = ?", (body.email,))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(body.password)
    db.execute(
        """INSERT INTO users (user_id, email, password_hash, full_name, mobile, role)
           VALUES (?, ?, ?, ?, ?, 'app_user')""",
        (user_id, body.email, pw_hash, body.full_name or "", body.mobile or ""),
    )

    # Create Stripe customer
    stripe_id = create_stripe_customer(body.email, body.full_name or "")
    if stripe_id:
        db.execute(
            "UPDATE users SET stripe_customer_id = ? WHERE user_id = ?",
            (stripe_id, user_id),
        )

    # Send OTP
    destination = body.email if body.otp_channel == "email" else body.mobile
    if not destination:
        raise HTTPException(status_code=400, detail="Mobile required for SMS OTP")
    otp_code = create_otp(user_id, body.otp_channel)
    deliver_otp(body.otp_channel, destination, otp_code)

    log_event("user_registered", user_id=user_id, ip_address=request.client.host)
    return {"user_id": user_id, "message": f"OTP sent via {body.otp_channel}"}


@router.post("/register-customer")
async def register_customer(body: RegisterRequest, request: Request):
    """
    Storefront registration for end-customers (shoppers).
    Creates a *customer* role account — no dashboard access.
    """
    existing = db.fetchone("SELECT user_id FROM users WHERE email = ?", (body.email,))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(body.password)
    db.execute(
        """INSERT INTO users (user_id, email, password_hash, full_name, mobile, role, is_verified)
           VALUES (?, ?, ?, ?, ?, 'customer', 1)""",
        (user_id, body.email, pw_hash, body.full_name or "", body.mobile or ""),
    )
    log_event("customer_registered", user_id=user_id, ip_address=request.client.host)
    return {"user_id": user_id, "message": "Customer account created"}


@router.post("/verify-otp")
@limiter.limit("10/minute")
async def verify_otp_endpoint(body: VerifyOTPRequest, request: Request):
    ok = verify_otp(body.user_id, body.otp_code, body.channel)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    db.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (body.user_id,))
    log_event("user_verified", user_id=body.user_id, ip_address=request.client.host)
    return {"message": "Account verified successfully"}


@router.post("/login")
@limiter.limit("10/minute")
async def login(body: LoginRequest, request: Request):
    user = db.fetchone(
        """SELECT user_id, password_hash, full_name, is_verified, plan, role,
                  is_active, owner_id, client_website_id
           FROM users WHERE email = ?""",
        (body.email,),
    )
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user["is_verified"]:
        raise HTTPException(status_code=403, detail="Please verify your account first")
    if user.get("is_active") == 0:
        raise HTTPException(status_code=403, detail="Account is deactivated. Contact your administrator.")

    role = user.get("role") or "app_user"
    # Customers have no dashboard — they log in via the storefront
    if role == "customer":
        raise HTTPException(status_code=403, detail="Customers access the store directly, not the dashboard.")

    token = create_access_token(user["user_id"], body.email, role=role)
    log_event("user_login", user_id=user["user_id"], ip_address=request.client.host)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["user_id"],
        "role": role,
        "plan": user["plan"],
        "owner_id": user.get("owner_id"),
        "client_website_id": user.get("client_website_id"),
    }


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    user = db.fetchone(
        """SELECT user_id, email, full_name, mobile, plan, role,
                  owner_id, permissions, client_website_id, created_at
           FROM users WHERE user_id = ?""",
        (current_user["sub"],),
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user["permissions"] = _json.loads(user.get("permissions") or "[]")
    except Exception:
        user["permissions"] = []
    return user


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    user = db.fetchone(
        "SELECT password_hash FROM users WHERE user_id = ?",
        (current_user["sub"],),
    )
    if not user or not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    db.execute(
        "UPDATE users SET password_hash = ? WHERE user_id = ?",
        (hash_password(body.new_password), current_user["sub"]),
    )
    return {"message": "Password changed successfully"}

