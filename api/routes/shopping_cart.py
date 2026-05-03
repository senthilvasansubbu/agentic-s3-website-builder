"""
Shopping cart & cart items catalog API routes.
"""
import uuid
import json
import re
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List

from api.routes.auth import get_current_user, require_app_user_or_above, require_client_or_above
from database.snowflake_client import db
from services.analytics_service import log_event
from services.currency_service import currency_from_ip
from services.image_service import process_image, ALLOWED_MIME
from services.secret_store import decrypt_json
from tools.catalog_scraper import scrape_catalog, parse_file_catalog

router = APIRouter(prefix="/shop", tags=["shop"])
logger = logging.getLogger("website_builder.shop")


# ── Schemas ────────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    website_id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int = 0


class CartItemCreate(BaseModel):
    website_id: str
    category_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: float
    compare_price: Optional[float] = None   # original price before discount
    discount_pct: Optional[float] = None    # 0-100
    currency: str = "USD"
    stock: int = 0
    stock_quantity: Optional[int] = None    # alias
    images: Optional[List[str]] = None
    image_url: Optional[str] = None         # primary image
    is_flash_offer: bool = False
    flash_offer_ends: Optional[str] = None  # ISO datetime

# Keep legacy alias so any stale import doesn't break immediately
ProductCreate = CartItemCreate


class CartSessionItem(BaseModel):
    product_id: str
    qty: int


class CatalogImportRequest(BaseModel):
    website_id: str
    catalog_url: str          # JSON feed, CSV, or any product page
    default_currency: str = "USD"
    overwrite: bool = False   # if True, delete existing cart items for this website first


class CartItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    compare_price: Optional[float] = None
    discount_pct: Optional[float] = None
    currency: Optional[str] = None
    stock_quantity: Optional[int] = None
    category_id: Optional[str] = None
    image_url: Optional[str] = None
    is_flash_offer: Optional[bool] = None
    flash_offer_ends: Optional[str] = None
    is_active: Optional[bool] = None

# Keep legacy alias
ProductUpdate = CartItemUpdate


# ── Image Upload ─────────────────────────────────────────────────────────────

@router.post("/upload-image")
async def upload_cart_item_image(
    file: UploadFile = File(...),
    website_id: Optional[str] = Form(None),
    current_user: dict = Depends(require_client_or_above),
):
    """
    Upload a cart item image.  Returns two variants:
      • Thumbnail  400×400 px WebP @ 72 quality  — cart/grid cards  → thumb_url
      • Full-size  800×800 px WebP @ 80 quality  — item detail view → full_url
    """
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type {content_type!r}. "
                   f"Allowed: JPEG, PNG, WebP, GIF, BMP, TIFF.",
        )

    raw = await file.read()
    storage_override = None
    if website_id:
        _assert_website_access(website_id, current_user)
        site = db.fetchone(
            "SELECT image_storage_backend, image_storage_config, image_storage_secrets_enc FROM websites WHERE website_id = ?",
            (website_id,),
        )
        if site:
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
            storage_override=storage_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Image processing error: %s", exc)
        raise HTTPException(status_code=500, detail="Image processing failed.")

    compression = round(100 * (1 - result.full_size / max(result.original_size, 1)))
    return {
        "thumb_url":      result.thumb_url,
        "full_url":       result.full_url,
        "width":          result.width,
        "height":         result.height,
        "thumb_size_kb":  round(result.thumb_size / 1024, 1),
        "full_size_kb":   round(result.full_size  / 1024, 1),
        "original_size_kb": round(result.original_size / 1024, 1),
        "compression_pct": compression,
    }


# ── Categories ───────────────────────────────────────────────────────────────

