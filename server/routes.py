from __future__ import annotations

import base64
import binascii
import hmac
from pathlib import Path
from typing import Optional
import html
import mimetypes
import re
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .renderer import ContentRenderer
from .session_store import SessionNotFoundError, SessionStore
from .models import SessionResponse, SessionSummary, UserImage


def build_router(store: SessionStore, renderer: ContentRenderer) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/api/sessions")
    async def list_sessions(request: Request) -> dict[str, list[dict[str, object]]]:
        _require_admin_token(request, store)
        sessions = store.list_sessions()
        summaries = [
            SessionSummary(
                session_id=session.session_id,
                status=session.status,
                created_at=session.created_at,
                updated_at=session.updated_at,
                title=session.content.title,
            ).model_dump(mode="json")
            for session in sessions
        ]
        return {"sessions": summaries}

    @router.get("/api/sessions/{session_id}")
    async def get_session(session_id: str, request: Request) -> JSONResponse:
        session = _get_session_or_404(store, session_id)
        _require_session_token(request, session)
        return JSONResponse(session.model_dump(mode="json"), headers=_response_headers())

    @router.post("/api/sessions/{session_id}/submit")
    async def submit_session(session_id: str, request: Request) -> JSONResponse:
        session = _get_session_or_404(store, session_id)
        _require_session_token(request, session)
        payload = await request.json()
        normalized = _normalize_images(store, session_id, payload)
        response = SessionResponse.model_validate(normalized)
        session = store.update_response(session_id, response)
        return JSONResponse(
            {
                "ok": True,
                "status": session.status,
                "submitted_at": session.response.submitted_at.isoformat() if session.response else None,
            },
            headers=_response_headers(),
        )

    @router.get("/{session_id}")
    async def render_session_page(session_id: str, request: Request) -> HTMLResponse:
        session = _get_session_or_404(store, session_id)
        _require_session_token(request, session)
        rendered = renderer.render(session)
        title = rendered.title
        working_dir_name = Path(session.working_dir or "brainstorm").name
        access_token = _session_access_token(session)
        option_markup = "\n".join(
            (
                f'<button type="button" class="option-button" '
                f'data-option-id="{html.escape(option.id)}" '
                f'data-option-label="{html.escape(option.label)}">'
                f"{html.escape(option.label)}"
                "</button>"
            )
            for option in session.content.options
        ) or '<p class="muted">No predefined options for this session.</p>'
        comment_section_options = "".join(
            f'<option value="{html.escape(section_id)}">{html.escape(section_id)}</option>'
            for section_id in rendered.section_ids
        )
        page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="referrer" content="no-referrer" />
    <title>{html.escape(working_dir_name)} · {html.escape(title)}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module" src="/static/app.js"></script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({{ startOnLoad: true, securityLevel: "strict" }});
    </script>
    <link rel="stylesheet" href="/static/app.css" />
  </head>
  <body class="page-shell">
    <main class="page-grid" data-session-id="{html.escape(session.session_id)}" data-session-token="{html.escape(access_token)}">
      <section class="panel hero-panel">
        <p class="eyebrow">Brainstorm Session</p>
        <h1>{html.escape(title)}</h1>
        <p class="prompt">{html.escape(session.content.prompt)}</p>
        <dl class="session-meta">
          <div><dt>Session</dt><dd>{html.escape(session.session_id)}</dd></div>
          <div><dt>Status</dt><dd id="status-chip">{html.escape(session.status)}</dd></div>
          <div><dt>Workspace</dt><dd>{html.escape(working_dir_name)}</dd></div>
        </dl>
      </section>

      <section class="panel content-panel">
        <div class="panel-header">
          <h2>Workspace</h2>
          <p>Rendered content supports markdown, mermaid, and trusted HTML.</p>
        </div>
        <div class="rendered-content">{rendered.html}</div>
      </section>

      <section class="panel interaction-panel">
        <div class="panel-header">
          <h2>Selections</h2>
          <p>Choose one or more options, then add comments or images before submitting.</p>
        </div>
        <div id="option-list" class="option-list">{option_markup}</div>
        <div id="selected-options" class="selected-options"></div>

        <div class="field-group">
          <label for="comment-section">Comment section</label>
          <select id="comment-section">
            <option value="">General</option>
            {comment_section_options}
          </select>
        </div>
        <div class="field-group">
          <label for="comment-text">Comment</label>
          <textarea id="comment-text" rows="4" placeholder="Add implementation notes, constraints, or tradeoffs."></textarea>
          <button type="button" id="add-comment" class="secondary-button">Add Comment</button>
        </div>
        <div id="comment-list" class="stack-list"></div>

        <div class="field-group">
          <label for="image-url">Image URL</label>
          <input id="image-url" type="url" placeholder="https://example.com/reference.png" />
          <button type="button" id="add-image-url" class="secondary-button">Add URL</button>
        </div>
        <div class="field-group">
          <label for="image-file">Image File</label>
          <input id="image-file" type="file" accept="image/*" />
          <p class="muted">Files are captured client-side as base64 to avoid multipart dependencies.</p>
        </div>
        <div id="image-list" class="stack-list"></div>

        <div class="action-row">
          <button type="button" id="submit-session" class="primary-button">Submit</button>
          <p id="submit-feedback" class="muted"></p>
        </div>
      </section>
    </main>
  </body>
