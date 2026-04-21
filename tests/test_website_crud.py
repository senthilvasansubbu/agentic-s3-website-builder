"""
Tests for the website CRUD endpoints:
  POST   /api/v1/websites          — create
  GET    /api/v1/websites/{id}     — read (if such a route exists) or build-status
  PATCH  /api/v1/websites/{id}     — update
  DELETE /api/v1/websites/{id}     — delete
"""
import uuid


AUTH_HEADER = lambda token: {"Authorization": f"Bearer {token}"}

CREATE_PAYLOAD = {
    "name": "pytest-bakery",
    "title": "The Pytest Bakery",
    "description": "Fresh tests daily",
    "theme": "modern",
    "classification": "food",
    "num_pages": 1,
}


def test_create_website_returns_id(client, verified_user):
    r = client.post(
        "/api/v1/websites",
        json=CREATE_PAYLOAD,
        headers=AUTH_HEADER(verified_user["token"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert "website_id" in body


def test_create_website_unauthenticated_returns_401(client):
    r = client.post("/api/v1/websites", json=CREATE_PAYLOAD)
    assert r.status_code == 401


def test_create_website_unknown_theme_returns_400(client, verified_user):
    payload = {**CREATE_PAYLOAD, "theme": "does-not-exist"}
    r = client.post(
        "/api/v1/websites",
        json=payload,
        headers=AUTH_HEADER(verified_user["token"]),
    )
    assert r.status_code == 400


def _create_site(client, verified_user) -> str:
    r = client.post(
        "/api/v1/websites",
        json=CREATE_PAYLOAD,
        headers=AUTH_HEADER(verified_user["token"]),
    )
    assert r.status_code == 200
    return r.json()["website_id"]


def test_update_website_title(client, verified_user):
    wid = _create_site(client, verified_user)
    r = client.patch(
        f"/api/v1/websites/{wid}",
        json={"title": "Updated Title"},
        headers=AUTH_HEADER(verified_user["token"]),
    )
    assert r.status_code == 200


def test_update_website_nothing_to_update(client, verified_user):
    wid = _create_site(client, verified_user)
    r = client.patch(
        f"/api/v1/websites/{wid}",
        json={},
        headers=AUTH_HEADER(verified_user["token"]),
    )
    assert r.status_code == 200
    assert "Nothing" in r.json().get("message", "")


def test_delete_website(client, verified_user):
    wid = _create_site(client, verified_user)
    r = client.delete(
        f"/api/v1/websites/{wid}",
        headers=AUTH_HEADER(verified_user["token"]),
    )
    assert r.status_code == 200


def test_delete_website_other_user_returns_404(client, verified_user, _in_memory_db):
    """A user cannot delete another user's website."""
    from services.auth_service import hash_password, create_access_token
    uid2 = str(uuid.uuid4())
    email2 = f"other_{uid2[:8]}@example.com"
    _in_memory_db.execute(
        "INSERT INTO users (user_id, email, password_hash, role, is_verified, is_active) VALUES (?, ?, ?, 'app_user', 1, 1)",
        (uid2, email2, hash_password("Pass!999")),
    )
    token2 = create_access_token(uid2, email2, role="app_user")

    # Create a website as verified_user
    wid = _create_site(client, verified_user)

    # Try to delete as uid2
    r = client.delete(
        f"/api/v1/websites/{wid}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert r.status_code == 404


def test_build_status_unknown_website_returns_404(client, verified_user):
    fake_id = str(uuid.uuid4())
    r = client.get(
        f"/api/v1/websites/{fake_id}/build-status",
        headers=AUTH_HEADER(verified_user["token"]),
    )
    assert r.status_code == 404