@router.post("/categories")
async def create_category(body: CategoryCreate, current_user: dict = Depends(require_client_or_above)):
    _assert_cart_access(body.website_id, current_user)
    cid = str(uuid.uuid4())
    slug = body.name.lower().replace(" ", "-")
    db.execute(
        """INSERT INTO cart_categories
           (category_id, website_id, parent_id, name, slug, description, image_url, sort_order)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (cid, body.website_id, body.parent_id, body.name, slug,
         body.description or "", body.image_url or "", body.sort_order),
    )
    return {"category_id": cid}


@router.get("/categories/{website_id}")
async def list_categories(website_id: str):
    rows = db.execute(
        "SELECT * FROM cart_categories WHERE website_id = %s ORDER BY sort_order, name",
        (website_id,),
    )
    # Build tree (parent → children)
    by_id = {r["category_id"]: {**r, "children": []} for r in rows}
    tree = []
    for node in by_id.values():
        pid = node.get("parent_id")
        if pid and pid in by_id:
            by_id[pid]["children"].append(node)
        else:
            tree.append(node)
    return tree


# ── Cart Items ────────────────────────────────────────────────────────────────

@router.post("/cart-items")
async def create_cart_item(body: CartItemCreate, current_user: dict = Depends(require_client_or_above)):
    _assert_cart_access(body.website_id, current_user)
    pid = str(uuid.uuid4())
    slug = body.name.lower().replace(" ", "-")
    stock_qty = body.stock_quantity if body.stock_quantity is not None else body.stock
    img_url = body.image_url or (body.images[0] if body.images else "")
    db.execute(
        """INSERT INTO cart_items
           (product_id, website_id, category_id, name, slug, description,
            price, compare_price, discount_pct, currency, stock, stock_quantity,
            image_url, images_json, is_flash_offer, flash_offer_ends)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (pid, body.website_id, body.category_id, body.name, slug,
         body.description or "", body.price,
         body.compare_price or 0, body.discount_pct or 0,
         body.currency, stock_qty, stock_qty, img_url,
         json.dumps(body.images or []),
         1 if body.is_flash_offer else 0,
         body.flash_offer_ends or ""),
    )
    return {"product_id": pid}

# Legacy route alias
@router.post("/products")
async def create_product_legacy(body: CartItemCreate, current_user: dict = Depends(require_client_or_above)):
    return await create_cart_item(body, current_user)


@router.get("/cart-items/{website_id}")
async def list_cart_items(website_id: str, category_id: Optional[str] = None,
                          min_price: Optional[float] = None,
                          max_price: Optional[float] = None,
                          flash_only: bool = False,
                          include_inactive: bool = False,
                          request: Request = None):
    sql = """
        SELECT ci.*, cc.name AS category, cc.name AS category_name
        FROM cart_items ci
        LEFT JOIN cart_categories cc ON ci.category_id = cc.category_id
        WHERE ci.website_id = ?
    """
    if not include_inactive:
        sql += " AND ci.is_active = 1"
    params: list = [website_id]
    if category_id:
        sql += " AND ci.category_id = ?"
        params.append(category_id)
    if min_price is not None:
        sql += " AND ci.price >= ?"
        params.append(min_price)
    if max_price is not None:
        sql += " AND ci.price <= ?"
        params.append(max_price)
    if flash_only:
        sql += " AND ci.is_flash_offer = 1"
    sql += " ORDER BY ci.name"
    items = db.execute(sql, params) or []
    if request:
        ip = request.client.host if request.client else "unknown"
        code, symbol = currency_from_ip(ip)
        for item in items:
            item["display_currency"] = code
            item["display_symbol"] = symbol
    return items

# Legacy route alias
@router.get("/products/{website_id}")
async def list_products_legacy(website_id: str, category_id: Optional[str] = None,
                               min_price: Optional[float] = None,
                               max_price: Optional[float] = None,
                               flash_only: bool = False,
                               include_inactive: bool = False,
                               request: Request = None):
    return await list_cart_items(website_id, category_id, min_price, max_price,
                                 flash_only, include_inactive, request)


@router.get("/cart-items/item/{product_id}")
async def get_cart_item(product_id: str, current_user: dict = Depends(require_client_or_above)):
    """Fetch a single cart item by its product_id."""
    item = db.fetchone(
        """SELECT ci.*, cc.name AS category, cc.name AS category_name
           FROM cart_items ci
           LEFT JOIN cart_categories cc ON ci.category_id = cc.category_id
           WHERE ci.product_id = ?""",
        (product_id,),
    )
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    _assert_cart_access(item["website_id"], current_user)
    return item

# Legacy route alias
@router.get("/products/item/{product_id}")
async def get_product_legacy(product_id: str, current_user: dict = Depends(require_client_or_above)):
    return await get_cart_item(product_id, current_user)


