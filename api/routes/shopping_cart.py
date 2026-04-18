"""
Shopping cart & product catalog API routes.
"""
import uuid
import json
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List

from api.routes.auth import get_current_user
from database.snowflake_client import db
from services.analytics_service import log_event
from services.currency_service import currency_from_ip

router = APIRouter(prefix="/shop", tags=["shop"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    website_id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int = 0


class ProductCreate(BaseModel):
    website_id: str
    category_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: float
    currency: str = "USD"
    stock: int = 0
    images: Optional[List[str]] = None


class CartItem(BaseModel):
    product_id: str
    qty: int


# ── Categories ──────────────────────────────────────────────────────────────────

@router.post("/categories")
async def create_category(body: CategoryCreate, current_user: dict = Depends(get_current_user)):
    _assert_website_owner(body.website_id, current_user["sub"])
    cid = str(uuid.uuid4())
    slug = body.name.lower().replace(" ", "-")
    db.execute(
        """INSERT INTO product_categories
           (category_id, website_id, parent_id, name, slug, description, image_url, sort_order)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (cid, body.website_id, body.parent_id, body.name, slug,
         body.description or "", body.image_url or "", body.sort_order),
    )
    return {"category_id": cid}


@router.get("/categories/{website_id}")
async def list_categories(website_id: str):
    rows = db.execute(
        "SELECT * FROM product_categories WHERE website_id = %s ORDER BY sort_order, name",
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


# ── Products ───────────────────────────────────────────────────────────────────

@router.post("/products")
async def create_product(body: ProductCreate, current_user: dict = Depends(get_current_user)):
    _assert_website_owner(body.website_id, current_user["sub"])
    pid = str(uuid.uuid4())
    slug = body.name.lower().replace(" ", "-")
    db.execute(
        """INSERT INTO products
           (product_id, website_id, category_id, name, slug, description,
            price, currency, stock, images_json)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,PARSE_JSON(%s))""",
        (pid, body.website_id, body.category_id, body.name, slug,
         body.description or "", body.price, body.currency, body.stock,
         json.dumps(body.images or [])),
    )
    return {"product_id": pid}


@router.get("/products/{website_id}")
async def list_products(website_id: str, category_id: Optional[str] = None,
                        request: Request = None):
    sql = "SELECT * FROM products WHERE website_id = %s AND is_active = TRUE"
    params: tuple = (website_id,)
    if category_id:
        sql += " AND category_id = %s"
        params += (category_id,)
    sql += " ORDER BY name"
    products = db.execute(sql, params)
    # Attach localised currency if request available
    if request:
        ip = request.client.host if request.client else "unknown"
        code, symbol = currency_from_ip(ip)
        for p in products:
            p["display_currency"] = code
            p["display_symbol"] = symbol
    return products


# ── Cart ────────────────────────────────────────────────────────────────────────

@router.post("/cart/{website_id}")
async def upsert_cart(website_id: str, items: List[CartItem],
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

    items = cart.get("items_json") or []
    enriched = []
    total = 0.0
    for item in items:
        prod = db.fetchone(
            "SELECT name, price, currency, images_json FROM products WHERE product_id = %s",
            (item["product_id"],),
        )
        if prod:
            line_total = prod["price"] * item["qty"]
            total += line_total
            enriched.append({**item, "name": prod["name"], "price": prod["price"],
                              "line_total": line_total, "currency_symbol": symbol})
    return {"items": enriched, "total": total, "currency": code, "symbol": symbol}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _assert_website_owner(website_id: str, user_id: str):
    row = db.fetchone(
        "SELECT user_id FROM websites WHERE website_id = %s", (website_id,)
    )
    if not row or row["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your website")
