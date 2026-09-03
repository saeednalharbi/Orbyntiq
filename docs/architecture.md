# Orbyntiq Architecture

## Overview

Orbyntiq is a local-first, production-focused multi-agent AI platform that combines an Angular product interface, an async FastAPI backend, local Ollama inference, LangGraph orchestration, retrieval-augmented generation, Model Context Protocol capabilities, persistence, real-time workflow events, and observability.

This document describes the implemented architecture for Orbyntiq v0.1.0. The root [`README.md`](../README.md) is the product-facing overview; this document focuses on system boundaries, request flows, infrastructure, and operational behavior.

## System at a Glance

```text
Angular 22 Frontend
Ask | Knowledge | Agents | Runs | Integrations | Settings
        |
        | HTTP + WebSocket
        v
FastAPI API
Health | Metrics | LLM | Agents | WebSocket | MCP
        |
        +-------------------------+
        |                         |
        | Direct                  | Smart workflow
        v                         v
   LLM Service             Multi-Agent Service
        |                         |
        |                    Supervisor
        |                  /     |     \
        |                 v      v      v
        |             Research General  MCP
        |                  \     |     /
        |                   \    |    /
        |                   Synthesizer
        |                         |
        +------------+------------+
                     |
                     v
                 Local Ollama
       qwen3:4b-instruct + embeddings
```

Supporting platform services:

```text
Qdrant            Semantic vector retrieval
Redis             Runtime state, sessions and cache services
MongoDB           Persisted executions and workflow history
OpenTelemetry     Application and AI instrumentation
OTel Collector    Telemetry collection/export
Prometheus        Metrics storage and querying
Tempo             Distributed trace backend
Grafana           Operational dashboards
```

## Frontend Layer

The frontend is an Angular 22 standalone application under [`frontend/`](../frontend/). It presents the platform as a usable AI product rather than exposing backend endpoints directly.

Primary product surfaces are:

- **Ask** - direct and Smart-mode conversations with live workflow progress.
- **Knowledge** - private document ingestion, library inspection, and semantic search.
- **Agents** - the implemented supervisor/specialist/synthesizer workflow and role descriptions.
- **Runs** - persisted execution history, status, routing information, and workflow details.
- **Integrations** - built-in MCP capabilities, tools, resources, prompts, and transport status.
- **Settings** - local model, retrieval, platform-service, and runtime health information.

The frontend communicates with FastAPI over HTTP and WebSocket. Multi-agent WebSocket events allow the UI to show routing decisions and workflow progress while a request is still executing.

## API Layer

The backend entry point is FastAPI. The public application surface currently includes:

| Interface | Endpoint | Responsibility |
| --- | --- | --- |
| Health | `GET /health` | Runtime health and environment |
| Metrics | `GET /metrics` | Prometheus-compatible metrics |
| Direct chat | `POST /api/v1/llm/chat` | Direct LLM request/response |
| Agent execution | `POST /api/v1/agents/execute` | Multi-agent workflow execution |
| WebSocket | `WS /api/v1/ws/chat` | Streaming chat and workflow events |
| MCP | `/mcp` | Streamable HTTP MCP transport |

The API layer also hosts request-ID propagation, structured request logging, metrics, tracing, dependency wiring, infrastructure lifecycle management, and consistent error handling.

## Request Execution Paths

### Direct LLM Path

```text
Frontend
   |
   v
FastAPI
   |
   v
LLMService
   |
   v
Ollama / qwen3:4b-instruct
   |
   v
Response
```

Direct mode is used when the caller explicitly wants a normal model interaction without multi-agent routing.

### Smart Multi-Agent Path

```text
User request
   |
   v
Multi-Agent Service
   |
   v
Supervisor
   |
   v
Validated route decision
   |-- research
   |-- general
   `-- mcp
   |
   v
Selected specialist
   |
   v
Synthesizer
   |
   v
Persist execution + workflow events
   |
   v
Final response
```

The supervisor does not answer the user directly. It chooses exactly one specialist route and records a short routing reason. Every specialist route returns through the synthesizer before completion.

## Agent Graph

The implemented LangGraph topology is:

```text
START
  |
  v
Supervisor
  |---------------|---------------|
  v               v               v
Research        General           MCP
  |               |               |
  `---------------|---------------'
                  |
                  v
             Synthesizer
                  |
                  v
                 END
```

Workflow roles:

- **Supervisor** - understands the request and selects the specialist route.
- **Research** - handles requests that require indexed documents, retrieval, or grounded RAG.
- **General** - handles normal model reasoning that does not require retrieval or tool execution.
- **MCP** - handles requests that require an MCP capability or tool.
- **Synthesizer** - prepares the final workflow response after specialist execution.

Agent nodes are instrumented with tracing attributes for agent name, route, and execution status.

## Retrieval-Augmented Generation

The research path is backed by the Orbyntiq RAG pipeline:

```text
TXT / Markdown / PDF
        |
        v
Load + normalize
        |
        v
Chunk
        |
        v
Local embedding model
qwen3-embedding:0.6b
        |
        v
Qdrant collection
        |
        v
Semantic retrieval
        |
        v
Retrieved context + source metadata
        |
        v
Local language model
        |
        v
Grounded answer + sources
```

The document loader supports:

- `.txt`
- `.md`
- `.pdf`

PDF ingestion retains page numbers when text is extractable. Retrieved chunks preserve document ID, source path, file name, chunk index, score, and optional page number.

