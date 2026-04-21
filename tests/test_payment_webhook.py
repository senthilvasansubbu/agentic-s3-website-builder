"""
Tests for the Stripe payment webhook endpoint.

The webhook handler verifies a Stripe-Signature header before processing.
These tests confirm:
  - Missing / invalid signature → 400
  - customer.subscription.updated → plan updated in DB
  - customer.subscription.deleted → plan reset to 'free'
"""
import json
import uuid
from unittest.mock import patch


WEBHOOK_URL = "/api/v1/payments/webhook"


def _post_event(client, event: dict, sig: str = ""):
    return client.post(
        WEBHOOK_URL,
        content=json.dumps(event).encode(),
        headers={
            "Content-Type": "application/json",
            "stripe-signature": sig,
        },
    )


def test_webhook_missing_signature_returns_400(client):
    event = {"type": "customer.subscription.updated", "data": {"object": {}}}
    r = _post_event(client, event, sig="")
    # verify_webhook returns None for empty secret / bad sig → 400
    assert r.status_code == 400


def test_webhook_invalid_signature_returns_400(client):
    event = {"type": "customer.subscription.updated", "data": {"object": {}}}
    r = _post_event(client, event, sig="t=1,v1=badhash")
    assert r.status_code == 400


def test_webhook_subscription_updated_changes_plan(client, _in_memory_db):
    """With a mocked verify_webhook, subscription.updated should update the user plan."""
    uid = str(uuid.uuid4())
    cust_id = f"cus_{uid[:12]}"
    _in_memory_db.execute(
        "INSERT INTO users (user_id, email, password_hash, stripe_customer_id, role, is_verified) VALUES (?, ?, 'x', ?, 'app_user', 1)",
        (uid, f"wh_{uid[:8]}@example.com", cust_id),
    )

    stripe_event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "customer": cust_id,
                "id": "sub_test123",
                "metadata": {"plan": "pro"},
            }
        },
    }

    with patch("api.routes.payment.verify_webhook", return_value=stripe_event):
        r = _post_event(client, stripe_event, sig="valid-mocked")

    assert r.status_code == 200
    user = _in_memory_db.fetchone("SELECT plan FROM users WHERE user_id = ?", (uid,))
    assert user["plan"] == "pro"


def test_webhook_subscription_deleted_resets_to_free(client, _in_memory_db):
    """customer.subscription.deleted should reset user plan to 'free'."""
    uid = str(uuid.uuid4())
    cust_id = f"cus_{uid[:12]}"
    _in_memory_db.execute(
        "INSERT INTO users (user_id, email, password_hash, stripe_customer_id, plan, role, is_verified) VALUES (?, ?, 'x', ?, 'pro', 'app_user', 1)",
        (uid, f"whdel_{uid[:8]}@example.com", cust_id),
    )

    stripe_event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": cust_id}},
    }

    with patch("api.routes.payment.verify_webhook", return_value=stripe_event):
        r = _post_event(client, stripe_event, sig="valid-mocked")

    assert r.status_code == 200
    user = _in_memory_db.fetchone("SELECT plan FROM users WHERE user_id = ?", (uid,))
    assert user["plan"] == "free"
