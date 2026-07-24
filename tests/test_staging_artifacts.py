"""Regression tests for folder-organized staging artifacts."""

import json
import io
import zipfile
from pathlib import Path

from agents.wb_websitebuilder import sync_legacy_entrypoint
from tools.html_generator import get_website_dir


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _insert_website(db, user_id: str, website_id: str, local_path: str):
    db.execute(
        """
        INSERT INTO websites (
            website_id, user_id, name, title, local_path, build_status, status, output_target
        ) VALUES (?, ?, ?, ?, ?, 'built', 'draft', 'legacy')
        """,
        (website_id, user_id, "Staging Test Site", "Staging Test Site", local_path),
    )


def test_get_staged_html_returns_manifest_metadata(client, verified_user, _in_memory_db, tmp_path):
    website_id = "staging-get-test"
    local_path = tmp_path / "output" / "staging" / website_id
    local_path.mkdir(parents=True)
    entry_file = local_path / "index.html"
    entry_file.write_text("<html><body><h1>Staging</h1></body></html>", encoding="utf-8")
    (local_path / "assets" / "css").mkdir(parents=True)
    (local_path / "assets" / "css" / "main.css").write_text("body{color:#111}", encoding="utf-8")
    manifest = {
        "entry_html": "index.html",
        "entry_file": str(entry_file),
        "artifact_count": 2,
        "artifacts": ["assets/css/main.css", "index.html"],
    }
    (local_path / "staging-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _insert_website(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    response = client.get(f"/api/v1/websites/{website_id}/staged-html", headers=_auth_header(verified_user["token"]))

    assert response.status_code == 200
    body = response.json()
    assert body["path"].endswith("index.html")
    assert isinstance(body.get("html_hash"), str)
    assert len(body["html_hash"]) == 64
    assert isinstance(body["staging"].get("manifest_etag"), str)
    assert len(body["staging"]["manifest_etag"]) == 64
    assert body["staging"]["entry_html"] == "index.html"
    assert body["staging"]["artifact_count"] == 2
    assert "assets/css/main.css" in body["staging"]["artifacts"]


def test_sync_legacy_entrypoint_noop_for_root_layout(tmp_path):
    site_dir = tmp_path / "output" / "staging" / "example"
    site_dir.mkdir(parents=True, exist_ok=True)
    html = (
        '<link rel="stylesheet" href="assets/css/main.css">'
        '<img src="assets/images/test.png">'
        '<script src=\'assets/js/main.js\'></script>'
    )

    sync_legacy_entrypoint(str(site_dir), html)

    assert not (tmp_path / "output" / "staging" / "example" / "index.html").exists()


def test_put_staged_html_writes_manifest_and_entry_file(client, verified_user, _in_memory_db, tmp_path):
    website_id = "staging-put-test"
    local_path = tmp_path / "output" / "staging" / website_id
    local_path.mkdir(parents=True)
    _insert_website(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    html = "<html><body><h1>Updated staging</h1></body></html>"
    response = client.put(
        f"/api/v1/websites/{website_id}/staged-html",
        headers=_auth_header(verified_user["token"]),
        json={"html": html, "entry_path": "pages/home.html"},
    )

    assert response.status_code == 200
    body = response.json()
    saved_entry = local_path / "pages" / "home.html"
    manifest_file = local_path / "staging-manifest.json"
    assert saved_entry.exists()
    assert saved_entry.read_text(encoding="utf-8") == html
    assert manifest_file.exists()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["entry_html"] == "pages/home.html"
    assert manifest["artifact_count"] >= 1
    assert isinstance(body.get("html_hash"), str)
    assert len(body["html_hash"]) == 64
    assert isinstance(body["staging"].get("manifest_etag"), str)
    assert len(body["staging"]["manifest_etag"]) == 64
    assert body["staging"]["entry_html"] == "pages/home.html"


def test_put_staged_html_rejects_stale_expected_hash(client, verified_user, _in_memory_db, tmp_path):
    website_id = "staging-put-conflict"
    local_path = tmp_path / "output" / "staging" / website_id
    local_path.mkdir(parents=True)
    (local_path / "index.html").write_text("<html><body><h1>Current</h1></body></html>", encoding="utf-8")
    _insert_website(_in_memory_db, verified_user["user_id"], website_id, str(local_path))

    response = client.put(
        f"/api/v1/websites/{website_id}/staged-html",
        headers=_auth_header(verified_user["token"]),
        json={
            "html": "<html><body><h1>New</h1></body></html>",
            "entry_path": "index.html",
            "expected_hash": "0" * 64,
        },
    )

    assert response.status_code == 409
    detail = str(response.json().get("detail") or "")
    assert "changed since last load" in detail.lower()


def test_output_static_files_are_served(client):
    repo_root = Path(__file__).resolve().parents[1]
    output_file = repo_root / "output" / "staging" / "static-regression" / "assets" / "css" / "main.css"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("body{background:#fafafa}", encoding="utf-8")
    try:
        response = client.get("/output/staging/static-regression/assets/css/main.css")
        assert response.status_code == 200
        assert "background" in response.text
    finally:
        if output_file.exists():
            output_file.unlink()


def test_output_browser_lists_folders_and_files(client, tmp_path, monkeypatch):
    import app as app_module

    output_root = tmp_path / "output"
    (output_root / "staging" / "demo-site" / "assets" / "css").mkdir(parents=True)
    (output_root / "staging" / "demo-site" / "assets" / "css" / "main.css").write_text(
        "body{color:#111}", encoding="utf-8"
    )
    (output_root / "staging" / "demo-site" / "index.html").write_text(
        "<html></html>", encoding="utf-8"
    )
    monkeypatch.setattr(app_module, "_output_dir", output_root)

    response = client.get("/output-browser?path=staging/demo-site/assets/css")

    assert response.status_code == 200
    assert "staging" in response.text
    assert "demo-site" in response.text
    assert "main.css" in response.text
    assert "Created Date" in response.text
    assert "Last Updated" in response.text
    assert "File Size" in response.text
    assert "Item Count" in response.text
    assert "Download" in response.text


def test_output_browser_sort_by_size_and_item_count(client, tmp_path, monkeypatch):
    import app as app_module

    output_root = tmp_path / "output"
    base = output_root / "staging" / "sort-site"
    (base / "dir-small").mkdir(parents=True)
    (base / "dir-large").mkdir(parents=True)
    (base / "dir-large" / "a.txt").write_text("a", encoding="utf-8")
    (base / "dir-large" / "b.txt").write_text("b", encoding="utf-8")

    (base / "small.txt").write_text("12345", encoding="utf-8")
    (base / "large.txt").write_text("x" * 100, encoding="utf-8")
    monkeypatch.setattr(app_module, "_output_dir", output_root)

    response_size = client.get("/output-browser?path=staging/sort-site&sort=size&order=desc")
    assert response_size.status_code == 200
    body_size = response_size.text
    assert body_size.find("large.txt") < body_size.find("small.txt")

    response_count = client.get("/output-browser?path=staging/sort-site&sort=count&order=desc")
    assert response_count.status_code == 200
    body_count = response_count.text
    assert body_count.find("dir-large") < body_count.find("dir-small")


def test_output_browser_download_zip_for_folder(client, tmp_path, monkeypatch):
    import app as app_module

    output_root = tmp_path / "output"
    folder = output_root / "staging" / "zip-site"
    (folder / "assets" / "css").mkdir(parents=True)
    (folder / "assets" / "css" / "main.css").write_text("body{color:#111}", encoding="utf-8")
    (folder / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(app_module, "_output_dir", output_root)

    response = client.get("/output-browser/download-zip?path=staging/zip-site")

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/zip")
    payload = io.BytesIO(response.content)
    with zipfile.ZipFile(payload, "r") as zf:
        names = set(zf.namelist())
    assert "index.html" in names
    assert "assets/css/main.css" in names


def test_get_website_dir_suffixes_duplicate_project_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    existing_dir = tmp_path / "output" / "staging" / "duplicate-site"
    existing_dir.mkdir(parents=True, exist_ok=True)
    (existing_dir / "index.html").write_text("<html></html>", encoding="utf-8")

    resolved_dir = get_website_dir("Duplicate Site", output_target="legacy")

    assert str(resolved_dir).startswith(str(tmp_path / "output" / "staging" / "duplicate-site"))
    assert resolved_dir != str(existing_dir)
    assert Path(resolved_dir).is_dir()
    assert Path(resolved_dir).name.startswith("duplicate-site_")
    assert (Path(resolved_dir) / "assets" / "css").exists()
    assert (Path(resolved_dir) / "assets" / "images").exists()
