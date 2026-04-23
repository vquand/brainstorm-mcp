from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server import BrainstormService, MinimalMCPServer, ServerHandle
from server.config import Settings
from server.preferences_store import PreferencesStore


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(repo_root=tmp_path, data_root=tmp_path / "data", port=0)


def _stub_server(service: BrainstormService) -> None:
    service.ensure_server_running = lambda: ServerHandle(
        host="127.0.0.1",
        port=8765,
        thread=type("StubThread", (), {"is_alive": lambda self: True})(),
    )


def test_global_preferences_round_trip(tmp_path: Path) -> None:
    store = PreferencesStore(_make_settings(tmp_path))
    store.set_global(uiux_level="amateur", uiux_style="corporate internal tool")

    effective = store.get_effective()
    assert effective.values.uiux_level == "amateur"
    assert effective.values.uiux_style == "corporate internal tool"
    assert effective.values.questioning_style is None
    assert effective.sources.uiux_level == "global"


def test_project_overrides_global_field_by_field(tmp_path: Path) -> None:
    store = PreferencesStore(_make_settings(tmp_path))
    store.set_global(uiux_level="amateur", uiux_style="corporate")
    store.set_project("/tmp/proj-a", uiux_style="marketing landing page")

    effective = store.get_effective("/tmp/proj-a")
    assert effective.values.uiux_level == "amateur"
    assert effective.sources.uiux_level == "global"
    assert effective.values.uiux_style == "marketing landing page"
    assert effective.sources.uiux_style == "project"
    assert effective.project_key
    assert effective.project_path.endswith("/tmp/proj-a") or "/tmp/proj-a" in effective.project_path


def test_project_preferences_stored_centrally_not_in_project_dir(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    store = PreferencesStore(settings)
    project = tmp_path / "some_project"
    project.mkdir()

    store.set_project(str(project), uiux_level="expert")

    centralized_files = list(settings.project_preferences_dir.glob("*.json"))
    assert len(centralized_files) == 1
    payload = json.loads(centralized_files[0].read_text())
    assert payload["preferences"]["uiux_level"] == "expert"
    assert not list(project.glob("*"))


def test_set_partial_update_preserves_existing_fields(tmp_path: Path) -> None:
    store = PreferencesStore(_make_settings(tmp_path))
    store.set_global(uiux_level="amateur", questioning_style="collaborative_stepwise")
    store.set_global(uiux_level="expert")

    effective = store.get_effective()
    assert effective.values.uiux_level == "expert"
    assert effective.values.questioning_style == "collaborative_stepwise"


def test_service_set_requires_project_path_when_scope_project(tmp_path: Path) -> None:
    service = BrainstormService(_make_settings(tmp_path))
    with pytest.raises(ValueError):
        service.set_brainstorm_preferences(scope="project", uiux_level="amateur")


def test_service_set_rejects_unknown_scope(tmp_path: Path) -> None:
    service = BrainstormService(_make_settings(tmp_path))
    with pytest.raises(ValueError):
        service.set_brainstorm_preferences(scope="user", uiux_level="amateur")


def test_start_session_includes_effective_preferences(tmp_path: Path) -> None:
    service = BrainstormService(_make_settings(tmp_path))
    _stub_server(service)
    project = "/tmp/some-brainstorm-project"
    service.set_brainstorm_preferences(scope="global", uiux_level="amateur")
    service.set_brainstorm_preferences(
        scope="project", project_path=project, uiux_style="children"
    )

    started = service.start_brainstorm_session(
        prompt="Plan the homepage",
        content_type="markdown",
        working_dir=project,
    )

    prefs = started["preferences"]
    assert prefs["values"]["uiux_level"] == "amateur"
    assert prefs["values"]["uiux_style"] == "children"
    assert prefs["sources"]["uiux_style"] == "project"
    assert prefs["sources"]["uiux_level"] == "global"


def test_start_session_omits_preferences_when_unset(tmp_path: Path) -> None:
    service = BrainstormService(_make_settings(tmp_path))
    _stub_server(service)
    started = service.start_brainstorm_session(
        prompt="Plan",
        content_type="markdown",
    )
    prefs = started["preferences"]
    assert prefs["values"] == {
        "uiux_level": None,
        "uiux_style": None,
        "questioning_style": None,
    }
    assert prefs["sources"] == {
        "uiux_level": None,
        "uiux_style": None,
        "questioning_style": None,
    }


def test_mcp_tools_list_exposes_preferences_tools(tmp_path: Path) -> None:
    service = BrainstormService(_make_settings(tmp_path))
    _stub_server(service)
    server = MinimalMCPServer(service)

    response = server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert "set_brainstorm_preferences" in names
    assert "get_brainstorm_preferences" in names


def test_mcp_tool_call_set_and_get_preferences(tmp_path: Path) -> None:
    service = BrainstormService(_make_settings(tmp_path))
    _stub_server(service)
    server = MinimalMCPServer(service)

    set_result = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "set_brainstorm_preferences",
                "arguments": {
                    "scope": "global",
                    "uiux_level": "expert",
                    "questioning_style": "autonomous_review",
                },
            },
        }
    )
    set_structured = set_result["result"]["structuredContent"]
    assert set_structured["values"]["uiux_level"] == "expert"
    assert set_structured["values"]["questioning_style"] == "autonomous_review"

    get_result = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_brainstorm_preferences",
                "arguments": {},
            },
        }
    )
    get_structured = get_result["result"]["structuredContent"]
    assert get_structured["values"]["uiux_level"] == "expert"
