"""Website editor/uploader media routes, isolated from shopping cart APIs."""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import Query

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from api.routes.auth import require_client_or_above
from database.snowflake_client import db
from services.image_service import ALLOWED_MIME, finalize_image, process_image
from services.secret_store import decrypt_json

router = APIRouter(prefix="/media", tags=["media"])
logger = logging.getLogger("website_builder.media")

_APP_ROOT = Path(__file__).resolve().parents[2]
_OUTPUT_ROOT = (_APP_ROOT / "output").resolve()


class FinalizeImageRequest(BaseModel):
    website_id: str
    site_slug: str
    filename: str


class SocialLinkCreateRequest(BaseModel):
    website_id: str
    url: str
    display_name: Optional[str] = None
    provider: Optional[str] = None


def _friendly_image_name(filename: str) -> str:
    stem = Path(str(filename or "").strip()).stem
    if not stem:
        return "Uploaded Image"
    cleaned = re.sub(r"[_\-]+", " ", stem)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:120] if cleaned else "Uploaded Image"


def _asset_filename_from_path(image_path: str) -> str:
    clean = str(image_path or "").strip().split("?")[0].split("#")[0]
    return Path(clean).name if clean else ""


def _ensure_uploaded_images_table() -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS website_uploaded_images (
            image_id TEXT PRIMARY KEY,
            website_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            asset_filename TEXT NOT NULL,
            image_path TEXT NOT NULL,
            original_filename TEXT,
            display_name TEXT,
            is_finalized INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            deleted_at DATETIME,
            deleted_by TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cols = {
        str(r.get("name") or "").strip().lower()
        for r in (db.fetchall("PRAGMA table_info(website_uploaded_images)") or [])
    }
    if "is_deleted" not in cols:
        db.execute("ALTER TABLE website_uploaded_images ADD COLUMN is_deleted INTEGER DEFAULT 0")
    if "deleted_at" not in cols:
        db.execute("ALTER TABLE website_uploaded_images ADD COLUMN deleted_at DATETIME")
    if "deleted_by" not in cols:
        db.execute("ALTER TABLE website_uploaded_images ADD COLUMN deleted_by TEXT")

    try:
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_uploaded_images_site_file ON website_uploaded_images(website_id, asset_filename)"
        )
    except Exception:
        pass


def _upsert_uploaded_image_record(
    website_id: str,
    user_id: str,
    asset_filename: str,
    image_path: str,
    *,
    original_filename: Optional[str] = None,
    display_name: Optional[str] = None,
    is_finalized: bool = False,
) -> None:
    if not website_id or not asset_filename or not image_path:
        return
    _ensure_uploaded_images_table()
    existing = db.fetchone(
        "SELECT image_id, original_filename, display_name FROM website_uploaded_images WHERE website_id = ? AND asset_filename = ?",
        (website_id, asset_filename),
    )
    if existing:
        next_original = original_filename or existing.get("original_filename") or ""
        next_display = display_name or existing.get("display_name") or _friendly_image_name(next_original or asset_filename)
        db.execute(
            "UPDATE website_uploaded_images SET image_path = ?, original_filename = ?, display_name = ?, is_finalized = ?, is_deleted = 0, deleted_at = NULL, deleted_by = NULL, updated_at = CURRENT_TIMESTAMP WHERE image_id = ?",
            (image_path, next_original, next_display, 1 if is_finalized else 0, existing.get("image_id")),
        )
        return

    image_id = str(uuid.uuid4())
    original_name = original_filename or ""
    display = display_name or _friendly_image_name(original_name or asset_filename)
    db.execute(
        "INSERT INTO website_uploaded_images (image_id, website_id, user_id, asset_filename, image_path, original_filename, display_name, is_finalized, is_deleted) VALUES (?,?,?,?,?,?,?,?,0)",
        (image_id, website_id, user_id, asset_filename, image_path, original_name, display, 1 if is_finalized else 0),
    )


