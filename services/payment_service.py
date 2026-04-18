"""
Payment service — Stripe integration for:
  1. Platform subscriptions (free / pro / enterprise)
  2. Per-website storefront checkout
"""
import os
from typing import Optional, Dict, Any

import stripe

# Platform Stripe keys (for billing users of our platform)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# ── Subscription plans ─────────────────────────────────────────────────────────

PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "label": "Free",
        "price_usd": 0,
        "stripe_price_id": None,
        "max_pages": 10,
        "shopping_cart": False,
        "custom_domain": False,
        "analytics": False,
    },
    "pro": {
        "label": "Pro",
        "price_usd": 19,
        "stripe_price_id": os.getenv("STRIPE_PRO_PRICE_ID", ""),
        "max_pages": 50,
        "shopping_cart": True,
        "custom_domain": True,
        "analytics": True,
    },
    "enterprise": {
        "label": "Enterprise",
        "price_usd": 79,
        "stripe_price_id": os.getenv("STRIPE_ENTERPRISE_PRICE_ID", ""),
        "max_pages": 999,
        "shopping_cart": True,
        "custom_domain": True,
        "analytics": True,
    },
    "superuser": {
        "label": "Superuser",
        "price_usd": 0,
        "stripe_price_id": None,
        "max_pages": 9999,
        "shopping_cart": True,
        "custom_domain": True,
        "analytics": True,
    },
}


# ── Customer helpers ──────────────────────────────────────────────────────────

def create_stripe_customer(email: str, name: str = "") -> Optional[str]:
    """Create a Stripe customer and return the customer_id."""
    try:
        customer = stripe.Customer.create(email=email, name=name)
        return customer.id
    except stripe.StripeError as exc:
        print(f"[payment] create_customer error: {exc}")
        return None


# ── Platform subscription ─────────────────────────────────────────────────────

def create_subscription_checkout(
    stripe_customer_id: str, plan: str, success_url: str, cancel_url: str
) -> Optional[str]:
    """Create a Stripe Checkout Session for a platform subscription plan."""
    price_id = PLANS.get(plan, {}).get("stripe_price_id")
    if not price_id:
        return None
    try:
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url
    except stripe.StripeError as exc:
        print(f"[payment] subscription checkout error: {exc}")
        return None


# ── Storefront checkout (per-website) ─────────────────────────────────────────

def create_storefront_checkout(
    line_items: list,           # [{"name": str, "price": int (cents), "qty": int}]
    currency: str,
    success_url: str,
    cancel_url: str,
    stripe_secret_key: Optional[str] = None,  # website-specific key
) -> Optional[str]:
    """
    Create a Stripe Checkout Session for an end-customer buying from a storefront.
    Uses the website owner's Stripe secret key when provided.
    """
    key = stripe_secret_key or os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        return None
    try:
        formatted = [
            {
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {"name": item["name"]},
                    "unit_amount": int(float(item["price"]) * 100),
                },
                "quantity": item["qty"],
            }
            for item in line_items
        ]
        session = stripe.checkout.Session.create(
            api_key=key,
            mode="payment",
            line_items=formatted,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url
    except stripe.StripeError as exc:
        print(f"[payment] storefront checkout error: {exc}")
        return None


# ── Webhook verification ───────────────────────────────────────────────────────

def verify_webhook(payload: bytes, sig_header: str, secret: str) -> Optional[stripe.Event]:
    try:
        return stripe.Webhook.construct_event(payload, sig_header, secret)
    except (ValueError, stripe.SignatureVerificationError):
        return None
