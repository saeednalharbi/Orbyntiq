# Orbyntiq Frontend

The Orbyntiq frontend is the Angular 22 product interface for the local-first multi-agent AI platform.

It turns the backend AI infrastructure into an inspectable workspace for direct conversations, Smart-mode agent orchestration, private knowledge retrieval, persisted execution history, MCP capabilities, and local runtime health.

## Product Surfaces

| Surface | Purpose |
| --- | --- |
| **Ask** | Direct AI conversations and Smart-mode multi-agent execution |
| **Knowledge** | Private document ingestion, semantic search, and indexed-document inspection |
| **Agents** | Visualize the supervisor, specialist routes, and synthesizer workflow |
| **Runs** | Inspect persisted executions, routing decisions, events, sources, and status |
| **Integrations** | Inspect built-in MCP transport, tools, resources, prompts, and agent integration |
| **Settings** | Inspect local models, RAG configuration, infrastructure, and runtime health |

## Interaction Modes

### Smart Mode

Smart mode sends the request through Orbyntiq's LangGraph workflow:

```text
Request
  |
  v
Supervisor
  |
  +-- Research
  +-- General
  `-- MCP
  |
  v
Synthesizer
  |
  v
Final response
```

The interface displays live workflow events while the request is executing, including routing and specialist progress.

### Direct Mode

Direct mode bypasses multi-agent routing and sends the request to the normal LLM chat path.

## Backend Interfaces

The frontend consumes the Orbyntiq FastAPI backend over HTTP and WebSocket.

| Interface | Endpoint |
| --- | --- |
| Health | `GET /health` |
| Direct LLM chat | `POST /api/v1/llm/chat` |
| Agent execution | `POST /api/v1/agents/execute` |
| Live chat/workflow stream | `WS /api/v1/ws/chat` |
| Metrics | `GET /metrics` |
| MCP transport | `/mcp` |

The validated local backend runs on:

```text
http://127.0.0.1:8000
```

## Local Development

### Prerequisites

Before starting the frontend, the Orbyntiq backend should be running.

From the repository root:

```powershell
docker compose up --build -d
docker compose ps
```

Ollama must also be available locally with the models configured by Orbyntiq.

Verify the API:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected status:

```text
healthy
```

### Install Frontend Dependencies

For a clean reproducible install:

```powershell
cd frontend
npm ci
```

### Start the Development Server

```powershell
npm start
```

Open:

```text
http://localhost:4200
```

Angular automatically reloads the application while frontend source files are changed.

## Build

Create a production frontend build with:

```powershell
npm run build
```

Build output is written to the Angular `dist/` directory.

## Tests

Run the frontend unit tests with:

```powershell
npm test -- --watch=false
```

The frontend uses Vitest through the Angular test runner.

## Main Technology

- Angular 22
- TypeScript
- RxJS
- Angular Router
- Angular Forms
- Vitest
- SCSS
- HTTP + WebSocket integration with FastAPI

## Runtime Experience

The UI is designed around the same core principles as the backend:

- **Private** - the workspace is built around local inference.
- **Grounded** - private knowledge is searchable through the RAG pipeline.
- **Agentic** - Smart mode exposes the coordinated multi-agent workflow.
- **Observable** - runs, routing decisions, workflow events, sources, and infrastructure state are inspectable.

## Related Documentation

For the full system architecture and backend infrastructure, see:

- [`../README.md`](../README.md)
- [`../docs/architecture.md`](../docs/architecture.md)
- [`../docs/load-testing/phase-11-results.md`](../docs/load-testing/phase-11-results.md)

## Portfolio Note

This frontend is part of the complete Orbyntiq v0.1.0 AI engineering project. It is not a standalone Angular demo; it is the product surface for the FastAPI, LangGraph, RAG, MCP, persistence, observability, and local-model runtime implemented in the repository.
