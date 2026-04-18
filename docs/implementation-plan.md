# Implementation Plan

## Context

This plan is based on the current [`README.md`](../README.md) only. The repository does not yet contain the server, MCP entrypoint, templates, storage layer, or tests described there, so this should be treated as a greenfield implementation plan with an MVP-first sequence.

## Goals

Build an MCP server that:

1. Starts a lightweight localhost brainstorming UI on demand.
2. Supports per-session URLs and isolated session state.
3. Renders `mermaid`, `html`, and `markdown` content.
4. Captures structured user submissions including selections, comments, and images.
5. Lets the AI agent retrieve session responses through MCP tools.
6. Optionally saves finalized outputs into the user's runtime data directory.

## Recommended Delivery Strategy

Implement this in phases, with a strict MVP before optional enhancements. The MVP should prove the full loop:

1. MCP tool call creates a session.
2. Browser UI opens at a session-specific URL.
3. User submits structured feedback.
4. MCP tool retrieves that feedback.

Do not start with advanced persistence, real-time collaboration, or export features.

## Proposed Project Structure

```text
brainstorm-mcp/
├── mcp_server.py
├── requirements.txt
├── server/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── models.py
│   ├── session_store.py
│   ├── renderer.py
│   ├── routes.py
│   └── static/
│       ├── app.css
│       └── app.js
├── docs/
│   └── implementation-plan.md
└── tests/
    ├── test_mcp_tools.py
    ├── test_routes.py
    ├── test_renderer.py
    └── test_session_store.py

Runtime data (outside the repo by default):
~/.mcp/brainstorm-mcp/
├── sessions/
│   └── assets/
└── plans/
```

## Architecture Decisions

### 1. Backend Framework

Use **FastAPI** for the HTTP/UI server unless there is a strong reason to prefer Flask.

Reasoning:

- Better request/response typing for MCP-adjacent structured data.
- Easy JSON APIs for session polling and submission retrieval.
- Straightforward static/template serving.
- Good fit for lightweight Python services.

### 2. Session Storage

Start with **JSON-backed file storage** under the user's runtime data directory.

Reasoning:

- Easier to inspect during development than SQLite.
- Good enough for single-user, low-volume sessions.
- Simpler bootstrap path for the MVP.

Add a clean storage interface so SQLite can be introduced later without changing route or MCP logic.

### 3. Rendering Model

Support three normalized content modes:

- `mermaid`
- `html`
- `markdown`

Internally, route all content through one renderer contract that returns:

- sanitized HTML fragment
- declared interactive elements
- metadata used by the frontend

### 4. Frontend Styling

Keep the frontend simple:

- Tailwind via CDN for MVP
- small local `app.js` for submit flow and clipboard/file handling
- Mermaid via CDN and client-side rendering

This avoids adding a Node build step early.

## Phase Plan

## Phase 0: Foundation And Scope Lock

### Deliverables

- Confirm FastAPI, JSON session storage, and CDN-based Tailwind/Mermaid.
- Create repo skeleton and dependency list.
- Define canonical session and response schemas.

### Tasks

- Add `requirements.txt`.
- Create package structure under `server/`.
- Define Pydantic models for:
  - `BrainstormSession`
  - `SessionContent`
  - `UserSelection`
  - `UserComment`
  - `UserImage`
  - `SessionResponse`
- Decide session lifecycle states:
  - `pending`
  - `submitted`
  - `closed`
  - `expired`

### Acceptance Criteria

- The repo can install cleanly in a fresh Python 3.9+ environment.
- Data models are stable enough to drive both MCP tools and HTTP routes.

## Phase 1: Session Store

### Deliverables

- A file-backed session store abstraction.

### Tasks

- Implement `server/session_store.py`.
- Support operations:
  - create session
  - get session
  - list sessions
  - update submission
  - close session
  - expire old sessions
- Store one JSON file per session under `~/.mcp/brainstorm-mcp/sessions/{session_id}.json` by default.
- Include timestamps, working directory, content type, content payload, status, and submission data.

### Acceptance Criteria

- Sessions survive process restarts if the session JSON remains on disk.
- Invalid or missing session IDs return controlled errors.

## Phase 2: Localhost UI Server

### Deliverables

- Running HTTP server with session routes.

### Tasks

- Implement FastAPI app in `server/app.py`.
- Add routes:
  - `GET /health`
  - `GET /{session_id}` to render the brainstorming UI
  - `POST /api/sessions/{session_id}/submit`
  - `GET /api/sessions/{session_id}`
  - `GET /api/sessions`
- Set browser tab title from the working directory name.
- Serve static assets and templates.

### Acceptance Criteria

- A created session URL renders without manual file edits.
- Submission endpoint stores data and returns a structured success payload.

## Phase 3: Content Rendering

### Deliverables

- Render pipeline for `mermaid`, `html`, and `markdown`.

### Tasks

- Implement `server/renderer.py`.
- For `mermaid`:
  - wrap source in a Mermaid container
  - preserve raw source for debugging if needed
- For `markdown`:
  - render markdown to HTML
  - support Mermaid code fences
  - support tables and headings
- For `html`:
  - render trusted or sanitized HTML depending on final threat model
- Define an auto-ID strategy for sections and interactive options.

### Acceptance Criteria

- All three content types render in one template without branching complexity leaking into the frontend.
- Mermaid diagrams initialize reliably on page load.

## Phase 4: Interactive Submission UX

### Deliverables

- Session page that users can interact with and submit.

### Tasks

