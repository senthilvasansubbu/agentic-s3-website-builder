"""
Image processing service — resize and compress uploaded product images for
fast shopping-cart display.

Output specs (optimised for cart thumbnails & product cards):
  • Format : WebP  (best quality-to-size ratio; falls back to JPEG for clients
                    that send Accept without webp)
  • Thumbnail  : 400 × 400 px  (cart/grid card image)
  • Full-size  : 800 × 800 px  (product detail lightbox)
  • Quality    : 72 (thumbnail)  /  80 (full-size)
  • Mode       : LANCZOS resampling, thumbnail mode (preserves aspect ratio,
                 no distortion, no padding)
"""

from __future__ import annotations

import io
import os
import hashlib
import logging
from pathlib import Path
from typing import NamedTuple, Optional, Any

from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger("website_builder.image_service")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Root folder where processed images are stored.

# Draft uploads go to assets/uploads, finalized images to assets/images
STAGING_ROOT = Path(os.getenv("STAGING_ROOT", "output/staging"))
def get_upload_dir(site_slug: str) -> Path:
    d = STAGING_ROOT / site_slug / "assets" / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d
def get_images_dir(site_slug: str) -> Path:
    d = STAGING_ROOT / site_slug / "assets" / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d

# Size presets  (max_width, max_height, quality, suffix)
PRESETS = {
    "thumb": (400, 400, 72, "_thumb"),      # cart card / catalogue grid
    "full":  (800, 800, 80, ""),            # product detail / lightbox
}

# Allowed input MIME types
ALLOWED_MIME = {
    "image/jpeg", "image/jpg", "image/png",
    "image/webp", "image/gif", "image/bmp",
    "image/tiff", "image/heic", "image/heif",
}

# Max raw upload size: 10 MB
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Storage backend selection for processed uploads:
#   IMAGE_STORAGE_BACKEND=local | s3 | gdrive | auto (default)
# In auto mode: prefer S3 when configured, else Google Drive, else local.
IMAGE_STORAGE_BACKEND = os.getenv("IMAGE_STORAGE_BACKEND", "auto").strip().lower()


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class ProcessedImage(NamedTuple):
    thumb_path: Path      # absolute path of thumbnail file
    full_path:  Path      # absolute path of full-size file
    thumb_url:  str       # relative URL  e.g. assets/uploads/abc123_thumb.webp
    full_url:   str       # relative URL  e.g. assets/uploads/abc123.webp
    thumb_size: int       # bytes
    full_size:  int       # bytes
    original_size: int    # bytes (raw upload)
    width:  int           # full-size width px
    height: int           # full-size height px


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def _stable_name(data: bytes, ext: str = "webp") -> str:
    """Deterministic filename based on content hash (deduplicates re-uploads)."""
    digest = hashlib.sha256(data).hexdigest()[:20]
    return f"{digest}.{ext}"


