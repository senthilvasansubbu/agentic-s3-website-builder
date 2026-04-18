"""
Auth API routes — register, verify OTP, login, get current user.
"""
import uuid
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from typing import Literal, Optional

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


# ── Dependency: get current user from Bearer token ────────────────────────────

def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    payload = decode_access_token(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register")
async def register(body: RegisterRequest, request: Request):
    existing = db.fetchone("SELECT user_id FROM users WHERE email = ?", (body.email,))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(body.password)
    db.execute(
        """INSERT INTO users (user_id, email, password_hash, full_name, mobile)
           VALUES (?, ?, ?, ?, ?)""",
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


@router.post("/verify-otp")
async def verify_otp_endpoint(body: VerifyOTPRequest, request: Request):
    ok = verify_otp(body.user_id, body.otp_code, body.channel)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    db.execute("UPDATE users SET is_verified = TRUE WHERE user_id = ?", (body.user_id,))
    log_event("user_verified", user_id=body.user_id, ip_address=request.client.host)
    return {"message": "Account verified successfully"}


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    user = db.fetchone(
        "SELECT user_id, password_hash, full_name, is_verified, plan FROM users WHERE email = ?",
        (body.email,),
    )
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user["is_verified"]:
        raise HTTPException(status_code=403, detail="Please verify your account first")

    token = create_access_token(user["user_id"], body.email)
    log_event("user_login", user_id=user["user_id"], ip_address=request.client.host)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["user_id"],
        "plan": user["plan"],
    }


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    user = db.fetchone(
        "SELECT user_id, email, full_name, mobile, plan, created_at FROM users WHERE user_id = ?",
        (current_user["sub"],),
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