@router.patch("/cart-items/{product_id}")
async def update_cart_item(product_id: str, body: CartItemUpdate,
                           current_user: dict = Depends(require_client_or_above)):
    """Update or toggle active status of a cart item."""
    item = db.fetchone("SELECT * FROM cart_items WHERE product_id = ?", (product_id,))
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    _assert_cart_access(item["website_id"], current_user)

    fields = []
    params = []
    if body.name is not None:
        fields.append("name = ?")
        params.append(body.name)
        fields.append("slug = ?")
        params.append(re.sub(r"[^a-z0-9-]", "-", body.name.lower())[:200])
    if body.description is not None:
        fields.append("description = ?")
        params.append(body.description)
    if body.price is not None:
        fields.append("price = ?")
        params.append(body.price)
    if body.compare_price is not None:
        fields.append("compare_price = ?")
        params.append(body.compare_price)
    if body.discount_pct is not None:
        fields.append("discount_pct = ?")
        params.append(body.discount_pct)
    if body.currency is not None:
        fields.append("currency = ?")
        params.append(body.currency.upper()[:3])
    if body.stock_quantity is not None:
        fields.append("stock_quantity = ?")
        params.append(body.stock_quantity)
        fields.append("stock = ?")
        params.append(body.stock_quantity)
    if body.category_id is not None:
        fields.append("category_id = ?")
        params.append(body.category_id)
    if body.image_url is not None:
        fields.append("image_url = ?")
        params.append(body.image_url)
    if body.is_flash_offer is not None:
        fields.append("is_flash_offer = ?")
        params.append(1 if body.is_flash_offer else 0)
    if body.flash_offer_ends is not None:
        fields.append("flash_offer_ends = ?")
        params.append(body.flash_offer_ends)
    if body.is_active is not None:
        fields.append("is_active = ?")
        params.append(1 if body.is_active else 0)

    if not fields:
        return {"message": "No changes"}

    fields.append("updated_at = datetime('now')")
    params.append(product_id)
    db.execute(
        f"UPDATE cart_items SET {', '.join(fields)} WHERE product_id = ?",
        tuple(params),
    )
    return {"message": "Cart item updated"}

# Legacy route alias
@router.patch("/products/{product_id}")
async def update_product_legacy(product_id: str, body: CartItemUpdate,
                                current_user: dict = Depends(require_client_or_above)):
    return await update_cart_item(product_id, body, current_user)


@router.delete("/cart-items/{product_id}")
async def delete_cart_item(product_id: str, current_user: dict = Depends(require_client_or_above)):
    """Permanently delete a cart item."""
    item = db.fetchone("SELECT * FROM cart_items WHERE product_id = ?", (product_id,))
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    _assert_cart_access(item["website_id"], current_user)
    db.execute("DELETE FROM cart_items WHERE product_id = ?", (product_id,))
    return {"message": "Cart item deleted"}

# Legacy route alias
@router.delete("/products/{product_id}")
async def delete_product_legacy(product_id: str, current_user: dict = Depends(require_client_or_above)):
    return await delete_cart_item(product_id, current_user)


# ── Catalog Import ────────────────────────────────────────────────────────────

@router.post("/import-catalog")
async def import_catalog(
    body: CatalogImportRequest,
    request: Request,
    current_user: dict = Depends(require_client_or_above),
):
    """
    Scrape a catalog URL (JSON feed, CSV, or HTML product page) and bulk-import
    the items into the specified website's shopping cart.

    Supported sources:
      • Any URL returning JSON array/object of items
      • Any URL returning a CSV file with item columns
      • Any HTML page with JSON-LD schema.org Product structured-data
      • IndiaMart seller catalog pages
    """
    user_id = current_user["sub"]
    _assert_cart_access(body.website_id, current_user)

    try:
        result = scrape_catalog(body.catalog_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Catalog scrape error for %s: %s", body.catalog_url, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch catalog URL.")

    items = result.get("products", [])

    if not items:
        return {
            "imported": 0,
            "source_type": result.get("source_type"),
            "warnings": result.get("warnings", []),
            "message": "No items found at the provided URL.",
        }

    if body.overwrite:
        db.execute("DELETE FROM cart_items WHERE website_id = ?", (body.website_id,))
        logger.info("Cleared existing cart items for website %s (overwrite=True)", body.website_id)

    imported, skipped = _bulk_insert_items(items, body.website_id, body.default_currency)

    log_event(
        "catalog_imported",
        user_id=user_id,
        website_id=body.website_id,
        ip_address=request.client.host,
        meta={"url": body.catalog_url, "imported": imported, "skipped": skipped},
    )
    logger.info(
        "Catalog import complete — website=%s  imported=%d  skipped=%d  source=%s",
        body.website_id, imported, skipped, result.get("source_type"),
    )

    return {
        "imported": imported,
        "skipped": skipped,
        "source_type": result.get("source_type"),
        "warnings": result.get("warnings", []),
    }


