import pathlib


def test_plan_limit_check_uses_cache_after_first_lookup(monkeypatch):
    from api.routes import website_builder as wb

    # Isolate cache state for this test.
    wb._plan_limit_cache.clear()

    calls = {"plan": 0, "count": 0}

    def fake_fetchone(sql, params=()):
        if "SELECT plan FROM users" in sql:
            calls["plan"] += 1
            return {"plan": "free"}
        if "SELECT COUNT(*) AS cnt FROM websites" in sql:
            calls["count"] += 1
            return {"cnt": 0}
        raise AssertionError(f"Unexpected query: {sql}")

    monkeypatch.setattr(wb.db, "fetchone", fake_fetchone)

    wb._check_plan_limits("user-cache-test", needs_cart=False)
    wb._check_plan_limits("user-cache-test", needs_cart=False)

    # First call loads plan + count; second call should be served from cache.
    assert calls["plan"] == 1
    assert calls["count"] == 1


def test_dashboard_apifetch_has_abort_timeout_and_toast_message():
    js = pathlib.Path("/workspaces/agentic-s3-website-builder/frontend/dashboard.js").read_text(encoding="utf-8")

    assert "AbortController" in js
    assert "ctrl.abort()" in js
    assert "Request timed out. Please try again." in js
    assert "Network error. Please check your connection and retry." in js
