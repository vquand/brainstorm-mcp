from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Optional, Union
import json
import re
import secrets
import socket
import sys
import time
import urllib.request

import uvicorn

from server.app import create_app
from server.config import Settings, get_settings
from server.models import (
    GetSessionResponseOutput,
    SessionOption,
    StartSessionInput,
    StartSessionOutput,
)
from server.session_store import SessionStore


JSONRPC_VERSION = "2.0"
DEFAULT_PROTOCOL_VERSION = "2025-03-26"


def _find_available_port(host: str, preferred_port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, preferred_port))
        except OSError:
            sock.bind((host, 0))
        return sock.getsockname()[1]


@dataclass
class ServerHandle:
    host: str
    port: int
    thread: Thread

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class BrainstormService:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.store = SessionStore(self.settings)
        self._lock = Lock()
        self._server_handle: Optional[ServerHandle] = None

    def start_brainstorm_session(
        self,
        *,
        prompt: str,
        content_type: str,
        content: Optional[str] = None,
        working_dir: Optional[str] = None,
        title: Optional[str] = None,
        options: Optional[list[Union[str, dict[str, Any]]]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        handle = self.ensure_server_running()
        parsed_options = [
            item if isinstance(item, str) else SessionOption.model_validate(item)
            for item in (options or [])
        ]
        session = self.store.create_session(
            StartSessionInput(
                prompt=prompt,
                content_type=content_type,
                content=content,
                title=title,
                working_dir=working_dir,
                options=parsed_options,
                metadata={
                    **(metadata or {}),
                    "access_token": secrets.token_urlsafe(24),
                },
            )
        )
        access_token = str(session.metadata["access_token"])
        return StartSessionOutput(
            session_id=session.session_id,
            url=f"{handle.base_url}/{session.session_id}?token={access_token}",
            port=handle.port,
            status=session.status,
        ).model_dump(mode="json")

    def get_session_response(self, session_id: str) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        payload = GetSessionResponseOutput(
            status=session.status,
            timestamp=session.response.submitted_at if session.response else None,
            response=session.response,
        )
        return payload.model_dump(mode="json")

    def list_sessions(self) -> dict[str, list[dict[str, Any]]]:
        base_url = self._server_handle.base_url if self._server_handle else None
        sessions = []
        for session in self.store.list_sessions():
            access_token = session.metadata.get("access_token")
            sessions.append(
                {
                    "session_id": session.session_id,
                    "status": session.status,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "url": (
                        f"{base_url}/{session.session_id}?token={access_token}"
                        if base_url and access_token
                        else None
                    ),
                }
            )
        return {"sessions": sessions}

    def close_session(self, session_id: str) -> dict[str, Any]:
        session = self.store.close_session(session_id)
        return {"session_id": session.session_id, "status": session.status}

    def save_plan(
        self,
        session_id: str,
        *,
        filename: Optional[str] = None,
    ) -> Path:
        session = self.store.get_session(session_id)
        safe_name = self._safe_plan_filename(filename or f"{session.session_id}.md")
        path = (self.settings.plans_dir / safe_name).resolve()
        plans_dir = self.settings.plans_dir.resolve()
        if plans_dir not in path.parents and path != plans_dir:
            raise ValueError("Refusing to write outside the plans directory")
        selections = [
            f"- {selection.label or selection.option_id}"
            for selection in (session.response.selections if session.response else [])
        ] or ["- None"]
        comments = [
            f"- [{comment.section_id or 'general'}] {comment.text}"
            for comment in (session.response.comments if session.response else [])
        ] or ["- None"]
        images = [
            f"- {image.name or image.url or 'image'} ({image.source_type})"
            for image in (session.response.images if session.response else [])
        ] or ["- None"]
        content_lines = [
            f"# {session.content.title or 'Brainstorm Session'}",
            "",
            "## Prompt",
            "",
            session.content.prompt,
            "",
            "## Content",
            "",
            "```",
            session.content.body,
            "```",
            "",
        ]
        if session.response:
            content_lines.extend(
                [
                    "## Selections",
                    "",
                    *selections,
                    "",
                    "## Comments",
                    "",
                    *comments,
                    "",
                    "## Images",
                    "",
                    *images,
                    "",
                ]
            )
        path.write_text("\n".join(content_lines), encoding="utf-8")
        return path

    def _safe_plan_filename(self, filename: str) -> str:
        name = PurePath(filename).name
        cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip("-")
        cleaned = cleaned or "plan.md"
        if not cleaned.endswith(".md"):
            cleaned = f"{cleaned}.md"
        return cleaned

    def ensure_server_running(self) -> ServerHandle:
        with self._lock:
            if self._server_handle and self._server_handle.thread.is_alive():
                if self._healthcheck(self._server_handle):
                    return self._server_handle
            port = _find_available_port(self.settings.host, self.settings.port)
            app = create_app(self.settings, store=self.store)
            config = uvicorn.Config(
                app=app,
                host=self.settings.host,
                port=port,
                log_level="warning",
            )
            server = uvicorn.Server(config)
            thread = Thread(target=server.run, daemon=True, name="brainstorm-ui-server")
            thread.start()
            handle = ServerHandle(host=self.settings.host, port=port, thread=thread)
            self._wait_for_server(handle)
            self._server_handle = handle
            return handle

    def _wait_for_server(self, handle: ServerHandle, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._healthcheck(handle):
                return
            time.sleep(0.1)
        raise RuntimeError("Timed out waiting for brainstorm UI server to start")

    def _healthcheck(self, handle: ServerHandle) -> bool:
        try:
            with urllib.request.urlopen(f"{handle.base_url}/health", timeout=0.5) as response:
                return response.status == 200
        except Exception:
            return False


class MinimalMCPServer:
    """Minimal MCP stdio server with tool support."""

    def __init__(self, service: Optional[BrainstormService] = None):
        self.service = service or BrainstormService()
        self._initialized = False

    def handle_message(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        if payload.get("jsonrpc") != JSONRPC_VERSION:
            return self._error(payload.get("id"), -32600, "Invalid JSON-RPC version")

        method = payload.get("method")
        params = payload.get("params") or {}
        request_id = payload.get("id")

        if method == "initialize":
            self._initialized = True
            protocol_version = params.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION
            return self._result(
                request_id,
                {
                    "protocolVersion": protocol_version,
                    "capabilities": {
                        "tools": {
                            "listChanged": False,
                        }
                    },
                    "serverInfo": {
                        "name": "brainstorm-mcp",
                        "version": "0.1.0",
                    },
                },
            )

        if method == "notifications/initialized":
            return None

        if method == "ping":
            return self._result(request_id, {})

        if method == "tools/list":
            return self._result(request_id, {"tools": self._tool_definitions()})

        if method == "tools/call":
            return self._handle_tool_call(request_id, params)

        if request_id is None:
            return None
        return self._error(request_id, -32601, f"Method not found: {method}")

    def handle_legacy(self, payload: dict[str, Any]) -> dict[str, Any]:
        method = payload.get("method")
        params = payload.get("params", {})
        if method == "start_brainstorm_session":
            return self.service.start_brainstorm_session(**params)
        if method == "get_session_response":
            return self.service.get_session_response(**params)
        if method == "list_sessions":
            return self.service.list_sessions()
        if method == "close_session":
            return self.service.close_session(**params)
        if method == "save_plan":
            path = self.service.save_plan(**params)
            return {"path": str(path)}
        raise ValueError(f"Unknown method: {method}")

    def _handle_tool_call(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in {tool["name"] for tool in self._tool_definitions()}:
            return self._error(request_id, -32601, f"Unknown tool: {name}")

        try:
            if name == "start_brainstorm_session":
                result = self.service.start_brainstorm_session(**arguments)
            elif name == "get_session_response":
                result = self.service.get_session_response(**arguments)
            elif name == "list_sessions":
                result = self.service.list_sessions()
            elif name == "close_session":
                result = self.service.close_session(**arguments)
            else:
                path = self.service.save_plan(**arguments)
                result = {"path": str(path)}
        except Exception as exc:
            return self._result(
                request_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )

        return self._result(
            request_id,
            {
                "content": [{"type": "text", "text": self._summarize_tool_result(name, result)}],
                "structuredContent": result,
            },
        )

    def _summarize_tool_result(self, name: str, result: dict[str, Any]) -> str:
        if name == "start_brainstorm_session":
            return (
                "Started brainstorm session "
                f"{result.get('session_id')} at {result.get('url')}."
            )
        if name == "get_session_response":
            return f"Session status: {result.get('status')}."
        if name == "list_sessions":
            return f"Found {len(result.get('sessions', []))} sessions."
        if name == "close_session":
            return f"Closed session {result.get('session_id')}."
        return f"Saved plan to {result.get('path')}."

    def _tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "start_brainstorm_session",
                "description": "Start an interactive brainstorming UI session and return the session URL.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "content_type": {
                            "type": "string",
                            "enum": ["mermaid", "html", "markdown"],
                        },
                        "content": {"type": "string"},
                        "working_dir": {"type": "string"},
                        "title": {"type": "string"},
                        "options": {
                            "type": "array",
                            "items": {
                                "anyOf": [
                                    {"type": "string"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "label": {"type": "string"},
                                            "description": {"type": "string"},
                                        },
                                        "required": ["id", "label"],
                                        "additionalProperties": False,
                                    },
                                ]
                            },
                        },
                        "metadata": {"type": "object"},
                    },
                    "required": ["prompt", "content_type"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "get_session_response",
                "description": "Get the current response and status for a brainstorm session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                    },
                    "required": ["session_id"],
                    "additionalProperties": False,
                },
                "annotations": {"readOnlyHint": True},
            },
            {
                "name": "list_sessions",
                "description": "List known brainstorming sessions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "annotations": {"readOnlyHint": True},
            },
            {
                "name": "close_session",
                "description": "Close a brainstorm session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                    },
                    "required": ["session_id"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "save_plan",
                "description": "Save a brainstorm session as a markdown plan file in the plans directory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "filename": {"type": "string"},
                    },
                    "required": ["session_id"],
                    "additionalProperties": False,
                },
            },
        ]

    def _result(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": result,
        }

    def _error(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }


def main() -> None:
    server = MinimalMCPServer()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            if isinstance(payload, list):
                responses = [
                    server.handle_message(item)
                    for item in payload
                    if isinstance(item, dict)
                ]
                response = [item for item in responses if item is not None]
                if response:
                    print(json.dumps(response), flush=True)
                continue

            if isinstance(payload, dict) and payload.get("jsonrpc") == JSONRPC_VERSION:
                response = server.handle_message(payload)
            else:
                response = {"ok": True, "result": server.handle_legacy(payload)}
        except Exception as exc:
            response = {"ok": False, "error": str(exc)}
        if response is not None:
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