def _assert_website_access(website_id: str, user: dict):
    site = db.fetchone(
        "SELECT user_id FROM websites WHERE website_id = ?",
        (website_id,),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    role = user.get("role", "app_user")
    user_id = user["sub"]

    if role == "superuser":
        return

    if role == "client":
        row = db.fetchone(
            "SELECT client_website_id FROM users WHERE user_id = ?",
            (user_id,),
        )
        if not row or row.get("client_website_id") != website_id:
            raise HTTPException(status_code=403, detail="Clients can only access their linked website")
        return

    if site.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your website")


def _website_site_slug(website_id: str) -> str:
    site = db.fetchone("SELECT local_path FROM websites WHERE website_id = ?", (website_id,))
    local_path = str((site or {}).get("local_path") or "").strip().rstrip("/\\")
    return Path(local_path).name if local_path else ""


def _ensure_uploaded_media_table() -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS website_uploaded_media (
            media_id TEXT PRIMARY KEY,
            website_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            media_type TEXT NOT NULL,
            asset_filename TEXT,
            media_path TEXT,
            external_url TEXT,
            display_name TEXT,
            provider TEXT,
            mime_type TEXT,
            is_deleted INTEGER DEFAULT 0,
            deleted_at DATETIME,
            deleted_by TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    try:
        db.execute(
            "CREATE INDEX IF NOT EXISTS ix_uploaded_media_site_type ON website_uploaded_media(website_id, media_type, updated_at)"
        )
    except Exception:
        pass


def _safe_asset_name(name: str) -> str:
    raw = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(name or "").strip())
    raw = re.sub(r"-+", "-", raw).strip("-.")
    return raw[:140] if raw else "media"


def _friendly_social_name(url: str, display_name: str = "", provider: str = "") -> str:
    if display_name and display_name.strip():
        return display_name.strip()[:120]
    if provider and provider.strip():
        return provider.strip()[:120]
    clean = str(url or "").strip()
    if not clean:
        return "Social Link"
    try:
        no_scheme = re.sub(r"^https?://", "", clean, flags=re.IGNORECASE)
        host = no_scheme.split("/")[0].strip()
        return host[:120] if host else "Social Link"
    except Exception:
        return "Social Link"


def _derive_social_provider(url: str) -> str:
    clean = str(url or "").strip().lower()
    if not clean:
        return ""
    host = re.sub(r"^https?://", "", clean, flags=re.IGNORECASE).split("/")[0].strip()
    if not host:
        return ""
    if "instagram." in host:
        return "instagram"
    if "facebook." in host:
        return "facebook"
    if "youtube." in host or "youtu.be" in host:
        return "youtube"
    if "linkedin." in host:
        return "linkedin"
    if "x.com" in host or "twitter." in host:
        return "x"
    if "tiktok." in host:
        return "tiktok"
    if "pinterest." in host:
        return "pinterest"
    if "snapchat." in host:
        return "snapchat"
    return host.replace("www.", "").split(":")[0][:80]


def _insert_media_record(
    *,
    website_id: str,
    user_id: str,
    media_type: str,
    asset_filename: str = "",
    media_path: str = "",
    external_url: str = "",
    display_name: str = "",
    provider: str = "",
    mime_type: str = "",
) -> str:
    _ensure_uploaded_media_table()
    media_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO website_uploaded_media (media_id, website_id, user_id, media_type, asset_filename, media_path, external_url, display_name, provider, mime_type, is_deleted) VALUES (?,?,?,?,?,?,?,?,?,?,0)",
        (
            media_id,
            website_id,
            user_id,
            media_type,
            asset_filename,
            media_path,
            external_url,
            display_name,
            provider,
            mime_type,
        ),
    )
    return media_id


