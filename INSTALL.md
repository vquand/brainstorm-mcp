# Installation Guide

This document explains how to install this MCP server once on a machine and reuse that same installation from multiple AI agents such as Codex, Claude Code, and other MCP-compatible clients.

## Where Data Is Stored

The repository contains the code, but runtime data is stored in the user's home directory by default:

- default data root: `~/.mcp/brainstorm-mcp`
- session JSON: `~/.mcp/brainstorm-mcp/sessions`
- uploaded image assets: `~/.mcp/brainstorm-mcp/sessions/assets`
- saved markdown plans: `~/.mcp/brainstorm-mcp/plans`

This keeps the git clone clean and lets multiple projects and agents reuse the same installation without filling the repository with local state.

If needed, override the location with:

```bash
export BRAINSTORM_DATA_DIR="/absolute/path/to/custom-brainstorm-data"
```

## Installation Model

This project is intended to be installed once per machine, not once per agent.

- Use one shared clone of the repository.
- Use one shared Python virtual environment for that clone.
- Point each MCP client to that same `python` executable and the same `mcp_server.py`.
- Do not create separate clones for Codex, Claude, Cursor, or other agents unless you specifically want isolated versions.

Because this server creates session-specific URLs and stores session data per session ID, multiple agents can use the same shared installation at the same time.

## Recommended Shared Location

Recommended standard location for a shared local install:

- macOS / Linux: `~/mcp-servers/brainstorm-mcp`
- Windows: `%USERPROFILE%\\mcp-servers\\brainstorm-mcp`

If you already cloned the repository somewhere else, you do not need to move it. Reuse that existing path.

## Prerequisites

- Python 3.9+
- A local MCP-capable client such as Codex or Claude Code
- Shell access so the client can start `python mcp_server.py`

## Scope And Visibility

This is the rule to remember:

- If you install this MCP server at the user or home level, it is available in any project for that client without extra setup.
- If you install it only at Project A level, Project B will not see it.

This project itself can stay in one shared clone on disk. The thing that changes visibility is the MCP client configuration scope, not the repo location.

### Codex Scope Behavior

Codex supports both:

- user-level config in `~/.codex/config.toml`
- project-level config in `.codex/config.toml`

So:

- put the server in `~/.codex/config.toml` and any project can use it
- put the server in `ProjectA/.codex/config.toml` and only Project A can use it

### Claude Code Scope Behavior

Claude Code supports:

- user scope in `~/.claude.json`
- project scope in `.mcp.json` at the project root
- local scope in `~/.claude.json`, but tied to the current project path

So:

- put the server in `~/.claude.json` with `--scope user` and any project can use it
- put the server in `ProjectA/.mcp.json` with `--scope project` and only Project A can use it
- local scope is also project-specific, but it is stored in `~/.claude.json` under the current project path instead of `.mcp.json`

Important:

- For Claude Code MCP, the normal shared project file is `.mcp.json`
- `.claude/settings.json` and `.claude/settings.local.json` are Claude settings files, not the primary project MCP server file

## Scope Examples

### Example 1: One Shared Install For All Projects

Shared clone on disk:

```text
~/mcp-servers/brainstorm-mcp
```

Codex user-level config in `~/.codex/config.toml`:

```toml
[mcp_servers.brainstorm]
command = "/Users/yourname/mcp-servers/brainstorm-mcp/.venv/bin/python"
args = ["/Users/yourname/mcp-servers/brainstorm-mcp/mcp_server.py"]
cwd = "/Users/yourname/mcp-servers/brainstorm-mcp"
startup_timeout_sec = 15
tool_timeout_sec = 120
```

Claude Code user-scope install:

```bash
claude mcp add --transport stdio --scope user brainstorm -- \
  /Users/yourname/mcp-servers/brainstorm-mcp/.venv/bin/python \
  /Users/yourname/mcp-servers/brainstorm-mcp/mcp_server.py
```

Result:

- Project A can use it
- Project B can use it
- you installed the repo only once

### Example 2: Only Project A Can Use It

Shared clone on disk:

```text
~/mcp-servers/brainstorm-mcp
```

Project A:

```text
~/work/project-a
```

Project B:

```text
~/work/project-b
```

Codex project-level config in `~/work/project-a/.codex/config.toml`:

```toml
[mcp_servers.brainstorm]
command = "/Users/yourname/mcp-servers/brainstorm-mcp/.venv/bin/python"
args = ["/Users/yourname/mcp-servers/brainstorm-mcp/mcp_server.py"]
cwd = "/Users/yourname/mcp-servers/brainstorm-mcp"
startup_timeout_sec = 15
tool_timeout_sec = 120
```

