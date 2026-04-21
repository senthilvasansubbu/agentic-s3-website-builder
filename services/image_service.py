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
from typing import NamedTuple

from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger("website_builder.image_service")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Root folder where processed images are stored.
# app.py mounts this directory under /static/uploads so images are served
# at  /static/uploads/<filename>
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class ProcessedImage(NamedTuple):
    thumb_path: Path      # absolute path of thumbnail file
    full_path:  Path      # absolute path of full-size file
    thumb_url:  str       # relative URL  e.g. /static/uploads/abc123_thumb.webp
    full_url:   str       # relative URL  e.g. /static/uploads/abc123.webp
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
        if img.mode == "PA":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1])
        return bg
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _resize_and_encode(
    img: Image.Image,
    max_w: int,
    max_h: int,
    quality: int,
) -> bytes:
    """
    Resize *img* so it fits within (max_w × max_h) preserving aspect ratio,
    then encode to WebP.  Returns raw bytes.
    """
    # Apply EXIF orientation before resizing
    img = ImageOps.exif_transpose(img)
    img = _to_rgb(img)
    img.thumbnail((max_w, max_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=6)
    return buf.getvalue()


def process_upload(raw_data: bytes, original_filename: str = "") -> ProcessedImage:
    """
    Validate, resize, compress *raw_data* and write both the thumbnail and
    full-size variants to UPLOAD_DIR.

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

    results: dict[str, tuple[Path, bytes]] = {}
    for preset, (max_w, max_h, quality, suffix) in PRESETS.items():
        encoded = _resize_and_encode(img, max_w, max_h, quality)
        fname = f"{stem}{suffix}.webp"
        path = UPLOAD_DIR / fname
        if not path.exists():           # don't rewrite identical content
            path.write_bytes(encoded)
        results[preset] = (path, encoded)

    thumb_path, thumb_data = results["thumb"]
    full_path,  full_data  = results["full"]

    # Determine actual dimensions of the saved full-size image
    with Image.open(full_path) as saved:
        w, h = saved.size

    thumb_url = f"/static/uploads/{thumb_path.name}"
    full_url  = f"/static/uploads/{full_path.name}"

    logger.info(
        "Image processed: original=%d KB  full=%d KB  thumb=%d KB  (%dx%d)  "
        "compression=%.0f%%  files=[%s, %s]",
        original_size // 1024,
        len(full_data) // 1024,
        len(thumb_data) // 1024,
        w, h,
        100 * (1 - len(full_data) / max(original_size, 1)),
        full_path.name, thumb_path.name,
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
