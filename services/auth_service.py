"""
Authentication service — password hashing, JWT tokens, OTP generation/verification.
"""
import os
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from database.snowflake_client import db

ALGORITHM  = "HS256"
TOKEN_TTL  = int(os.getenv("JWT_TTL_MINUTES", "1440"))  # 24 h


def _get_jwt_secret() -> str:
    secret = (os.getenv("JWT_SECRET") or "").strip()
    # Reject empty/default values to prevent token forgery with known secrets.
    if not secret or secret.lower() in {"change-me-in-production", "changeme", "default", "secret"}:
        raise RuntimeError(
            "JWT_SECRET is not configured securely. "
            "Set a strong, unique JWT_SECRET before starting the app."
        )
    return secret


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str, role: str = "app_user") -> str:
    payload = {
        "sub":   user_id,
        "email": email,
        "role":  role,
        "exp":   datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL),
        "iat":   datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _get_jwt_secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None
    except RuntimeError:
        return None


# ── OTP helpers ───────────────────────────────────────────────────────────────

def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def create_otp(user_id: str, channel: str) -> str:
    """Insert a fresh OTP; return the plaintext code."""
    code = _generate_otp()
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.execute(
        """INSERT INTO otp_tokens (user_id, otp_code, channel, expires_at)
           VALUES (%s, %s, %s, %s)""",
        (user_id, code, channel, expires),
    )
    return code


def verify_otp(user_id: str, code: str, channel: str) -> bool:
    """Return True and mark OTP used if valid; False otherwise."""
    row = db.fetchone(
        """SELECT token_id, expires_at, used
           FROM otp_tokens
           WHERE user_id = %s AND otp_code = %s AND channel = %s
             AND used = FALSE
           ORDER BY created_at DESC
           LIMIT 1""",
        (user_id, code, channel),
    )
    if not row:
        return False
    if datetime.now(timezone.utc) > row["expires_at"].replace(tzinfo=timezone.utc):
        return False
    db.execute(
        "UPDATE otp_tokens SET used = TRUE WHERE token_id = %s",
        (row["token_id"],),
    )
    return True
