import uuid


AUTH = lambda token: {"Authorization": f"Bearer {token}"}


def _create_site(client, token: str) -> str:
    payload = {
        "name": "wave-build-site",
        "title": "Wave Build Site",
        "description": "Build test",
        "theme": "modern",
        "classification": "generic",
        "num_pages": 1,
    }
    res = client.post("/api/v1/websites", json=payload, headers=AUTH(token))
    assert res.status_code == 200
    return res.json()["website_id"]


def test_wave_build_website_queues_and_tracks_status(client, verified_user, monkeypatch):
    from api.routes import website_builder as wb

    def _fake_build(prompt, **kwargs):
        return {"output_dir": "output/staging/wave-build-site/legacy", "fallback": False}

    monkeypatch.setattr(wb, "build_website", _fake_build)

    wid = _create_site(client, verified_user["token"])
    payload = {
        "requirements": "Create a simple one-page business website",
        "use_web_search": False,
        "use_social_search": False,
        "build_mode": "agentic_only",
        "output_target": "legacy",
    }
    r = client.post(f"/api/v1/websites/{wid}/build", json=payload, headers=AUTH(verified_user["token"]))

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    assert body["build_mode"] == "agentic_only"
    assert body["output_target"] == "legacy"
    assert body["website_id"] == wid
    assert body.get("job_id")

    s = client.get(f"/api/v1/websites/{wid}/build-status", headers=AUTH(verified_user["token"]))
    assert s.status_code == 200
    status_body = s.json()
    assert status_body["website_id"] == wid
    assert status_body["build_status"] in {"queued", "running", "built"}


def test_wave_build_website_rejects_unknown_output_target(client, verified_user):
    wid = _create_site(client, verified_user["token"])

    r = client.post(
        f"/api/v1/websites/{wid}/build",
        json={
            "requirements": "Create a website",
            "use_web_search": False,
            "build_mode": "agentic_only",
            "output_target": "unknown-target",
        },
        headers=AUTH(verified_user["token"]),
    )

    assert r.status_code == 400
    assert "Unknown output_target" in r.json().get("detail", "")
