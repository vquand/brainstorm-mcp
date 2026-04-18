from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Settings
from server.models import StartSessionInput
from server.session_store import SessionStore


def make_app(tmp_path: Path):
    settings = Settings(repo_root=tmp_path, data_root=tmp_path / "data", port=8877)
    store = SessionStore(settings)
    app = create_app(settings, store=store)
    return app, store


def test_session_page_and_submit_flow(tmp_path: Path) -> None:
    app, store = make_app(tmp_path)
    session = store.create_session(
        StartSessionInput(
            prompt="Plan it",
            content_type="markdown",
            content="# Section\n\nSome notes",
            options=["One", "Two"],
        )
    )
    client = TestClient(app)
    token = session.metadata["access_token"]

    unauthorized_client = TestClient(app)
    unauthorized_submit = unauthorized_client.post(
        f"/api/sessions/{session.session_id}/submit",
        json={"selections": [], "comments": [], "images": []},
    )
    assert unauthorized_submit.status_code == 403

    page = client.get(f"/{session.session_id}?token={token}")
    assert page.status_code == 200
    assert "Plan it" in page.text

    submit = client.post(
        f"/api/sessions/{session.session_id}/submit",
        json={
            "selections": [{"option_id": "option-1", "label": "One"}],
            "comments": [{"section_id": "section", "text": "Keep it simple"}],
            "images": [{"source_type": "url", "url": "https://example.com/a.png"}],
        },
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "submitted"

    session_payload = client.get(f"/api/sessions/{session.session_id}")
    assert session_payload.status_code == 200
    assert session_payload.json()["response"]["comments"][0]["text"] == "Keep it simple"


def test_list_sessions_requires_admin_token(tmp_path: Path) -> None:
    app, store = make_app(tmp_path)
    store.create_session(StartSessionInput(prompt="Plan it", content_type="markdown"))
    client = TestClient(app)

    denied = client.get("/api/sessions")
    assert denied.status_code == 403

    allowed = client.get(
        "/api/sessions",
        headers={"x-brainstorm-admin-token": store.settings.http_admin_token},
    )
    assert allowed.status_code == 200


def test_submit_rejects_non_image_upload(tmp_path: Path) -> None:
    app, store = make_app(tmp_path)
    session = store.create_session(
        StartSessionInput(prompt="Plan it", content_type="markdown")
    )
    token = session.metadata["access_token"]
    client = TestClient(app)
    client.cookies.set(f"brainstorm_session_{session.session_id}", token)

    response = client.post(
        f"/api/sessions/{session.session_id}/submit",
        json={
            "selections": [],
            "comments": [],
            "images": [
                {
                    "source_type": "upload",
                    "name": "bad.txt",
                    "media_type": "text/plain",
                    "data_base64": "Zm9v",
                }
            ],
        },
    )
    assert response.status_code == 400
