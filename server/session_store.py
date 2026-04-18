from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from threading import RLock
from typing import Iterable, Union
import json
import os
import secrets
import tempfile

from .config import Settings
from .models import (
    BrainstormSession,
    SessionContent,
    SessionOption,
    SessionResponse,
    SessionStatus,
    StartSessionInput,
    utc_now,
)


class SessionNotFoundError(FileNotFoundError):
    pass


class SessionStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = RLock()
        self._ensure_storage_roots()

    def _ensure_storage_roots(self) -> None:
        try:
            self.settings.sessions_dir.mkdir(parents=True, exist_ok=True)
            self.settings.assets_dir.mkdir(parents=True, exist_ok=True)
            self.settings.plans_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            fallback_root = Path(tempfile.gettempdir()) / "brainstorm-mcp" / os.getenv("USER", "user")
            self.settings.data_root = fallback_root
            self.settings.sessions_dir.mkdir(parents=True, exist_ok=True)
            self.settings.assets_dir.mkdir(parents=True, exist_ok=True)
            self.settings.plans_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, session_id: str) -> Path:
        return self.settings.sessions_dir / f"{session_id}.json"

    def create_session(self, payload: StartSessionInput) -> BrainstormSession:
        content_body = payload.content or payload.prompt
        options = self._normalize_options(payload.options)
        session = BrainstormSession(
            working_dir=payload.working_dir,
            expires_at=utc_now() + timedelta(seconds=self.settings.session_ttl_seconds),
            content=SessionContent(
                prompt=payload.prompt,
                body=content_body,
                content_type=payload.content_type,
                title=payload.title,
                options=options,
            ),
            metadata={
                **payload.metadata,
                "access_token": payload.metadata.get("access_token") or secrets.token_urlsafe(24),
            },
        )
        self.save(session)
        return session

    def save(self, session: BrainstormSession) -> BrainstormSession:
        session.updated_at = utc_now()
        path = self._path_for(session.session_id)
        with self._lock:
            path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
        return session

    def get_session(self, session_id: str) -> BrainstormSession:
        path = self._path_for(session_id)
        if not path.exists():
            raise SessionNotFoundError(session_id)
        with self._lock:
            data = json.loads(path.read_text(encoding="utf-8"))
        session = BrainstormSession.model_validate(data)
        return self._expire_if_needed(session)

    def list_sessions(self) -> list[BrainstormSession]:
        sessions: list[BrainstormSession] = []
        for path in sorted(self.settings.sessions_dir.glob("*.json")):
            try:
                session = BrainstormSession.model_validate_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            sessions.append(self._expire_if_needed(session))
        return sorted(sessions, key=lambda item: item.created_at, reverse=True)

    def update_response(self, session_id: str, response: SessionResponse) -> BrainstormSession:
        session = self.get_session(session_id)
        if session.status in {SessionStatus.closed, SessionStatus.expired}:
            raise ValueError(f"Session {session_id} is {session.status}")
        session.response = response
        session.status = SessionStatus.submitted
        return self.save(session)

    def close_session(self, session_id: str) -> BrainstormSession:
        session = self.get_session(session_id)
        session.status = SessionStatus.closed
        return self.save(session)

    def expire_sessions(self) -> int:
        expired = 0
        for session in self.list_sessions():
            if session.status == SessionStatus.expired:
                expired += 1
        return expired

    def session_asset_dir(self, session_id: str) -> Path:
        asset_dir = self.settings.assets_dir / session_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        return asset_dir

    def persist_image_bytes(
        self,
        session_id: str,
        *,
        data: bytes,
        filename: str,
    ) -> Path:
        asset_dir = self.session_asset_dir(session_id)
        path = asset_dir / filename
        path.write_bytes(data)
        return path

    def _normalize_options(self, options: Iterable[Union[str, SessionOption]]) -> list[SessionOption]:
        normalized: list[SessionOption] = []
        for index, option in enumerate(options, start=1):
            if isinstance(option, SessionOption):
                normalized.append(option)
                continue
            normalized.append(SessionOption(id=f"option-{index}", label=str(option)))
        return normalized

    def _expire_if_needed(self, session: BrainstormSession) -> BrainstormSession:
        if session.expires_at and utc_now() >= session.expires_at and session.status == SessionStatus.pending:
            session.status = SessionStatus.expired
            self.save(session)
        return session
