"""
Database client — uses Snowflake when credentials are configured,
falls back to SQLite (local file: data/website_builder.db) automatically.

Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER and SNOWFLAKE_PASSWORD in .env to
switch to Snowflake.  Leave them blank to use the built-in SQLite fallback.
"""
import os
import re
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.getenv("SQLITE_DB_PATH", "data/website_builder.db")

_snowflake_configured = all([
    os.getenv("SNOWFLAKE_ACCOUNT"),
    os.getenv("SNOWFLAKE_USER"),
    os.getenv("SNOWFLAKE_PASSWORD"),
])


# ── SQLite backend ─────────────────────────────────────────────────────────────

def _adapt_sql_for_sqlite(sql: str) -> str:
    """Convert Snowflake-specific SQL to SQLite-compatible SQL."""
    sql = re.sub(r"DEFAULT UUID_STRING\(\)", "DEFAULT (lower(hex(randomblob(4)))||'-'||lower(hex(randomblob(2)))||'-4'||substr(lower(hex(randomblob(2))),2)||'-'||substr('89ab',abs(random())%4+1,1)||substr(lower(hex(randomblob(2))),2)||'-'||lower(hex(randomblob(6))))", sql)
    sql = re.sub(r"TIMESTAMP_NTZ", "DATETIME", sql, flags=re.IGNORECASE)
    sql = re.sub(r"DEFAULT CURRENT_TIMESTAMP\(\)", "DEFAULT CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"CURRENT_TIMESTAMP\(\)", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"VARCHAR\(\d+\)", "TEXT", sql, flags=re.IGNORECASE)
    sql = re.sub(r"NUMBER\(\d+,\d+\)", "REAL", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bVARIANT\b", "TEXT", sql, flags=re.IGNORECASE)
    sql = re.sub(r"PARSE_JSON\((%s|'[^']*')\)", r"\1", sql, flags=re.IGNORECASE)
    sql = re.sub(r"REFERENCES \w+\(\w+\)", "", sql, flags=re.IGNORECASE)
    return sql


class SQLiteClient:
    def __init__(self, db_path: str = SQLITE_PATH):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._db_path = db_path
        print(f"ℹ️  Snowflake not configured — using SQLite at '{db_path}'")

    def _connect(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=OFF")
        return conn

    def execute(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        sql = _adapt_sql_for_sqlite(sql)
        try:
            with self._connect() as conn:
                cur = conn.execute(sql, params or ())
                conn.commit()
                try:
                    rows = cur.fetchall()
                    return [dict(r) for r in rows]
                except Exception:
                    return []
        except Exception as exc:
            print(f"[sqlite] execute error: {exc}\nSQL: {sql[:200]}")
            return []

    def execute_many(self, sql: str, rows: List[tuple]) -> None:
        sql = _adapt_sql_for_sqlite(sql)
        with self._connect() as conn:
            conn.executemany(sql, rows)
            conn.commit()

    def fetchone(self, sql: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        results = self.execute(sql, params)
        return results[0] if results else None


# ── Snowflake backend ──────────────────────────────────────────────────────────

class SnowflakeClient:
    """Thin wrapper around snowflake-connector-python."""

    def __init__(self):
        import snowflake.connector
        from snowflake.connector import DictCursor
        self._sf = snowflake.connector
        self._DictCursor = DictCursor
        self._conn_params = {
            "account":   os.getenv("SNOWFLAKE_ACCOUNT", ""),
            "user":      os.getenv("SNOWFLAKE_USER", ""),
            "password":  os.getenv("SNOWFLAKE_PASSWORD", ""),
            "database":  os.getenv("SNOWFLAKE_DATABASE", "WEBSITE_BUILDER"),
            "schema":    os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            "role":      os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
        }

    @contextmanager
    def get_connection(self):
        conn = self._sf.connect(**self._conn_params)
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor(self._DictCursor) as cur:
                cur.execute(sql, params or ())
                try:
                    return cur.fetchall()
                except Exception:
                    return []

    def execute_many(self, sql: str, rows: List[tuple]) -> None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, rows)
            conn.commit()

    def fetchone(self, sql: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        rows = self.execute(sql, params)
        return rows[0] if rows else None


# ── Auto-select backend ────────────────────────────────────────────────────────

def _create_db_client():
    if _snowflake_configured:
        print("✅ Snowflake credentials found — connecting to Snowflake.")
        return SnowflakeClient()
    return SQLiteClient()


db = _create_db_client()