def _open_image(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()          # force decode so errors surface here
        return img
    except UnidentifiedImageError as exc:
        raise ValueError("Uploaded file is not a recognised image format.") from exc


def _to_rgb(img: Image.Image) -> Image.Image:
    """Ensure image is in RGB (needed for WebP / JPEG save)."""
    if img.mode in ("RGBA", "LA", "PA"):
        # Composite over white background for transparency
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def _resize_and_encode(img: Image.Image, max_w: int, max_h: int, quality: int) -> bytes:
    """Resize image to fit bounds and encode as WebP bytes."""
    normalized = ImageOps.exif_transpose(img)
    work = _to_rgb(normalized)
    # Preserve aspect ratio within requested bounds.
    work.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    work.save(out, format="WEBP", quality=int(quality), method=6)
    return out.getvalue()

def process_image(
    raw_data: bytes,
    original_filename: str = "",
    site_slug: str = "website",
    storage_override: Optional[dict[str, Any]] = None,
) -> ProcessedImage:
    """
    Validate, resize, compress *raw_data* and write both the thumbnail and
    full-size variants to assets/uploads/ for the given site.
    Returns a :class:`ProcessedImage` with URLs and size statistics.
    Raises ``ValueError`` for oversized or invalid files.
    """
    original_size = len(raw_data)
    if original_size > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Image is too large ({original_size // 1024} KB). "
            f"Maximum allowed is {MAX_UPLOAD_BYTES // (1024*1024)} MB."
        )

    img = _open_image(raw_data)
    base_name = _stable_name(raw_data)  # e.g. "abc123def456.webp"
    stem = base_name[:-5]               # strip ".webp"

    upload_dir = get_upload_dir(site_slug)
    results: dict[str, tuple[Path, bytes]] = {}
    for preset, (max_w, max_h, quality, suffix) in PRESETS.items():
        encoded = _resize_and_encode(img, max_w, max_h, quality)
        fname = f"{stem}{suffix}.webp"
        path = upload_dir / fname
        if not path.exists():           # don't rewrite identical content
            path.write_bytes(encoded)
        results[preset] = (path, encoded)

    thumb_path, thumb_data = results["thumb"]
    full_path,  full_data  = results["full"]

    with Image.open(full_path) as saved:
        w, h = saved.size

    # Always return relative paths for assets/uploads
    thumb_url = f"assets/uploads/{thumb_path.name}"
    full_url = f"assets/uploads/{full_path.name}"

    logger.info(
        "Image processed: original=%d KB  full=%d KB  thumb=%d KB  (%dx%d)",
        original_size // 1024,
        len(full_data) // 1024,
        len(thumb_data) // 1024,
        w, h,
    )

    return ProcessedImage(
        thumb_path=thumb_path,
        full_path=full_path,
        thumb_url=thumb_url,
        full_url=full_url,
        thumb_size=len(thumb_data),
        full_size=len(full_data),
        original_size=original_size,
        width=w,
        height=h,
    )

# Move finalized image from uploads to images and return new relative path
def finalize_image(site_slug: str, filename: str) -> str:
    uploads_dir = get_upload_dir(site_slug)
    images_dir = get_images_dir(site_slug)
    src = uploads_dir / filename
    dst = images_dir / filename
    if not src.exists():
        raise FileNotFoundError(f"Image {filename} not found in uploads.")
    src.replace(dst)
    return f"assets/images/{filename}"
    # ── Upload to S3 when configured, else serve from local static ────────────
    thumb_url, full_url = _upload_to_remote_or_local(
        thumb_path, full_path, stem, storage_override
    )

    logger.info(
        "Image processed: original=%d KB  full=%d KB  thumb=%d KB  (%dx%d)  "
        "compression=%.0f%%  storage=%s",
        original_size // 1024,
        len(full_data) // 1024,
        len(thumb_data) // 1024,
        w, h,
        100 * (1 - len(full_data) / max(original_size, 1)),
        _active_storage_name(storage_override),
    )

    return ProcessedImage(
        thumb_path=thumb_path,
        full_path=full_path,
        thumb_url=thumb_url,
        full_url=full_url,
        thumb_size=len(thumb_data),
        full_size=len(full_data),
        original_size=original_size,
        width=w,
        height=h,
    )


# ---------------------------------------------------------------------------
# Remote upload helpers (S3 / Google Drive / OneDrive / FTP)
# ---------------------------------------------------------------------------

def _active_storage_name(storage_override: Optional[dict[str, Any]] = None) -> str:
    backend = _resolve_backend(storage_override)
    if backend == "local":
        return "local"
    if backend == "s3":
        return "s3" if _s3_configured(storage_override) else "local(fallback)"
    if backend == "gdrive":
        return "gdrive" if _gdrive_configured(storage_override) else "local(fallback)"
    if backend == "onedrive":
        return "onedrive" if _onedrive_configured(storage_override) else "local(fallback)"
    if backend == "ftp":
        return "ftp" if _ftp_configured(storage_override) else "local(fallback)"
    # auto
    if _s3_configured(storage_override):
        return "s3"
    if _gdrive_configured(storage_override):
        return "gdrive"
    if _onedrive_configured(storage_override):
        return "onedrive"
    if _ftp_configured(storage_override):
        return "ftp"
    return "local"


def _resolve_backend(storage_override: Optional[dict[str, Any]] = None) -> str:
    if storage_override and storage_override.get("backend"):
        return str(storage_override.get("backend", "auto")).strip().lower()
    return IMAGE_STORAGE_BACKEND or "auto"


def _s3_configured(storage_override: Optional[dict[str, Any]] = None) -> bool:
    bucket_override = ""
    key_override = ""
    secret_override = ""
    if storage_override:
        bucket_override = str(storage_override.get("s3_bucket", "")).strip()
        key_override = str(storage_override.get("aws_access_key_id", "")).strip()
        secret_override = str(storage_override.get("aws_secret_access_key", "")).strip()
    return bool(
        (key_override or os.getenv("AWS_ACCESS_KEY_ID"))
        and (secret_override or os.getenv("AWS_SECRET_ACCESS_KEY"))
        and (bucket_override or os.getenv("S3_BUCKET_NAME"))
    )


def _gdrive_configured(storage_override: Optional[dict[str, Any]] = None) -> bool:
    sa_override = ""
    if storage_override:
        sa_override = str(storage_override.get("service_account_file", "")).strip()
    sa_file = sa_override or os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "")
    return bool(sa_file)


def _onedrive_configured(storage_override: Optional[dict[str, Any]] = None) -> bool:
    drive_override = (
        str(storage_override.get("onedrive_drive_id", "")).strip()
        if storage_override else ""
    )
    tenant_override = (
        str(storage_override.get("onedrive_tenant_id", "")).strip()
        if storage_override else ""
    )
    client_override = (
        str(storage_override.get("onedrive_client_id", "")).strip()
        if storage_override else ""
    )
    secret_override = (
        str(storage_override.get("onedrive_client_secret", "")).strip()
        if storage_override else ""
    )
    return bool(
        (tenant_override or os.getenv("ONEDRIVE_TENANT_ID"))
        and (client_override or os.getenv("ONEDRIVE_CLIENT_ID"))
        and (secret_override or os.getenv("ONEDRIVE_CLIENT_SECRET"))
        and (drive_override or os.getenv("ONEDRIVE_DRIVE_ID"))
    )


def _ftp_configured(storage_override: Optional[dict[str, Any]] = None) -> bool:
    public_override = (
        str(storage_override.get("ftp_public_base_url", "")).strip()
        if storage_override else ""
    )
    host_override = (
        str(storage_override.get("ftp_host", "")).strip()
        if storage_override else ""
    )
    user_override = (
        str(storage_override.get("ftp_user", "")).strip()
        if storage_override else ""
    )
    pass_override = (
        str(storage_override.get("ftp_password", "")).strip()
        if storage_override else ""
    )
    return bool(
        (host_override or os.getenv("FTP_HOST"))
        and (user_override or os.getenv("FTP_USER"))
        and (pass_override or os.getenv("FTP_PASSWORD"))
        and (public_override or os.getenv("FTP_PUBLIC_BASE_URL"))
    )


def _upload_to_remote_or_local(
    thumb_path: Path,
    full_path: Path,
    stem: str,
    storage_override: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    """
    Upload both image variants to configured remote backend.
    Returns (thumb_url, full_url) — remote public URLs or local /static/uploads/ paths.
    """
    backend = _resolve_backend(storage_override)

    if backend == "local":
        return _local_urls(thumb_path, full_path)

    if backend == "s3":
        if _s3_configured(storage_override):
            return _upload_to_s3(thumb_path, full_path, storage_override)
        logger.warning("IMAGE_STORAGE_BACKEND=s3 but S3 env vars are missing; using local fallback")
        return _local_urls(thumb_path, full_path)

    if backend == "gdrive":
        if _gdrive_configured(storage_override):
            return _upload_to_gdrive(thumb_path, full_path, storage_override)
        logger.warning("IMAGE_STORAGE_BACKEND=gdrive but Drive env vars are missing; using local fallback")
        return _local_urls(thumb_path, full_path)

    if backend == "onedrive":
        if _onedrive_configured(storage_override):
            return _upload_to_onedrive(thumb_path, full_path, storage_override)
        logger.warning("IMAGE_STORAGE_BACKEND=onedrive but OneDrive env vars are missing; using local fallback")
        return _local_urls(thumb_path, full_path)

    if backend == "ftp":
        if _ftp_configured(storage_override):
            return _upload_to_ftp(thumb_path, full_path, storage_override)
        logger.warning("IMAGE_STORAGE_BACKEND=ftp but FTP env vars are missing; using local fallback")
        return _local_urls(thumb_path, full_path)

    # auto mode
    if _s3_configured(storage_override):
        return _upload_to_s3(thumb_path, full_path, storage_override)
    if _gdrive_configured(storage_override):
        return _upload_to_gdrive(thumb_path, full_path, storage_override)
    if _onedrive_configured(storage_override):
        return _upload_to_onedrive(thumb_path, full_path, storage_override)
    if _ftp_configured(storage_override):
        return _upload_to_ftp(thumb_path, full_path, storage_override)
    return _local_urls(thumb_path, full_path)


def _local_urls(thumb_path: Path, full_path: Path) -> tuple[str, str]:
    # Deprecated: use only for legacy fallback
    return (
        f"assets/uploads/{thumb_path.name}",
        f"assets/uploads/{full_path.name}",
    )


def _join_remote_path(*parts: str) -> str:
    clean = [str(p).strip().strip("/") for p in parts if str(p).strip()]
    return "/".join(clean)


def _upload_to_s3(
    thumb_path: Path,
    full_path: Path,
    storage_override: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    import boto3
    from botocore.exceptions import ClientError

    bucket = (
        str(storage_override.get("s3_bucket", "")).strip()
        if storage_override else os.getenv("S3_BUCKET_NAME", "")
    ) or os.getenv("S3_BUCKET_NAME", "")
    access_key = (
        str(storage_override.get("aws_access_key_id", "")).strip()
        if storage_override else ""
    ) or os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = (
        str(storage_override.get("aws_secret_access_key", "")).strip()
        if storage_override else ""
    ) or os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "us-east-1")
    prefix = (
        str(storage_override.get("s3_prefix", "")).strip()
        if storage_override else os.getenv("S3_UPLOADS_PREFIX", "uploads")
    ) or os.getenv("S3_UPLOADS_PREFIX", "uploads")
    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    urls: dict[str, str] = {}
    for path in (thumb_path, full_path):
        key = _join_remote_path(prefix, path.name)
        try:
            s3.upload_file(
                str(path),
                bucket,
                key,
                ExtraArgs={"ContentType": "image/webp", "ACL": "public-read"},
            )
            urls[path.name] = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
            logger.info("Uploaded %s → s3://%s/%s", path.name, bucket, key)
        except ClientError as exc:
            logger.error("S3 upload failed for %s: %s — falling back to local", path.name, exc)
            urls[path.name] = f"/static/uploads/{path.name}"

    return urls[thumb_path.name], urls[full_path.name]


def _upload_to_gdrive(
    thumb_path: Path,
    full_path: Path,
    storage_override: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    """
    Upload both files to Google Drive using server-side service account credentials.
    Per-website config controls destination folder/subfolder only.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    sa_file = (
        str(storage_override.get("service_account_file", "")).strip()
        if storage_override else os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "")
    ) or os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "")
    folder_id = (
        str(storage_override.get("folder_id", "")).strip()
        if storage_override else os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    ) or os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    subfolder = (
        str(storage_override.get("gdrive_subfolder", "")).strip()
        if storage_override else ""
    )

    scopes = ["https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_file(sa_file, scopes=scopes)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    urls: dict[str, str] = {}
    for path in (thumb_path, full_path):
        remote_name = _join_remote_path(subfolder, path.name) if subfolder else path.name
        metadata = {"name": remote_name}
        if folder_id:
            metadata["parents"] = [folder_id]

        media = MediaFileUpload(str(path), mimetype="image/webp", resumable=False)
        try:
            file_obj = drive.files().create(body=metadata, media_body=media, fields="id").execute()
            file_id = file_obj.get("id")
            if not file_id:
                raise ValueError("Google Drive did not return a file id")

            drive.permissions().create(
                fileId=file_id,
                body={"role": "reader", "type": "anyone"},
                fields="id",
            ).execute()

            urls[path.name] = f"https://drive.google.com/uc?id={file_id}"
            logger.info("Uploaded %s to Google Drive fileId=%s", path.name, file_id)
        except Exception as exc:
            logger.error("Google Drive upload failed for %s: %s — falling back to local", path.name, exc)
            urls[path.name] = f"/static/uploads/{path.name}"

    return urls[thumb_path.name], urls[full_path.name]


def _upload_to_onedrive(
    thumb_path: Path,
    full_path: Path,
    storage_override: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    import requests

    tenant_id = (
        str(storage_override.get("onedrive_tenant_id", "")).strip()
        if storage_override else ""
    ) or os.getenv("ONEDRIVE_TENANT_ID", "")
    client_id = (
        str(storage_override.get("onedrive_client_id", "")).strip()
        if storage_override else ""
    ) or os.getenv("ONEDRIVE_CLIENT_ID", "")
    client_secret = (
        str(storage_override.get("onedrive_client_secret", "")).strip()
        if storage_override else ""
    ) or os.getenv("ONEDRIVE_CLIENT_SECRET", "")
    drive_id = (
        str(storage_override.get("onedrive_drive_id", "")).strip()
        if storage_override else ""
    ) or os.getenv("ONEDRIVE_DRIVE_ID", "")
    folder = (
        str(storage_override.get("onedrive_folder", "")).strip()
        if storage_override else ""
    ) or os.getenv("ONEDRIVE_FOLDER", "uploads")
    subfolder = (
        str(storage_override.get("onedrive_subfolder", "")).strip()
        if storage_override else ""
    )

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_resp = requests.post(
        token_url,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=20,
    )
    token_resp.raise_for_status()
    access_token = token_resp.json().get("access_token", "")
    if not access_token:
        raise RuntimeError("OneDrive access token missing")

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "image/webp"}
    share_headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    urls: dict[str, str] = {}
    for path in (thumb_path, full_path):
        remote_path = _join_remote_path(folder, subfolder, path.name)
        upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{remote_path}:/content"
        try:
            with open(path, "rb") as f:
                put_resp = requests.put(upload_url, headers=headers, data=f, timeout=60)
            put_resp.raise_for_status()
            item = put_resp.json()
            item_id = item.get("id")

            share_url = ""
            if item_id:
                link_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/createLink"
                link_resp = requests.post(
                    link_url,
                    headers=share_headers,
                    json={"type": "view", "scope": "anonymous"},
                    timeout=20,
                )
                if link_resp.ok:
                    share_url = ((link_resp.json().get("link") or {}).get("webUrl") or "")

            urls[path.name] = share_url or f"/static/uploads/{path.name}"
            logger.info("Uploaded %s to OneDrive path=%s", path.name, remote_path)
        except Exception as exc:
            logger.error("OneDrive upload failed for %s: %s — falling back to local", path.name, exc)
            urls[path.name] = f"/static/uploads/{path.name}"

    return urls[thumb_path.name], urls[full_path.name]


def _upload_to_ftp(
    thumb_path: Path,
    full_path: Path,
    storage_override: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    from ftplib import FTP

    host = (
        str(storage_override.get("ftp_host", "")).strip()
        if storage_override else ""
    ) or os.getenv("FTP_HOST", "")
    port = int((
        str(storage_override.get("ftp_port", "")).strip()
        if storage_override else ""
    ) or os.getenv("FTP_PORT", "21"))
    user = (
        str(storage_override.get("ftp_user", "")).strip()
        if storage_override else ""
    ) or os.getenv("FTP_USER", "")
    password = (
        str(storage_override.get("ftp_password", "")).strip()
        if storage_override else ""
    ) or os.getenv("FTP_PASSWORD", "")
    remote_dir = (
        str(storage_override.get("ftp_remote_dir", "")).strip()
        if storage_override else ""
    ) or os.getenv("FTP_REMOTE_DIR", "uploads")
    public_base = (
        str(storage_override.get("ftp_public_base_url", "")).strip()
        if storage_override else ""
    ) or os.getenv("FTP_PUBLIC_BASE_URL", "")

    urls: dict[str, str] = {}
    ftp = FTP()
    ftp.connect(host=host, port=port, timeout=20)
    ftp.login(user=user, passwd=password)
    try:
        for seg in [s for s in remote_dir.split("/") if s]:
            try:
                ftp.cwd(seg)
            except Exception:
                ftp.mkd(seg)
                ftp.cwd(seg)

        for path in (thumb_path, full_path):
            try:
                with open(path, "rb") as f:
                    ftp.storbinary(f"STOR {path.name}", f)
                remote_rel = _join_remote_path(remote_dir, path.name)
                urls[path.name] = f"{public_base.rstrip('/')}/{remote_rel}"
                logger.info("Uploaded %s via FTP to %s", path.name, remote_rel)
            except Exception as exc:
                logger.error("FTP upload failed for %s: %s — falling back to local", path.name, exc)
                urls[path.name] = f"/static/uploads/{path.name}"
    finally:
        try:
            ftp.quit()
        except Exception:
            pass

    return urls[thumb_path.name], urls[full_path.name]
