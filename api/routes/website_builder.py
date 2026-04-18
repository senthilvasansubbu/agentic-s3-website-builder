"""
Website builder API routes — create, list, build, deploy, customise websites.
"""
import uuid
import json
import os
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List

from api.routes.auth import get_current_user
from database.snowflake_client import db
from agents.crew import build_website
from tools.theme_builder import THEMES, render_page
from tools.web_search import search_for_website_content
from tools.social_media_search import social_context_for_topic
from services.hosting_service import deploy_to_s3, save_locally, custom_domain_instructions
from services.analytics_service import log_event
from services.payment_service import PLANS
from config.settings import settings

router = APIRouter(prefix="/websites", tags=["websites"])

FREE_PAGE_LIMIT = 10


# ── Schemas ────────────────────────────────────────────────────────────────────

class CreateWebsiteRequest(BaseModel):
    name: str
    title: str
    description: Optional[str] = None
    theme: str = "modern"
    logo_url: Optional[str] = None
    domain: Optional[str] = None
    hosting_env: str = "s3"
    include_shopping_cart: bool = False
    cart_features: Optional[List[str]] = None  # e.g. ["categories","coupons","flash_offers","ads","email_notify"]
    num_pages: int = 1
    custom_css: Optional[str] = None


class BuildWebsiteRequest(BaseModel):
    requirements: str                  # natural language
    use_web_search: bool = True
    use_social_search: bool = False


class UpdateWebsiteRequest(BaseModel):
    title: Optional[str] = None
    logo_url: Optional[str] = None
    domain: Optional[str] = None
    theme: Optional[str] = None
    custom_css: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _check_plan_limits(user_id: str, num_pages: int, needs_cart: bool):
    user = db.fetchone("SELECT plan FROM users WHERE user_id = %s", (user_id,))
    plan = user["plan"] if user else "free"
    plan_info = PLANS.get(plan, PLANS["free"])

    if num_pages > plan_info["max_pages"]:
        raise HTTPException(
            status_code=402,
            detail=f"Your '{plan}' plan allows up to {plan_info['max_pages']} pages. "
                   f"Upgrade to build more.",
        )
    if needs_cart and not plan_info["shopping_cart"]:
        raise HTTPException(
            status_code=402,
            detail="Shopping cart requires the Pro or Enterprise plan.",
        )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("")
async def create_website(body: CreateWebsiteRequest, request: Request,
                         current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    _check_plan_limits(user_id, body.num_pages, body.include_shopping_cart)

    if body.theme not in THEMES:
        raise HTTPException(status_code=400, detail=f"Unknown theme. Available: {list(THEMES)}")

    website_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO websites
           (website_id, user_id, name, title, description, logo_url, domain,
            hosting_env, theme, custom_css, cart_features, status)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft')""",
        (website_id, user_id, body.name, body.title, body.description or "",
         body.logo_url or "", body.domain or "", body.hosting_env,
         body.theme, body.custom_css or "",
         json.dumps(body.cart_features or [])),
    )
    log_event("website_created", user_id=user_id, website_id=website_id,
              ip_address=request.client.host)
    return {"website_id": website_id, "message": "Website record created. Use /build to generate pages."}


