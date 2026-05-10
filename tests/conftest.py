"""
Shared pytest fixtures.

Uses an isolated in-memory SQLite DB so tests never touch the real data file.
"""
import os
import sys
import types
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

# ── Point the app at an in-memory SQLite DB before anything imports ──────────
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("STRIPE_SECRET_KEY", "")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("ALLOW_MISSING_OPENAI_API_KEY", "true")

# Stub out Snowflake so the import chain works without real credentials
snowflake_stub = types.ModuleType("snowflake")
snowflake_connector_stub = types.ModuleType("snowflake.connector")
snowflake_stub.connector = snowflake_connector_stub
sys.modules.setdefault("snowflake", snowflake_stub)
sys.modules.setdefault("snowflake.connector", snowflake_connector_stub)


@pytest.fixture(scope="session", autouse=True)
def _in_memory_db():
    """Replace the global db singleton with an in-memory SQLite backed client."""
    import database.snowflake_client as sc

    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.row_factory = sqlite3.Row

    # Minimal mirror of the real db client interface.
    # Translates Snowflake-style %s placeholders → SQLite ? placeholders.
    # Also normalises CURRENT_TIMESTAMP() → CURRENT_TIMESTAMP for SQLite.
    class _MemDB:
        @staticmethod
        def _sq(sql: str) -> str:
            import re as _re
            s = sql.replace("%s", "?")
            s = _re.sub(r'CURRENT_TIMESTAMP\(\)', 'CURRENT_TIMESTAMP', s, flags=_re.IGNORECASE)
            s = _re.sub(r'\bTRUE\b', '1', s)
            s = _re.sub(r'\bFALSE\b', '0', s)
            return s

        def execute(self, sql, params=()):
            con.execute(self._sq(sql), params)
            con.commit()

        def fetchone(self, sql, params=()):
            row = con.execute(self._sq(sql), params).fetchone()
            return dict(row) if row else None

        def fetchall(self, sql, params=()):
            return [dict(r) for r in con.execute(self._sq(sql), params).fetchall()]

    mem = _MemDB()
    sc.db = mem

    # Bootstrap schema (minimal subset needed for tests)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            mobile TEXT DEFAULT '',
            role TEXT DEFAULT 'app_user',
            plan TEXT DEFAULT 'free',
            is_verified INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            stripe_customer_id TEXT,
            owner_id TEXT,
            client_website_id TEXT,
            permissions TEXT DEFAULT '[]',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS otp_tokens (
            token_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            otp_code TEXT NOT NULL,
            channel TEXT NOT NULL,
            expires_at DATETIME NOT NULL,
            used INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS websites (
            website_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            title TEXT,
            description TEXT DEFAULT '',
            logo_url TEXT DEFAULT '',
            domain TEXT DEFAULT '',
            hosting_env TEXT DEFAULT 's3',
            theme TEXT DEFAULT 'modern',
            custom_css TEXT DEFAULT '',
            pages_json TEXT DEFAULT '[]',
            s3_bucket TEXT,
            image_storage_backend TEXT DEFAULT 'auto',
            image_storage_config TEXT DEFAULT '{}',
            classification TEXT DEFAULT 'generic',
            build_mode TEXT DEFAULT 'agentic_only',
            output_target TEXT DEFAULT 'legacy',
            classification_label TEXT DEFAULT '',
            classification_group TEXT DEFAULT '',
            input_snapshot_json TEXT DEFAULT '{}',
            source_context_json TEXT DEFAULT '{}',
            s3_url TEXT,
            status TEXT DEFAULT 'draft',
            plan_required TEXT DEFAULT 'free',
            cart_features TEXT DEFAULT '[]',
            enable_chatbot INTEGER DEFAULT 0,
            enable_blog INTEGER DEFAULT 0,
            enable_livestream INTEGER DEFAULT 0,
            build_status TEXT DEFAULT 'idle',
            build_job_id TEXT,
            build_started_at DATETIME,
            build_error TEXT,
            live_url TEXT,
            local_path TEXT DEFAULT '',
            content_depth INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            sub_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            stripe_sub_id TEXT,
            status TEXT DEFAULT 'active',
            current_period_end TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    con.commit()
    yield mem


@pytest.fixture()
def client(_in_memory_db):
    """Return a TestClient for the FastAPI app."""
    from fastapi.testclient import TestClient
    # Patch external side-effects that would fail without real credentials
    with (
        patch("services.otp_service.deliver_otp", return_value=None),
        patch("services.payment_service.create_stripe_customer", return_value="cus_test123"),
        patch("database.migrations.run_migrations", return_value=None),
    ):
        from app import app
        with TestClient(app, raise_server_exceptions=True) as tc:
            yield tc


@pytest.fixture()
def verified_user(_in_memory_db):
    """Insert and return a pre-verified app_user for use in auth-required tests."""
    import uuid
    from services.auth_service import hash_password, create_access_token
    uid = str(uuid.uuid4())
    email = f"test_{uid[:8]}@example.com"
    pw = "Str0ng!Pass"
    _in_memory_db.execute(
        """INSERT INTO users (user_id, email, password_hash, role, is_verified, is_active)
           VALUES (?, ?, ?, 'app_user', 1, 1)""",
        (uid, email, hash_password(pw)),
    )
    token = create_access_token(uid, email, role="app_user")
    return {"user_id": uid, "email": email, "password": pw, "token": token}
