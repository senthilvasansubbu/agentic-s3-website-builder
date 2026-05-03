from services.image_service import finalize_image
# Finalize image: move from uploads to images and return new path
from fastapi import APIRouter, Body, Depends, HTTPException
from api.routes.auth import require_app_user_or_above

router = APIRouter()

@router.post("/shop/finalize-image")
async def api_finalize_image(
    site_slug: str = Body(...),
    filename: str = Body(...),
    current_user: dict = Depends(require_app_user_or_above),
):
    # Optionally: check user owns the site (omitted for brevity)
    try:
        image_url = finalize_image(site_slug, filename)
        return {"image_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
"""
Website builder API routes — create, list, build, deploy, customise websites.
"""
import uuid
import json
import os
import logging
import time
import asyncio
import re
import shutil
from pathlib import Path
from urllib.parse import unquote
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

from api.routes.auth import get_current_user, require_app_user_or_above, require_client_or_above
from database.snowflake_client import db
from agents.crew import build_website
from agents.requirements_analyst import build_prompt, BuildRequest as AnalystRequest
from tools.theme_builder import THEMES, render_page
from tools.web_search import search_for_website_content
from tools.social_media_search import social_context_for_topic
from tools.website_scraper import scrape_website, scrape_to_prompt_context
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


# ── Schemas ────────────────────────────────────────────────────────────────────

class CreateWebsiteRequest(BaseModel):
    name: str
    title: str
    description: Optional[str] = None
    theme: str = "modern"
    classification: str = "generic"
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
    num_pages: int = 1
    custom_css: Optional[str] = None


class BuildWebsiteRequest(BaseModel):
    requirements: str                  # natural language
    use_web_search: bool = True
    use_social_search: bool = False
    existing_website_url: Optional[str] = None      # scrape this URL to pre-seed the build
    num_pages: int = 1                              # number of pages to generate
    include_shopping_cart: bool = False             # enable e-commerce / cart features
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
    image_storage_backend: Optional[str] = None
    image_storage_config: Optional[dict] = None
    image_storage_secrets: Optional[dict] = None


class ScrapeUrlRequest(BaseModel):
    url: str


class StagedHtmlRequest(BaseModel):
    html: str


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
        except Exception:
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
        except Exception:
            continue
    return {"rewritten_refs": rewritten_refs, "copied_files": len(rels_copied)}
# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/scrape-url")
async def scrape_existing_website(
    body: ScrapeUrlRequest,
    current_user: dict = Depends(require_client_or_above),
):
    """
    Fetch an existing website URL and return extracted business information
    (title, description, contact details, colours, headings, etc.)  that can
    be used to pre-fill the build form or seed the AI prompt.
    """
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
    _check_plan_limits(user_id, body.num_pages, body.include_shopping_cart)

    if body.theme not in THEMES:
        raise HTTPException(status_code=400, detail=f"Unknown theme. Available: {list(THEMES)}")

    website_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO websites
           (website_id, user_id, name, title, description, logo_url, domain,
                hosting_env, image_storage_backend, image_storage_config,
                theme, classification, custom_css, cart_features, enable_chatbot, enable_blog, enable_livestream, status)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft')""",
        (website_id, user_id, body.name, body.title, body.description or "",
         body.logo_url or "", body.domain or "", body.hosting_env,
            body.image_storage_backend or "auto", json.dumps(body.image_storage_config or {}),
            body.theme, body.classification, body.custom_css or "",
         json.dumps(body.cart_features or []),
         1 if body.enable_chatbot else 0,
         1 if body.enable_blog else 0,
         1 if body.enable_livestream else 0),
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

    # Gather web/social content
    extra_context = ""

    # ── Scrape existing website if URL provided ────────────────────────────────
    if body.existing_website_url:
        logger.info("[%s] 🔗 Scraping existing website: %s", trace_id, body.existing_website_url)
        t1 = time.time()
        scraped_context = scrape_to_prompt_context(body.existing_website_url)
        extra_context += "\n\n" + scraped_context
        logger.info("[%s] 🔗 Scraping done in %.1fs", trace_id, time.time() - t1)

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

    # If scraping, extract title and nav_links for prompt
    scraped_title = None
    nav_links = None
    if body.existing_website_url:
        try:
            scraped = scrape_website(body.existing_website_url)
            scraped_title = scraped.get('title')
            nav_links = [l['text'] for l in scraped.get('nav_links', []) if l.get('text')]
        except Exception as exc:
            logger.warning("[%s] Could not extract title/nav_links from scrape: %s", trace_id, exc)

    analyst_req = AnalystRequest(
        requirements=body.requirements,
        use_web_search=body.use_web_search,
        use_social_search=body.use_social_search,
        existing_website_url=body.existing_website_url,
        categories=body.categories,
        location=body.location,
        email=body.email,
        phone=body.phone,
        booking_prefix=body.booking_prefix,
        social_links=body.social_links,
        website_id=website_id,
        include_shopping_cart=body.include_shopping_cart,
        scraped_title=scraped_title,
        nav_links=nav_links,
    )
    full_prompt, cart_features = build_prompt(analyst_req, site, extra_context)

    logger.info("[%s] 🏗  Prompt ready (%d chars, %d cart features, chatbot=%s) — queuing build",
                trace_id, len(full_prompt), len(cart_features), bool(site.get("enable_chatbot")))

    # Mark as queued immediately so the client can start polling
    db.execute(
        "UPDATE websites SET build_status = 'queued', build_job_id = %s, "
        "build_started_at = CURRENT_TIMESTAMP(), build_error = NULL, "
        "updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
        (trace_id, website_id),
    )

    # ── Background task — does NOT block the HTTP response ────────────────────
    # Use the real site name as the project/folder name (not first words of the prompt)
    _site_name = site.get("name") or site.get("title") or ""
    if scraped_title:
        _site_name = scraped_title
        # Strip duplicate suffix e.g. "Foo – Foo" → "Foo"
        if " – " in _site_name:
            _parts = [p.strip() for p in _site_name.split(" – ")]
            if _parts[0] == _parts[-1]:
                _site_name = _parts[0]

    def _run_build(wid: str, prompt: str, site_name: str, uid: str, ip: str, tid: str, t_start: float, theme: str = "modern", classification: str = "generic"):
        try:
            db.execute(
                "UPDATE websites SET build_status = 'running', updated_at = CURRENT_TIMESTAMP() "
                "WHERE website_id = %s",
                (wid,),
            )
            output_path = build_website(prompt, project_name=site_name, theme_key=theme, classification=classification)
            local_path = output_path.get("output_dir", "") if isinstance(output_path, dict) else ""
            db.execute(
                "UPDATE websites SET build_status = 'built', status = 'built', "
                "build_error = NULL, local_path = %s, updated_at = CURRENT_TIMESTAMP() WHERE website_id = %s",
                (local_path, wid),
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
        max_ticks = 150          # 5 min (150 × 2s)
        ticks = 0
        while ticks < max_ticks:
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

            await asyncio.sleep(2)
            ticks += 1

        yield f"data: {json.dumps({'build_status': 'timeout'})}\n\n"

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
            "SELECT website_id, name, title, theme, status, domain, s3_url, cart_features, image_storage_backend, image_storage_config, "
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
        "SELECT website_id, name, title, theme, status, domain, s3_url, cart_features, image_storage_backend, image_storage_config, enable_chatbot, enable_blog, enable_livestream, local_path, build_status, created_at, updated_at "
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
        "SELECT website_id, name, title, theme, status, domain, s3_url, image_storage_backend, image_storage_config, local_path, build_status, created_at"
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
