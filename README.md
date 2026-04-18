# MCP Brainstorm Server

An MCP (Model Context Protocol) server that spawns a lightweight, resource-efficient localhost UI for interactive AI-assisted brainstorming, planning, and visualization. Designed to work seamlessly with Claude and other AI agents for collaborative ideation workflows.

## What It Does

### Core Workflow
1. **Detection**: When you mention brainstorming keywords (brainstorm, plan, think, how do...), the AI agent asks if you want to use the interactive UI
2. **Launch**: Server starts on localhost with a session-specific URL
3. **Interaction**: Render brainstorming materials using mermaid diagrams or Tailwind-styled HTML UI
4. **Submission**: Users interact with clickable buttons, input comments, and optionally upload/paste images
5. **Retrieval**: AI agent reads submitted responses to continue work
6. **Documentation**: Optional saving to `plans/*.md` for future reference

### Features

- **Multi-Session Support**: Each AI agent session gets its own URL (`localhost:{port}/{sessionid}`) with tab names reflecting working directory for easy distinction
- **Rich Content Rendering**:
  - Mermaid diagrams for graphs, flowcharts, and visualizations
  - Tailwind CSS-styled UI for brainstorming options and interfaces
  - Markdown-compatible format renderer with embedded diagrams and tables
  
- **Interactive Elements**:
  - Auto-generated IDs for sections and options (for easy reference)
  - Clickable buttons for user choices
  - Inline comment input fields
  - Submit/Done workflow
  
- **Image Support**: 
  - Local file upload via file picker
  - Internet-accessible URLs
  - Clipboard paste-in capability
  
- **Resource Efficient**: Lightweight Python server designed for single-user operation

## Architecture

### Components

```
├── mcp_server.py          # MCP server implementation (Python)
├── server/                # localhost UI server
│   ├── app.py            # Flask/FastAPI server
│   ├── templates/        # HTML templates
│   └── static/           # CSS, JS, assets
├── sessions/             # Session state storage
├── plans/                # User-saved markdown plans (optional)
└── requirements.txt      # Dependencies
```

### Session Management

- Each session gets a unique `sessionid` (UUID or similar)
- Session state stored in memory or lightweight persistent storage
- URLs: `localhost:PORT/{sessionid}`
- Tab titles reflect the working directory (`pwd`) of the AI agent terminal

## Tech Stack

- **MCP Framework**: Python MCP SDK
- **Backend**: Python (Flask/FastAPI for lightweight HTTP server)
- **Frontend Rendering**:
  - **Diagrams**: Mermaid.js
  - **UI/Styling**: Tailwind CSS
  - **Markdown**: Compatible format with embedded Mermaid support
- **Storage**: JSON/SQLite (minimal, for session state)

## Installation & Usage

### Prerequisites
- Python 3.9+
- MCP client (Claude or compatible AI agent)

### Setup
```bash
git clone <repo-url>
cd mcp-brainstorm-server
pip install -r requirements.txt
```

### Running the Server
The server is started on-demand by the MCP tool when the AI agent detects brainstorming keywords. Users can also manually start it:

```bash
python mcp_server.py
```

### Expected Dependencies
```
anthropic-mcp
flask  # or fastapi
pydantic
python-dotenv
```

## Protocol Flow

### Example: Planning a Feature

1. **User**: "Let me brainstorm the architecture for this feature"
2. **AI Agent**: Detects keyword → Asks "Should I open the interactive brainstorming UI?"
3. **User**: "Yes"
4. **Server**: Launches at `localhost:8080/abc-def-123-ghi` (sessionid based on pwd)
5. **UI**: Renders mermaid diagram of possible architectures with clickable options, comment fields, and image upload area
6. **User**: Clicks preferred architecture option, adds comments, optionally uploads a reference diagram
7. **User**: Clicks "Submit"
8. **Server**: Stores submission under sessionid
9. **User**: Returns to AI agent and says "response submitted"
10. **AI Agent**: Retrieves submission via MCP → Continues planning with the user's input
11. **AI Agent** (optional): "Should I save this plan? Suggested location: `plans/feature-architecture.md`"

## MCP Tool Specification

### Available Tools

#### `start_brainstorm_session`
Starts an interactive brainstorming UI session.

**Input**:
- `prompt` (str): Initial brainstorming prompt/context
- `content_type` (str): `"mermaid"`, `"html"`, or `"markdown"`
- `working_dir` (str, optional): Current working directory (used for tab title)

**Output**:
- `session_id` (str): Unique session identifier
- `url` (str): Full localhost URL to access the UI
- `port` (int): Port number used

#### `get_session_response`
Retrieves user submission from a completed session.

**Input**:
- `session_id` (str): Session identifier

**Output**:
- `response` (dict): User's submitted choices, comments, and images
- `timestamp` (str): When submission occurred
- `status` (str): `"pending"`, `"submitted"`, `"expired"`

#### `list_sessions`
Lists all active sessions.

**Output**:
- `sessions` (list): Array of active session objects with IDs, URLs, and creation times

#### `close_session`
Terminates and cleans up a session.

**Input**:
- `session_id` (str): Session to close

## Design Principles

- **Minimal Resource Usage**: Single-user operation, no heavy dependencies
- **Stateless Where Possible**: Sessions are ephemeral unless saved to disk
- **Ease of Reference**: Auto-generated IDs on all interactive elements
- **AI-Agent Friendly**: Structured response format for easy parsing and continuation
- **Visual Clarity**: Clear separation of UI sections with markdown/mermaid rendering

## Future Enhancements

- Persistent session history
- Real-time collaboration (future multi-user support)
- Custom Tailwind component library for brainstorming templates
- Built-in export to various formats (PDF, PNG, etc.)
- Integration with git for automatic plan versioning

## License

MIT

## Contributing

Contributions welcome. Please follow PEP 8 for Python code and ensure the server remains lightweight.