</html>
"""
        response = HTMLResponse(page, headers=_response_headers())
        response.set_cookie(
            key=_session_cookie_name(session.session_id),
            value=access_token,
            httponly=True,
            secure=False,
            samesite="strict",
            max_age=store.settings.session_ttl_seconds,
        )
        return response

    return router


def _get_session_or_404(store: SessionStore, session_id: str):
    try:
        return store.get_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from exc


def _response_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-src 'self'; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "form-action 'self'"
        ),
    }


def _session_cookie_name(session_id: str) -> str:
    return f"brainstorm_session_{session_id}"


def _session_access_token(session) -> str:
    token = session.metadata.get("access_token")
    if not token:
        raise HTTPException(status_code=500, detail="Session access token is missing")
    return str(token)


def _require_session_token(request: Request, session) -> None:
    expected = _session_access_token(session)
    supplied = (
        request.query_params.get("token")
        or request.headers.get("x-brainstorm-token")
        or request.cookies.get(_session_cookie_name(session.session_id))
    )
    if not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="Invalid session token")


def _require_admin_token(request: Request, store: SessionStore) -> None:
    supplied = request.headers.get("x-brainstorm-admin-token")
    expected = store.settings.http_admin_token
    if not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="Invalid admin token")


def _normalize_images(store: SessionStore, session_id: str, payload: dict) -> dict:
    normalized = dict(payload)
    images = []
    for index, item in enumerate(payload.get("images", []), start=1):
        image = UserImage.model_validate(item)
        if image.source_type == "url":
            _validate_image_url(image.url)
        if image.source_type in {"upload", "clipboard"} and image.data_base64:
            _validate_image_media_type(image.media_type)
            decoded = _decode_image_data(store, image.data_base64)
            extension = _guess_extension(image.media_type, image.name)
            filename = _safe_filename(image.name or f"upload-{index}{extension}")
            asset_path = store.persist_image_bytes(
                session_id,
                data=decoded,
                filename=filename,
            )
            image.url = str(asset_path)
            image.data_base64 = None
        images.append(image.model_dump())
    normalized["images"] = images
    return normalized


def _guess_extension(media_type: Optional[str], name: Optional[str]) -> str:
    if name and "." in name:
        return ""
    if media_type:
        guessed = mimetypes.guess_extension(media_type)
        if guessed:
            return guessed
    return ".txt"


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    return cleaned or "upload.txt"


def _validate_image_media_type(media_type: Optional[str]) -> None:
    if not media_type or not media_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")


def _decode_image_data(store: SessionStore, data_base64: str) -> bytes:
    try:
        decoded = base64.b64decode(data_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image payload") from exc
    if len(decoded) > store.settings.max_image_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds maximum allowed size")
    return decoded


def _validate_image_url(url: Optional[str]) -> None:
    if not url:
        raise HTTPException(status_code=400, detail="Image URL is required")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Only http and https image URLs are allowed")