def _safe_candidates_for_delete(site_slug: str, asset_filename: str, image_path: str):
    candidates = []
    rel_path = str(image_path or "").split("?")[0].split("#")[0].lstrip("/")
    if rel_path:
        resolved = (_APP_ROOT / rel_path).resolve()
        try:
            resolved.relative_to(_OUTPUT_ROOT)
            candidates.append(resolved)
        except Exception:
            pass

    if site_slug and asset_filename:
        for folder in ("images", "uploads"):
            candidate = (_OUTPUT_ROOT / "staging" / site_slug / "assets" / folder / asset_filename).resolve()
            try:
                candidate.relative_to(_OUTPUT_ROOT)
                candidates.append(candidate)
            except Exception:
                continue

    unique = []
    seen = set()
    for c in candidates:
        key = str(c)
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique


@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    website_id: Optional[str] = Form(None),
    current_user: dict = Depends(require_client_or_above),
):
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type {content_type!r}. Allowed: JPEG, PNG, WebP, GIF, BMP, TIFF.",
        )

    raw = await file.read()
    storage_override = None
    site_slug = "website"
    if website_id:
        _assert_website_access(website_id, current_user)
        site = db.fetchone(
            "SELECT image_storage_backend, image_storage_config, image_storage_secrets_enc, local_path FROM websites WHERE website_id = ?",
            (website_id,),
        )
        if site:
            local_path = str(site.get("local_path") or "").strip().rstrip("/\\")
            if local_path:
                site_slug = Path(local_path).name or site_slug
            cfg_raw = site.get("image_storage_config")
            cfg = {}
            if isinstance(cfg_raw, dict):
                cfg = cfg_raw
            elif isinstance(cfg_raw, str) and cfg_raw.strip():
                try:
                    cfg = json.loads(cfg_raw)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    logger.debug("Invalid image_storage_config JSON for website_id=%s: %s", website_id, exc)
                    cfg = {}
            secrets = decrypt_json(site.get("image_storage_secrets_enc"))
            storage_override = {
                "backend": (site.get("image_storage_backend") or "auto"),
                "folder_id": cfg.get("folder_id") or "",
                "gdrive_subfolder": cfg.get("gdrive_subfolder") or "",
                "s3_bucket": cfg.get("s3_bucket") or "",
                "s3_prefix": cfg.get("s3_prefix") or "",
                "onedrive_folder": cfg.get("onedrive_folder") or "",
                "onedrive_subfolder": cfg.get("onedrive_subfolder") or "",
                "ftp_remote_dir": cfg.get("ftp_remote_dir") or "",
                "ftp_public_base_url": cfg.get("ftp_public_base_url") or "",
            }
            storage_override.update(secrets)

    try:
        result = process_image(
            raw,
            original_filename=file.filename or "",
            site_slug=site_slug,
            storage_override=storage_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Image processing error: %s", exc)
        raise HTTPException(status_code=500, detail="Image processing failed.")

    compression = round(100 * (1 - result.full_size / max(result.original_size, 1)))
    if website_id:
        try:
            asset_filename = Path(result.full_url).name
            _upsert_uploaded_image_record(
                website_id,
                current_user.get("sub", ""),
                asset_filename,
                result.full_url,
                original_filename=file.filename or "",
                display_name=_friendly_image_name(file.filename or asset_filename),
                is_finalized=False,
            )
        except Exception as exc:
            logger.debug("Failed to persist uploaded image metadata for website_id=%s: %s", website_id, exc)

    return {
        "thumb_url": result.thumb_url,
        "full_url": result.full_url,
        "width": result.width,
        "height": result.height,
        "thumb_size_kb": round(result.thumb_size / 1024, 1),
        "full_size_kb": round(result.full_size / 1024, 1),
        "original_size_kb": round(result.original_size / 1024, 1),
        "compression_pct": compression,
    }


@router.post("/finalize-image")
async def finalize_uploaded_image(
    body: FinalizeImageRequest,
    current_user: dict = Depends(require_client_or_above),
):
    _assert_website_access(body.website_id, current_user)

    filename = (body.filename or "").strip()
    site_slug = (body.site_slug or "").strip()
    if not filename or not site_slug:
        raise HTTPException(status_code=400, detail="site_slug and filename are required")
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    try:
        image_url = finalize_image(site_slug, filename)
        try:
            _upsert_uploaded_image_record(
                body.website_id,
                current_user.get("sub", ""),
                filename,
                image_url,
                is_finalized=True,
            )
        except Exception as exc:
            logger.debug(
                "Failed to update finalize metadata for website_id=%s filename=%s: %s",
                body.website_id,
                filename,
                exc,
            )
        return {"image_url": image_url}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found in uploads")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to finalize image for site_slug=%s: %s", site_slug, exc)
        raise HTTPException(status_code=400, detail="Failed to finalize image")


