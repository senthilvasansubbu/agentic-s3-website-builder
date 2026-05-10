import threading
import types
import sqlite3

import database.snowflake_client as sc
from database.snowflake_client import SQLiteClient, SnowflakeClient, _adapt_sql_for_sqlite


def test_sqlite_client_reuses_connection_per_thread(tmp_path):
    db_path = tmp_path / "pooling.db"
    client = SQLiteClient(str(db_path))

    client.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT)")

    conn1 = client._get_connection()
    client.execute("INSERT INTO t (name) VALUES (?)", ("a",))
    conn2 = client._get_connection()

    assert conn1 is conn2
    rows = client.fetchall("SELECT name FROM t")
    assert rows == [{"name": "a"}]

    client.close_all()


def test_sqlite_client_uses_distinct_connections_across_threads(tmp_path):
    db_path = tmp_path / "pooling_threads.db"
    client = SQLiteClient(str(db_path))
    client.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT)")

    conn_ids = []
    lock = threading.Lock()

    def worker(name: str):
        client.execute("INSERT INTO t (name) VALUES (?)", (name,))
        conn = client._get_connection()
        with lock:
            conn_ids.append(id(conn))

    t1 = threading.Thread(target=worker, args=("a",))
    t2 = threading.Thread(target=worker, args=("b",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Distinct threads should have distinct pooled connections.
    assert len(set(conn_ids)) == 2

    rows = client.fetchall("SELECT name FROM t ORDER BY name")
    assert rows == [{"name": "a"}, {"name": "b"}]

    client.close_all()


def test_adapt_sql_for_sqlite_transforms_common_snowflake_syntax():
    sql = (
        "CREATE TABLE demo ("
        "id TEXT DEFAULT UUID_STRING(), "
        "created TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), "
        "payload VARIANT, "
        "price NUMBER(10,2), "
        "name VARCHAR(255), "
        "site_id TEXT REFERENCES websites(website_id)"
        ")"
    )

    adapted = _adapt_sql_for_sqlite(sql)
    assert "UUID_STRING()" not in adapted
    assert "TIMESTAMP_NTZ" not in adapted
    assert "VARIANT" not in adapted
    assert "NUMBER(10,2)" not in adapted
    assert "VARCHAR(255)" not in adapted
    assert "REFERENCES websites(website_id)" not in adapted
    assert "DATETIME" in adapted
    assert "DEFAULT CURRENT_TIMESTAMP" in adapted


def test_sqlite_client_recovers_when_pooled_connection_is_closed(tmp_path):
    db_path = tmp_path / "stale.db"
    client = SQLiteClient(str(db_path))
    client.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT)")

    conn = client._get_connection()
    conn.close()

    # Should transparently refresh the connection and succeed.
    client.execute("INSERT INTO t (name) VALUES (?)", ("after-close",))
    row = client.fetchone("SELECT name FROM t WHERE name = ?", ("after-close",))
    assert row == {"name": "after-close"}
    client.close_all()


def test_sqlite_client_execute_many_and_fetchone_fetchall(tmp_path):
    db_path = tmp_path / "many.db"
    client = SQLiteClient(str(db_path))
    client.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT)")

    client.execute_many("INSERT INTO t (name) VALUES (?)", [("a",), ("b",), ("c",)])

    first = client.fetchone("SELECT name FROM t ORDER BY id LIMIT 1")
    all_rows = client.fetchall("SELECT name FROM t ORDER BY id")

    assert first == {"name": "a"}
    assert all_rows == [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    client.close_all()


def test_sqlite_client_retry_failure_returns_empty_list(tmp_path, monkeypatch):
    client = SQLiteClient(str(tmp_path / "retry_fail.db"))

    def raise_programming_error(*args, **kwargs):
        raise sqlite3.ProgrammingError("closed")

    monkeypatch.setattr(client, "_get_connection", raise_programming_error)

    def raise_retry_error(*args, **kwargs):
        raise RuntimeError("retry failed")

    monkeypatch.setattr(client, "_refresh_connection", raise_retry_error)
    out = client.execute("SELECT 1")
    assert out == []


def test_sqlite_client_execute_many_refresh_path(tmp_path, monkeypatch):
    client = SQLiteClient(str(tmp_path / "retry_many.db"))

    class FirstConn:
        def executemany(self, *args, **kwargs):
            raise sqlite3.ProgrammingError("closed")

        def commit(self):
            pass

    class GoodConn:
        def __init__(self):
            self.called = False

        def executemany(self, *args, **kwargs):
            self.called = True

        def commit(self):
            pass

    good = GoodConn()
    monkeypatch.setattr(client, "_get_connection", lambda: FirstConn())
    monkeypatch.setattr(client, "_refresh_connection", lambda: good)

    client.execute_many("INSERT INTO t(name) VALUES (?)", [("x",)])
    assert good.called is True


def test_close_all_ignores_connection_close_errors(tmp_path):
    client = SQLiteClient(str(tmp_path / "close_err.db"))

    class BadConn:
        def close(self):
            raise RuntimeError("cannot close")

    client._all_conns[123] = BadConn()
    client.close_all()
    assert client._all_conns == {}


def test_snowflake_client_execute_and_execute_many(monkeypatch):
    class DummyCursor:
        def __init__(self, rows=None, fail_fetch=False):
            self._rows = rows or []
            self._fail_fetch = fail_fetch

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params):
            self.last = (sql, params)

        def executemany(self, sql, rows):
            self.many = (sql, rows)

        def fetchall(self):
            if self._fail_fetch:
                raise RuntimeError("no rows")
            return self._rows

    class DummyConn:
        def __init__(self, rows=None, fail_fetch=False):
            self.rows = rows or []
            self.fail_fetch = fail_fetch
            self.committed = False
            self.closed = False

        def cursor(self, *args, **kwargs):
            return DummyCursor(self.rows, self.fail_fetch)

        def commit(self):
            self.committed = True

        def close(self):
            self.closed = True

    conn_ok = DummyConn(rows=[{"k": 1}])
    conn_empty = DummyConn(rows=[], fail_fetch=True)
    queue = [conn_ok, conn_empty, conn_ok, conn_ok, conn_ok]

    sf_mod = types.SimpleNamespace(connect=lambda **kwargs: queue.pop(0))
    monkeypatch.setitem(__import__("sys").modules, "snowflake", types.SimpleNamespace(connector=sf_mod))
    monkeypatch.setitem(__import__("sys").modules, "snowflake.connector", types.SimpleNamespace(DictCursor=object, connect=sf_mod.connect))

    client = SnowflakeClient()
    assert client.execute("SELECT 1") == [{"k": 1}]
    assert client.execute("SELECT 1") == []
    client.execute_many("INSERT INTO t VALUES (%s)", [(1,), (2,)])
    assert conn_ok.committed is True
    assert client.fetchone("SELECT 1") == {"k": 1}
    assert client.fetchall("SELECT 1") == [{"k": 1}]


def test_create_db_client_returns_sqlite_or_snowflake(monkeypatch, tmp_path):
    monkeypatch.setattr(sc, "_snowflake_configured", False)
    client = sc._create_db_client()
    assert isinstance(client, SQLiteClient)

    class DummySnowflake:
        pass

    monkeypatch.setattr(sc, "_snowflake_configured", True)
    monkeypatch.setattr(sc, "SnowflakeClient", lambda: DummySnowflake())
    client2 = sc._create_db_client()
    assert isinstance(client2, DummySnowflake)
