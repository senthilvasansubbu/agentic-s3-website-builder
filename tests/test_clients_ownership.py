"""
Tests for cross-tenant ownership enforcement in /clients endpoints (issue #18).

Every mutating or read endpoint must return 404 (not 403 / raw data) when
a different app_user tries to access a client they do not own.
"""
import uuid
import pytest
from services.auth_service import hash_password, create_access_token


AUTH = lambda token: {"Authorization": f"Bearer {token}"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_app_user(db):
    """Insert a verified app_user and return (user_id, token)."""
    uid = str(uuid.uuid4())
    email = f"user_{uid[:8]}@example.com"
    db.execute(
        "INSERT INTO users (user_id, email, password_hash, role, is_verified, is_active) "
        "VALUES (?, ?, ?, 'app_user', 1, 1)",
        (uid, email, hash_password("Pass@1234")),
    )
    token = create_access_token(uid, email, role="app_user")
    return uid, token


def _make_website(db, owner_id):
    """Insert a website owned by owner_id and return website_id."""
    wid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO websites (website_id, user_id, name, theme, status) "
        "VALUES (?, ?, 'test-site', 'modern', 'draft')",
        (wid, owner_id),
    )
    return wid


def _make_client(db, owner_id, website_id):
    """Insert a client user belonging to owner_id and return client_id."""
    cid = str(uuid.uuid4())
    email = f"client_{cid[:8]}@example.com"
    db.execute(
        "INSERT INTO users "
        "(user_id, email, password_hash, role, owner_id, client_website_id, is_verified, is_active, permissions) "
        "VALUES (?, ?, ?, 'client', ?, ?, 1, 1, '[]')",
        (cid, email, hash_password("Pass@1234"), owner_id, website_id),
    )
    return cid


# ── Ownership tests ────────────────────────────────────────────────────────────

def test_get_client_cross_tenant_returns_404(client, _in_memory_db):
    """A different app_user cannot read another owner's client."""
    owner_id, _ = _make_app_user(_in_memory_db)
    attacker_id, attacker_token = _make_app_user(_in_memory_db)
    wid = _make_website(_in_memory_db, owner_id)
    cid = _make_client(_in_memory_db, owner_id, wid)

    r = client.get(f"/api/v1/clients/{cid}", headers=AUTH(attacker_token))
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


def test_patch_client_cross_tenant_returns_404(client, _in_memory_db):
    """A different app_user cannot update another owner's client."""
    owner_id, _ = _make_app_user(_in_memory_db)
    attacker_id, attacker_token = _make_app_user(_in_memory_db)
    wid = _make_website(_in_memory_db, owner_id)
    cid = _make_client(_in_memory_db, owner_id, wid)

    r = client.patch(
        f"/api/v1/clients/{cid}",
        json={"full_name": "Hacked Name"},
        headers=AUTH(attacker_token),
    )
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


def test_delete_client_cross_tenant_returns_404(client, _in_memory_db):
    """A different app_user cannot delete another owner's client."""
    owner_id, _ = _make_app_user(_in_memory_db)
    attacker_id, attacker_token = _make_app_user(_in_memory_db)
    wid = _make_website(_in_memory_db, owner_id)
    cid = _make_client(_in_memory_db, owner_id, wid)

    r = client.delete(f"/api/v1/clients/{cid}", headers=AUTH(attacker_token))
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


def test_get_client_services_cross_tenant_returns_404(client, _in_memory_db):
    """A different app_user cannot read service permissions of another owner's client."""
    owner_id, _ = _make_app_user(_in_memory_db)
    attacker_id, attacker_token = _make_app_user(_in_memory_db)
    wid = _make_website(_in_memory_db, owner_id)
    cid = _make_client(_in_memory_db, owner_id, wid)

    r = client.get(f"/api/v1/clients/{cid}/services", headers=AUTH(attacker_token))
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


def test_patch_client_services_cross_tenant_returns_404(client, _in_memory_db):
    """A different app_user cannot modify service permissions of another owner's client."""
    owner_id, _ = _make_app_user(_in_memory_db)
    attacker_id, attacker_token = _make_app_user(_in_memory_db)
    wid = _make_website(_in_memory_db, owner_id)
    cid = _make_client(_in_memory_db, owner_id, wid)

    r = client.patch(
        f"/api/v1/clients/{cid}/services",
        json={"service": "build", "enabled": True},
        headers=AUTH(attacker_token),
    )
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


def test_list_clients_only_returns_own(client, _in_memory_db):
    """GET /clients/ must return only clients owned by the requesting user."""
    owner_id, owner_token = _make_app_user(_in_memory_db)
    other_id, _ = _make_app_user(_in_memory_db)
    wid = _make_website(_in_memory_db, owner_id)
    own_cid = _make_client(_in_memory_db, owner_id, wid)

    wid2 = _make_website(_in_memory_db, other_id)
    _make_client(_in_memory_db, other_id, wid2)

    r = client.get("/api/v1/clients/", headers=AUTH(owner_token))
    assert r.status_code == 200
    ids = [item["user_id"] for item in r.json().get("items", [])]
    assert own_cid in ids, "Owner's client must appear in list"
    # Ensure no other-owner clients leaked into this response
    for item in r.json().get("items", []):
        assert item.get("owner_id") == owner_id or item.get("user_id") == own_cid, \
            f"Leaked cross-tenant client in list: {item}"
