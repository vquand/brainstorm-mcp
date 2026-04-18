from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .renderer import ContentRenderer
from .routes import build_router
from .session_store import SessionStore


def create_app(
    settings: Optional[Settings] = None,
    *,
    store: Optional[SessionStore] = None,
    renderer: Optional[ContentRenderer] = None,
) -> FastAPI:
    settings = settings or get_settings()
    store = store or SessionStore(settings)
    renderer = renderer or ContentRenderer()
    static_dir = Path(__file__).resolve().parent / "static"

    app = FastAPI(title="MCP Brainstorm Server")
    app.state.settings = settings
    app.state.store = store
    app.state.renderer = renderer
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(build_router(store, renderer))
    return app


app = create_app()
