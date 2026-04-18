from __future__ import annotations

from pathlib import Path

from mcp_server import BrainstormService, MinimalMCPServer, ServerHandle
from server.config import Settings


def test_service_start_and_retrieve_session(tmp_path: Path) -> None:
    service = BrainstormService(Settings(repo_root=tmp_path, data_root=tmp_path / "data", port=0))
    service.ensure_server_running = lambda: ServerHandle(
        host="127.0.0.1",
        port=8765,
        thread=type("StubThread", (), {"is_alive": lambda self: True})(),
    )

    started = service.start_brainstorm_session(
        prompt="Plan the project",
        content_type="markdown",
        content="# Overview\n\nInitial content",
        options=["Alpha", "Beta"],
    )
    assert started["session_id"]
    assert started["url"].startswith("http://")

    listed = service.list_sessions()
    assert listed["sessions"]

    response = service.get_session_response(started["session_id"])
    assert response["status"] == "pending"


def test_minimal_mcp_server_initialize_list_and_call(tmp_path: Path) -> None:
    service = BrainstormService(Settings(repo_root=tmp_path, data_root=tmp_path / "data", port=0))
    service.ensure_server_running = lambda: ServerHandle(
        host="127.0.0.1",
        port=8765,
        thread=type("StubThread", (), {"is_alive": lambda self: True})(),
    )
    server = MinimalMCPServer(service)

    initialize = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
        }
    )
    assert initialize["result"]["capabilities"]["tools"]["listChanged"] is False

    tools = server.handle_message(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    tool_names = [tool["name"] for tool in tools["result"]["tools"]]
    assert "start_brainstorm_session" in tool_names

    started = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "start_brainstorm_session",
                "arguments": {
                    "prompt": "Plan the project",
                    "content_type": "markdown",
                    "content": "# Overview",
                },
            },
        }
    )
    structured = started["result"]["structuredContent"]
    assert structured["session_id"]
    assert structured["url"].startswith("http://")
    assert "token=" in structured["url"]


def test_save_plan_sanitizes_filename(tmp_path: Path) -> None:
    service = BrainstormService(Settings(repo_root=tmp_path, data_root=tmp_path / "data", port=0))
    service.ensure_server_running = lambda: ServerHandle(
        host="127.0.0.1",
        port=8765,
        thread=type("StubThread", (), {"is_alive": lambda self: True})(),
    )
    started = service.start_brainstorm_session(
        prompt="Plan the project",
        content_type="markdown",
    )

    path = service.save_plan(started["session_id"], filename="../../../escape.md")

    assert path.parent == service.settings.plans_dir.resolve()
    assert path.name == "escape.md"
