import uuid

import pytest


def test_finalize_image_requires_authentication(client):
    r = client.post(
        "/api/v1/shop/finalize-image",
        json={
            "website_id": "site-1",
            "site_slug": "site-1",
            "filename": "image.webp",
        },
    )
    assert r.status_code == 401


def test_finalize_image_forbidden_for_non_owner(client, verified_user, _in_memory_db):
    website_id = str(uuid.uuid4())
    other_owner = str(uuid.uuid4())
    _in_memory_db.execute(
        """INSERT INTO websites (website_id, user_id, name)
           VALUES (?, ?, ?)""",
        (website_id, other_owner, "Other Owner Site"),
    )

    r = client.post(
        "/api/v1/shop/finalize-image",
        headers={"Authorization": f"Bearer {verified_user['token']}"},
        json={
            "website_id": website_id,
            "site_slug": "site-1",
            "filename": "image.webp",
        },
    )
    assert r.status_code == 403


def test_startup_validation_requires_openai_key_unless_override(monkeypatch):
    from app import _validate_startup_configuration

    monkeypatch.setenv("JWT_SECRET", "strong-test-secret")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ALLOW_MISSING_OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        _validate_startup_configuration()

    monkeypatch.setenv("ALLOW_MISSING_OPENAI_API_KEY", "true")
    _validate_startup_configuration()


def test_auth_service_rejects_default_jwt_secret(monkeypatch):
    from services.auth_service import create_access_token

    monkeypatch.setenv("JWT_SECRET", "change-me-in-production")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        create_access_token("u1", "u1@example.com")


def test_coupon_update_still_works_with_allowlisted_fields(client, verified_user, _in_memory_db):
    website_id = str(uuid.uuid4())
    coupon_id = str(uuid.uuid4())
    _in_memory_db.execute(
        """CREATE TABLE IF NOT EXISTS coupons (
               coupon_id TEXT PRIMARY KEY,
               website_id TEXT NOT NULL,
               code TEXT,
               discount_type TEXT,
               discount_value REAL,
               min_order REAL,
               max_uses INTEGER,
               valid_from TEXT,
               valid_until TEXT,
               is_active INTEGER DEFAULT 1,
               created_at DATETIME DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    _in_memory_db.execute(
        """INSERT INTO websites (website_id, user_id, name)
           VALUES (?, ?, ?)""",
        (website_id, verified_user["user_id"], "Owned Site"),
    )
    _in_memory_db.execute(
        """INSERT INTO coupons (coupon_id, website_id, code, discount_type, discount_value, min_order, max_uses, valid_from, valid_until, is_active)
           VALUES (?, ?, 'SAVE10', 'percent', 10, 0, 0, '', '', 1)""",
        (coupon_id, website_id),
    )

    r = client.patch(
        f"/api/v1/commerce/coupons/{coupon_id}",
        headers={"Authorization": f"Bearer {verified_user['token']}"},
        json={"discount_value": 25},
    )
    assert r.status_code == 200

    row = _in_memory_db.fetchone(
        "SELECT discount_value FROM coupons WHERE coupon_id = ?",
        (coupon_id,),
    )
    assert float(row["discount_value"]) == 25.0
