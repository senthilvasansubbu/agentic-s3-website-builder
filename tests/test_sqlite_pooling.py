import threading

from database.snowflake_client import SQLiteClient


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
