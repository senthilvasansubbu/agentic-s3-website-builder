"""
Website builder API routes — create, list, build, deploy, customise websites.
"""
import uuid
import json
import os
import ipaddress
import logging
import time
import asyncio
import re
import shutil
import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

from api.routes.auth import get_current_user, require_app_user_or_above, require_client_or_above
from database.snowflake_client import db
from agents.crew import build_website
from agents.requirements_analyst import build_prompt, BuildRequest as AnalystRequest
from tools.theme_builder import THEMES, render_page
from tools.web_search import search_for_website_content
from tools.social_media_search import social_context_for_topic
from tools.website_scraper import scrape_website, prompt_context_from_scraped_data
from services.hosting_service import deploy_to_s3, save_locally, custom_domain_instructions
from services.analytics_service import log_event
from services.payment_service import PLANS
from services.secret_store import encrypt_json, can_encrypt
from services.secret_store import decrypt_json
from services.hosting_service import deploy_directory_to_gdrive
from config.settings import settings

router = APIRouter(prefix="/websites", tags=["websites"])
logger = logging.getLogger("website_builder.api")

FREE_PAGE_LIMIT = 10


def _reference_quality_metrics(scraped: dict) -> dict:
    headings = scraped.get("headings") or []
    paragraphs = scraped.get("paragraphs") or []
    nav_links = scraped.get("nav_links") or []
    images = scraped.get("images") or []
    description = (scraped.get("description") or "").strip()
    title = (scraped.get("title") or "").strip()

    return {
        "title": title,
        "description_len": len(description),
        "headings": len(headings),
        "paragraphs": len(paragraphs),
        "nav_links": len([n for n in nav_links if isinstance(n, dict) and n.get("text")]),
        "images": len(images),
    }


def _is_reference_usable(metrics: dict) -> bool:
    # Strict baseline: must carry actual textual structure plus either
    # navigational or visual signals, otherwise it is too sparse to anchor AI.
    has_text_structure = metrics["headings"] >= 2 or metrics["paragraphs"] >= 2 or metrics["description_len"] >= 80
    has_structure_or_media = metrics["images"] >= 1 or metrics["nav_links"] >= 1
    return has_text_structure and has_structure_or_media


