"""
Snowflake database client — connection pooling and query helpers.
"""
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import snowflake.connector
from snowflake.connector import DictCursor
from dotenv import load_dotenv

load_dotenv()


class SnowflakeClient:
    """Thin wrapper around snowflake-connector-python."""

    def __init__(self):
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
        """Yield a Snowflake connection and close it when done."""
        conn = snowflake.connector.connect(**self._conn_params)
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a DML/DDL statement and return rows as list-of-dicts."""
        with self.get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute(sql, params or ())
                try:
                    return cur.fetchall()
                except Exception:
                    return []

    def execute_many(self, sql: str, rows: List[tuple]) -> None:
        """Batch-insert helper."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, rows)
            conn.commit()

    def fetchone(self, sql: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        rows = self.execute(sql, params)
        return rows[0] if rows else None


# Singleton instance used across the application
db = SnowflakeClient()
