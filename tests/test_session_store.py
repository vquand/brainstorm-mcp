from __future__ import annotations

from pathlib import Path

from server.config import Settings
from server.models import SessionResponse, StartSessionInput, UserComment, UserSelection
from server.session_store import SessionStore


def make_settings(tmp_path: Path) -> Settings:
    return Settings(repo_root=tmp_path, data_root=tmp_path / "data", port=8877)


def test_create_and_get_session(tmp_path: Path) -> None:
    store = SessionStore(make_settings(tmp_path))
    session = store.create_session(
        StartSessionInput(
            prompt="Plan the backend",
            content_type="markdown",
            options=["API first", "UI first"],
        )
    )

    loaded = store.get_session(session.session_id)

    assert loaded.session_id == session.session_id
    assert loaded.content.prompt == "Plan the backend"
    assert [item.label for item in loaded.content.options] == ["API first", "UI first"]


def test_update_response_marks_session_submitted(tmp_path: Path) -> None:
    store = SessionStore(make_settings(tmp_path))
    session = store.create_session(
        StartSessionInput(prompt="Decide a path", content_type="markdown")
    )

    updated = store.update_response(
        session.session_id,
        SessionResponse(
            selections=[UserSelection(option_id="option-1", label="API first")],
            comments=[UserComment(section_id="section-1", text="Need a stable schema")],
        ),
    )

    assert updated.status == "submitted"
    assert updated.response is not None
    assert updated.response.comments[0].text == "Need a stable schema"