@router.get("/site-images/{website_id}")
async def list_site_images(
    website_id: str,
    current_user: dict = Depends(require_client_or_above),
):
    _assert_website_access(website_id, current_user)
    _ensure_uploaded_images_table()
    rows = db.fetchall(
        "SELECT image_id, image_path, asset_filename, original_filename, display_name, is_finalized, created_at, updated_at "
        "FROM website_uploaded_images "
        "WHERE website_id = ? AND COALESCE(is_deleted, 0) = 0 "
        "ORDER BY updated_at DESC, created_at DESC",
        (website_id,),
    ) or []
    items = []
    for row in rows:
        path = str(row.get("image_path") or "").strip()
        if not path:
            continue
        folder = "images" if "/images/" in f"/{path}" else ("uploads" if "/uploads/" in f"/{path}" else "unknown")
        display_name = (row.get("display_name") or "").strip() or _friendly_image_name(
            row.get("original_filename") or row.get("asset_filename") or ""
        )
        items.append(
            {
                "image_id": row.get("image_id"),
                "path": path,
                "name": display_name,
                "filename": row.get("asset_filename") or _asset_filename_from_path(path),
                "folder": folder,
                "is_finalized": bool(int(row.get("is_finalized") or 0)),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
            }
        )
    return {"items": items}


@router.post("/upload-video")
async def upload_video(
    file: UploadFile = File(...),
    website_id: str = Form(...),
    current_user: dict = Depends(require_client_or_above),
):
    _assert_website_access(website_id, current_user)

    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if not content_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="Unsupported video type")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty video file")
    if len(raw) > 150 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Video too large (max 150MB)")

    site_slug = _website_site_slug(website_id)
    if not site_slug:
        raise HTTPException(status_code=400, detail="Unable to resolve site folder")

    original = str(file.filename or "video.mp4")
    ext = Path(original).suffix.lower() or ".mp4"
    if ext not in {".mp4", ".webm", ".ogg", ".mov", ".m4v"}:
        ext = ".mp4"
    safe_name = _safe_asset_name(Path(original).stem)
    asset_filename = f"{uuid.uuid4().hex[:12]}-{safe_name}{ext}"
    rel_path = f"assets/videos/{asset_filename}"
    abs_path = (_OUTPUT_ROOT / "staging" / site_slug / rel_path).resolve()
    try:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(raw)
    except Exception as exc:
        logger.error("Failed to write uploaded video: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to store video")

    media_id = _insert_media_record(
        website_id=website_id,
        user_id=current_user.get("sub", ""),
        media_type="video",
        asset_filename=asset_filename,
        media_path=rel_path,
        display_name=_friendly_image_name(original),
        mime_type=content_type,
    )

    return {
        "media_id": media_id,
        "media_type": "video",
        "path": rel_path,
        "url": rel_path,
        "name": _friendly_image_name(original),
        "mime_type": content_type,
        "size_bytes": len(raw),
    }


