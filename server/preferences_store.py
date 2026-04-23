from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Optional
import json
import os

from .config import Settings
from .models import (
    BrainstormPreferences,
    EffectivePreferences,
    PreferenceScope,
    PreferenceSources,
)


class PreferencesStore:
    """JSON-backed store for global and per-project brainstorm preferences."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = RLock()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.settings.preferences_dir.mkdir(parents=True, exist_ok=True)
        self.settings.project_preferences_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def project_key(project_path: str) -> str:
        normalized = os.path.abspath(os.path.expanduser(project_path))
        return sha256(normalized.encode("utf-8")).hexdigest()[:32]

    def _project_path(self, project_path: str) -> Path:
        return self.settings.project_preferences_dir / f"{self.project_key(project_path)}.json"

    def _read(self, path: Path) -> BrainstormPreferences:
        if not path.exists():
            return BrainstormPreferences()
        with self._lock:
            data = json.loads(path.read_text(encoding="utf-8"))
        prefs_payload = data.get("preferences", data)
        return BrainstormPreferences.model_validate(prefs_payload)

    def _write(self, path: Path, prefs: BrainstormPreferences, *, project_path: Optional[str] = None) -> None:
        payload = {"preferences": prefs.model_dump(exclude_none=True)}
        if project_path is not None:
            payload["project_path"] = os.path.abspath(os.path.expanduser(project_path))
        with self._lock:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_global(self) -> BrainstormPreferences:
        return self._read(self.settings.global_preferences_path)

    def get_project(self, project_path: str) -> BrainstormPreferences:
        return self._read(self._project_path(project_path))

    def set_global(
        self,
        *,
        uiux_level: Optional[str] = None,
        uiux_style: Optional[str] = None,
        questioning_style: Optional[str] = None,
    ) -> BrainstormPreferences:
        existing = self.get_global()
        merged = self._merge(existing, uiux_level, uiux_style, questioning_style)
        self._write(self.settings.global_preferences_path, merged)
        return merged

    def set_project(
        self,
        project_path: str,
        *,
        uiux_level: Optional[str] = None,
        uiux_style: Optional[str] = None,
        questioning_style: Optional[str] = None,
    ) -> BrainstormPreferences:
        existing = self.get_project(project_path)
        merged = self._merge(existing, uiux_level, uiux_style, questioning_style)
        self._write(self._project_path(project_path), merged, project_path=project_path)
        return merged

    def get_effective(self, project_path: Optional[str] = None) -> EffectivePreferences:
        global_prefs = self.get_global()
        project_prefs = self.get_project(project_path) if project_path else BrainstormPreferences()

        values = BrainstormPreferences()
        sources = PreferenceSources()
        for field in ("uiux_level", "uiux_style", "questioning_style"):
            project_value = getattr(project_prefs, field)
            if project_value is not None:
                setattr(values, field, project_value)
                setattr(sources, field, PreferenceScope.project)
                continue
            global_value = getattr(global_prefs, field)
            if global_value is not None:
                setattr(values, field, global_value)
                setattr(sources, field, PreferenceScope.global_)

        return EffectivePreferences(
            values=values,
            sources=sources,
            project_key=self.project_key(project_path) if project_path else None,
            project_path=os.path.abspath(os.path.expanduser(project_path)) if project_path else None,
        )

    @staticmethod
    def _merge(
        existing: BrainstormPreferences,
        uiux_level: Optional[str],
        uiux_style: Optional[str],
        questioning_style: Optional[str],
    ) -> BrainstormPreferences:
        return BrainstormPreferences(
            uiux_level=uiux_level if uiux_level is not None else existing.uiux_level,
            uiux_style=uiux_style if uiux_style is not None else existing.uiux_style,
            questioning_style=(
                questioning_style if questioning_style is not None else existing.questioning_style
            ),
        )
