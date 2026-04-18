"""
DDL / migration script — run once to initialise the Snowflake schema.
Execute: python -m database.migrations
"""
from database.snowflake_client import db

TABLES = [
    # ── Users / Tenants ───────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id        VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        email          VARCHAR(320) UNIQUE NOT NULL,
        mobile         VARCHAR(20),
        password_hash  VARCHAR(256),
        full_name      VARCHAR(200),
        is_verified    BOOLEAN      DEFAULT FALSE,
        plan           VARCHAR(20)  DEFAULT 'free',   -- free | pro | enterprise
        stripe_customer_id VARCHAR(64),
        created_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
        updated_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── OTP tokens ────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS otp_tokens (
        token_id   VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        user_id    VARCHAR(36)  NOT NULL REFERENCES users(user_id),
        otp_code   VARCHAR(10)  NOT NULL,
        channel    VARCHAR(10)  NOT NULL,   -- email | sms
        expires_at TIMESTAMP_NTZ NOT NULL,
        used       BOOLEAN      DEFAULT FALSE,
        created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Websites ──────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS websites (
        website_id    VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        user_id       VARCHAR(36)  NOT NULL REFERENCES users(user_id),
        name          VARCHAR(200) NOT NULL,
        title         VARCHAR(300),
        description   VARCHAR(2000),
        logo_url      VARCHAR(500),
        domain        VARCHAR(300),
        hosting_env   VARCHAR(20)  DEFAULT 's3',  -- s3 | custom
        theme         VARCHAR(50)  DEFAULT 'modern',
        custom_css    TEXT,
        pages_json    VARIANT,                    -- JSON array of page configs
        s3_bucket     VARCHAR(200),
        s3_url        VARCHAR(500),
        status        VARCHAR(20)  DEFAULT 'draft',
        plan_required VARCHAR(20)  DEFAULT 'free',
        created_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
        updated_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Product Categories ────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS product_categories (
        category_id   VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        website_id    VARCHAR(36)  NOT NULL REFERENCES websites(website_id),
        parent_id     VARCHAR(36),
        name          VARCHAR(200) NOT NULL,
        slug          VARCHAR(200),
        description   VARCHAR(1000),
        image_url     VARCHAR(500),
        sort_order    INTEGER      DEFAULT 0,
        created_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Products ──────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS products (
        product_id    VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        website_id    VARCHAR(36)  NOT NULL REFERENCES websites(website_id),
        category_id   VARCHAR(36)  REFERENCES product_categories(category_id),
        name          VARCHAR(300) NOT NULL,
        slug          VARCHAR(300),
        description   TEXT,
        price         NUMBER(12,2) NOT NULL DEFAULT 0,
        currency      VARCHAR(3)   DEFAULT 'USD',
        stock         INTEGER      DEFAULT 0,
        images_json   VARIANT,
        attributes    VARIANT,
        is_active     BOOLEAN      DEFAULT TRUE,
        created_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
        updated_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Carts ─────────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS carts (
        cart_id    VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        user_id    VARCHAR(36)  REFERENCES users(user_id),
        website_id VARCHAR(36)  NOT NULL REFERENCES websites(website_id),
        session_id VARCHAR(100),
        items_json VARIANT,
        currency   VARCHAR(3)   DEFAULT 'USD',
        created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
        updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Orders ────────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS orders (
        order_id          VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        cart_id           VARCHAR(36)  REFERENCES carts(cart_id),
        user_id           VARCHAR(36)  REFERENCES users(user_id),
        website_id        VARCHAR(36)  NOT NULL REFERENCES websites(website_id),
        status            VARCHAR(20)  DEFAULT 'pending',
        total_amount      NUMBER(12,2),
        currency          VARCHAR(3)   DEFAULT 'USD',
        stripe_payment_id VARCHAR(120),
        shipping_address  VARIANT,
        items_snapshot    VARIANT,
        created_at        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
        updated_at        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Subscriptions (platform billing) ─────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS subscriptions (
        sub_id              VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        user_id             VARCHAR(36)  NOT NULL REFERENCES users(user_id),
        plan                VARCHAR(20)  NOT NULL,
        stripe_sub_id       VARCHAR(120),
        status              VARCHAR(20)  DEFAULT 'active',
        current_period_end  TIMESTAMP_NTZ,
        created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Analytics / Activity log ──────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS activity_log (
        log_id     VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        user_id    VARCHAR(36)  REFERENCES users(user_id),
        website_id VARCHAR(36)  REFERENCES websites(website_id),
        event      VARCHAR(100) NOT NULL,
        meta       VARIANT,
        ip_address VARCHAR(45),
        country    VARCHAR(60),
        created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Payment gateway configs per website ───────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS payment_configs (
        config_id          VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        website_id         VARCHAR(36)  NOT NULL REFERENCES websites(website_id),
        gateway            VARCHAR(30)  DEFAULT 'stripe',
        publishable_key    VARCHAR(200),
        secret_key_enc     VARCHAR(500),   -- AES-encrypted at rest
        webhook_secret_enc VARCHAR(500),
        enabled_methods    VARIANT,        -- ["card","paypal","apple_pay",...]
        created_at         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,
]


def run_migrations():
    print("Running Snowflake migrations…")
    for ddl in TABLES:
        db.execute(ddl.strip())
    print("✅ All tables created / verified.")


if __name__ == "__main__":
    run_migrations()
