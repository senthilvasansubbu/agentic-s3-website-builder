import json
import uuid

from database.migrations import TABLES


AUTH = lambda token: {"Authorization": f"Bearer {token}"}


def _bootstrap_shop_tables(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS cart_categories (
            category_id TEXT PRIMARY KEY,
            website_id TEXT NOT NULL,
            parent_id TEXT,
            name TEXT NOT NULL,
            slug TEXT,
            description TEXT,
            image_url TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS cart_items (
            product_id TEXT PRIMARY KEY,
            website_id TEXT NOT NULL,
            category_id TEXT,
            name TEXT NOT NULL,
            slug TEXT,
            description TEXT,
            price REAL NOT NULL DEFAULT 0,
            compare_price REAL DEFAULT 0,
            discount_pct REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            stock_quantity INTEGER DEFAULT 0,
            image_url TEXT,
            images_json TEXT,
            is_flash_offer INTEGER DEFAULT 0,
            flash_offer_ends TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS carts (
            cart_id TEXT PRIMARY KEY,
            user_id TEXT,
            website_id TEXT NOT NULL,
            session_id TEXT,
            items_json TEXT DEFAULT '[]',
            currency TEXT DEFAULT 'USD',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def test_upsert_cart_rejects_invalid_product_id(client, verified_user, _in_memory_db):
    _bootstrap_shop_tables(_in_memory_db)

    website_id = str(uuid.uuid4())
    _in_memory_db.execute(
        "INSERT INTO websites (website_id, user_id, name, cart_features) VALUES (?, ?, ?, ?)",
        (website_id, verified_user["user_id"], "Wave5 Site", json.dumps(["shopping_cart"])),
    )

    payload = [{"product_id": "not-a-uuid", "qty": 1}]
    r = client.post(
        f"/api/v1/shop/cart/{website_id}",
        json=payload,
        headers=AUTH(verified_user["token"]),
    )

    assert r.status_code == 422
    assert "invalid product_id" in r.json().get("detail", "")


def test_create_cart_item_writes_stock_quantity(client, verified_user, _in_memory_db):
    _bootstrap_shop_tables(_in_memory_db)

    website_id = str(uuid.uuid4())
    _in_memory_db.execute(
        "INSERT INTO websites (website_id, user_id, name, cart_features) VALUES (?, ?, ?, ?)",
        (website_id, verified_user["user_id"], "Wave5 Cart", json.dumps(["shopping_cart"])),
    )

    payload = {
        "website_id": website_id,
        "name": "Widget",
        "description": "Sample",
        "price": 12.5,
        "stock": 9,
        "currency": "USD",
    }

    r = client.post("/api/v1/shop/cart-items", json=payload, headers=AUTH(verified_user["token"]))
    assert r.status_code == 200
    product_id = r.json()["product_id"]

    row = _in_memory_db.fetchone(
        "SELECT product_id, stock_quantity FROM cart_items WHERE product_id = ?",
        (product_id,),
    )
    assert row is not None
    assert row["stock_quantity"] == 9


def test_wave5_schema_defaults_and_contracts_present():
    ddl = "\n".join(TABLES)

    assert "title         VARCHAR(300) DEFAULT ''" in ddl
    assert "description   VARCHAR(2000) DEFAULT ''" in ddl
    assert "domain        VARCHAR(300) DEFAULT ''" in ddl
    assert "s3_url        VARCHAR(500) DEFAULT ''" in ddl
    assert "items_json VARIANT DEFAULT '[]'" in ddl

    cart_items_block = next(x for x in TABLES if "CREATE TABLE IF NOT EXISTS cart_items" in x)
    assert "stock_quantity" in cart_items_block
    assert "stock           INTEGER" not in cart_items_block