@router.post("/site-links")
async def create_site_link(
    body: SocialLinkCreateRequest,
    current_user: dict = Depends(require_client_or_above),
):
    _assert_website_access(body.website_id, current_user)
    url = str(body.url or "").strip()
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Social URL must start with http:// or https://")

    provider = str(body.provider or "").strip()[:80] or _derive_social_provider(url)
    display = _friendly_social_name(url, str(body.display_name or ""), provider)
    media_id = _insert_media_record(
        website_id=body.website_id,
        user_id=current_user.get("sub", ""),
        media_type="social",
        external_url=url,
        display_name=display,
        provider=provider,
        mime_type="text/uri-list",
    )

    return {
        "media_id": media_id,
        "media_type": "social",
        "url": url,
        "name": display,
        "provider": provider,
    }


@router.get("/site-media/{website_id}")
async def list_site_media(
    website_id: str,
    media_type: str = Query(default="all"),
    current_user: dict = Depends(require_client_or_above),
):
    _assert_website_access(website_id, current_user)
    mtype = str(media_type or "all").strip().lower()
    if mtype not in {"all", "image", "video", "social"}:
        raise HTTPException(status_code=400, detail="Invalid media_type")

    _ensure_uploaded_images_table()
    _ensure_uploaded_media_table()

    items = []
    if mtype in {"all", "image"}:
        rows = db.fetchall(
            "SELECT image_id, image_path, asset_filename, original_filename, display_name, is_finalized, created_at, updated_at "
            "FROM website_uploaded_images "
            "WHERE website_id = ? AND COALESCE(is_deleted, 0) = 0 "
            "ORDER BY updated_at DESC, created_at DESC",
            (website_id,),
        ) or []
        for row in rows:
            path = str(row.get("image_path") or "").strip()
            if not path:
                continue
            folder = "images" if "/images/" in f"/{path}" else ("uploads" if "/uploads/" in f"/{path}" else "unknown")
            display_name = (row.get("display_name") or "").strip() or _friendly_image_name(
                row.get("original_filename") or row.get("asset_filename") or ""
            )
            items.append(
                {
                    "media_id": row.get("image_id"),
                    "image_id": row.get("image_id"),
                    "media_type": "image",
                    "path": path,
                    "url": path,
                    "name": display_name,
                    "filename": row.get("asset_filename") or _asset_filename_from_path(path),
                    "folder": folder,
                    "is_finalized": bool(int(row.get("is_finalized") or 0)),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                }
            )

    if mtype in {"all", "video", "social"}:
        params = [website_id]
        q = (
            "SELECT media_id, media_type, asset_filename, media_path, external_url, display_name, provider, mime_type, created_at, updated_at "
            "FROM website_uploaded_media "
            "WHERE website_id = ? AND COALESCE(is_deleted, 0) = 0"
        )
        if mtype in {"video", "social"}:
            q += " AND media_type = ?"
            params.append(mtype)
        q += " ORDER BY updated_at DESC, created_at DESC"
        rows = db.fetchall(q, tuple(params)) or []
        for row in rows:
            mt = str(row.get("media_type") or "").strip().lower()
            path = str(row.get("media_path") or "").strip()
            ext_url = str(row.get("external_url") or "").strip()
            items.append(
                {
                    "media_id": row.get("media_id"),
                    "media_type": mt,
                    "path": path,
                    "url": ext_url or path,
                    "name": (row.get("display_name") or "").strip() or "Uploaded Media",
                    "filename": row.get("asset_filename") or "",
                    "provider": (row.get("provider") or _derive_social_provider(ext_url) or ""),
                    "mime_type": row.get("mime_type") or "",
                    "folder": "videos" if mt == "video" else "external",
                    "is_finalized": True,
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                }
            )

    items.sort(key=lambda x: str(x.get("updated_at") or x.get("created_at") or ""), reverse=True)
    return {"items": items}


