# Phase 11 — Load Testing and Optimization Results

## Outcome

Phase 11 validated Orbyntiq REST and WebSocket behavior from one to
100 concurrent lightweight users. All official tests completed without
request failures or API health-check failures.

AI workloads were limited to two concurrent users because the local
4-core CPU model runner and available memory were the limiting resources.

## Test environment

- Windows 11 Pro 10.0.26200
- Python 3.11.9
- Docker Engine 29.7.2
- Docker Compose 5.4.0
- Intel Core i7-8665U
- 4 physical cores and 8 logical processors
- 15.81 GiB installed RAM
- Ollama qwen3:4b-instruct
- Ollama model footprint while resident: approximately 3.2 GB
- FastAPI, Redis, MongoDB, Qdrant, Prometheus, Grafana, Tempo and
  OpenTelemetry Collector under Docker Compose

## Scenarios

The Locust suite covers:

- `GET /health`
- `POST /api/v1/llm/chat`
- `POST /api/v1/agents/execute`
- WebSocket connection establishment
- WebSocket ping/pong
- Complete WebSocket LLM streaming
- Response-contract validation
- Host CPU and available-memory sampling
- Docker service statistics
- Redis hit/miss deltas
- API health monitoring during load

## Single-user baselines

| Scenario | Recorded operations | Failures | RPS | P50 | P95 | P99 |
|---|---:|---:|---:|---:|---:|---:|
| Health | 59 | 0 | 1.020 | 6 ms | 9 ms | 11 ms |
| WebSocket heartbeat aggregate | 30 | 0 | 0.513 | 3 ms | 5 ms | 12 ms |
| Warm LLM REST | 12 | 0 | 0.213 | 1300 ms | 3100 ms | 3100 ms |
| Warm WebSocket stream aggregate | 11 | 0 | 0.209 | 1300 ms | 2100 ms | 2100 ms |
| Warm agent workflow | 1 | 0 | 0.028 | 36213 ms | 36213 ms | 36213 ms |

The agent console completed two requests between 20.587 and 36.213
seconds. The final CSV captured one request because another completed
during Locust shutdown.

## Lightweight concurrency

### REST health endpoint

| Users | Requests | Failures | RPS | P50 | P95 | P99 | Average host CPU | Minimum free RAM |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 297 | 0 | 10.16 | 8 ms | 18 ms | 27 ms | 14.4% | 4.89 GiB |
| 50 | 1441 | 0 | 49.43 | 7 ms | 22 ms | 56 ms | 14.5% | 4.94 GiB |
| 100 | 2893 | 0 | 99.15 | 6 ms | 20 ms | 89 ms | 16.4% | 4.92 GiB |

### WebSocket heartbeat

| Users | Operations | Failures | RPS | P50 | P95 | P99 | Average host CPU | Minimum free RAM |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 159 | 0 | 5.44 | 5 ms | 16 ms | 20 ms | 13.6% | 5.03 GiB |
| 50 | 782 | 0 | 26.80 | 3 ms | 32 ms | 48 ms | 12.4% | 5.00 GiB |
| 100 | 1575 | 0 | 53.95 | 3 ms | 57 ms | 180 ms | 13.7% | 4.96 GiB |

At 100 connections, ping/pong P99 was approximately 95 ms, while
connection establishment reached approximately 200 ms. The aggregated
P99 includes both operations.

## AI concurrency

Two concurrent users were the highest intentionally tested AI load.

| Scenario | Requests | Failures | RPS | P50 | P95 | P99 | Average CPU | Minimum free RAM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LLM REST, pre-optimization | 16 | 0 | 0.393 | 1500 ms | 3000 ms | 3000 ms | 44.3% | 2.48 GiB |
| WebSocket stream, pre-optimization | 18 | 0 | 0.409 | 1500 ms | 2900 ms | 2900 ms | 45.2% | 2.30 GiB |
| LLM REST, post-optimization | 16 | 0 | 0.394 | 1300 ms | 4600 ms | 4600 ms | 51.0% | 1.89 GiB |
| WebSocket stream, post-optimization | 15 | 0 | 0.358 | 1600 ms | 4300 ms | 4300 ms | 50.5% | 1.91 GiB |

The post-optimization run did not demonstrate a throughput improvement.
LLM median latency improved, but tail latency increased. Streaming
throughput declined by approximately 12.5%. These small CPU-bound
samples were affected by lower available memory and host variability.

No performance improvement is claimed from these results.

## Cold-start behavior

The first Docker-to-Ollama request initially failed while the model was
loading. A later successful cold request took approximately 32.152
seconds. Warm sequential requests took approximately 1.85–2.43 seconds.

Official steady-state AI benchmarks therefore warmed the model first.
Cold-start behavior remains documented as a separate reliability risk.

## Redis cache measurements

Every benchmark recorded Redis statistics before and after its workload.

The measured application-route workloads produced:

- Cache hits: 0
- Cache misses: 0
- Hit rate: not applicable

The tested routes do not currently invoke `RedisCache`, so inventing a
cache-hit percentage would be misleading. Redis connectivity, storage,
expiration behavior and cache metrics are verified by integration and
unit tests. The Phase 11 Redis Compose correction also restored actual
API-to-Redis connectivity.

## Bottlenecks identified

1. Local Ollama inference is the primary throughput bottleneck.
2. The resident model substantially reduces available host memory.
3. Multi-agent execution performs multiple model calls and is therefore
   much slower than direct LLM chat.
4. The Ollama provider previously created a new HTTP client for every
   request, preventing effective connection reuse.
5. WebSocket connection-establishment tail latency rises at 100
   simultaneous connections.
6. No evidence of FastAPI event-loop blocking appeared in health or
   heartbeat tests through 100 users.
7. No Redis rejection, eviction, error or slow-log activity occurred.

## Optimizations implemented

- Added Redis to Docker Compose with persistent storage and health checks.
- Corrected API Redis networking from container-local `localhost` to the
  Compose Redis service.
- Configured the Docker API to reach host Ollama.
- Reused a bounded `httpx.AsyncClient` connection pool.
- Limited local model concurrency to two requests.
- Configured four HTTP connections and two keep-alive connections.
- Added a 10-minute Ollama keep-alive value.
- Added clean LLM client shutdown and cache lifecycle cleanup.
- Added unit coverage for pool reuse, concurrency limiting, keep-alive,
  shutdown and client reopening.
- Added a memory safety gate to benchmark execution.
- Avoided unsafe high-concurrency multi-agent testing on constrained
  hardware.

## Conclusion

Orbyntiq's lightweight FastAPI and WebSocket infrastructure handled
100 concurrent local users without errors. The system's practical AI
capacity on this machine is governed by local model inference and memory,
not by REST routing, WebSocket heartbeat handling, Redis or the FastAPI
event loop.

The pooling and concurrency changes improve resource control and
operational predictability. They are not presented as a measured raw
throughput improvement.
