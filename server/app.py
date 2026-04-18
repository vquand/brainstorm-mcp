from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import Settings, get_settings, is_loopback_host
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
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @app.middleware("http")
    async def enforce_loopback_clients(request: Request, call_next):
        client_host = request.client.host if request.client else None
        if not client_host or not is_loopback_host(client_host):
            return JSONResponse(
                {"detail": "Brainstorm UI only accepts loopback connections"},
                status_code=403,
            )
        return await call_next(request)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(build_router(store, renderer))
    return app


app = create_app()
