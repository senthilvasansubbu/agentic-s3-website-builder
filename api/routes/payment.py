"""
Payment API routes — platform subscriptions + per-website storefront checkout.
"""
import os
import json
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
    price: float          # in whole currency unit, e.g. 12.99
    qty: int


class StorefrontCheckoutRequest(BaseModel):
    website_id: str
    items: List[CheckoutItem]
    currency: str = "USD"
    success_url: str
    cancel_url: str


# ── Platform subscription ──────────────────────────────────────────────────────

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
    if plan == "free":
        db.execute("UPDATE users SET plan = 'free' WHERE user_id = %s", (current_user["sub"],))
        return {"message": "Switched to Free plan"}

    user = db.fetchone("SELECT stripe_customer_id FROM users WHERE user_id = %s",
                       (current_user["sub"],))
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
        raise HTTPException(status_code=500, detail="Could not create Stripe checkout session")
    return {"checkout_url": url}


# ── Storefront checkout ────────────────────────────────────────────────────────

@router.post("/checkout")
async def storefront_checkout(body: StorefrontCheckoutRequest,
                              current_user: dict = Depends(get_current_user)):
    # Fetch website-specific Stripe key
    cfg = db.fetchone(
        "SELECT secret_key_enc FROM payment_configs WHERE website_id = %s", (body.website_id,)
    )
    secret_key = cfg["secret_key_enc"] if cfg else None  # decryption TODO: add KMS

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

class PaymentConfigRequest(BaseModel):
    website_id: str
    publishable_key: str
    secret_key: str
    webhook_secret: Optional[str] = None
    enabled_methods: Optional[List[str]] = None


@router.post("/configure")
async def configure_payment(body: PaymentConfigRequest,
                             current_user: dict = Depends(get_current_user)):
    import uuid
    # Verify ownership
    site = db.fetchone(
        "SELECT user_id FROM websites WHERE website_id = %s", (body.website_id,)
    )
    if not site or site["user_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not your website")

    existing = db.fetchone(
        "SELECT config_id FROM payment_configs WHERE website_id = %s", (body.website_id,)
    )
    methods = json.dumps(body.enabled_methods or ["card"])
    if existing:
        db.execute(
            """UPDATE payment_configs SET publishable_key=%s, secret_key_enc=%s,
               webhook_secret_enc=%s, enabled_methods=PARSE_JSON(%s)
               WHERE website_id=%s""",
            (body.publishable_key, body.secret_key, body.webhook_secret or "", methods, body.website_id),
        )
    else:
        db.execute(
            """INSERT INTO payment_configs
               (config_id, website_id, publishable_key, secret_key_enc, webhook_secret_enc, enabled_methods)
               VALUES (%s,%s,%s,%s,%s,PARSE_JSON(%s))""",
            (str(uuid.uuid4()), body.website_id, body.publishable_key,
             body.secret_key, body.webhook_secret or "", methods),
        )
    return {"message": "Payment gateway configured"}


# ── Stripe webhook ─────────────────────────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    event = verify_webhook(payload, sig, secret)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    etype = event["type"]
    if etype == "customer.subscription.updated":
        sub = event["data"]["object"]
        cust_id = sub.get("customer")
        plan = sub.get("metadata", {}).get("plan", "pro")
        db.execute(
            "UPDATE users SET plan = %s WHERE stripe_customer_id = %s", (plan, cust_id)
        )
    elif etype == "customer.subscription.deleted":
        cust_id = event["data"]["object"].get("customer")
        db.execute(
            "UPDATE users SET plan = 'free' WHERE stripe_customer_id = %s", (cust_id,)
        )
    return Response(status_code=200)
