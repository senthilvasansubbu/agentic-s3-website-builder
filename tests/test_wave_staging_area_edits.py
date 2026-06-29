import json


AUTH = lambda token: {"Authorization": f"Bearer {token}"}


def _insert_site(db, user_id: str, website_id: str, local_path: str):
    db.execute(
        """
        INSERT INTO websites (
            website_id, user_id, name, title, local_path, build_status, status, output_target
        ) VALUES (?, ?, ?, ?, ?, 'built', 'draft', 'legacy')
        """,
        (website_id, user_id, "Wave Staging", "Wave Staging", local_path),
    )


def test_wave_staging_area_get_uses_manifest_entry(client, verified_user, _in_memory_db, tmp_path):
    website_id = "wave-staging-get"
    local_path = tmp_path / "output" / "staging" / website_id
    target_entry = local_path / "pages" / "landing.html"
    target_entry.parent.mkdir(parents=True, exist_ok=True)
    target_entry.write_text("<html><body><h1>Landing</h1></body></html>", encoding="utf-8")
    (local_path / "staging-manifest.json").write_text(
        json.dumps({"entry_html": "pages/landing.html"}),
        encoding="utf-8",
    )
    _insert_site(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    r = client.get(f"/api/v1/websites/{website_id}/staged-html", headers=AUTH(verified_user["token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["path"].endswith("pages/landing.html")
    assert body["staging"]["entry_html"] == "pages/landing.html"


def test_wave_staging_area_put_updates_entry_and_manifest(client, verified_user, _in_memory_db, tmp_path):
    website_id = "wave-staging-put"
    local_path = tmp_path / "output" / "staging" / website_id
    local_path.mkdir(parents=True, exist_ok=True)
    _insert_site(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    html = "<html><body><p>Wave staging update</p></body></html>"
    r = client.put(
        f"/api/v1/websites/{website_id}/staged-html",
        json={"html": html, "entry_path": "pages/home.html"},
        headers=AUTH(verified_user["token"]),
    )

    assert r.status_code == 200
    body = r.json()
    assert body["saved"] is True
    assert body["staging"]["entry_html"] == "pages/home.html"

    entry_file = local_path / "pages" / "home.html"
    assert entry_file.exists()
    assert entry_file.read_text(encoding="utf-8") == html

    manifest = json.loads((local_path / "staging-manifest.json").read_text(encoding="utf-8"))
    assert manifest["entry_html"] == "pages/home.html"
    assert "pages/home.html" in manifest["artifacts"]
