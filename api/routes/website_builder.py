"""
Website builder API routes — create, list, build, deploy, customise websites.
"""
import uuid
import json
import os
import logging
import time
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
logger = logging.getLogger("website_builder.api")

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
    enable_chatbot: bool = False
    enable_blog: bool = False
    num_pages: int = 1
    custom_css: Optional[str] = None


class BuildWebsiteRequest(BaseModel):
    requirements: str                  # natural language
    use_web_search: bool = True
    use_social_search: bool = False
    # Optional structured fields — enriches AI prompt when provided
    categories: Optional[List[str]] = None          # e.g. ["Cakes","Pastries","Breads"]
    location: Optional[str] = None                  # e.g. "123 Main St, New York, NY 10001"
    email: Optional[str] = None                     # e.g. "info@mybakery.com"
    phone: Optional[str] = None                     # e.g. "+1-212-555-0199"
    booking_prefix: Optional[str] = None            # e.g. "BK" — order ref prefix
    social_links: Optional[dict] = None             # e.g. {"instagram": "https://...", "facebook": [...], "linkedin": "https://..."}


class UpdateWebsiteRequest(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    logo_url: Optional[str] = None
    domain: Optional[str] = None
    theme: Optional[str] = None
    custom_css: Optional[str] = None
    status: Optional[str] = None


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
            hosting_env, theme, custom_css, cart_features, enable_chatbot, enable_blog, status)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft')""",
        (website_id, user_id, body.name, body.title, body.description or "",
         body.logo_url or "", body.domain or "", body.hosting_env,
         body.theme, body.custom_css or "",
         json.dumps(body.cart_features or []),
         1 if body.enable_chatbot else 0,
         1 if body.enable_blog else 0),
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
    trace_id = str(uuid.uuid4())[:8]
    t0 = time.time()
    user_id = current_user["sub"]
    logger.info("[%s] ▶ BUILD REQUEST  website_id=%s  user=%s  cart=%s  web_search=%s  social_search=%s",
                trace_id, website_id, user_id,
                body.categories, body.use_web_search, body.use_social_search)

    site = db.fetchone(
        "SELECT * FROM websites WHERE website_id = %s AND user_id = %s",
        (website_id, user_id),
    )
    if not site:
        logger.warning("[%s] 404 website_id=%s not found for user=%s", trace_id, website_id, user_id)
        raise HTTPException(status_code=404, detail="Website not found")

    logger.info("[%s] 🔍 website found: name=%r  theme=%s  cart_features=%s  chatbot=%s",
                trace_id, site.get("name"), site.get("theme"),
                site.get("cart_features"), site.get("enable_chatbot"))

    # Gather web/social content
    extra_context = ""
    if body.use_web_search:
        logger.info("[%s] 🌐 Running web search...", trace_id)
        t1 = time.time()
        extra_context += "\n\n=== Web Research ===\n" + search_for_website_content(body.requirements)
        logger.info("[%s] 🌐 Web search done in %.1fs", trace_id, time.time()-t1)
    if body.use_social_search:
        logger.info("[%s] 📱 Running social media search...", trace_id)
        t1 = time.time()
        extra_context += "\n\n=== Social Media Trends ===\n" + social_context_for_topic(body.requirements)
        logger.info("[%s] 📱 Social search done in %.1fs", trace_id, time.time()-t1)

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

    if site.get("enable_blog"):
        full_prompt += (
            "\n\n=== Blog Section ===\n"
            "Include a Blog section on the website with a dedicated /blog page. "
            "The blog page should display a grid of sample blog post cards, each with "
            "a title, short excerpt, author, date, reading time, and a 'Read More' link. "
            "Include at least 3 realistic sample blog posts relevant to the business niche. "
            "Add a 'Blog' link in the main navigation."
        )

    if site.get("enable_chatbot"):
        full_prompt += (
            "\n\n=== Chatbot Widget ===\n"
            "Embed a floating customer-support chatbot widget on every page. "
            "The widget should appear as a chat bubble in the bottom-right corner, "
            "open a chat panel on click, greet the visitor, and allow them to send "
            "messages. Include a clean HTML/CSS/JS implementation with a configurable "
            "welcome message and a placeholder for an API endpoint to handle replies."
        )

    # ── Rich structured content enrichment ────────────────────────────────────
    site_name = site.get("name") or site.get("title") or "Business"
    site_desc = site.get("description") or ""

    enrichment_lines = [
        "\n\n=== CONTENT & STYLE ENRICHMENT ===",
        "You MUST use every piece of information below in the generated website.",
        f"Business Name: {site_name}",
    ]

    if site_desc:
        enrichment_lines.append(
            f"Business Description:\n{site_desc}\n"
            "Incorporate this description into the hero tagline, about section, and category cards."
        )

    # Categories — from explicit field or extracted from description/requirements
    cats = body.categories or []
    if not cats:
        # Auto-extract capitalised words as category hints from requirements
        import re as _re
        cats = _re.findall(r'(?:categor(?:y|ies)[:\s]+|types?[:\s]+)([A-Za-z ,&]+)', body.requirements)
        if cats:
            cats = [c.strip() for item in cats for c in item.split(',') if c.strip()]
    if cats:
        cat_list = "\n".join(f"  - {c}" for c in cats)
        enrichment_lines.append(
            f"\nProduct/Service Categories (create a visual card for EACH with a relevant Unsplash image):\n{cat_list}"
        )
        # Build Unsplash image hints per category
        unsplash_hints = "\n".join(
            f"  - {c}: https://source.unsplash.com/featured/400x300/?{c.lower().replace(' ', ',')}"
            for c in cats
        )
        enrichment_lines.append(f"\nSuggested Unsplash images per category:\n{unsplash_hints}")

    # Location
    location = body.location or ""
    if location:
        import urllib.parse as _up
        map_query = _up.quote(location)
        enrichment_lines.append(
            f"\nBusiness Location: {location}\n"
            f"Embed this Google Map in the Contact section:\n"
            f'<iframe src="https://maps.google.com/maps?q={map_query}&output=embed" '
            f'width="100%" height="350" style="border:0;border-radius:12px" allowfullscreen loading="lazy"></iframe>'
        )

    # Email
    email = body.email or f"info@{site_name.lower().replace(' ', '')}.com"
    enrichment_lines.append(f"\nBusiness Email: {email}")

    # Phone
    if body.phone:
        enrichment_lines.append(f"Business Phone: {body.phone}")

    # Booking/order reference prefix
    prefix = body.booking_prefix or "ORD"
    enrichment_lines.append(
        f"\nOrder/Booking Reference Prefix: {prefix}\n"
        f"The booking form must auto-generate a reference like '{prefix}-' + Date.now() on submission."
    )

    # Social links
    if body.social_links:
        sl = body.social_links
        social_parts = []
        if sl.get('instagram'):
            urls = sl['instagram'] if isinstance(sl['instagram'], list) else [sl['instagram']]
            social_parts.append('Instagram: ' + ', '.join(urls))
        if sl.get('facebook'):
            urls = sl['facebook'] if isinstance(sl['facebook'], list) else [sl['facebook']]
            social_parts.append('Facebook: ' + ', '.join(urls))
        if sl.get('linkedin'):
            urls = sl['linkedin'] if isinstance(sl['linkedin'], list) else [sl['linkedin']]
            social_parts.append('LinkedIn: ' + ', '.join(urls))
        if social_parts:
            enrichment_lines.append(
                "\nSocial Media Profiles (use these real URLs in the footer social icons):\n"
                + '\n'.join(social_parts)
            )
    elif body.use_social_search:
        enrichment_lines.append(
            f"\n=== SOCIAL MEDIA SEARCH DIRECTIVE ===\n"
            f"No social media URLs were provided by the user. You are AUTHORISED to search the web "
            f"for the official Instagram, Facebook, and LinkedIn profiles of '{site_name}' and use "
            f"those real URLs in the footer social icons. If you cannot find them, use '#' as a "
            f"placeholder but still render the social icon buttons in the footer."
        )

    # Hero image
    niche_kw = (cats[0] if cats else site_name).lower().replace(' ', ',')
    enrichment_lines.append(
        f"\nHero background image: https://source.unsplash.com/featured/1400x700/?{niche_kw}"
    )

    enrichment_lines.append(
        "\n=== STYLE DIRECTIVE ===\n"
        "The website must feel PREMIUM and CLASSY — use elegant fonts (e.g. Playfair Display for headings, "
        "Lato or Inter for body), generous whitespace, subtle drop shadows, smooth hover transitions, "
        "and a refined colour palette. NO clip-art, no garish colours. Sections should feel editorial — "
        "inspired by Squarespace or Behance premium portfolios."
    )

    full_prompt += "\n".join(enrichment_lines)

    logger.info("[%s] 🏗  Prompt ready (%d chars, %d cart features, chatbot=%s) — calling build_website",
                trace_id, len(full_prompt), len(cart_features), bool(site.get("enable_chatbot")))

    # Build via AI crew (or static fallback)
    try:
        t1 = time.time()
        output_path = build_website(full_prompt)
        logger.info("[%s] ✅ build_website completed in %.1fs  output=%s",
                    trace_id, time.time()-t1, output_path)
    except Exception as exc:
        logger.exception("[%s] ❌ build_website FAILED after %.1fs: %s", trace_id, time.time()-t0, exc)
        db.execute(
            "UPDATE websites SET status = 'error', updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
            (website_id,),
        )
        raise HTTPException(status_code=500, detail=f"Build failed: {exc}")

    db.execute(
        "UPDATE websites SET status = 'built', updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
        (website_id,),
    )
    log_event("website_built", user_id=user_id, website_id=website_id,
              ip_address=request.client.host)
    logger.info("[%s] 🎉 BUILD COMPLETE  website_id=%s  total=%.1fs", trace_id, website_id, time.time()-t0)
    return {"message": "Website built successfully", "output": output_path, "trace_id": trace_id}


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


@router.delete("/{website_id}")
async def delete_website(website_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    site = db.fetchone(
        "SELECT website_id FROM websites WHERE website_id = %s AND user_id = %s",
        (website_id, user_id),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    db.execute("DELETE FROM websites WHERE website_id = %s", (website_id,))
    return {"message": "Website deleted"}


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
        "SELECT website_id, name, title, theme, status, domain, s3_url, cart_features, enable_chatbot, enable_blog, created_at, updated_at "
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
