"""
Payment API routes — platform subscriptions + per-website storefront checkout.
"""
import os
import json
import uuid
import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel
from typing import Optional, List

from api.routes.auth import get_current_user
from database.snowflake_client import db
from services.payment_service import (
    PLANS,
    create_subscription_checkout,
    create_storefront_checkout,
    verify_webhook,
)
from services.analytics_service import log_event

router = APIRouter(prefix="/payments", tags=["payments"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class CheckoutItem(BaseModel):
    name: str
    price: float
    qty: int


class StorefrontCheckoutRequest(BaseModel):
    website_id: str
    items: List[CheckoutItem]
    currency: str = "USD"
    success_url: str
    cancel_url: str


class PaymentConfigRequest(BaseModel):
    website_id: str
    publishable_key: str
    secret_key: str
    webhook_secret: Optional[str] = None
    enabled_methods: Optional[List[str]] = None


# ── Internal helper ────────────────────────────────────────────────────────────

def _upsert_subscription(user_id: str, plan: str, stripe_sub_id: str = None,
                          status: str = "active"):
    """Write or update the subscriptions row; always refreshes next_billing_date."""
    next_billing = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    existing = db.fetchone(
        "SELECT sub_id FROM subscriptions WHERE user_id = ?", (user_id,)
    )
    if existing:
        db.execute(
            "UPDATE subscriptions SET plan=?, stripe_sub_id=?, status=?, "
            "next_billing_date=? WHERE user_id=?",
            (plan, stripe_sub_id, status, next_billing, user_id),
        )
    else:
        db.execute(
            "INSERT INTO subscriptions "
            "(sub_id, user_id, plan, stripe_sub_id, status, next_billing_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, plan, stripe_sub_id, status, next_billing),
        )


# ── Platform subscription ──────────────────────────────────────────────────────

@router.get("/subscription")
async def get_my_subscription(current_user: dict = Depends(get_current_user)):
    sub = db.fetchone(
        "SELECT plan, status, next_billing_date, stripe_sub_id FROM subscriptions WHERE user_id=?",
        (current_user["sub"],),
    )
    return sub or {}


@router.get("/plans")
async def list_plans():
    return [
        {
            "plan": k,
            "label": v["label"],
            "price_usd": v["price_usd"],
            "max_pages": v["max_pages"],
            "shopping_cart": v["shopping_cart"],
            "custom_domain": v["custom_domain"],
            "analytics": v["analytics"],
        }
        for k, v in PLANS.items()
    ]


@router.post("/subscribe/{plan}")
async def subscribe(plan: str, request: Request,
                    current_user: dict = Depends(get_current_user)):
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail="Unknown plan")

    user_id = current_user["sub"]

    if plan == "free":
        db.execute("UPDATE users SET plan='free' WHERE user_id=?", (user_id,))
        _upsert_subscription(user_id, "free", status="active")
        return {"message": "Switched to Free plan"}

    user = db.fetchone("SELECT stripe_customer_id FROM users WHERE user_id=?", (user_id,))

    # If Stripe is not configured, activate directly (demo/dev mode)
    stripe_configured = bool(os.getenv("STRIPE_SECRET_KEY", ""))
    if not stripe_configured:
        db.execute("UPDATE users SET plan=? WHERE user_id=?", (plan, user_id))
        _upsert_subscription(user_id, plan, status="active")
        return {"message": f"Switched to {plan} plan"}

    if not user or not user["stripe_customer_id"]:
        raise HTTPException(status_code=400, detail="No Stripe customer linked to account")

    base = str(request.base_url).rstrip("/")
    url = create_subscription_checkout(
        stripe_customer_id=user["stripe_customer_id"],
        plan=plan,
        success_url=f"{base}/billing/success",
        cancel_url=f"{base}/billing/cancel",
    )
    if not url:
        # Demo/dev mode — no Stripe configured; activate directly
        db.execute("UPDATE users SET plan=? WHERE user_id=?", (plan, user_id))
        _upsert_subscription(user_id, plan, status="active")
        return {"message": f"Subscribed to {plan} plan (demo mode — no charge)"}

    # Real Stripe: mark pending until webhook confirms
    _upsert_subscription(user_id, plan, status="pending")
    return {"checkout_url": url}


# ── Storefront checkout ────────────────────────────────────────────────────────

@router.post("/checkout")
async def storefront_checkout(body: StorefrontCheckoutRequest,
                              current_user: dict = Depends(get_current_user)):
    cfg = db.fetchone(
        "SELECT secret_key_enc FROM payment_configs WHERE website_id=?", (body.website_id,)
    )
    secret_key = cfg["secret_key_enc"] if cfg else None

    url = create_storefront_checkout(
        line_items=[{"name": i.name, "price": i.price, "qty": i.qty} for i in body.items],
        currency=body.currency,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        stripe_secret_key=secret_key,
    )
    if not url:
        raise HTTPException(status_code=500, detail="Checkout session creation failed")
    log_event("checkout_initiated", website_id=body.website_id, user_id=current_user["sub"])
    return {"checkout_url": url}


# ── Configure payment gateway for a website ────────────────────────────────────

@router.post("/configure")
async def configure_payment(body: PaymentConfigRequest,
                             current_user: dict = Depends(get_current_user)):
    site = db.fetchone(
        "SELECT user_id FROM websites WHERE website_id=?", (body.website_id,)
    )
    if not site or site["user_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not your website")

    existing = db.fetchone(
        "SELECT config_id FROM payment_configs WHERE website_id=?", (body.website_id,)
    )
    methods = json.dumps(body.enabled_methods or ["card"])
    if existing:
        db.execute(
            "UPDATE payment_configs SET publishable_key=?, secret_key_enc=?, "
            "webhook_secret_enc=?, enabled_methods=? WHERE website_id=?",
            (body.publishable_key, body.secret_key, body.webhook_secret or "", methods, body.website_id),
        )
    else:
        db.execute(
            "INSERT INTO payment_configs "
            "(config_id, website_id, publishable_key, secret_key_enc, webhook_secret_enc, enabled_methods) "
            "VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), body.website_id, body.publishable_key,
             body.secret_key, body.webhook_secret or "", methods),
        )
    return {"message": "Payment gateway configured"}


# ── Stripe webhook ─────────────────────────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig    = request.headers.get("stripe-signature", "")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    event  = verify_webhook(payload, sig, secret)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    etype = event["type"]
    if etype == "customer.subscription.updated":
        sub       = event["data"]["object"]
        cust_id   = sub.get("customer")
        plan      = sub.get("metadata", {}).get("plan", "pro")
        stripe_id = sub.get("id")
        user = db.fetchone("SELECT user_id FROM users WHERE stripe_customer_id=?", (cust_id,))
        if user:
            db.execute("UPDATE users SET plan=? WHERE user_id=?", (plan, user["user_id"]))
            _upsert_subscription(user["user_id"], plan, stripe_sub_id=stripe_id, status="active")
    elif etype == "customer.subscription.deleted":
        cust_id = event["data"]["object"].get("customer")
        user = db.fetchone("SELECT user_id FROM users WHERE stripe_customer_id=?", (cust_id,))
        if user:
            db.execute("UPDATE users SET plan='free' WHERE user_id=?", (user["user_id"],))
            _upsert_subscription(user["user_id"], "free", status="cancelled")
    return Response(status_code=200)
