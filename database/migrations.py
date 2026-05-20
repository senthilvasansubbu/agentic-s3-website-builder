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
        title         VARCHAR(300) DEFAULT '',
        description   VARCHAR(2000) DEFAULT '',
        logo_url      VARCHAR(500),
        domain        VARCHAR(300) DEFAULT '',
        hosting_env   VARCHAR(20)  DEFAULT 's3',  -- s3 | custom
        theme         VARCHAR(50)  DEFAULT 'modern',
        custom_css    TEXT,
        pages_json    VARIANT,                    -- JSON array of page configs
        s3_bucket     VARCHAR(200),
        image_storage_backend VARCHAR(20) DEFAULT 'auto', -- auto | local | s3 | gdrive
        image_storage_config  VARIANT,
        classification VARCHAR(50) DEFAULT 'generic',
        build_mode    VARCHAR(20)  DEFAULT 'agentic_only', -- combined | agentic_only
        output_target VARCHAR(30)  DEFAULT 'legacy',       -- legacy | react | vue | php | ...
        classification_label VARCHAR(120),
        classification_group VARCHAR(120),
        input_snapshot_json VARIANT,
        source_context_json VARIANT,
        s3_url        VARCHAR(500) DEFAULT '',
        status        VARCHAR(20)  DEFAULT 'draft',
        plan_required VARCHAR(20)  DEFAULT 'free',
        created_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
        updated_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Cart Categories ─────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS cart_categories (
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

    # ── Cart Items ────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS cart_items (
        product_id      VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        website_id      VARCHAR(36)  NOT NULL REFERENCES websites(website_id),
        category_id     VARCHAR(36)  REFERENCES cart_categories(category_id),
        name            VARCHAR(300) NOT NULL,
        slug            VARCHAR(300),
        description     TEXT,
        price           NUMBER(12,2) NOT NULL DEFAULT 0,
        compare_price   NUMBER(12,2) DEFAULT 0,
        discount_pct    NUMBER(5,2)  DEFAULT 0,
        currency        VARCHAR(3)   DEFAULT 'USD',
        stock_quantity  INTEGER      DEFAULT 0,
        image_url       VARCHAR(500),
        images_json     VARIANT,
        attributes      VARIANT,
        is_flash_offer  BOOLEAN      DEFAULT FALSE,
        flash_offer_ends TIMESTAMP_NTZ,
        is_active       BOOLEAN      DEFAULT TRUE,
        created_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
        updated_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Carts ─────────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS carts (
        cart_id    VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        user_id    VARCHAR(36)  REFERENCES users(user_id),
        website_id VARCHAR(36)  NOT NULL REFERENCES websites(website_id),
        session_id VARCHAR(100),
        items_json VARIANT DEFAULT '[]',
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
        next_billing_date   TEXT,
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
        secret_key_enc     VARCHAR(500),
        webhook_secret_enc VARCHAR(500),
        enabled_methods    VARIANT,
        created_at         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Customer feedback ─────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        website_id  VARCHAR(36)  REFERENCES websites(website_id),
        name        VARCHAR(120),
        email       VARCHAR(200),
        rating      INTEGER      DEFAULT 5,
        message     TEXT,
        created_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Monitor checks — one row per check type per website ───────────────────
    """
    CREATE TABLE IF NOT EXISTS monitor_checks (
        check_id     VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        website_id   VARCHAR(36)  REFERENCES websites(website_id),
        check_type   VARCHAR(60)  NOT NULL,
        status       VARCHAR(20)  NOT NULL,
        latency_ms   INTEGER,
        detail       TEXT,
        checked_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Monitor incidents — open/resolved outage records ─────────────────────
    """
    CREATE TABLE IF NOT EXISTS monitor_incidents (
        incident_id  VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        website_id   VARCHAR(36)  REFERENCES websites(website_id),
        check_type   VARCHAR(60)  NOT NULL,
        severity     VARCHAR(20)  DEFAULT 'warning',
        status       VARCHAR(20)  DEFAULT 'open',
        detail       TEXT,
        notified_at  TIMESTAMP_NTZ,
        resolved_at  TIMESTAMP_NTZ,
        created_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Payment reminders & escalation log ───────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS payment_reminders (
        reminder_id   VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        user_id       VARCHAR(36)  REFERENCES users(user_id),
        reminder_type VARCHAR(40)  NOT NULL,
        channel       VARCHAR(20)  NOT NULL,
        status        VARCHAR(20)  DEFAULT 'sent',
        due_date      TEXT,
        amount        REAL,
        sent_at       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Notification log ─────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS notification_log (
        log_id       VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        user_id      VARCHAR(36),
        channel      VARCHAR(20)  NOT NULL,
        destination  VARCHAR(200) NOT NULL,
        subject      VARCHAR(300),
        body         TEXT,
        status       VARCHAR(20)  DEFAULT 'sent',
        error        TEXT,
        sent_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Coupons ───────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS coupons (
        coupon_id      VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        website_id     VARCHAR(36)  NOT NULL REFERENCES websites(website_id),
        code           VARCHAR(50)  NOT NULL,
        discount_type  VARCHAR(10)  NOT NULL DEFAULT 'percent',
        discount_value NUMBER(10,2) NOT NULL DEFAULT 0,
        min_order      NUMBER(10,2) DEFAULT 0,
        max_uses       INTEGER      DEFAULT 0,
        uses_count     INTEGER      DEFAULT 0,
        valid_from     TEXT,
        valid_until    TEXT,
        is_active      INTEGER      DEFAULT 1,
        created_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Advertisements ────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS advertisements (
        ad_id      VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        website_id VARCHAR(36)  NOT NULL REFERENCES websites(website_id),
        title      VARCHAR(200),
        image_url  VARCHAR(500),
        link_url   VARCHAR(500),
        position   VARCHAR(30)  DEFAULT 'banner',
        is_active  INTEGER      DEFAULT 1,
        starts_at  TEXT,
        ends_at    TEXT,
        created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Notification campaigns ────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS notification_campaigns (
        campaign_id  VARCHAR(36)  PRIMARY KEY DEFAULT UUID_STRING(),
        website_id   VARCHAR(36)  NOT NULL REFERENCES websites(website_id),
        owner_id     VARCHAR(36)  NOT NULL REFERENCES users(user_id),
        title        VARCHAR(200) NOT NULL,
        channel      VARCHAR(20)  NOT NULL,
        subject      VARCHAR(300),
        body         TEXT         NOT NULL,
        status       VARCHAR(20)  DEFAULT 'draft',
        sent_count   INTEGER      DEFAULT 0,
        scheduled_at TEXT,
        sent_at      TEXT,
        created_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """,

    # ── Plan Feature Access ───────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS plan_features (
        plan     TEXT NOT NULL,
        feature  TEXT NOT NULL,
        enabled  INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (plan, feature)
    )
    """,
]


def _safe_alter(sql: str):
    """Run an ALTER TABLE silently — ignore if column already exists."""
    try:
        from database.snowflake_client import db
        db.execute(sql)
    except Exception:
        pass


def run_migrations():
    print("Running migrations…")
    from database.snowflake_client import db

    # ── Schema version tracking ───────────────────────────────────────────────
    db.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            description TEXT,
            applied_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    def _applied(v: int) -> bool:
        rows = db.execute("SELECT version FROM schema_version WHERE version = ?", [v])
        return bool(rows)

    def _mark(v: int, desc: str):
        try:
            db.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                [v, desc]
            )
        except Exception:
            pass  # already recorded

    def _exec_strict(sql: str, params=None):
        fn = getattr(db, "execute_strict", None)
        if callable(fn):
            return fn(sql, tuple(params or ()))
        return db.execute(sql, tuple(params or ()))

    def _table_columns(table_name: str) -> set[str]:
        """Best-effort table column discovery for SQLite/Snowflake backends."""
        safe_table = "".join(ch for ch in str(table_name or "") if ch.isalnum() or ch == "_")
        if not safe_table:
            return set()

        # SQLite path
        try:
            rows = db.fetchall(f"PRAGMA table_info({safe_table})")
            cols = {str(r.get("name") or "").strip().lower() for r in (rows or []) if r.get("name")}
            if cols:
                return cols
        except Exception:
            pass

        # Snowflake path
        try:
            rows = db.fetchall(
                "SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS "
                f"WHERE table_name = '{safe_table.upper()}'"
            )
            cols = {str(r.get("COLUMN_NAME") or r.get("column_name") or "").strip().lower() for r in (rows or [])}
            return {c for c in cols if c}
        except Exception:
            return set()

    def _has_column(table_name: str, column_name: str) -> bool:
        return str(column_name or "").strip().lower() in _table_columns(table_name)

    def _run_migration(version: int, description: str, up_fn, rollback_fn=None):
        """Apply a migration in a transaction and rollback on failure."""
        if _applied(version):
            return
        try:
            _exec_strict("BEGIN")
            up_fn()
            _mark(version, description)
            _exec_strict("COMMIT")
        except Exception as exc:
            try:
                _exec_strict("ROLLBACK")
            except Exception:
                pass
            if rollback_fn is not None:
                try:
                    rollback_fn()
                except Exception:
                    pass
            raise RuntimeError(f"Migration v{version} failed: {description}: {exc}")

    # ── Base tables (always idempotent via CREATE IF NOT EXISTS) ─────────────
    for ddl in TABLES:
        db.execute(ddl.strip())

    # ── Version 1: initial additive columns ──────────────────────────────────
    if not _applied(1):
        _safe_alter("ALTER TABLE users ADD COLUMN owner_id TEXT")
        _safe_alter("ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT '[]'")
        _safe_alter("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'app_user'")
        _safe_alter("ALTER TABLE users ADD COLUMN client_website_id TEXT")
        _safe_alter("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        _mark(1, "initial user/website/cart additive columns")

    # ── Version 2: website feature flags ─────────────────────────────────────
    if not _applied(2):
        _safe_alter("ALTER TABLE websites ADD COLUMN cart_features TEXT DEFAULT '[]'")
        _safe_alter("ALTER TABLE websites ADD COLUMN enable_chatbot INTEGER DEFAULT 0")
        _safe_alter("ALTER TABLE websites ADD COLUMN enable_blog INTEGER DEFAULT 0")
        _safe_alter("ALTER TABLE websites ADD COLUMN enable_livestream INTEGER DEFAULT 0")
        _mark(2, "website feature flag columns")

    # ── Version 3: cart item enhancements ────────────────────────────────────
    if not _applied(3):
        for col, ddl in [
            ("image_url", "ALTER TABLE cart_items ADD COLUMN image_url TEXT"),
            ("compare_price", "ALTER TABLE cart_items ADD COLUMN compare_price REAL DEFAULT 0"),
            ("discount_pct", "ALTER TABLE cart_items ADD COLUMN discount_pct REAL DEFAULT 0"),
            ("is_flash_offer", "ALTER TABLE cart_items ADD COLUMN is_flash_offer INTEGER DEFAULT 0"),
            ("flash_offer_ends", "ALTER TABLE cart_items ADD COLUMN flash_offer_ends TEXT"),
            ("stock_quantity", "ALTER TABLE cart_items ADD COLUMN stock_quantity INTEGER DEFAULT 0"),
            ("updated_at", "ALTER TABLE cart_items ADD COLUMN updated_at TEXT"),
        ]:
            if not _has_column("cart_items", col):
                _safe_alter(ddl)
        _mark(3, "cart item price/stock/flash-offer columns")

    # ── Version 4: async build tracking ──────────────────────────────────────
    if not _applied(4):
        _safe_alter("ALTER TABLE websites ADD COLUMN build_status TEXT DEFAULT 'idle'")
        _safe_alter("ALTER TABLE websites ADD COLUMN build_job_id TEXT")
        _safe_alter("ALTER TABLE websites ADD COLUMN build_started_at TEXT")
        _safe_alter("ALTER TABLE websites ADD COLUMN build_error TEXT")
        _safe_alter("ALTER TABLE websites ADD COLUMN classification TEXT DEFAULT 'generic'")
        _safe_alter("ALTER TABLE websites ADD COLUMN live_url TEXT")
        _mark(4, "async build tracking columns")

    # ── Version 5: superuser role back-fill ──────────────────────────────────
    if not _applied(5):
        try:
            db.execute(
                "UPDATE users SET role='superuser' "
                "WHERE plan='superuser' AND (role IS NULL OR role='app_user')"
            )
        except Exception:
            pass
        _mark(5, "backfill superuser role from plan field")

    # ── Version 6: per-website image storage configuration ───────────────────
    if not _applied(6):
        _safe_alter("ALTER TABLE websites ADD COLUMN image_storage_backend TEXT DEFAULT 'auto'")
        _safe_alter("ALTER TABLE websites ADD COLUMN image_storage_config TEXT")
        _mark(6, "website image storage backend and config columns")

    # ── Version 7: encrypted per-website storage credentials ────────────────
    if not _applied(7):
        _safe_alter("ALTER TABLE websites ADD COLUMN image_storage_secrets_enc TEXT")
        _mark(7, "encrypted website storage credentials")

    # ── Version 8: generation contract fields ───────────────────────────────
    if not _applied(8):
        _safe_alter("ALTER TABLE websites ADD COLUMN build_mode TEXT DEFAULT 'agentic_only'")
        _safe_alter("ALTER TABLE websites ADD COLUMN output_target TEXT DEFAULT 'legacy'")
        _safe_alter("ALTER TABLE websites ADD COLUMN classification_label TEXT")
        _safe_alter("ALTER TABLE websites ADD COLUMN input_snapshot_json TEXT")
        _safe_alter("ALTER TABLE websites ADD COLUMN source_context_json TEXT")
        _mark(8, "build mode/output target/classification label/context snapshot columns")

    # ── Version 9: grouped classification taxonomy ─────────────────────────
    if not _applied(9):
        _safe_alter("ALTER TABLE websites ADD COLUMN classification_group TEXT")
        _mark(9, "grouped classification taxonomy column")

    # ── Version 10: content depth (replaces num_pages) ────────────────────
    if not _applied(10):
        if not _has_column("websites", "content_depth"):
            _safe_alter("ALTER TABLE websites ADD COLUMN content_depth TEXT DEFAULT 'standard'")
        # Migrate existing num_pages values to closest depth tier only if both columns exist
        if _has_column("websites", "num_pages") and _has_column("websites", "content_depth"):
            try:
                db.execute(
                    "UPDATE websites SET content_depth = CASE\n"
                    "    WHEN num_pages <= 1 THEN 'minimal'\n"
                    "    WHEN num_pages <= 3 THEN 'standard'\n"
                    "    WHEN num_pages > 3 THEN 'rich'\n"
                    "    ELSE 'unknown' END"
                )
            except Exception:
                pass
        _mark(10, "content_depth column replacing num_pages")

    # ── Version 11: enable foreign-key enforcement + orphan cleanup ───────────
    if not _applied(11):
        # Remove orphaned child rows before PRAGMA foreign_keys=ON is enforced.
        # This runs once; subsequent connections already have FK enforcement on.
        try:
            # websites whose owner user no longer exists
            db.execute(
                "DELETE FROM websites WHERE user_id NOT IN (SELECT user_id FROM users)"
            )
            # carts whose website no longer exists
            db.execute(
                "DELETE FROM carts WHERE website_id NOT IN (SELECT website_id FROM websites)"
            )
            # cart_items whose website no longer exists
            db.execute(
                "DELETE FROM cart_items WHERE website_id NOT IN (SELECT website_id FROM websites)"
            )
            # orders whose website no longer exists
            db.execute(
                "DELETE FROM orders WHERE website_id NOT IN (SELECT website_id FROM websites)"
            )
            # subscriptions whose user no longer exists
            db.execute(
                "DELETE FROM subscriptions WHERE user_id NOT IN (SELECT user_id FROM users)"
            )
            # client users whose owner_id no longer exists
            db.execute(
                "DELETE FROM users WHERE role='client' AND owner_id IS NOT NULL "
                "AND owner_id NOT IN (SELECT user_id FROM users)"
            )
        except Exception as _exc:
            print(f"⚠️  Orphan cleanup warning (non-fatal): {_exc}")
        _mark(11, "foreign-key enforcement enabled + orphan row cleanup")

    # ── Version 12: consolidate cart stock fields (stock_quantity canonical) ─
    def _up_v12():
        # Only add stock_quantity column if it does not already exist
        has_stock_quantity = _has_column("cart_items", "stock_quantity")
        if not has_stock_quantity:
            _safe_alter("ALTER TABLE cart_items ADD COLUMN stock_quantity INTEGER DEFAULT 0")
            has_stock_quantity = True
        has_stock = _has_column("cart_items", "stock")

        # Backfill canonical stock_quantity from legacy stock only when that legacy column actually exists.
        if has_stock_quantity:
            if has_stock:
                try:
                    _exec_strict(
                        "UPDATE cart_items SET stock_quantity = COALESCE(stock_quantity, stock, 0)"
                    )
                except Exception:
                    pass
                # Remove redundant legacy stock column.
                try:
                    if _has_column("cart_items", "stock"):
                        _safe_alter("ALTER TABLE cart_items DROP COLUMN stock")
                except Exception:
                    pass
            else:
                try:
                    _exec_strict("UPDATE cart_items SET stock_quantity = COALESCE(stock_quantity, 0)")
                except Exception:
                    pass

    def _down_v12():
        _safe_alter("ALTER TABLE cart_items ADD COLUMN stock INTEGER DEFAULT 0")
        if _has_column("cart_items", "stock") and _has_column("cart_items", "stock_quantity"):
            _exec_strict("UPDATE cart_items SET stock = COALESCE(stock_quantity, 0)")

    _run_migration(
        12,
        "cart_items uses stock_quantity as the sole stock field",
        _up_v12,
        _down_v12,
    )

    # ── Version 13: carts.items_json contract + validation metadata ───────────
    def _up_v13():
        _safe_alter("ALTER TABLE carts ADD COLUMN items_json TEXT DEFAULT '[]'")
        _exec_strict("UPDATE carts SET items_json = '[]' WHERE items_json IS NULL OR TRIM(items_json) = ''")
        _exec_strict(
            """
            CREATE TABLE IF NOT EXISTS schema_contracts (
                contract_id TEXT PRIMARY KEY,
                schema_json TEXT NOT NULL,
                notes TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _exec_strict(
            """
            INSERT OR REPLACE INTO schema_contracts (contract_id, schema_json, notes)
            VALUES (
                'carts.items_json',
                '{"type":"array","items":{"type":"object","required":["product_id","qty"],"properties":{"product_id":{"type":"string","format":"uuid"},"qty":{"type":"integer","minimum":1}},"additionalProperties":false}}',
                'Validated in api/routes/shopping_cart.py::_validate_cart_items_payload'
            )
            """
        )

    def _down_v13():
        _exec_strict("DELETE FROM schema_contracts WHERE contract_id = 'carts.items_json'")

    _run_migration(
        13,
        "define carts.items_json schema contract and normalize null cart payloads",
        _up_v13,
        _down_v13,
    )

    # ── Version 14: normalize nullable website fields to empty-string defaults ─
    def _up_v14():
        _exec_strict("UPDATE websites SET title = '' WHERE title IS NULL")
        _exec_strict("UPDATE websites SET description = '' WHERE description IS NULL")
        _exec_strict("UPDATE websites SET domain = '' WHERE domain IS NULL")
        _exec_strict("UPDATE websites SET s3_url = '' WHERE s3_url IS NULL")

    def _down_v14():
        # Irreversible data normalization (empty string may be intentional), keep no-op.
        return

    _run_migration(
        14,
        "normalize website nullable text fields (title/description/domain/s3_url)",
        _up_v14,
        _down_v14,
    )

    # ── Version 15: migration rollback registry metadata ──────────────────────
    def _up_v15():
        _exec_strict(
            """
            CREATE TABLE IF NOT EXISTS migration_rollback_registry (
                version INTEGER PRIMARY KEY,
                rollback_notes TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _exec_strict(
            "INSERT OR REPLACE INTO migration_rollback_registry (version, rollback_notes) VALUES (12, 'Re-add cart_items.stock and copy from stock_quantity')"
        )
        _exec_strict(
            "INSERT OR REPLACE INTO migration_rollback_registry (version, rollback_notes) VALUES (13, 'Delete schema_contracts row for carts.items_json')"
        )
        _exec_strict(
            "INSERT OR REPLACE INTO migration_rollback_registry (version, rollback_notes) VALUES (14, 'No-op: data normalization is irreversible by design')"
        )
        _exec_strict(
            "INSERT OR REPLACE INTO migration_rollback_registry (version, rollback_notes) VALUES (15, 'Drop migration_rollback_registry table')"
        )

    def _down_v15():
        _exec_strict("DROP TABLE IF EXISTS migration_rollback_registry")

    _run_migration(
        15,
        "register rollback notes and transactional migration framework metadata",
        _up_v15,
        _down_v15,
    )

    # ── Always re-seed plan_features (INSERT OR IGNORE = idempotent) ─────────
    _seed_plan_features()

    print("✅ All tables created / verified.")


# Feature matrix: plan → feature → enabled
_PLAN_FEATURE_SEED = {
    "free":       {"web_search": 1, "social_search": 0, "shopping_cart": 0, "livestream": 0, "blog": 0, "chatbot": 0},
    "pro":        {"web_search": 1, "social_search": 1, "shopping_cart": 1, "livestream": 0, "blog": 0, "chatbot": 1},
    "enterprise": {"web_search": 1, "social_search": 1, "shopping_cart": 1, "livestream": 1, "blog": 1, "chatbot": 1},
    "superuser":  {"web_search": 1, "social_search": 1, "shopping_cart": 1, "livestream": 1, "blog": 1, "chatbot": 1},
}


def _seed_plan_features():
    """Insert default plan-feature rows; skip rows that already exist."""
    from database.snowflake_client import db
    for plan, features in _PLAN_FEATURE_SEED.items():
        for feature, enabled in features.items():
            try:
                db.execute(
                    "INSERT OR IGNORE INTO plan_features (plan, feature, enabled) VALUES (?, ?, ?)",
                    (plan, feature, enabled),
                )
            except Exception:
                pass


if __name__ == "__main__":
    run_migrations()
