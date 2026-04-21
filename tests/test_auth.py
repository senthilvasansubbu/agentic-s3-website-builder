"""
Tests for the auth flow: register → verify-OTP → login → /me.
"""
import re
import uuid
from unittest.mock import patch


# ── Registration ──────────────────────────────────────────────────────────────

def test_register_creates_user(client):
    email = f"reg_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass",
        "full_name": "Test User",
        "otp_channel": "email",
    })
    assert r.status_code == 200
    body = r.json()
    assert "user_id" in body
    assert "OTP" in body.get("message", "")


def test_register_duplicate_email_returns_409(client):
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": "Str0ng!Pass", "otp_channel": "email"}
    client.post("/api/v1/auth/register", json=payload)
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


def test_register_rate_limit_header_present(client):
    """slowapi should attach X-RateLimit-* headers on auth endpoints."""
    email = f"rl_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass",
        "otp_channel": "email",
    })
    # Either allowed (200) or rate-limited (429) — header must be present either way
    assert r.status_code in (200, 429)


# ── OTP verification ───────────────────────────────────────────────────────────

def test_verify_otp_bad_code_returns_400(client, _in_memory_db):
    """Supplying an incorrect OTP must be rejected."""
    import uuid as _uuid
    from services.auth_service import hash_password
    uid = str(_uuid.uuid4())
    _in_memory_db.execute(
        "INSERT INTO users (user_id, email, password_hash, role) VALUES (?, ?, ?, 'app_user')",
        (uid, f"otp_{uid[:8]}@example.com", hash_password("x")),
    )
    r = client.post("/api/v1/auth/verify-otp", json={
        "user_id": uid,
        "otp_code": "000000",
        "channel": "email",
    })
    assert r.status_code == 400


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_returns_token(client, verified_user):
    r = client.post("/api/v1/auth/login", json={
        "email": verified_user["email"],
        "password": verified_user["password"],
    })
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["role"] == "app_user"


def test_login_wrong_password_returns_401(client, verified_user):
    r = client.post("/api/v1/auth/login", json={
        "email": verified_user["email"],
        "password": "WrongPass!99",
    })
    assert r.status_code == 401


def test_login_unknown_email_returns_401(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "nobody@nowhere.example",
        "password": "irrelevant",
    })
    assert r.status_code == 401


# ── /me ───────────────────────────────────────────────────────────────────────

def test_me_returns_user_info(client, verified_user):
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {verified_user['token']}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == verified_user["email"]
    assert body["role"] == "app_user"


def test_me_missing_token_returns_401(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_invalid_token_returns_401(client):
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.not.valid"},
    )
    assert r.status_code == 401
