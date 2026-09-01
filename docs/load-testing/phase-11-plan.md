# Phase 11 Load-Testing Plan

## Test system

- Operating system: Windows 11 Pro 10.0.26200
- CPU: Intel Core i7-8665U, 4 physical cores / 8 logical processors
- Memory: 15.81 GB
- Python: 3.11.9
- Docker Engine: 29.7.2
- Docker Compose: 5.4.0
- Local LLM: qwen3:4b-instruct
- API target: http://127.0.0.1:8000
- Load generator: Locust 2.46.x

## Workloads

| Profile | Purpose | Planned concurrency |
|---|---|---:|
| HealthUser | HTTP and middleware throughput | 1, 10, 50, conditional 100 |
| LLMChatUser | Local Ollama generation | 1, 2, conditional 4 |
| AgentExecuteUser | LangGraph orchestration | 1, 2, conditional 4 |
| WebSocket heartbeat | Connection concurrency | 10, 50, conditional 100 |
| WebSocket streaming | Streaming generation | 1, 2, conditional 4 |

Expensive LLM and agent workloads are intentionally tested separately
from lightweight connection concurrency. One hundred simultaneous local
LLM generations would not be realistic for this four-core development
machine.

## Measurements

Every recorded benchmark must include:

- Request count and throughput
- Failure count and failure rate
- P50, P95, and P99 latency
- Host CPU and available memory
- Container CPU and memory
- Redis cache hits and misses
- WebSocket connections and streaming completion
- Exact user count, spawn rate, duration, and workload class

## Safety limits

Stop or reduce the test when:

- Available system memory falls below 1.5 GB
- CPU remains above 90 percent
- Failure rate exceeds 5 percent
- Docker or API health checks fail
- The machine becomes unresponsive

No performance number is documented until it has been measured.
Before-and-after runs must use identical workload settings.