def _safe_json_loads(raw: Optional[str], default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.debug("Failed to decode JSON payload in website_builder helper: %s", exc)
        return default


def _read_index_html(local_path: str) -> str:
    try:
        if not local_path:
            return ""
        p = os.path.join(local_path, "index.html")
        if not os.path.exists(p):
            return ""
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError as exc:
        logger.debug("Failed to read index.html from %s: %s", local_path, exc)
        return ""


def _generate_build_narrative(
    website_id: str,
    input_snapshot: dict,
    source_context: dict,
    local_path: str,
) -> dict:
    req = (input_snapshot.get("requirements") or "").strip()
    reference_urls = source_context.get("reference_urls") or []
    nav_links = source_context.get("nav_links") or []
    reference_sites = source_context.get("reference_sites") or []
    extra_context = source_context.get("extra_context") or ""

    scraped_image_count = 0
    for rs in reference_sites:
        scraped_image_count += len(rs.get("images") or [])

    html = _read_index_html(local_path)
    html_low = html.lower()
    section_count = len(re.findall(r"<section\\b", html_low))
    local_img_count = len(re.findall(r"<img[^>]+src=[\"']assets/images/", html, re.I))
    remote_img_count = len(re.findall(r"<img[^>]+src=[\"']https?://", html, re.I))

    medical_intent = bool(re.search(
        r"\\b(medical|medicinal|diagnostic|diagnostics|pharma|pharmaceutical|laboratory|lab\\s*equipment|reagent|reseller|distributor)\\b",
        req,
        re.I,
    ))

    off_domain_markers = {
        "cloud solutions": html_low.count("cloud solutions"),
        "cybersecurity": html_low.count("cybersecurity"),
        "managed it services": html_low.count("managed it services"),
        "it strategy": html_low.count("it strategy"),
        "enterprise solutions": html_low.count("enterprise solutions"),
        "proconnect": html_low.count("proconnect"),
    }
    off_domain_hits = sum(off_domain_markers.values())

    site_name = (input_snapshot.get("site_name") or "").strip()
    placeholder_markers = {
        "grace community church": html_low.count("grace community church"),
        "grace community": html_low.count("grace community"),
    }
    placeholder_hits = sum(placeholder_markers.values())

    expect_blog = bool(input_snapshot.get("enable_blog"))
    expect_livestream = bool(input_snapshot.get("enable_livestream"))
    expect_chatbot = bool(input_snapshot.get("enable_chatbot"))
    has_blog = bool(re.search(r'id=["\']blog["\']|href=["\']#blog["\']|/blog\b|>\s*blog\s*<', html, re.I))
    has_livestream = bool(re.search(r'id=["\']livestream["\']|live\s*stream|href=["\']#livestream["\']', html, re.I))
    has_chatbot = bool(re.search(r'chatbot|chat bubble|id=["\']chat[^"\']*["\']|aria-label=["\'][^"\']*chat', html, re.I))

    web_search_requested = bool(input_snapshot.get("use_web_search"))
    web_search_empty = "=== Web Research ===" in extra_context and "No external content found" in extra_context

    checks = []
    checks.append({
        "name": "Reference Data Richness",
        "status": "pass" if (len(nav_links) > 0 or scraped_image_count > 0) else "warning",
        "details": (
            f"reference_urls={len(reference_urls)}, nav_links={len(nav_links)}, scraped_images={scraped_image_count}. "
            "Low extracted structure/images reduces domain anchoring for the model."
        ),
    })
    checks.append({
        "name": "Web Research Coverage",
        "status": "warning" if (web_search_requested and web_search_empty) else "pass",
        "details": (
            "Web search returned no external content; model had less factual grounding beyond prompt/reference extraction."
            if (web_search_requested and web_search_empty)
            else "Web research either not requested or returned content."
        ),
    })
    checks.append({
        "name": "Domain Relevance in Output",
        "status": "warning" if (medical_intent and off_domain_hits > 0) else "pass",
        "details": (
            f"medical_intent={medical_intent}, off_domain_hits={off_domain_hits}, markers={off_domain_markers}"
        ),
    })
    checks.append({
        "name": "Image Localization",
        "status": "pass" if remote_img_count == 0 else "warning",
        "details": (
            f"local_images={local_img_count}, remote_images={remote_img_count}. "
            "Remote images can still appear when source extraction is sparse or generated HTML contains non-placeholder URLs."
        ),
    })
    checks.append({
        "name": "Output Structure",
        "status": "pass" if section_count >= 4 else "warning",
        "details": f"Detected {section_count} <section> blocks in generated HTML.",
    })
    checks.append({
        "name": "Brand Placeholder Leakage",
        "status": "warning" if placeholder_hits > 0 else "pass",
        "details": (
            f"site_name={site_name!r}, placeholder_hits={placeholder_hits}, markers={placeholder_markers}."
        ),
    })
    checks.append({
        "name": "Feature Flag Fulfillment",
        "status": "warning" if ((expect_blog and not has_blog) or (expect_livestream and not has_livestream) or (expect_chatbot and not has_chatbot)) else "pass",
        "details": (
            f"expected(blog={expect_blog},live={expect_livestream},chatbot={expect_chatbot}) "
            f"observed(blog={has_blog},live={has_livestream},chatbot={has_chatbot})."
        ),
    })

    can_do = [
        "Apply business name, contact fields, and structural guardrails deterministically after generation.",
        "Use extracted reference images when available, otherwise fall back to generated placeholder seeds.",
        "Produce responsive multi-section layouts from minimal textual requirements.",
    ]
    cannot_do = [
        "Guarantee domain-accurate long-form copy when reference extraction is sparse and web research returns no content.",
        "Infer missing product catalog details that are not present in user requirements or extracted source context.",
        "Reliably preserve competitor/reference site semantics without explicit, structured product data."
    ]
    user_expected_inputs = [
        "Provide 6-12 explicit product/service names in requirements or categories.",
        "Provide at least one rich reference URL with accessible headings/nav/images.",
        "If web search is enabled, include domain keywords (brand, product line, city) in requirements for better retrieval.",
        "Review and refine generated output in Staging when requirements are broad or sparse."
    ]

    summary = (
        "Build narrative generated from persisted input snapshot, source context, and final HTML. "
        "Drift risk increases when extracted reference context is sparse or contradictory to requested domain."
    )

    return {
        "website_id": website_id,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "summary": summary,
        "inputs_used": {
            "requirements": req,
            "build_mode": input_snapshot.get("build_mode"),
            "classification": input_snapshot.get("classification"),
            "classification_label": input_snapshot.get("classification_label"),
            "classification_group": input_snapshot.get("classification_group"),
            "reference_urls": reference_urls,
            "reference_usage_by_url": input_snapshot.get("reference_usage_by_url") or [],
            "use_web_search": web_search_requested,
            "use_social_search": bool(input_snapshot.get("use_social_search")),
            "location": input_snapshot.get("location"),
            "email": input_snapshot.get("email"),
            "phone": input_snapshot.get("phone"),
        },
        "checks": checks,
        "can_do": can_do,
        "cannot_do": cannot_do,
        "user_expected_inputs": user_expected_inputs,
    }


def _log_build_narrative(website_id: str, narrative: dict) -> None:
    try:
        os.makedirs("logs", exist_ok=True)
        payload = {
            "ts": datetime.datetime.utcnow().isoformat() + "Z",
            "website_id": website_id,
            "narrative": narrative,
        }
        with open("logs/build_narratives.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        logger.info("[%s] 📝 build narrative logged", website_id)
    except Exception as exc:
        logger.warning("[%s] Failed to write build narrative log: %s", website_id, exc)


# ── Schemas ────────────────────────────────────────────────────────────────────

class CreateWebsiteRequest(BaseModel):
    name: str
    title: str
    description: Optional[str] = None
    theme: str = "modern"
    classification: str = "generic"
    classification_label: Optional[str] = None
    classification_group: Optional[str] = None
    build_mode: str = "agentic_only"            # combined | agentic_only
    output_target: str = "legacy"               # legacy | react | vue | php | ...
    logo_url: Optional[str] = None
    domain: Optional[str] = None
    hosting_env: str = "s3"
    image_storage_backend: str = "auto"   # auto | local | s3 | gdrive
    image_storage_config: Optional[dict] = None
    include_shopping_cart: bool = False
    cart_features: Optional[List[str]] = None  # e.g. ["categories","coupons","flash_offers","ads","email_notify"]
    enable_chatbot: bool = False
    enable_blog: bool = False
    enable_livestream: bool = False
    content_depth: str = 'standard'  # minimal | standard | detailed | enterprise
    custom_css: Optional[str] = None


class BuildWebsiteRequest(BaseModel):
    requirements: str                  # natural language
    use_web_search: bool = True
    use_social_search: bool = False
    existing_website_url: Optional[str] = None      # scrape this URL to pre-seed the build
    existing_website_urls: Optional[List[str]] = None  # optional multi-reference URLs
    reference_usage_by_url: Optional[List[dict]] = None  # e.g. [{"url":"https://...","usage":"picture references"}]
    content_depth: str = 'standard'                 # minimal | standard | detailed | enterprise
    niche: Optional[str] = None                     # UI niche/category hint
    include_shopping_cart: bool = False             # enable e-commerce / cart features
    build_mode: Optional[str] = None                # combined | agentic_only
    output_target: Optional[str] = None             # legacy | react | vue | php | ...
    classification_label: Optional[str] = None
    classification_group: Optional[str] = None
    # Optional structured fields — enriches AI prompt when provided
    categories: Optional[List[str]] = None          # e.g. ["Cakes","Pastries","Breads"]
    catalog_items: Optional[List[str]] = None        # exact product/model names — prevents AI hallucination
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
    image_storage_backend: Optional[str] = None
    image_storage_config: Optional[dict] = None
    image_storage_secrets: Optional[dict] = None


class ScrapeUrlRequest(BaseModel):
    url: str


class StagedHtmlRequest(BaseModel):
    html: str


ALLOWED_BUILD_MODES = {"combined", "agentic_only"}
ALLOWED_OUTPUT_TARGETS = {"legacy", "react", "vue", "php"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _check_plan_limits(user_id: str, needs_cart: bool):
    user = db.fetchone("SELECT plan FROM users WHERE user_id = %s", (user_id,))
    plan = user["plan"] if user else "free"
    plan_info = PLANS.get(plan, PLANS["free"])

    if needs_cart and not plan_info["shopping_cart"]:
        raise HTTPException(
            status_code=402,
            detail="Shopping cart requires the Pro or Enterprise plan.",
        )

    max_websites = plan_info.get("max_websites", 1)
    if max_websites < 9999:
        existing = db.fetchone(
            "SELECT COUNT(*) AS cnt FROM websites WHERE user_id = %s AND status != 'deleted'",
            (user_id,),
        )
        count = existing["cnt"] if existing else 0
        if count >= max_websites:
            raise HTTPException(
                status_code=402,
                detail=f"Your '{plan}' plan allows up to {max_websites} website(s). "
                       f"Upgrade to create more.",
            )


def _bundle_local_upload_assets(published_dir: str) -> dict:
    """
    Copy locally hosted uploaded images into the published folder and rewrite
    HTML references from /static/uploads/... to relative ./assets/uploads/... paths.
    """
    root = Path(published_dir)
    uploads_src = Path("data") / "uploads"
    uploads_dst = root / "assets" / "uploads"
    uploads_dst.mkdir(parents=True, exist_ok=True)

    if not uploads_src.exists():
        return {"rewritten_refs": 0, "copied_files": 0}

    copied = set()
    rewritten_refs = 0

    abs_pat = re.compile(r"https?://[^\"'\s]+/static/uploads/([A-Za-z0-9._-]+)")
    rel_pat = re.compile(r"/static/uploads/([A-Za-z0-9._-]+)")

    def _rewrite_html(html_path: Path, text: str) -> str:
        nonlocal rewritten_refs
        rel_upload_dir = os.path.relpath(uploads_dst, html_path.parent).replace("\\", "/")

        def _replace_match(match: re.Match) -> str:
            nonlocal rewritten_refs
            fname = unquote(match.group(1)).strip()
            src = uploads_src / fname
            if src.exists():
                dst = uploads_dst / fname
                if fname not in copied:
                    shutil.copy2(src, dst)
                    copied.add(fname)
                rewritten_refs += 1
                return f"{rel_upload_dir}/{fname}"
            return match.group(0)

        text = abs_pat.sub(_replace_match, text)
        text = rel_pat.sub(_replace_match, text)
        return text

    for html_path in root.rglob("*.html"):
        try:
            content = html_path.read_text(encoding="utf-8", errors="ignore")
            updated = _rewrite_html(html_path, content)
            if updated != content:
                html_path.write_text(updated, encoding="utf-8")
        except OSError as exc:
            logger.debug("Skipping unreadable HTML file %s: %s", html_path, exc)
            continue

    return {"rewritten_refs": rewritten_refs, "copied_files": len(copied)}


def _bundle_all_local_assets(published_dir: str, staging_dir: str) -> dict:
    """
    Copy all referenced local assets (img, css, js, fonts) into published_dir, preserving folder structure.
    Rewrite HTML links to point to the new locations.
    """
    root = Path(published_dir)
    staging = Path(staging_dir)
    exts = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.ico', '.css', '.js', '.woff', '.woff2', '.ttf', '.eot', '.otf'}
    rels_copied = set()
    rewritten_refs = 0

    # Patterns for src/href in HTML
    pat = re.compile(r'(?:src|href)=["\']([^"\']+)["\']', re.I)

    def _copy_asset(rel_path: str):
        rel_path = rel_path.lstrip('/')
        src = (staging / rel_path) if not rel_path.startswith('assets/uploads/') else root / rel_path
        dst = root / rel_path
        if not dst.parent.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            rels_copied.add(rel_path)

    for html_path in root.rglob('*.html'):
        try:
            content = html_path.read_text(encoding='utf-8', errors='ignore')
            changed = False
            for m in pat.finditer(content):
                ref = m.group(1)
                if not ref or ref.startswith('http') or ref.startswith('mailto:') or ref.startswith('tel:'):
                    continue
                # Only process local/relative refs
                rel_ref = ref.lstrip('/')
                ext = Path(rel_ref).suffix.lower()
                if ext in exts:
                    # Try to copy from staging to published
                    _copy_asset(rel_ref)
                    # Rewrite to relative path (preserve subfolders)
                    rel_url = rel_ref
                    if ref != rel_url:
                        content = content.replace(ref, rel_url)
                        changed = True
                        rewritten_refs += 1
            if changed:
                html_path.write_text(content, encoding='utf-8')
        except OSError as exc:
            logger.debug("Skipping unreadable HTML file %s: %s", html_path, exc)
            continue
    return {"rewritten_refs": rewritten_refs, "copied_files": len(rels_copied)}
# ── SSRF protection ───────────────────────────────────────────────────────────

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / AWS metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _validate_scrape_url(url: str) -> None:
    """Raise HTTPException if the URL is disallowed (bad scheme or private IP)."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid URL.")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=422,
            detail="Only http and https URLs are supported.",
        )

    hostname = parsed.hostname or ""
    if not hostname:
        raise HTTPException(status_code=422, detail="URL must include a hostname.")

    # Block raw IP addresses that resolve to private/loopback ranges
    try:
        addr = ipaddress.ip_address(hostname)
        for net in _PRIVATE_NETWORKS:
            if addr in net:
                raise HTTPException(
                    status_code=422,
                    detail="Requests to private or loopback addresses are not allowed.",
                )
    except ValueError:
        pass  # hostname is a domain name, not a raw IP — allow through


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/scrape-url")
@limiter.limit("10/minute")
async def scrape_existing_website(
    request: Request,
    body: ScrapeUrlRequest,
    current_user: dict = Depends(require_client_or_above),
):
    """
    Fetch an existing website URL and return extracted business information
    (title, description, contact details, colours, headings, etc.)  that can
    be used to pre-fill the build form or seed the AI prompt.
    """
    _validate_scrape_url(body.url)
    try:
        data = scrape_website(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Unexpected scrape error for %s: %s", body.url, exc)
        raise HTTPException(status_code=500, detail="Failed to scrape the provided URL.")
    return data


@router.post("")
async def create_website(body: CreateWebsiteRequest, request: Request,
                         current_user: dict = Depends(require_app_user_or_above)):
    user_id = current_user["sub"]
    _check_plan_limits(user_id, body.include_shopping_cart)

    if body.theme not in THEMES:
        raise HTTPException(status_code=400, detail=f"Unknown theme. Available: {list(THEMES)}")

    build_mode = (body.build_mode or "agentic_only").strip().lower()
    if build_mode not in ALLOWED_BUILD_MODES:
        raise HTTPException(status_code=400, detail=f"Unknown build_mode. Available: {sorted(ALLOWED_BUILD_MODES)}")

    output_target = (body.output_target or "legacy").strip().lower()
    if output_target not in ALLOWED_OUTPUT_TARGETS:
        raise HTTPException(status_code=400, detail=f"Unknown output_target. Available: {sorted(ALLOWED_OUTPUT_TARGETS)}")

    classification_label = (body.classification_label or body.classification or "generic").strip()
    classification_group = (body.classification_group or "general").strip()

    website_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO websites
           (website_id, user_id, name, title, description, logo_url, domain,
                hosting_env, image_storage_backend, image_storage_config,
                                theme, classification, classification_label, classification_group, build_mode, output_target,
                                custom_css, cart_features, enable_chatbot, enable_blog, enable_livestream, content_depth, status)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft')""",
        (website_id, user_id, body.name, body.title, body.description or "",
         body.logo_url or "", body.domain or "", body.hosting_env,
            body.image_storage_backend or "auto", json.dumps(body.image_storage_config or {}),
                        body.theme, body.classification, classification_label, classification_group, build_mode, output_target,
                        body.custom_css or "",
         json.dumps(body.cart_features or []),
         1 if body.enable_chatbot else 0,
         1 if body.enable_blog else 0,
         1 if body.enable_livestream else 0,
         body.content_depth),
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
    current_user: dict = Depends(require_app_user_or_above),
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

    requested_build_mode = (body.build_mode or site.get("build_mode") or "agentic_only").strip().lower()
    if requested_build_mode not in ALLOWED_BUILD_MODES:
        raise HTTPException(status_code=400, detail=f"Unknown build_mode. Available: {sorted(ALLOWED_BUILD_MODES)}")

    requested_output_target = (body.output_target or site.get("output_target") or "legacy").strip().lower()
    if requested_output_target not in ALLOWED_OUTPUT_TARGETS:
        raise HTTPException(status_code=400, detail=f"Unknown output_target. Available: {sorted(ALLOWED_OUTPUT_TARGETS)}")

    requested_class_label = (
        body.classification_label
        or site.get("classification_label")
        or site.get("classification")
        or "generic"
    ).strip()
    requested_class_group = (
        body.classification_group
        or site.get("classification_group")
        or "general"
    ).strip()

    # Collect and dedupe reference URLs while preserving order.
    reference_urls: List[str] = []
    primary_reference = (body.existing_website_url or "").strip()
    if primary_reference:
        reference_urls.append(primary_reference)
    for raw_url in (body.existing_website_urls or []):
        url = (raw_url or "").strip()
        if url and url not in reference_urls:
            reference_urls.append(url)

    if requested_build_mode == "combined" and not reference_urls:
        raise HTTPException(status_code=400, detail="Combined mode requires at least one reference URL")

    reference_usage_map: Dict[str, str] = {}
    for item in (body.reference_usage_by_url or []):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        usage = str(item.get("usage") or "").strip()
        if not url or not usage:
            continue
        reference_usage_map[url] = usage[:300]

    db.execute(
        "UPDATE websites SET build_mode = %s, output_target = %s, classification_label = %s, classification_group = %s, updated_at = CURRENT_TIMESTAMP() "
        "WHERE website_id = %s",
        (requested_build_mode, requested_output_target, requested_class_label, requested_class_group, website_id),
    )

    # Gather web/social content
    extra_context = ""

    # ── Scrape reference websites if URL(s) provided ───────────────────────────
    scraped_title = None
    nav_links: List[str] = []
    scraped_reference_summaries: List[dict] = []
    reference_images: List[str] = []
    reference_quality: List[dict] = []
    failed_reference_urls: List[str] = []
    if reference_urls:
        for idx, ref_url in enumerate(reference_urls, start=1):
            logger.info("[%s] 🔗 Scraping reference website %d/%d: %s", trace_id, idx, len(reference_urls), ref_url)
            t1 = time.time()
            try:
                per_url_usage = reference_usage_map.get(ref_url, "")
                scraped = scrape_website(ref_url)
                scraped_context = prompt_context_from_scraped_data(scraped)
                # Label this clearly as a reference/competitor site so the AI uses it for
                # domain/industry inspiration but does NOT copy the brand name or identity.
                extra_context += (
                    f"\n\n=== REFERENCE SITE {idx}/{len(reference_urls)} (for domain & content inspiration only) ===\n"
                    f"Reference URL: {ref_url}\n"
                    + (f"How to use this reference: {per_url_usage}\n" if per_url_usage else "") +
                    "The following content was scraped from a reference/competitor website. "
                    "Use it to understand the INDUSTRY, PRODUCTS, SERVICES, and TERMINOLOGY relevant to the build. "
                    "Do NOT use the brand name, logo, email, phone, or identity from this reference site. "
                    "The actual brand being built is specified in the WEBSITE BUILD SPECIFICATION above.\n\n"
                ) + scraped_context

                this_title = scraped.get("title")
                this_nav_links = [l["text"] for l in scraped.get("nav_links", []) if l.get("text")]
                this_images = scraped.get("images", [])
                this_quality = _reference_quality_metrics(scraped)
                if not scraped_title and this_title:
                    scraped_title = this_title
                nav_links.extend(this_nav_links)
                reference_images.extend(img for img in this_images if img not in reference_images)
                reference_quality.append({"url": ref_url, **this_quality})
                scraped_reference_summaries.append({
                    "url": ref_url,
                    "title": this_title,
                    "nav_links": this_nav_links,
                    "images": this_images[:10],
                })
                logger.info("[%s] 🔗 Scraping done for %s in %.1fs", trace_id, ref_url, time.time() - t1)
            except Exception as exc:
                logger.warning("[%s] Could not scrape reference URL %s: %s", trace_id, ref_url, exc)
                failed_reference_urls.append(ref_url)

        # Deduplicate nav links preserving order.
        nav_links = list(dict.fromkeys(nav_links))

        # Combined-mode reference quality check: proceed even if sparse,
        # but record a warning so user-provided context is treated as primary.
        if requested_build_mode == "combined":
            usable = [q for q in reference_quality if _is_reference_usable(q)]
            agg_headings = sum(q.get("headings", 0) for q in reference_quality)
            agg_paragraphs = sum(q.get("paragraphs", 0) for q in reference_quality)
            agg_images = sum(q.get("images", 0) for q in reference_quality)
            agg_nav = sum(q.get("nav_links", 0) for q in reference_quality)

            sparse = (
                len(usable) == 0
                or agg_headings < 2
                or agg_paragraphs < 1
                or (agg_images < 1 and agg_nav < 1)
            )

            if sparse:
                per_ref = "; ".join(
                    f"{q['url']} => title={'yes' if q.get('title') else 'no'}, "
                    f"desc_len={q.get('description_len', 0)}, headings={q.get('headings', 0)}, "
                    f"paras={q.get('paragraphs', 0)}, nav={q.get('nav_links', 0)}, images={q.get('images', 0)}"
                    for q in reference_quality
                ) or "no successful reference extraction"

                failed_hint = (
                    f" Failed URLs: {', '.join(failed_reference_urls)}."
                    if failed_reference_urls else ""
                )

                logger.warning(
                    "[%s] Combined build proceeding with sparse reference extraction. "
                    "Metrics: usable_refs=%s/%s, agg_headings=%s, agg_paragraphs=%s, agg_nav=%s, agg_images=%s. "
                    "Per-reference: %s.%s",
                    trace_id,
                    len(usable),
                    len(reference_urls),
                    agg_headings,
                    agg_paragraphs,
                    agg_nav,
                    agg_images,
                    per_ref,
                    failed_hint,
                )
                extra_context += (
                    "\n\n=== REFERENCE QUALITY WARNING ===\n"
                    "Reference extraction is sparse (limited paragraphs/nav). Use imported fields and user requirements as the primary truth."
                )

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

    # ── Assemble full LLM prompt via RequirementsAnalystAgent ─────────────────

    # Keep compatibility with older prompt logic that expects Optional[list].
    # Nav precedence: explicit menu in requirements > user-edited nav chips > scraped nav links.
    user_nav_links: List[str] = []
    req_nav_match = re.search(
        r"NAVIGATION\s*\([^\)]*\)\s*:\s*(.+)",
        body.requirements or "",
        re.I,
    )
    if req_nav_match:
        user_nav_links = [n.strip() for n in req_nav_match.group(1).split("|") if n.strip()]

    nav_links_for_prompt = (user_nav_links or body.categories or nav_links) or None

    analyst_req = AnalystRequest(
        requirements=body.requirements,
        use_web_search=body.use_web_search,
        use_social_search=body.use_social_search,
        existing_website_url=reference_urls[0] if reference_urls else None,
        existing_website_urls=reference_urls or None,
        build_mode=requested_build_mode,
        output_target=requested_output_target,
        categories=body.categories,
        catalog_items=body.catalog_items,
        location=body.location,
        email=body.email,
        phone=body.phone,
        booking_prefix=body.booking_prefix,
        niche=body.niche,
        social_links=body.social_links,
        website_id=website_id,
        include_shopping_cart=body.include_shopping_cart,
        # NOTE: scraped_title is intentionally NOT passed here — it comes from an external
        # reference/competitor URL and must not replace the user's DB site title as the business name.
        # The scraped content is already in extra_context for AI enrichment.
        scraped_title=None,
        nav_links=nav_links_for_prompt,
        classification=site.get("classification", "generic") or "generic",
        classification_label=requested_class_label,
        classification_group=requested_class_group,
        content_depth=body.content_depth,
    )
    full_prompt, cart_features = build_prompt(analyst_req, site, extra_context)

    input_snapshot = {
        "site_name": site.get("title") or site.get("name") or "",
        "requirements": body.requirements,
        "use_web_search": body.use_web_search,
        "use_social_search": body.use_social_search,
        "existing_website_url": reference_urls[0] if reference_urls else None,
        "existing_website_urls": reference_urls,
        "reference_usage_by_url": [
            {"url": u, "usage": reference_usage_map[u]} for u in reference_urls if u in reference_usage_map
        ],
        "build_mode": requested_build_mode,
        "output_target": requested_output_target,
        "classification": site.get("classification", "generic") or "generic",
        "classification_label": requested_class_label,
        "classification_group": requested_class_group,
        "categories": body.categories or [],
        "catalog_items": body.catalog_items or [],
        "location": body.location,
        "email": body.email,
        "phone": body.phone,
        "booking_prefix": body.booking_prefix,
        "niche": body.niche,
        "social_links": body.social_links or {},
        "content_depth": body.content_depth,
        "include_shopping_cart": body.include_shopping_cart,
        "enable_chatbot": bool(site.get("enable_chatbot")),
        "enable_blog": bool(site.get("enable_blog")),
        "enable_livestream": bool(site.get("enable_livestream")),
        "cart_features": cart_features,
        "theme": site.get("theme", "modern") or "modern",
    }
    source_context = {
        "scraped_title": scraped_title,
        "nav_links": nav_links_for_prompt or [],
        "reference_urls": reference_urls,
        "reference_usage_by_url": [
            {"url": u, "usage": reference_usage_map[u]} for u in reference_urls if u in reference_usage_map
        ],
        "reference_sites": scraped_reference_summaries,
        "reference_quality": reference_quality,
        "failed_reference_urls": failed_reference_urls,
        "extra_context": extra_context,
    }

    logger.info("[%s] 🏗  Prompt ready (%d chars, %d cart features, chatbot=%s) — queuing build",
                trace_id, len(full_prompt), len(cart_features), bool(site.get("enable_chatbot")))

    # Mark as queued immediately so the client can start polling
    db.execute(
        "UPDATE websites SET build_status = 'queued', build_job_id = %s, "
        "build_started_at = CURRENT_TIMESTAMP(), build_error = NULL, "
        "input_snapshot_json = %s, source_context_json = %s, updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
        (trace_id, json.dumps(input_snapshot), json.dumps(source_context), website_id),
    )

    # ── Background task — does NOT block the HTTP response ────────────────────
    # Use the DB site title/name as the project folder name — never the scraped reference URL title
    _site_name = site.get("title") or site.get("name") or ""

    def _run_build(
        wid: str,
        prompt: str,
        site_name: str,
        uid: str,
        ip: str,
        tid: str,
        t_start: float,
        theme: str = "modern",
        classification: str = "generic",
        classification_label: str = "Generic",
        classification_group: str = "general",
        build_mode: str = "agentic_only",
        output_target: str = "legacy",
        ref_imgs: list = None,
        wsite_id: str = "",
    ):
        try:
            # ── Log classification context being sent to CrewAI ──
            logger.info(
                "[%s] 🏷️  Classification context for CrewAI: key=%s label='%s' group='%s'",
                tid, classification, classification_label, classification_group
            )
            
            db.execute(
                "UPDATE websites SET build_status = 'running', updated_at = CURRENT_TIMESTAMP() "
                "WHERE website_id = %s",
                (wid,),
            )
            output_path = build_website(
                prompt,
                project_name=site_name,
                theme_key=theme,
                classification=classification,
                classification_label=classification_label,
                classification_group=classification_group,
                build_mode=build_mode,
                output_target=output_target,
                reference_images=ref_imgs,
                website_id=wsite_id,
            )
            local_path = output_path.get("output_dir", "") if isinstance(output_path, dict) else ""
            fallback_used = bool(output_path.get("fallback")) if isinstance(output_path, dict) else False
            fallback_error = output_path.get("error") if isinstance(output_path, dict) else None
            next_status = "fallback" if fallback_used else "built"

            row = db.fetchone(
                "SELECT input_snapshot_json, source_context_json FROM websites WHERE website_id = %s",
                (wid,),
            ) or {}
            snapshot_obj = _safe_json_loads(row.get("input_snapshot_json"), {})
            source_obj = _safe_json_loads(row.get("source_context_json"), {})
            narrative = _generate_build_narrative(wid, snapshot_obj, source_obj, local_path)
            source_obj["build_narrative"] = narrative
            _log_build_narrative(wid, narrative)

            db.execute(
                "UPDATE websites SET build_status = %s, "
                "build_error = %s, local_path = %s, source_context_json = %s, updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
                (next_status, fallback_error, local_path, json.dumps(source_obj), wid),
            )
            log_event("website_built", user_id=uid, website_id=wid, ip_address=ip)
            logger.info("[%s] 🎉 BUILD COMPLETE  website_id=%s  total=%.1fs",
                        tid, wid, time.time() - t_start)
        except Exception as exc:
            logger.exception("[%s] ❌ build_website FAILED after %.1fs: %s",
                             tid, time.time() - t_start, exc)
            db.execute(
                "UPDATE websites SET build_status = 'error', status = 'error', "
                "build_error = %s, updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
                (str(exc)[:1000], wid),
            )

    background_tasks.add_task(
        _run_build,
        website_id, full_prompt, _site_name, user_id,
        request.client.host, trace_id, t0,
        site.get("theme", "modern") or "modern",
        site.get("classification", "generic") or "generic",
        requested_class_label,
        requested_class_group,
        requested_build_mode,
        requested_output_target,
        reference_images or [],
        website_id,
    )

    # Optionally include the JWT token from the Authorization header if present
    token = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]

    response = {
        "message": "Build queued. Use GET /websites/{id}/build-status to track progress.",
        "job_id":    trace_id,
        "status":    "queued",
        "website_id": website_id,
        "build_mode": requested_build_mode,
        "output_target": requested_output_target,
    }
    if token:
        response["token"] = token
    return response


@router.get("/{website_id}/build-status")
async def get_build_status(
    website_id: str,
    current_user: dict = Depends(require_app_user_or_above),
):
    """
    Poll this endpoint after calling POST /{website_id}/build.

    Possible build_status values:
      • queued   — job accepted, worker not yet started
      • running  — agent pipeline actively executing
      • built    — completed successfully
      • error    — build failed; see build_error for detail
    """
    user_id = current_user["sub"]
    site = db.fetchone(
        """SELECT website_id, name, status, build_status, build_job_id,
                  build_started_at, build_error
           FROM websites
           WHERE website_id = %s AND user_id = %s""",
        (website_id, user_id),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    build_status = site.get("build_status") or "idle"
    response = {
        "website_id":      website_id,
        "name":            site.get("name"),
        "build_status":    build_status,
        "job_id":          site.get("build_job_id"),
        "started_at":      str(site.get("build_started_at") or ""),
        "complete":        build_status in ("built", "error"),
        "success":         build_status == "built",
    }
    if build_status == "error":
        response["error"] = site.get("build_error")

    return response


@router.get("/{website_id}/build-narrative")
async def get_build_narrative(
    website_id: str,
    current_user: dict = Depends(require_app_user_or_above),
):
    """Return a concrete post-build narrative explaining what happened and why."""
    user_id = current_user["sub"]
    site = db.fetchone(
        """SELECT website_id, name, build_status, local_path, input_snapshot_json, source_context_json
           FROM websites
           WHERE website_id = %s AND user_id = %s""",
        (website_id, user_id),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    source_obj = _safe_json_loads(site.get("source_context_json"), {})
    narrative = source_obj.get("build_narrative")

    if not narrative:
        snapshot_obj = _safe_json_loads(site.get("input_snapshot_json"), {})
        narrative = _generate_build_narrative(
            website_id,
            snapshot_obj,
            source_obj,
            site.get("local_path") or "",
        )
        source_obj["build_narrative"] = narrative
        db.execute(
            "UPDATE websites SET source_context_json = %s, updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
            (json.dumps(source_obj), website_id),
        )
        _log_build_narrative(website_id, narrative)

    return {
        "website_id": website_id,
        "name": site.get("name"),
        "build_status": site.get("build_status"),
        "narrative": narrative,
    }


@router.get("/{website_id}/build-stream")
async def build_status_stream(
    website_id: str,
    request: Request,
    token: str = Query(default=""),
):
    """
    Server-Sent Events stream for real-time build progress.

    Auth: pass JWT as ?token=<bearer> (EventSource can't set headers).
        Emits JSON events every 2 seconds until build_status is 'built' or 'error'.
        Connection guardrails:
            - Max stream duration: 5 minutes
            - Cleanup on client disconnect via generator finalizer
    """
    from services.auth_service import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        # Return an error event and close
        async def _auth_error():
            yield f"data: {json.dumps({'error': 'unauthorized'})}\n\n"
        return StreamingResponse(_auth_error(), media_type="text/event-stream")

    user_id = payload.get("sub")

    async def _event_generator():
        poll_interval_sec = 2
        max_duration_sec = 300
        max_ticks = max_duration_sec // poll_interval_sec
        ticks = 0
        try:
            while ticks < max_ticks:
                if await request.is_disconnected():
                    logger.info("SSE build-stream client disconnected: website_id=%s user_id=%s", website_id, user_id)
                    return

                site = db.fetchone(
                    """SELECT build_status, build_error FROM websites
                       WHERE website_id = %s AND user_id = %s""",
                    (website_id, user_id),
                )
                if not site:
                    yield f"data: {json.dumps({'build_status': 'not_found'})}\n\n"
                    return

                status = site.get("build_status") or "idle"
                payload_data = json.dumps({"build_status": status, "error": site.get("build_error")})
                yield f"data: {payload_data}\n\n"

                if status in ("built", "error"):
                    return

                await asyncio.sleep(poll_interval_sec)
                ticks += 1

            yield f"data: {json.dumps({'build_status': 'timeout'})}\n\n"
        finally:
            logger.debug("SSE build-stream cleanup complete for website_id=%s user_id=%s", website_id, user_id)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{website_id}/staged-html")
async def get_staged_html(
    website_id: str,
    current_user: dict = Depends(require_app_user_or_above),
):
    """Return the raw HTML of the staged index.html for preview/editing."""
    user_id = current_user["sub"]
    site = db.fetchone(
        "SELECT local_path FROM websites WHERE website_id = %s AND user_id = %s",
        (website_id, user_id),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    local_path = site.get("local_path") or ""
    if not local_path:
        raise HTTPException(status_code=404, detail="Website has not been built yet")
    index_file = os.path.join(local_path, "index.html")
    if not os.path.isfile(index_file):
        raise HTTPException(status_code=404, detail="index.html not found in staging area")
    with open(index_file, "r", encoding="utf-8") as f:
        html = f.read()
    return {"html": html, "path": index_file}


@router.put("/{website_id}/staged-html")
async def put_staged_html(
    website_id: str,
    body: StagedHtmlRequest,
    current_user: dict = Depends(require_app_user_or_above),
):
    """Overwrite the staged index.html with edited HTML content."""
    user_id = current_user["sub"]
    site = db.fetchone(
        "SELECT local_path FROM websites WHERE website_id = %s AND user_id = %s",
        (website_id, user_id),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    local_path = site.get("local_path") or ""
    if not local_path:
        raise HTTPException(status_code=404, detail="Website has not been built yet")
    os.makedirs(local_path, exist_ok=True)
    index_file = os.path.join(local_path, "index.html")
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(body.html)
    db.execute(
        "UPDATE websites SET build_status = 'staged', updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
        (website_id,),
    )
    return {"saved": True, "path": index_file}


@router.post("/{website_id}/deploy")
async def deploy_website(website_id: str, request: Request,
                         current_user: dict = Depends(require_app_user_or_above)):
    import datetime
    user_id = current_user["sub"]
    print(f"[deploy] {datetime.datetime.now().isoformat()} user={user_id} website_id={website_id} from={request.client.host}")
    site = db.fetchone(
        "SELECT * FROM websites WHERE website_id = %s AND user_id = %s",
        (website_id, user_id),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    local_path = site.get("local_path") or ""

    # ── S3 deploy ──────────────────────────────────────────────────────────
    has_s3_creds = bool(settings.AWS_ACCESS_KEY_ID and settings.S3_BUCKET_NAME)
    if site["hosting_env"] == "s3" and has_s3_creds:
        url = deploy_to_s3(
            local_dir=local_path or settings.OUTPUT_DIR,
            bucket_name=site.get("s3_bucket") or settings.S3_BUCKET_NAME or "",
            access_key=settings.AWS_ACCESS_KEY_ID or "",
            secret_key=settings.AWS_SECRET_ACCESS_KEY or "",
            region=settings.AWS_REGION,
            prefix=website_id,
        )
        if not url:
            raise HTTPException(status_code=500, detail="S3 deployment failed. Check AWS credentials.")
        db.execute(
            "UPDATE websites SET s3_url = %s, status = 'live', updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
            (url, website_id),
        )
        log_event("website_deployed", user_id=user_id, website_id=website_id,
                  ip_address=request.client.host, meta={"url": url})
        return {"url": url, "target": "s3"}

    # ── Local / Go-Live deploy (copy staging → output/published/<website_id>/) ──
    if not local_path or not os.path.isdir(local_path):
        raise HTTPException(status_code=400, detail="No staged build found. Build the website first.")
    import shutil
    published_dir = os.path.join("output", "published", website_id)
    if os.path.exists(published_dir):
        shutil.rmtree(published_dir)
    shutil.copytree(local_path, published_dir)
    bundle_stats = _bundle_local_upload_assets(published_dir)
    # Also bundle all referenced local assets (img, css, js, fonts)
    all_asset_stats = _bundle_all_local_assets(published_dir, local_path)

    # ── Optional Google Drive deploy for full website files ────────────────
    if (site.get("image_storage_backend") or "").strip().lower() == "gdrive":
        cfg_raw = site.get("image_storage_config")
        cfg = {}
        if isinstance(cfg_raw, dict):
            cfg = cfg_raw
        elif isinstance(cfg_raw, str) and cfg_raw.strip():
            try:
                cfg = json.loads(cfg_raw)
            except Exception:
                cfg = {}

        secrets = decrypt_json(site.get("image_storage_secrets_enc"))
        service_account_file = (
            str((secrets or {}).get("service_account_file") or "").strip()
            or os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "")
        )
        oauth_token = str((secrets or {}).get("oauth_token") or "").strip()
        folder_id = (
            str(cfg.get("folder_id") or "").strip()
            or os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
        )

        if folder_id and (service_account_file or oauth_token):
            try:
                gdrive_result = deploy_directory_to_gdrive(
                    local_dir=published_dir,
                    parent_folder_id=folder_id,
                    site_folder_name=f"{site.get('name') or 'website'}-{website_id[:8]}",
                    service_account_file=service_account_file,
                    oauth_token=oauth_token,
                )
            except Exception as exc:
                logger.exception("Google Drive deploy failed for website_id=%s", website_id)
                raise HTTPException(status_code=500, detail=str(exc))
            if gdrive_result and gdrive_result.get("url"):
                gdrive_url = gdrive_result.get("url")
                db.execute(
                    "UPDATE websites SET status = 'live', live_url = %s, updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
                    (gdrive_url, website_id),
                )
                log_event("website_deployed", user_id=user_id, website_id=website_id,
                          ip_address=request.client.host, meta={
                              "url": gdrive_url,
                              "target": "gdrive",
                              "folder_id": gdrive_result.get("folder_id"),
                              "folder_name": gdrive_result.get("folder_name"),
                              "files_uploaded": gdrive_result.get("files_uploaded", 0),
                              "bundled_refs": bundle_stats.get("rewritten_refs", 0),
                              "bundled_files": bundle_stats.get("copied_files", 0),
                              "all_asset_refs": all_asset_stats.get("rewritten_refs", 0),
                              "all_asset_files": all_asset_stats.get("copied_files", 0),
                          })
                return {
                    "url": gdrive_url,
                    "target": "gdrive",
                    "folder_id": gdrive_result.get("folder_id"),
                    "folder_name": gdrive_result.get("folder_name"),
                    "files_uploaded": gdrive_result.get("files_uploaded", 0),
                    "bundled_refs": bundle_stats.get("rewritten_refs", 0),
                    "bundled_files": bundle_stats.get("copied_files", 0),
                    "all_asset_refs": all_asset_stats.get("rewritten_refs", 0),
                    "all_asset_files": all_asset_stats.get("copied_files", 0),
                }
            raise HTTPException(
                status_code=500,
                detail="Google Drive deployment failed. Verify credentials and folder access.",
            )

        missing = []
        if not folder_id:
            missing.append("folder id")
        if not service_account_file and not oauth_token:
            missing.append("credentials (service_account_file or oauth_token)")
        raise HTTPException(
            status_code=400,
            detail=f"Google Drive deployment is configured but missing {' and '.join(missing)}. Set these in Storage settings.",
        )

    live_url = f"/output/published/{website_id}/index.html"
    # Keep local_path pointing to staging so editor/preview still works
    db.execute(
        "UPDATE websites SET status = 'live', live_url = %s, updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
        (live_url, website_id),
    )
    log_event("website_deployed", user_id=user_id, website_id=website_id,
              ip_address=request.client.host, meta={"url": live_url, "target": "local"})
    return {"url": live_url, "target": "local"}


@router.patch("/{website_id}")
async def update_website(website_id: str, body: UpdateWebsiteRequest,
                         current_user: dict = Depends(require_client_or_above)):
    user_id = current_user["sub"]
    role = current_user.get("role", "app_user")

    if role == "client":
        # Clients may only edit their own linked website
        u = db.fetchone("SELECT client_website_id FROM users WHERE user_id = ?", (user_id,))
        if not u or u.get("client_website_id") != website_id:
            raise HTTPException(status_code=403, detail="Clients can only edit their own website")
        site = db.fetchone("SELECT website_id FROM websites WHERE website_id = ?", (website_id,))
    else:
        site = db.fetchone(
            "SELECT website_id FROM websites WHERE website_id = %s AND user_id = %s",
            (website_id, user_id),
        )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"message": "Nothing to update"}

    if "image_storage_config" in updates and not isinstance(updates["image_storage_config"], str):
        updates["image_storage_config"] = json.dumps(updates["image_storage_config"] or {})

    if "image_storage_secrets" in updates:
        secrets = updates.pop("image_storage_secrets") or {}
        if not isinstance(secrets, dict):
            raise HTTPException(status_code=400, detail="image_storage_secrets must be a JSON object")
        if secrets:
            if not can_encrypt():
                raise HTTPException(status_code=400, detail="Server encryption key missing. Set STORAGE_SECRETS_KEY")
            updates["image_storage_secrets_enc"] = encrypt_json(secrets)

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = tuple(updates.values()) + (website_id,)
    db.execute(
        f"UPDATE websites SET {set_clause}, updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
        values,
    )
    return {"message": "Website updated"}


@router.delete("/{website_id}")
async def delete_website(website_id: str, current_user: dict = Depends(require_app_user_or_above)):
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
async def list_my_websites(
    page:  int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_client_or_above),
):
    """Return websites visible to the current user (paginated).
    - app_user: all their own websites
    - client: only their single linked website (client_website_id)
    - sub-user (owner_id set): their owner's websites
    """
    user_id = current_user["sub"]
    role = current_user.get("role", "app_user")
    offset = (page - 1) * limit

    if role == "client":
        # Clients see only the one website they are linked to
        u = db.fetchone("SELECT client_website_id FROM users WHERE user_id = ?", (user_id,))
        website_id = u.get("client_website_id") if u else None
        if not website_id:
            return {"items": [], "total": 0, "page": page, "pages": 1}
        site = db.fetchone(
            "SELECT website_id, name, title, theme, classification, classification_label, classification_group, build_mode, output_target, "
            "status, domain, s3_url, cart_features, image_storage_backend, image_storage_config, "
            "enable_chatbot, enable_blog, enable_livestream, local_path, build_status, created_at, updated_at "
            "FROM websites WHERE website_id = ?",
            (website_id,),
        )
        items = [site] if site else []
        return {"items": items, "total": len(items), "page": 1, "pages": 1}

    # app_user / superuser — also follow owner_id for sub-users
    u = db.fetchone("SELECT owner_id FROM users WHERE user_id = ?", (user_id,))
    owner_id = u.get("owner_id") if u else None
    effective_id = owner_id if owner_id else user_id

    total_row = db.fetchone("SELECT COUNT(*) AS cnt FROM websites WHERE user_id = ?", (effective_id,))
    total = total_row["cnt"] if total_row else 0

    items = db.fetchall(
        "SELECT website_id, name, title, theme, classification, classification_label, classification_group, build_mode, output_target, "
        "status, domain, s3_url, cart_features, image_storage_backend, image_storage_config, enable_chatbot, enable_blog, enable_livestream, local_path, build_status, created_at, updated_at "
        "FROM websites WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (effective_id, limit, offset),
    ) or []
    return {"items": items, "total": total, "page": page, "pages": max(1, -(-total // limit))}


@router.get("")
async def list_websites(
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    offset  = (page - 1) * limit

    total_row = db.fetchone(
        "SELECT COUNT(*) AS cnt FROM websites WHERE user_id = %s",
        (user_id,),
    )
    total = total_row["cnt"] if total_row else 0

    items = db.fetchall(
        "SELECT website_id, name, title, theme, classification, classification_label, classification_group, build_mode, output_target, status, domain, s3_url, image_storage_backend, image_storage_config, local_path, build_status, created_at"
        " FROM websites WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (user_id, limit, offset),
    ) or []
    return {
        "items": items,
        "total": total,
        "page":  page,
        "pages": max(1, -(-total // limit)),
    }


@router.get("/themes")
async def list_themes():
    return [{"key": k, **{f: v for f, v in v.items() if f == "label"}} for k, v in THEMES.items()]
