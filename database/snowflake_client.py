"""
Database client — uses Snowflake when credentials are configured,
falls back to SQLite (local file: data/website_builder.db) automatically.

Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER and SNOWFLAKE_PASSWORD in .env to
switch to Snowflake.  Leave them blank to use the built-in SQLite fallback.
"""
import os
import re
import sqlite3
import threading
import atexit
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
    sql = re.sub(r"PARSE_JSON\((%s|\?|'[^']*')\)", r"\1", sql, flags=re.IGNORECASE)
    sql = re.sub(r"REFERENCES \w+\(\w+\)", "", sql, flags=re.IGNORECASE)
    # Normalise placeholders: Snowflake uses %s, SQLite requires ?
    sql = sql.replace("%s", "?")
    return sql


class SQLiteClient:
    def __init__(self, db_path: str = SQLITE_PATH):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._db_path = db_path
        self._thread_local = threading.local()
        self._all_conns: Dict[int, sqlite3.Connection] = {}
        self._conn_lock = threading.Lock()
        atexit.register(self.close_all)
        print(f"ℹ️  Snowflake not configured — using SQLite at '{db_path}'")

    def _new_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=OFF")
        return conn

    def _get_connection(self) -> sqlite3.Connection:
        """Return a per-thread pooled SQLite connection."""
        conn = getattr(self._thread_local, "conn", None)
        if conn is not None:
            return conn

        conn = self._new_connection()
        self._thread_local.conn = conn
        tid = threading.get_ident()
        with self._conn_lock:
            self._all_conns[tid] = conn
        return conn

    def _refresh_connection(self) -> sqlite3.Connection:
        """Replace a stale/broken connection for current thread."""
        old = getattr(self._thread_local, "conn", None)
        if old is not None:
            try:
                old.close()
            except Exception:
                pass

        conn = self._new_connection()
        self._thread_local.conn = conn
        tid = threading.get_ident()
        with self._conn_lock:
            self._all_conns[tid] = conn
        return conn

    def close_all(self) -> None:
        with self._conn_lock:
            conns = list(self._all_conns.values())
            self._all_conns.clear()
        for conn in conns:
            try:
                conn.close()
            except Exception:
                pass

    def execute(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        sql = _adapt_sql_for_sqlite(sql)
        try:
            conn = self._get_connection()
            cur = conn.execute(sql, params or ())
            conn.commit()
            try:
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            except Exception:
                return []
        except sqlite3.ProgrammingError as exc:
            # Connection may be stale/closed; refresh once and retry.
            print(f"[sqlite] stale connection detected, refreshing pool entry: {exc}")
            try:
                conn = self._refresh_connection()
                cur = conn.execute(sql, params or ())
                conn.commit()
                try:
                    rows = cur.fetchall()
                    return [dict(r) for r in rows]
                except Exception:
                    return []
            except Exception as retry_exc:
                print(f"[sqlite] execute retry error: {retry_exc}\nSQL: {sql[:200]}")
                return []
        except Exception as exc:
            print(f"[sqlite] execute error: {exc}\nSQL: {sql[:200]}")
            return []

    def execute_many(self, sql: str, rows: List[tuple]) -> None:
        sql = _adapt_sql_for_sqlite(sql)
        conn = self._get_connection()
        try:
            conn.executemany(sql, rows)
            conn.commit()
        except sqlite3.ProgrammingError:
            conn = self._refresh_connection()
            conn.executemany(sql, rows)
            conn.commit()

    def fetchone(self, sql: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        results = self.execute(sql, params)
        return results[0] if results else None

    def fetchall(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        return self.execute(sql, params)


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

    def fetchall(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        return self.execute(sql, params)


# ── Auto-select backend ────────────────────────────────────────────────────────

def _create_db_client():
    if _snowflake_configured:
        print("✅ Snowflake credentials found — connecting to Snowflake.")
        return SnowflakeClient()
    return SQLiteClient()


db = _create_db_client()