If no suitable context is retrieved, the RAG service returns a defined no-context response instead of fabricating knowledge from the private document collection.

## Model Context Protocol

Orbyntiq contains a built-in MCP server mounted through the FastAPI application using streamable HTTP.

Current MCP capabilities include:

- `platform_status`
- `search_knowledge`
- `answer_with_rag`

The MCP specialist is also part of the LangGraph routing topology, which allows Smart-mode requests to reach MCP capabilities through the same supervisor -> specialist -> synthesizer execution model.

## Runtime State and Persistence

### Redis

Redis provides short-lived runtime storage used by Orbyntiq services, including:

- sessions
- conversation/runtime state
- agent state
- cache services
- TTL-based expiration

Redis connectivity and expiration behavior are covered by unit and integration tests.

### MongoDB

MongoDB stores durable platform history, including multi-agent executions and workflow events. This enables the Runs UI to inspect completed and failed requests after execution has ended.

### Qdrant

Qdrant stores embedded document chunks used for semantic retrieval. Retrieval supports metadata filters and score thresholds before context is sent to the RAG generation step.

## Local Model Runtime

Language-model and embedding inference run through Ollama:

```text
qwen3:4b-instruct
qwen3-embedding:0.6b
```

In the validated local deployment, Ollama runs on the host while the production-style API runs in Docker and reaches the host model runtime through its configured Ollama base URL.

The LLM provider uses a bounded reusable HTTP client pool, explicit concurrency limits, keep-alive configuration, retries, timeouts, and clean shutdown behavior.

## Observability

Orbyntiq instruments both normal application traffic and AI-specific work.

```text
FastAPI / WebSocket / LLM / RAG / Agents
                    |
                    v
              OpenTelemetry
                    |
                    v
          OpenTelemetry Collector
              /             \
             v               v
        Prometheus          Tempo
              \             /
               \           /
                  Grafana
```

Instrumentation includes:

- HTTP request counts and latency
- request IDs and structured JSON logs
- WebSocket connections and messages
- LLM operations
- RAG operations
- multi-agent execution counts and status
- routing decisions
- agent spans
- trace/span correlation

Grafana is provisioned with Orbyntiq observability configuration under [`infra/grafana/`](../infra/grafana/).

## Deployment Topology

The production-style Docker Compose stack contains eight services:

```text
api
redis
mongodb
qdrant
otel-collector
tempo
prometheus
grafana
```

The Angular development frontend runs separately on port `4200` during local development. The FastAPI service is exposed on `127.0.0.1:8000` in the validated Compose configuration.

Persistent data volumes are used for stateful infrastructure services.

## Container Security Baseline

The production API image and Compose runtime are hardened with:

- multi-stage image construction
- non-root `orbyntiq` runtime user
- `uid=10001` and `gid=10001`
- read-only root filesystem in Compose
- `no-new-privileges`
- all Linux capabilities dropped
- health checks
- secret files excluded from the build context
- localhost-bound infrastructure ports where appropriate

Security CI performs dependency auditing, Git-history secret scanning, and production-image vulnerability scanning.

## Validation Architecture

The repository uses three complementary GitHub Actions workflows:

```text
Python Quality & Tests
    |-- Ruff
    |-- pytest
    |-- Redis / MongoDB / Qdrant services
    `-- Compose validation

Production Image & Smoke Test
    |-- build production image
    |-- verify non-root identity
    |-- verify package + Uvicorn
    |-- start hardened runtime
    `-- validate API health

Security CI
    |-- dependency audit
    |-- Git-history secret scan
    `-- production-image vulnerability scan
```

The recorded v0.1.0 engineering snapshot includes:

- **349 backend tests passing**
- **100-user REST health test with 0 failures**
- **100-user WebSocket heartbeat test with 0 failures**
- **production end-to-end smoke verification passing**
- **0 HIGH / CRITICAL Trivy findings at the Phase 12.6 checkpoint**

Detailed load-test methodology and measurements are available in [`docs/load-testing/phase-11-results.md`](load-testing/phase-11-results.md).

## Repository Boundaries

```text
frontend/                   Angular product interface
src/orbyntiq/api/           FastAPI routes, middleware and application lifecycle
src/orbyntiq/agents/        LangGraph state, contracts and agent nodes
src/orbyntiq/rag/           Ingestion, embeddings, retrieval and grounded generation
src/orbyntiq/mcp_services/  Built-in MCP server and capabilities
src/orbyntiq/services/      Application orchestration and state services
src/orbyntiq/core/          Configuration and infrastructure clients
src/orbyntiq/observability/ Metrics, tracing and AI spans
infra/                      Grafana, Prometheus, Tempo and OTel configuration
load_tests/                 Locust workloads and benchmark support
tests/                      Unit, integration and performance-contract tests
scripts/                    Verification and maintenance utilities
```

## Design Principles

Orbyntiq is intentionally built around these engineering principles:

1. **Local-first** - model inference and private knowledge can stay under local control.
2. **Grounded** - document-dependent answers use retrieval and explicit source metadata.
3. **Agentic** - routing and specialist execution are explicit, inspectable workflow steps.
4. **Observable** - application and AI operations emit metrics, logs, and traces.
5. **Persistent** - execution history survives beyond a single request.
6. **Testable** - infrastructure boundaries, agent behavior, RAG, APIs, and runtime lifecycle are covered by automated tests.
7. **Production-minded** - container hardening, CI, security scanning, load testing, resource limits, and failure behavior are treated as part of the AI system rather than afterthoughts.
