"""Regression tests for folder-organized staging artifacts."""

import json
from pathlib import Path


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
    local_path = tmp_path / "output" / "staging" / website_id / "legacy"
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
    assert body["staging"]["entry_html"] == "index.html"
    assert body["staging"]["artifact_count"] == 2
    assert "assets/css/main.css" in body["staging"]["artifacts"]


def test_put_staged_html_writes_manifest_and_entry_file(client, verified_user, _in_memory_db, tmp_path):
    website_id = "staging-put-test"
    local_path = tmp_path / "output" / "staging" / website_id / "legacy"
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
    assert body["staging"]["entry_html"] == "pages/home.html"


def test_output_static_files_are_served(client):
    repo_root = Path(__file__).resolve().parents[1]
    output_file = repo_root / "output" / "staging" / "static-regression" / "legacy" / "assets" / "css" / "main.css"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("body{background:#fafafa}", encoding="utf-8")
    try:
        response = client.get("/output/staging/static-regression/legacy/assets/css/main.css")
        assert response.status_code == 200
        assert "background" in response.text
    finally:
        if output_file.exists():
            output_file.unlink()