Claude Code project-level config in `~/work/project-a/.mcp.json`:

```json
{
  "mcpServers": {
    "brainstorm": {
      "type": "stdio",
      "command": "/Users/yourname/mcp-servers/brainstorm-mcp/.venv/bin/python",
      "args": ["/Users/yourname/mcp-servers/brainstorm-mcp/mcp_server.py"],
      "env": {}
    }
  }
}
```

Result:

- Project A can use it
- Project B will not see it
- the repo is still cloned only once

### Example 3: Claude Code Local Scope

If you run this inside Project A:

```bash
claude mcp add --transport stdio --scope local brainstorm -- \
  /Users/yourname/mcp-servers/brainstorm-mcp/.venv/bin/python \
  /Users/yourname/mcp-servers/brainstorm-mcp/mcp_server.py
```

Result:

- it is only available when working in Project A
- Claude stores that in `~/.claude.json` under Project A’s path
- Project B will not see it

## Scenario 1: The Repository Is Already Cloned

If the repository is already on the machine, the agent should reuse it instead of cloning again.

### What To Tell An Agent

For Codex:

```text
The repository is already cloned at /absolute/path/to/brainstorm-mcp.
Use that existing folder.
Create or reuse a shared Python virtual environment there, install dependencies, and register this repo as an MCP server for Codex.
Do not clone it again.
```

For Claude Code:

```text
The repository is already cloned at /absolute/path/to/brainstorm-mcp.
Use that existing folder.
Create or reuse a shared Python virtual environment there, install dependencies, and register this repo as an MCP server for Claude Code.
Do not clone it again.
```

### Manual Steps

Set the shared paths:

```bash
REPO_DIR="/absolute/path/to/brainstorm-mcp"
cd "$REPO_DIR"
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Shared executable paths:

```bash
PYTHON_BIN="$REPO_DIR/.venv/bin/python"
SERVER_SCRIPT="$REPO_DIR/mcp_server.py"
```

## Scenario 2: The Repository Is Not Cloned Yet

If the user only has the repo URL, clone it once into the shared MCP server location and then configure clients to use that single clone.

### What To Tell An Agent

For Codex:

```text
Clone <REPO_URL> into ~/mcp-servers/brainstorm-mcp, create a shared Python virtual environment there, install dependencies, and register it as an MCP server for Codex.
Use that shared installation so other agents can reuse it later.
```

For Claude Code:

```text
Clone <REPO_URL> into ~/mcp-servers/brainstorm-mcp, create a shared Python virtual environment there, install dependencies, and register it as an MCP server for Claude Code.
Use that shared installation so other agents can reuse it later.
```

### Manual Steps

macOS / Linux:

```bash
mkdir -p ~/mcp-servers
git clone <REPO_URL> ~/mcp-servers/brainstorm-mcp
cd ~/mcp-servers/brainstorm-mcp
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\mcp-servers" | Out-Null
git clone <REPO_URL> "$HOME\mcp-servers\brainstorm-mcp"
cd "$HOME\mcp-servers\brainstorm-mcp"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Codex Setup

OpenAI documents that Codex supports MCP servers in both the CLI and IDE extension, and that both share the same MCP configuration in `~/.codex/config.toml` by default.

### Install With The Codex CLI

After the shared install is ready:

```bash
REPO_DIR="/absolute/path/to/brainstorm-mcp"
PYTHON_BIN="$REPO_DIR/.venv/bin/python"
codex mcp add brainstorm -- "$PYTHON_BIN" "$REPO_DIR/mcp_server.py"
codex mcp list
```