@router.post("/import-catalog/upload")
async def import_catalog_file(
    request: Request,
    website_id: str,
    overwrite: bool = False,
    default_currency: str = "USD",
    file: UploadFile = File(...),
    current_user: dict = Depends(require_client_or_above),
):
    """
    Upload a local file (CSV, JSON, Excel .xlsx/.xls, or TXT/TSV) and bulk-import
    its items into the specified website's shopping cart.
    """
    _assert_cart_access(website_id, current_user)
    user_id = current_user["sub"]

    allowed_ext = {"csv", "json", "xlsx", "xls", "txt", "tsv"}
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(allowed_ext))}"
        )

    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum 10 MB.")

    result = parse_file_catalog(raw, filename, default_currency=default_currency.upper())
    items = result.get("products", [])

    if not items:
        return {
            "imported": 0,
            "source_type": result.get("source_type"),
            "warnings": result.get("warnings", []),
            "message": "No items found in the uploaded file.",
        }

    if overwrite:
        db.execute("DELETE FROM cart_items WHERE website_id = ?", (website_id,))

    imported, skipped = _bulk_insert_items(items, website_id, default_currency)

    log_event(
        "catalog_file_imported",
        user_id=user_id,
        website_id=website_id,
        ip_address=request.client.host,
        meta={"filename": filename, "imported": imported, "skipped": skipped},
    )
    return {
        "imported": imported,
        "skipped": skipped,
        "source_type": result.get("source_type"),
        "warnings": result.get("warnings", []),
        "message": f"Successfully imported {imported} cart item(s).",
    }


# ── Cart Session ──────────────────────────────────────────────────────────────

@router.post("/cart/{website_id}")
async def upsert_cart(website_id: str, items: List[CartSessionItem],
                      request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    ip = request.client.host if request.client else "unknown"
    _, symbol = currency_from_ip(ip)

    existing = db.fetchone(
        "SELECT cart_id FROM carts WHERE user_id = %s AND website_id = %s",
        (user_id, website_id),
    )
    items_data = [{"product_id": i.product_id, "qty": i.qty} for i in items]
    if existing:
        db.execute(
            "UPDATE carts SET items_json = PARSE_JSON(%s), updated_at = CURRENT_TIMESTAMP() WHERE cart_id = %s",
            (json.dumps(items_data), existing["cart_id"]),
        )
        return {"cart_id": existing["cart_id"]}
    else:
        cart_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO carts (cart_id, user_id, website_id, items_json) VALUES (%s,%s,%s,PARSE_JSON(%s))",
            (cart_id, user_id, website_id, json.dumps(items_data)),
        )
        return {"cart_id": cart_id}


