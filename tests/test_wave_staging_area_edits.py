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


def test_wave_staging_page_templates_lists_blank_and_recommended(client, verified_user, _in_memory_db, tmp_path):
    website_id = "wave-page-templates"
    local_path = tmp_path / "output" / "staging" / website_id
    local_path.mkdir(parents=True, exist_ok=True)
    _insert_site(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    r = client.get(f"/api/v1/websites/{website_id}/page-templates", headers=AUTH(verified_user["token"]))

    assert r.status_code == 200
    body = r.json()
    assert body["classification"] == "generic"
    assert isinstance(body.get("recommended"), list)
    assert len(body["recommended"]) >= 1
    assert isinstance(body.get("all_templates"), list)
    assert len(body["all_templates"]) >= len(body["recommended"])
    assert body["blank_template"]["template_key"] == "blank"


def test_wave_staging_create_page_from_blank_template(client, verified_user, _in_memory_db, tmp_path):
    website_id = "wave-create-page"
    local_path = tmp_path / "output" / "staging" / website_id
    local_path.mkdir(parents=True, exist_ok=True)
    (local_path / "index.html").write_text("<html><head><title>Wave</title></head><body><h1>Home</h1></body></html>", encoding="utf-8")
    _insert_site(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    r = client.post(
        f"/api/v1/websites/{website_id}/pages/create",
        json={
            "entry_path": "pages/about",
            "template_key": "blank",
            "conflict_mode": "overwrite",
            "retain_header": False,
            "retain_menu": False,
            "retain_footer": False,
        },
        headers=AUTH(verified_user["token"]),
    )

    assert r.status_code == 200
    body = r.json()
    assert body["saved"] is True
    assert body["entry_path"] == "pages/about.html"
    created = local_path / "pages" / "about.html"
    assert created.exists()
    html = created.read_text(encoding="utf-8")
    assert "New Page" in html
    assert "<main" in html


def test_wave_staging_create_page_with_retained_shell_uses_relative_partial_paths(client, verified_user, _in_memory_db, tmp_path):
    website_id = "wave-create-page-retain-shell"
    local_path = tmp_path / "output" / "staging" / website_id
    local_path.mkdir(parents=True, exist_ok=True)
    (local_path / "index.html").write_text(
        "<html><head><title>Wave</title></head><body><header><h1>Home</h1></header><nav><a href='index.html'>Home</a></nav><main></main><footer>F</footer></body></html>",
        encoding="utf-8",
    )
    _insert_site(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    r = client.post(
        f"/api/v1/websites/{website_id}/pages/create",
        json={
            "entry_path": "pages/clinical",
            "template_key": "blank",
            "conflict_mode": "overwrite",
            "retain_header": True,
            "retain_menu": True,
            "retain_footer": True,
        },
        headers=AUTH(verified_user["token"]),
    )

    assert r.status_code == 200
    created = local_path / "pages" / "clinical.html"
    assert created.exists()
    html = created.read_text(encoding="utf-8")
    assert 'data-wb-include="../partials/header.html"' in html
    assert 'data-wb-include="../partials/menu.html"' in html
    assert 'data-wb-include="../partials/footer.html"' in html
    assert '<script src="../partials/include-partials.js"></script>' in html


def test_wave_staging_set_home_updates_manifest_entry(client, verified_user, _in_memory_db, tmp_path):
    website_id = "wave-set-home"
    local_path = tmp_path / "output" / "staging" / website_id
    target_entry = local_path / "pages" / "landing.html"
    target_entry.parent.mkdir(parents=True, exist_ok=True)
    target_entry.write_text("<html><body><h1>Landing</h1></body></html>", encoding="utf-8")
    (local_path / "index.html").write_text("<html><body><h1>Home</h1></body></html>", encoding="utf-8")
    _insert_site(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    r = client.post(
        f"/api/v1/websites/{website_id}/staged-home",
        json={"entry_path": "pages/landing.html"},
        headers=AUTH(verified_user["token"]),
    )

    assert r.status_code == 200
    body = r.json()
    assert body["saved"] is True
    assert body["staging"]["entry_html"] == "pages/landing.html"

    manifest = json.loads((local_path / "staging-manifest.json").read_text(encoding="utf-8"))
    assert manifest["entry_html"] == "pages/landing.html"


def test_wave_staging_set_home_rejects_stale_manifest_etag(client, verified_user, _in_memory_db, tmp_path):
    website_id = "wave-set-home-conflict"
    local_path = tmp_path / "output" / "staging" / website_id
    target_entry = local_path / "pages" / "landing.html"
    target_entry.parent.mkdir(parents=True, exist_ok=True)
    target_entry.write_text("<html><body><h1>Landing</h1></body></html>", encoding="utf-8")
    (local_path / "index.html").write_text("<html><body><h1>Home</h1></body></html>", encoding="utf-8")
    _insert_site(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    # Initialize manifest state.
    seed = client.put(
        f"/api/v1/websites/{website_id}/staged-html",
        json={"html": "<html><body><h1>Seed</h1></body></html>", "entry_path": "index.html"},
        headers=AUTH(verified_user["token"]),
    )
    assert seed.status_code == 200

    r = client.post(
        f"/api/v1/websites/{website_id}/staged-home",
        json={"entry_path": "pages/landing.html", "expected_manifest_etag": "0" * 64},
        headers=AUTH(verified_user["token"]),
    )

    assert r.status_code == 409
    detail = str(r.json().get("detail") or "")
    assert "manifest changed since last load" in detail.lower()


def test_wave_staging_create_page_rejects_stale_manifest_etag(client, verified_user, _in_memory_db, tmp_path):
    website_id = "wave-create-page-conflict"
    local_path = tmp_path / "output" / "staging" / website_id
    local_path.mkdir(parents=True, exist_ok=True)
    (local_path / "index.html").write_text("<html><head><title>Wave</title></head><body><h1>Home</h1></body></html>", encoding="utf-8")
    _insert_site(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    # Initialize manifest state.
    seed = client.put(
        f"/api/v1/websites/{website_id}/staged-html",
        json={"html": "<html><body><h1>Seed</h1></body></html>", "entry_path": "index.html"},
        headers=AUTH(verified_user["token"]),
    )
    assert seed.status_code == 200

    r = client.post(
        f"/api/v1/websites/{website_id}/pages/create",
        json={
            "entry_path": "pages/about",
            "template_key": "blank",
            "conflict_mode": "overwrite",
            "retain_header": False,
            "retain_menu": False,
            "retain_footer": False,
            "expected_manifest_etag": "f" * 64,
        },
        headers=AUTH(verified_user["token"]),
    )

    assert r.status_code == 409
    detail = str(r.json().get("detail") or "")
    assert "manifest changed since last load" in detail.lower()