@router.delete("/site-media/{website_id}/{media_id}")
async def delete_site_media(
    website_id: str,
    media_id: str,
    current_user: dict = Depends(require_client_or_above),
):
    _assert_website_access(website_id, current_user)
    _ensure_uploaded_images_table()
    _ensure_uploaded_media_table()

    img_row = db.fetchone(
        "SELECT image_id, asset_filename, image_path FROM website_uploaded_images "
        "WHERE website_id = ? AND image_id = ? AND COALESCE(is_deleted, 0) = 0",
        (website_id, media_id),
    )
    if img_row:
        site_slug = _website_site_slug(website_id)
        asset_filename = str(img_row.get("asset_filename") or "").strip() or _asset_filename_from_path(img_row.get("image_path") or "")
        image_path = str(img_row.get("image_path") or "")

        deleted_file = False
        for file_path in _safe_candidates_for_delete(site_slug, asset_filename, image_path):
            try:
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
                    deleted_file = True
                    break
            except Exception as exc:
                logger.debug("Failed deleting image file %s: %s", file_path, exc)

        db.execute(
            "UPDATE website_uploaded_images SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deleted_by = ?, updated_at = CURRENT_TIMESTAMP WHERE image_id = ?",
            (current_user.get("sub", ""), media_id),
        )
        return {"ok": True, "media_id": media_id, "deleted_file": deleted_file}

    media_row = db.fetchone(
        "SELECT media_id, media_type, asset_filename, media_path FROM website_uploaded_media "
        "WHERE website_id = ? AND media_id = ? AND COALESCE(is_deleted, 0) = 0",
        (website_id, media_id),
    )
    if not media_row:
        raise HTTPException(status_code=404, detail="Media not found")

    deleted_file = False
    media_path = str(media_row.get("media_path") or "").strip()
    if media_path:
        site_slug = _website_site_slug(website_id)
        asset_filename = str(media_row.get("asset_filename") or "").strip() or _asset_filename_from_path(media_path)
        for file_path in _safe_candidates_for_delete(site_slug, asset_filename, media_path):
            try:
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
                    deleted_file = True
                    break
            except Exception as exc:
                logger.debug("Failed deleting media file %s: %s", file_path, exc)

    db.execute(
        "UPDATE website_uploaded_media SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deleted_by = ?, updated_at = CURRENT_TIMESTAMP WHERE media_id = ?",
        (current_user.get("sub", ""), media_id),
    )
    return {"ok": True, "media_id": media_id, "deleted_file": deleted_file}


@router.delete("/site-images/{website_id}/{image_id}")
async def delete_site_image(
    website_id: str,
    image_id: str,
    current_user: dict = Depends(require_client_or_above),
):
    _assert_website_access(website_id, current_user)
    _ensure_uploaded_images_table()

    row = db.fetchone(
        "SELECT image_id, asset_filename, image_path FROM website_uploaded_images "
        "WHERE website_id = ? AND image_id = ? AND COALESCE(is_deleted, 0) = 0",
        (website_id, image_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")

    site = db.fetchone("SELECT local_path FROM websites WHERE website_id = ?", (website_id,))
    local_path = str((site or {}).get("local_path") or "").strip().rstrip("/\\")
    site_slug = Path(local_path).name if local_path else ""
    asset_filename = str(row.get("asset_filename") or "").strip() or _asset_filename_from_path(row.get("image_path") or "")
    image_path = str(row.get("image_path") or "")

    deleted_file = False
    for file_path in _safe_candidates_for_delete(site_slug, asset_filename, image_path):
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                deleted_file = True
                break
        except Exception as exc:
            logger.debug("Failed deleting image file %s: %s", file_path, exc)

    db.execute(
        "UPDATE website_uploaded_images SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deleted_by = ?, updated_at = CURRENT_TIMESTAMP WHERE image_id = ?",
        (current_user.get("sub", ""), image_id),
    )

    return {"ok": True, "image_id": image_id, "deleted_file": deleted_file}