@router.get("/cart/{website_id}")
async def get_cart(website_id: str, request: Request,
                   current_user: dict = Depends(get_current_user)):
    cart = db.fetchone(
        "SELECT * FROM carts WHERE user_id = %s AND website_id = %s",
        (current_user["sub"], website_id),
    )
    if not cart:
        return {"items": [], "total": 0}

    ip = request.client.host if request.client else "unknown"
    code, symbol = currency_from_ip(ip)

    session_items = cart.get("items_json") or []
    enriched = []
    total = 0.0
    for item in session_items:
        ci = db.fetchone(
            "SELECT name, price, currency, images_json FROM cart_items WHERE product_id = %s",
            (item["product_id"],),
        )
        if ci:
            line_total = ci["price"] * item["qty"]
            total += line_total
            enriched.append({**item, "name": ci["name"], "price": ci["price"],
                              "line_total": line_total, "currency_symbol": symbol})
    return {"items": enriched, "total": total, "currency": code, "symbol": symbol}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _bulk_insert_items(items: list, website_id: str, default_currency: str) -> tuple[int, int]:
    """Insert a list of catalog dicts into cart_items. Returns (imported, skipped)."""
    imported = 0
    skipped = 0
    for p in items:
        try:
            pid = str(uuid.uuid4())
            name = str(p.get("name", "")).strip()
            if not name:
                skipped += 1
                continue
            slug = re.sub(r"[^a-z0-9-]", "-", name.lower())[:200]
            currency = (p.get("currency") or default_currency or "USD").upper()[:3]
            price = float(p.get("price") or 0)
            compare_price = float(p.get("compare_price") or 0)
            discount_pct = float(p.get("discount_pct") or 0)
            stock = int(p.get("stock") or 0)
            image_url = str(p.get("image_url") or "")
            description = str(p.get("description") or "")

            # Category — create if needed
            cat_name = str(p.get("category") or "").strip()
            category_id = None
            if cat_name:
                existing_cat = db.fetchone(
                    "SELECT category_id FROM cart_categories WHERE website_id = ? AND name = ?",
                    (website_id, cat_name),
                )
                if existing_cat:
                    category_id = existing_cat["category_id"]
                else:
                    category_id = str(uuid.uuid4())
                    cat_slug = re.sub(r"[^a-z0-9-]", "-", cat_name.lower())[:200]
                    db.execute(
                        """INSERT INTO cart_categories
                           (category_id, website_id, name, slug, sort_order)
                           VALUES (?,?,?,?,0)""",
                        (category_id, website_id, cat_name, cat_slug),
                    )

            db.execute(
                """INSERT INTO cart_items
                   (product_id, website_id, category_id, name, slug, description,
                    price, compare_price, discount_pct, currency, stock, stock_quantity,
                    image_url, images_json, is_flash_offer, flash_offer_ends)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,'')""",
                (pid, website_id, category_id, name, slug, description,
                 price, compare_price, discount_pct, currency,
                 stock, stock, image_url, json.dumps([image_url] if image_url else [])),
            )
            imported += 1
        except Exception as exc:
            logger.warning("Failed to insert cart item %r: %s", p.get("name"), exc)
            skipped += 1
    return imported, skipped


def _assert_cart_access(website_id: str, user: dict):
    """
    Enforce that:
      1. The website exists.
      2. The website has the shopping cart feature enabled.
      3. The caller owns the website or is a linked client.
    Raises HTTPException 404 / 403 as appropriate.
    """
    site = db.fetchone(
        "SELECT user_id, cart_features FROM websites WHERE website_id = ?",
        (website_id,),
    )
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    try:
        cart_features = json.loads(site.get("cart_features") or "[]")
    except Exception:
        cart_features = []
    if not cart_features:
        raise HTTPException(
            status_code=403,
            detail="This website does not have the shopping cart feature enabled. "
                   "Enable it when building the website.",
        )

    role = user.get("role", "app_user")
    user_id = user["sub"]

    if role == "superuser":
        return

    if role == "client":
        row = db.fetchone(
            "SELECT client_website_id FROM users WHERE user_id = ?", (user_id,)
        )
        if not row or row.get("client_website_id") != website_id:
            raise HTTPException(
                status_code=403,
                detail="Clients can only manage cart items on their own linked website.",
            )
    else:
        if site["user_id"] != user_id:
            client_row = db.fetchone(
                "SELECT user_id FROM users WHERE client_website_id = ? AND owner_id = ? AND role = 'client'",
                (website_id, user_id),
            )
            if not client_row:
                raise HTTPException(status_code=403, detail="Not your website")


def _assert_website_access(website_id: str, user: dict):
    """Access check for non-cart website operations (e.g. shared image upload endpoint)."""
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


def _assert_website_owner(website_id: str, user_id: str):
    row = db.fetchone(
        "SELECT user_id FROM websites WHERE website_id = ?", (website_id,)
    )
    if not row or row["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your website")