- Build `server/templates/session.html`.
- Add frontend behavior in `server/static/app.js` for:
  - button selection
  - inline comments
  - submit/done flow
  - disable submit while request is in flight
- Include a clear section model:
  - prompt/context
  - rendered content
  - choices
  - comments
  - images
  - submit controls
- Define the submission payload shape.

### Acceptance Criteria

- A user can select options, add comments, click submit, and see confirmation.
- Submission data is structured enough for direct MCP consumption without brittle scraping.

## Phase 5: Image Input Support

### Deliverables

- Support for file uploads, image URLs, and clipboard paste.

### Tasks

- Extend submission schema with image objects containing:
  - source type
  - local filename or original URL
  - stored path if uploaded
  - optional note
- Implement upload handling for:
  - file picker
  - pasted clipboard image blobs
  - manually entered image URLs
- Store uploaded files in a session-scoped directory such as `~/.mcp/brainstorm-mcp/sessions/assets/{session_id}/`.
- Enforce file size and MIME-type limits.

### Acceptance Criteria

- Users can submit at least one uploaded image and one URL image reference.
- The stored session response clearly distinguishes uploaded files from remote URLs.

## Phase 6: MCP Server Layer

### Deliverables

- Working MCP tool entrypoint exposing the tools described in the README.

### Tasks

- Implement `mcp_server.py`.
- Add tools:
  - `start_brainstorm_session`
  - `get_session_response`
  - `list_sessions`
  - `close_session`
- `start_brainstorm_session` should:
  - ensure the UI server is running
  - create a new session
  - return session metadata and URL
- `get_session_response` should return:
  - status
  - timestamp
  - response object
- Ensure tool outputs are stable and easy for AI agents to parse.

### Acceptance Criteria

- An MCP client can create a session and retrieve its submission using only the documented tools.
- Tool output formats match the README specification or a documented revision.

## Phase 7: Optional Plan Saving

### Deliverables

- Save finalized content into `~/.mcp/brainstorm-mcp/plans/*.md` by default.

### Tasks

- Implement a helper that converts session response data into markdown.
- Define a safe filename strategy:
  - slugified title or prompt fragment
  - timestamp suffix to avoid collisions
- Save to the user's plans directory only when explicitly requested by the agent or user.

### Acceptance Criteria

- Saved markdown is readable, structured, and includes enough context to be useful later.

## Phase 8: Reliability, Testing, And Documentation

### Deliverables

- Basic automated coverage and operator documentation.

### Tasks

- Add tests for:
  - session store CRUD
  - route behavior
  - renderer behavior
  - MCP tool contracts
- Add failure-path tests:
  - expired session
  - duplicate submit
  - invalid upload type
  - missing session
- Update `README.md` setup instructions with exact commands and architecture notes.
- Add example screenshots or sample rendered content later if useful.

### Acceptance Criteria

- Core flows are covered by automated tests.
- A new contributor can run the service from the README without guessing missing steps.

## MVP Definition

The MVP should include only:

- FastAPI server
- file-backed session storage
- session-specific page rendering
- `mermaid`, `markdown`, and `html` content support
- button selection and comments
- submit/retrieve via MCP tools

The MVP can defer:

- image uploads if schedule is tight
- persistent history beyond session JSON
- advanced sanitization policy
- export features
- git integration
- multi-user behavior

## Suggested Build Order

1. Scaffold Python project, dependencies, and models.
2. Implement session store and tests.
3. Implement FastAPI app and session routes.
4. Add renderer for all content types.
5. Build session UI and submit flow.
6. Implement MCP tools and server bootstrap.
7. Add image handling.
8. Add markdown plan saving.
9. Finish tests, docs, and cleanup.

## Risks And Mitigations

### 1. MCP Server And Web Server Lifecycle Coupling

Risk:
Starting or reusing the UI server from the MCP layer can become fragile.

Mitigation:

- isolate server startup logic behind a dedicated function
- probe `/health` before starting another instance
- keep port selection explicit and deterministic where possible

### 2. Unsafe HTML Rendering

Risk:
Allowing raw HTML can introduce XSS concerns even in localhost usage.

Mitigation:

- define whether HTML is trusted input from the AI agent
- sanitize by default unless raw HTML is intentionally allowed

### 3. Frontend Complexity Creep

Risk:
The UI can become over-engineered if it tries to support too many interaction types early.

Mitigation:

- keep the initial frontend to buttons, comments, uploads, and submit
- add richer widgets only when a concrete need appears

### 4. Ambiguous Response Shapes For Agents

Risk:
If responses are loosely structured, agents will need brittle parsing logic.

Mitigation:

- define strict response schemas early
- keep labels and IDs explicit
- preserve both raw and normalized values when useful

## Suggested Task Breakdown For First Implementation Sprint

### Sprint 1

- Create project skeleton.
- Add dependencies and base models.
- Implement file-backed session store.
- Implement FastAPI app and health route.
- Render a basic session page with placeholder content.

### Sprint 2

- Implement markdown, Mermaid, and HTML rendering.
- Add interactive controls and submit API.
- Store normalized response payloads.
- Add route and renderer tests.

### Sprint 3

- Implement MCP tools and server bootstrap.
- Test end-to-end session creation and retrieval.
- Add optional plan saving into the user's runtime plans directory.
- Tighten README and example usage.

## Definition Of Done

The project is ready for initial use when:

1. An MCP client can create a brainstorm session from a prompt.
2. The returned URL opens a working local UI tied to that session.
3. The user can submit choices and comments from the page.
4. The MCP client can retrieve that structured submission.
5. The service can list and close sessions.
6. The README accurately documents setup and behavior.