### Configure Codex Manually

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.brainstorm]
command = "/absolute/path/to/brainstorm-mcp/.venv/bin/python"
args = ["/absolute/path/to/brainstorm-mcp/mcp_server.py"]
cwd = "/absolute/path/to/brainstorm-mcp"
startup_timeout_sec = 15
tool_timeout_sec = 120
```

### Agent Prompt For Codex

```text
Install the MCP server from /absolute/path/to/brainstorm-mcp into Codex.
Reuse the existing clone and shared virtualenv.
Register it as a stdio MCP server that runs /absolute/path/to/brainstorm-mcp/mcp_server.py with the Python executable from that repo's .venv.
```

## Claude Code Setup

Anthropic documents that Claude Code supports local stdio MCP servers and that user-scope configuration lives in `~/.claude.json`. Claude Code also supports project-scoped setup in `.mcp.json`.

### Install With The Claude CLI

User-scope install, shared across all your projects:

```bash
REPO_DIR="/absolute/path/to/brainstorm-mcp"
PYTHON_BIN="$REPO_DIR/.venv/bin/python"
claude mcp add --transport stdio --scope user brainstorm -- "$PYTHON_BIN" "$REPO_DIR/mcp_server.py"
claude mcp list
```

Project-scope install, only for the current project:

```bash
REPO_DIR="/absolute/path/to/brainstorm-mcp"
PYTHON_BIN="$REPO_DIR/.venv/bin/python"
claude mcp add --transport stdio --scope project brainstorm -- "$PYTHON_BIN" "$REPO_DIR/mcp_server.py"
claude mcp list
```

### Configure Claude Code Manually

Example JSON configuration for `claude mcp add-json`:

```json
{
  "type": "stdio",
  "command": "/absolute/path/to/brainstorm-mcp/.venv/bin/python",
  "args": ["/absolute/path/to/brainstorm-mcp/mcp_server.py"],
  "env": {}
}
```

Example command:

```bash
claude mcp add-json brainstorm '{"type":"stdio","command":"/absolute/path/to/brainstorm-mcp/.venv/bin/python","args":["/absolute/path/to/brainstorm-mcp/mcp_server.py"],"env":{}}' --scope user
```

### Claude Code Desktop

Claude’s documentation says Claude Code desktop and Claude Code CLI share MCP server configuration from `~/.claude.json` and `.mcp.json`. In practice, if you add the server with `claude mcp add ...`, it is available in both Claude Code CLI and the Claude Code desktop app.

### Agent Prompt For Claude Code

```text
Install the MCP server from /absolute/path/to/brainstorm-mcp into Claude Code with user scope.
Reuse the existing clone and shared virtualenv.
Register it as a stdio MCP server that runs /absolute/path/to/brainstorm-mcp/mcp_server.py with the Python executable from that repo's .venv.
```

## Claude Desktop Chat App

This is separate from Claude Code. Anthropic’s current docs distinguish the Claude Desktop chat app configuration from Claude Code MCP configuration.

If you need the Claude Desktop chat app specifically, the MCP server entry should follow the standard local stdio shape:

```json
{
  "mcpServers": {
    "brainstorm": {
      "type": "stdio",
      "command": "/absolute/path/to/brainstorm-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/brainstorm-mcp/mcp_server.py"],
      "env": {}
    }
  }
}
```

Use the Claude Desktop MCP configuration file or import into Claude Code from Claude Desktop if that fits your workflow.

## Other MCP-Compatible Clients

Any MCP client that supports local stdio servers can point to this server with the same shared install:

```json
{
  "mcpServers": {
    "brainstorm": {
      "type": "stdio",
      "command": "/absolute/path/to/brainstorm-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/brainstorm-mcp/mcp_server.py"],
      "env": {}
    }
  }
}
```

The important part is that every client should reuse the same repository path and the same Python environment.

## Multi-Agent Reuse

To make this installation reusable across multiple agents:

1. Keep one shared clone on disk.
2. Keep one shared virtualenv inside that clone.
3. Configure each client separately, but point all of them to the same `python` path and same `mcp_server.py`.
4. Do not duplicate the repo per agent.

Example shared layout:

```text
~/mcp-servers/brainstorm-mcp/
├── .venv/
├── mcp_server.py
└── server/

~/.mcp/brainstorm-mcp/
├── sessions/
│   └── assets/
└── plans/
```

This gives you:

- one installation to maintain
- one place to update
- no wasted duplicate clones
- simultaneous usage by multiple agents through independent MCP client processes

## Verify The Install

After registration, verify from the client:

- Codex: `codex mcp list`
- Claude Code: `claude mcp list`

You can also test the server process directly:

```bash
cd /absolute/path/to/brainstorm-mcp
. .venv/bin/activate
python mcp_server.py
```

Then send MCP JSON-RPC lines such as:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"manual-test","version":"1.0"}}}
```

Then:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

## Updating Later

To update the shared install:

```bash
cd /absolute/path/to/brainstorm-mcp
git pull
. .venv/bin/activate
pip install -r requirements.txt
```

Because clients point to the shared clone, they all pick up the updated version automatically.

## Notes

- Prefer absolute paths in MCP configuration.
- Reusing one shared clone is the recommended setup for this project.
- If an agent is installing this for you, tell it explicitly not to clone the repo a second time if the repo already exists locally.
- If you want this server available only inside one repository, use Claude Code project scope or Codex project config instead of user scope.