@router.post("/{website_id}/build")
async def build_website_pages(
    website_id: str,
    body: BuildWebsiteRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    site = db.fetchone(
        "SELECT * FROM websites WHERE website_id = %s AND user_id = %s",
        (website_id, user_id),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    # Gather web/social content
    extra_context = ""
    if body.use_web_search:
        extra_context += "\n\n=== Web Research ===\n" + search_for_website_content(body.requirements)
    if body.use_social_search:
        extra_context += "\n\n=== Social Media Trends ===\n" + social_context_for_topic(body.requirements)

    full_prompt = body.requirements + extra_context

    # Inject shopping cart feature requirements into the prompt
    cart_features = []
    try:
        import json as _json
        cf = site.get("cart_features") or "[]"
        cart_features = _json.loads(cf) if isinstance(cf, str) else cf
    except Exception:
        pass

    FEATURE_PROMPTS = {
        "categories":     "Product listing with category navigation and breadcrumbs.",
        "price_filter":   "Price range filter slider on product/shop pages.",
        "images":         "Product image gallery with zoom and multiple images per product.",
        "discounts":      "Display original price, sale price, and discount percentage badge.",
        "coupons":        "Coupon code input field at checkout with validation feedback.",
        "flash_offers":   "Flash sale section with countdown timer and highlighted deal cards.",
        "ads":            "Advertisement banner placeholders (hero, sidebar, and footer positions).",
        "email_notify":   "Email subscription opt-in form for promotions and newsletters.",
        "sms_notify":     "SMS/WhatsApp opt-in checkbox at checkout for order updates.",
        "whatsapp_notify":"WhatsApp contact button and order notification opt-in.",
        "reviews":        "Product review and star-rating section on product detail pages.",
        "wishlist":       "Add-to-wishlist button on product cards.",
        "search":         "Search bar with autocomplete for products.",
    }
    if cart_features:
        feat_text = "\n".join(f"- {FEATURE_PROMPTS.get(f, f)}" for f in cart_features if f in FEATURE_PROMPTS)
        if feat_text:
            full_prompt += f"\n\n=== Required E-commerce Features ===\nThe shopping cart/storefront must include:\n{feat_text}"

    # Build via AI crew (or static fallback)
    output_path = build_website(full_prompt)

    db.execute(
        "UPDATE websites SET status = 'built', updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
        (website_id,),
    )
    log_event("website_built", user_id=user_id, website_id=website_id,
              ip_address=request.client.host)
    return {"message": "Website built successfully", "output": output_path}


@router.post("/{website_id}/deploy")
async def deploy_website(website_id: str, request: Request,
                         current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    site = db.fetchone(
        "SELECT * FROM websites WHERE website_id = %s AND user_id = %s",
        (website_id, user_id),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    if site["hosting_env"] == "s3":
        url = deploy_to_s3(
            local_dir=settings.OUTPUT_DIR,
            bucket_name=site["s3_bucket"] or settings.S3_BUCKET_NAME or "",
            access_key=settings.AWS_ACCESS_KEY_ID or "",
            secret_key=settings.AWS_SECRET_ACCESS_KEY or "",
            region=settings.AWS_REGION,
            prefix=website_id,
        )
        if not url:
            raise HTTPException(status_code=500, detail="S3 deployment failed. Check AWS credentials.")
        db.execute(
            "UPDATE websites SET s3_url = %s, status = 'live' WHERE website_id = %s",
            (url, website_id),
        )
        log_event("website_deployed", user_id=user_id, website_id=website_id,
                  ip_address=request.client.host, meta={"url": url})
        return {"url": url}

    raise HTTPException(status_code=400, detail=f"Unsupported hosting_env: {site['hosting_env']}")


@router.patch("/{website_id}")
async def update_website(website_id: str, body: UpdateWebsiteRequest,
                         current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    site = db.fetchone(
        "SELECT website_id FROM websites WHERE website_id = %s AND user_id = %s",
        (website_id, user_id),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"message": "Nothing to update"}

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = tuple(updates.values()) + (website_id,)
    db.execute(
        f"UPDATE websites SET {set_clause}, updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
        values,
    )
    return {"message": "Website updated"}


@router.get("/{website_id}/domain-instructions")
async def domain_instructions(website_id: str, current_user: dict = Depends(get_current_user)):
    site = db.fetchone(
        "SELECT domain, s3_bucket FROM websites WHERE website_id = %s AND user_id = %s",
        (website_id, current_user["sub"]),
    )
    if not site or not site["domain"]:
        raise HTTPException(status_code=400, detail="No custom domain set for this website")
    return {
        "instructions": custom_domain_instructions(
            site["domain"], site["s3_bucket"] or "", settings.AWS_REGION
        )
    }


@router.get("/my")
async def list_my_websites(current_user: dict = Depends(get_current_user)):
    """Alias used by user dashboard."""
    user_id = current_user["sub"]
    # Also include websites owned by the user's owner (for sub-users)
    u = db.fetchone("SELECT owner_id FROM users WHERE user_id = ?", (user_id,))
    owner_id = u.get("owner_id") if u else None
    effective_id = owner_id if owner_id else user_id
    return db.execute(
        "SELECT website_id, name, title, theme, status, domain, s3_url, cart_features, slug, created_at "
        "FROM websites WHERE user_id = ? ORDER BY created_at DESC",
        (effective_id,),
    ) or []


@router.get("")
async def list_websites(current_user: dict = Depends(get_current_user)):
    return db.execute(
        "SELECT website_id, name, title, theme, status, domain, s3_url, created_at FROM websites WHERE user_id = %s ORDER BY created_at DESC",
        (current_user["sub"],),
    )


@router.get("/themes")
async def list_themes():
    return [{"key": k, **{f: v for f, v in v.items() if f == "label"}} for k, v in THEMES.items()]
