from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import secrets


def _default_data_root() -> Path:
    return Path.home() / ".mcp" / "brainstorm-mcp"


@dataclass
class Settings:
    host: str = os.getenv("BRAINSTORM_HOST", "127.0.0.1")
    port: int = int(os.getenv("BRAINSTORM_PORT", "8765"))
    session_ttl_seconds: int = int(os.getenv("BRAINSTORM_SESSION_TTL_SECONDS", "86400"))
    max_image_bytes: int = int(os.getenv("BRAINSTORM_MAX_IMAGE_BYTES", str(2 * 1024 * 1024)))
    http_admin_token: str = os.getenv("BRAINSTORM_HTTP_ADMIN_TOKEN", secrets.token_urlsafe(24))
    repo_root: Path = Path(__file__).resolve().parent.parent
    data_root: Path = Path(os.getenv("BRAINSTORM_DATA_DIR", str(_default_data_root())))

    @property
    def sessions_dir(self) -> Path:
        return self.data_root / "sessions"

    @property
    def assets_dir(self) -> Path:
        return self.sessions_dir / "assets"

    @property
    def plans_dir(self) -> Path:
        return self.data_root / "plans"


def get_settings() -> Settings:
    return Settings()
