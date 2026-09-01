from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import websocket
from pymongo import MongoClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
)
from redis import Redis

from orbyntiq.core.config import Settings
from orbyntiq.core.qdrant import (
    close_qdrant_client,
    create_qdrant_client,
    verify_qdrant_connection,
)
from orbyntiq.rag.embeddings import create_embedding_provider
from orbyntiq.rag.ingestion import DocumentIngestor

API_BASE = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/api/v1/ws/chat"

MONGODB_URL = "mongodb://127.0.0.1:27017"
MONGODB_DATABASE = "orbyntiq"

REDIS_URL = "redis://127.0.0.1:6379/0"

PROMETHEUS_URL = "http://127.0.0.1:9090"

RAG_FILE_NAME = "phase12_production_verification.txt"
RAG_FACT = (
    "The Meridian Archive synchronization interval "
    "is exactly 59 hours."
)


def heading(value: str) -> None:
    print(f"\n===== {value} =====")


def production_rag_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="production",
        qdrant_url="http://127.0.0.1:6333",
        ollama_base_url="http://127.0.0.1:11434",
        embedding_provider="ollama",
        embedding_model="qwen3-embedding:0.6b",
        embedding_dimension=1024,
    )


async def seed_rag_document() -> str:
    settings = production_rag_settings()

    qdrant = create_qdrant_client(settings)
    embeddings = create_embedding_provider(settings)

    try:
        await verify_qdrant_connection(qdrant)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / RAG_FILE_NAME

            path.write_text(
                (
                    "Orbyntiq Phase 12 production verification document.\n\n"
                    f"{RAG_FACT}\n\n"
                    "This fact exists only for the production end-to-end "
                    "verification."
                ),
                encoding="utf-8",
            )

            source_path = str(path.resolve())

            ingestor = DocumentIngestor(
                qdrant=qdrant,
                embeddings=embeddings,
                settings=settings,
            )

            result = await ingestor.ingest(path)

            if result.chunks_indexed < 1:
                raise RuntimeError(
                    "RAG verification document produced no chunks."
                )

            print("DOCUMENT_ID:", result.document_id)
            print("CHUNKS_INDEXED:", result.chunks_indexed)
            print("SOURCE_PATH:", source_path)

            return source_path

    finally:
        await embeddings.close()
        await close_qdrant_client(qdrant)


async def cleanup_rag_document(source_path: str) -> None:
    settings = production_rag_settings()
    qdrant = create_qdrant_client(settings)

    try:
        selector = FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="source_path",
                        match=MatchValue(
                            value=source_path,
                        ),
                    )
                ]
            )
        )

        await qdrant.delete(
            collection_name=settings.qdrant_collection,
            points_selector=selector,
            wait=True,
        )

    finally:
        await close_qdrant_client(qdrant)


def verify_health(client: httpx.Client) -> None:
    heading("1. API HEALTH")

    response = client.get("/health")
    response.raise_for_status()

    body = response.json()

    print(json.dumps(body, indent=2))

    if body.get("status") != "healthy":
        raise RuntimeError("API is not healthy.")

    if body.get("environment") != "production":
        raise RuntimeError(
            "API is not running with production environment."
        )

    print("API_HEALTH_OK")


def verify_llm(client: httpx.Client) -> None:
    heading("2. REAL LLM REST")

    response = client.post(
        "/api/v1/llm/chat",
        json={
            "prompt": (
                "Reply with exactly: ORBYNTIQ_PHASE12_LLM_OK"
            )
        },
    )

    response.raise_for_status()

    body = response.json()

    print(json.dumps(body, indent=2))

    if not body.get("content", "").strip():
        raise RuntimeError("LLM returned empty content.")

    if body.get("model") != "qwen3:4b-instruct":
        raise RuntimeError(
            f"Unexpected LLM model: {body.get('model')}"
        )

    print("LLM_REST_OK")


def verify_chat_websocket() -> None:
    heading("3. REAL LLM WEBSOCKET STREAM")

    request_id = f"phase12-chat-{uuid4().hex[:12]}"

    connection = websocket.create_connection(
        WS_URL,
        timeout=180,
    )

    chunks: list[str] = []

    try:
        connection.send(
            json.dumps(
                {
                    "type": "chat",
                    "request_id": request_id,
                    "message": (
                        "Reply with exactly: "
                        "ORBYNTIQ_PHASE12_WS_OK"
                    ),
                }
            )
        )

        started = False
        completed = False

        while not completed:
            event = json.loads(connection.recv())

            print(
                "EVENT:",
                event.get("type"),
            )

            event_type = event.get("type")

            if event_type == "started":
                started = True

            elif event_type == "chunk":
                chunks.append(
                    str(event.get("content", ""))
                )

            elif event_type == "completed":
                completed = True

            elif event_type == "error":
                raise RuntimeError(
                    f"WebSocket LLM error: {event}"
                )

        content = "".join(chunks).strip()

        print("STREAMED RESPONSE:")
        print(content)

        if not started:
            raise RuntimeError(
                "WebSocket never emitted started event."
            )

        if not chunks:
            raise RuntimeError(
                "WebSocket emitted no content chunks."
            )

        print("LLM_WEBSOCKET_OK")

    finally:
        connection.close()


def execute_agent(
    client: httpx.Client,
    *,
    query: str,
    request_id: str,
    conversation_id: str,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/agents/execute",
        json={
            "query": query,
            "request_id": request_id,
            "conversation_id": conversation_id,
            "max_hops": 8,
        },
    )

    response.raise_for_status()

    return response.json()


def verify_general_agent(
    client: httpx.Client,
    conversation_id: str,
) -> str:
    heading("4. REAL MULTI-AGENT REST — GENERAL")

    body = execute_agent(
        client,
        query=(
            "What is 2 + 2? "
            "Answer with only the number."
        ),
        request_id=f"phase12-general-{uuid4().hex[:12]}",
        conversation_id=conversation_id,
    )

    print(json.dumps(body, indent=2))

    if body.get("route") != "general":
        raise RuntimeError(
            f"Expected general route, got {body.get('route')}"
        )

    if not body.get("final_response", "").strip():
        raise RuntimeError(
            "General agent returned no final response."
        )

    print("GENERAL_AGENT_OK")

    return str(body["execution_id"])


def verify_research_agent(
    client: httpx.Client,
    conversation_id: str,
) -> str:
    heading("5. REAL MULTI-AGENT REST — RAG RESEARCH")

    query = (
        "Search the indexed knowledge base. "
        "According to the Orbyntiq Phase 12 production "
        "verification document, what is the Meridian Archive "
        "synchronization interval?"
    )

    body = execute_agent(
        client,
        query=query,
        request_id=f"phase12-research-{uuid4().hex[:12]}",
        conversation_id=conversation_id,
    )

    print(json.dumps(body, indent=2))

    route = body.get("route")
    answer = body.get("final_response", "")
    sources = body.get("sources", [])

    if route != "research":
        raise RuntimeError(
            f"Expected research route, got {route}"
        )

    normalized_answer = answer.lower()

    if "59" not in normalized_answer:
        raise RuntimeError(
            f"Expected 59-hour fact in answer: {answer}"
        )

    if "hour" not in normalized_answer:
        raise RuntimeError(
            f"Expected hour unit in answer: {answer}"
        )

    matching_source = any(
        source.get("file_name") == RAG_FILE_NAME
        for source in sources
    )

    if not matching_source:
        raise RuntimeError(
            "RAG answer did not reference the verification document."
        )

    print("RAG_RESEARCH_AGENT_OK")

    return str(body["execution_id"])


def verify_agent_websocket(
    conversation_id: str,
) -> str:
    heading("6. REAL MULTI-AGENT WEBSOCKET EVENTS")

    request_id = f"phase12-agent-ws-{uuid4().hex[:12]}"

    connection = websocket.create_connection(
        WS_URL,
        timeout=180,
    )

    events: list[dict[str, Any]] = []

    try:
        connection.send(
            json.dumps(
                {
                    "type": "agent_execute",
                    "request_id": request_id,
                    "query": (
                        "What is 3 + 4? "
                        "Answer with only the number."
                    ),
                    "conversation_id": conversation_id,
                    "max_hops": 8,
                }
            )
        )

        execution_id: str | None = None

        while True:
            event = json.loads(connection.recv())

            print(
                event.get("sequence"),
                event.get("event_type"),
                event.get("agent_name"),
            )

            if event.get("type") == "error":
                raise RuntimeError(
                    f"Multi-agent WebSocket error: {event}"
                )

            if event.get("type") != "agent_event":
                continue

            events.append(event)

            execution_id = str(
                event.get(
                    "execution_id",
                    execution_id or "",
                )
            )

            if event.get("event_type") == "execution_completed":
                break

        event_types = [
            str(event.get("event_type"))
            for event in events
        ]

        required = {
            "execution_started",
            "routing_completed",
            "agent_result",
            "execution_completed",
        }

        missing = required.difference(event_types)

        if missing:
            raise RuntimeError(
                f"Missing workflow events: {sorted(missing)}"
            )

        if not execution_id:
            raise RuntimeError(
                "WebSocket execution ID was not returned."
            )

        print("EVENT TYPES:", event_types)
        print("EXECUTION ID:", execution_id)
        print("MULTI_AGENT_WEBSOCKET_OK")

        return execution_id

    finally:
        connection.close()


def verify_redis(key: str) -> None:
    heading("7. REDIS PRODUCTION ROUNDTRIP")

    redis_client = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    try:
        if redis_client.ping() is not True:
            raise RuntimeError("Redis ping failed.")

        redis_client.setex(
            key,
            60,
            "ORBYNTIQ_PHASE12_REDIS_OK",
        )

        value = redis_client.get(key)

        print("KEY:", key)
        print("VALUE:", value)

        if value != "ORBYNTIQ_PHASE12_REDIS_OK":
            raise RuntimeError(
                "Redis roundtrip verification failed."
            )

        print("REDIS_ROUNDTRIP_OK")

    finally:
        redis_client.delete(key)
        redis_client.close()


def verify_mongodb(
    execution_ids: list[str],
) -> None:
    heading("8. MONGODB AGENT PERSISTENCE")

    mongo = MongoClient(
        MONGODB_URL,
        serverSelectionTimeoutMS=5000,
    )

    try:
        mongo.admin.command("ping")

        database = mongo[MONGODB_DATABASE]

        for execution_id in execution_ids:
            execution = database.agent_executions.find_one(
                {
                    "_id": execution_id,
                }
            )

            if execution is None:
                raise RuntimeError(
                    "Missing persisted agent execution: "
                    f"{execution_id}"
                )

            print(
                "EXECUTION:",
                execution_id,
                "STATUS:",
                execution.get("status"),
            )

            if execution.get("status") != "completed":
                raise RuntimeError(
                    "Persisted execution did not complete."
                )

            workflow_count = (
                database.workflow_history.count_documents(
                    {
                        "execution_id": execution_id,
                    }
                )
            )

            print(
                "WORKFLOW EVENTS:",
                workflow_count,
            )

            if workflow_count < 4:
                raise RuntimeError(
                    "Expected persisted workflow history."
                )

        print("MONGODB_PERSISTENCE_OK")

    finally:
        mongo.close()


def cleanup_mongodb(
    execution_ids: list[str],
) -> None:
    if not execution_ids:
        return

    mongo = MongoClient(
        MONGODB_URL,
        serverSelectionTimeoutMS=5000,
    )

    try:
        database = mongo[MONGODB_DATABASE]

        database.workflow_history.delete_many(
            {
                "execution_id": {
                    "$in": execution_ids,
                }
            }
        )

        database.agent_executions.delete_many(
            {
                "_id": {
                    "$in": execution_ids,
                }
            }
        )

    finally:
        mongo.close()


def verify_metrics(client: httpx.Client) -> None:
    heading("9. PRODUCTION METRICS")

    response = client.get("/metrics")
    response.raise_for_status()

    body = response.text

    expected_metrics = (
        "orbyntiq_http_requests_total",
        "orbyntiq_http_request_duration_seconds",
        "orbyntiq_websocket_connections_total",
        "orbyntiq_websocket_messages_total",
    )

    for metric in expected_metrics:
        if metric not in body:
            raise RuntimeError(
                f"Missing metric: {metric}"
            )

        print(metric, "= OK")

    print("API_METRICS_OK")


def verify_prometheus() -> None:
    heading("10. PROMETHEUS API TARGET")

    response = httpx.get(
        f"{PROMETHEUS_URL}/api/v1/targets",
        timeout=20,
    )
    response.raise_for_status()

    targets = response.json()["data"]["activeTargets"]

    api_targets = [
        target
        for target in targets
        if "api:8000" in target.get("scrapeUrl", "")
    ]

    if not api_targets:
        raise RuntimeError(
            "Prometheus API scrape target was not found."
        )

    for target in api_targets:
        print(
            target.get("scrapeUrl"),
            target.get("health"),
            target.get("lastError"),
        )

        if target.get("health") != "up":
            raise RuntimeError(
                "Prometheus API target is not healthy."
            )

    print("PROMETHEUS_API_TARGET_OK")


def main() -> None:
    token = uuid4().hex[:12]

    conversation_id = (
        f"phase12-production-conversation-{token}"
    )

    redis_key = (
        f"orbyntiq:production:phase12:e2e:{token}"
    )

    execution_ids: list[str] = []
    rag_source_path: str | None = None

    client = httpx.Client(
        base_url=API_BASE,
        timeout=180,
    )

    try:
        verify_health(client)
        verify_llm(client)
        verify_chat_websocket()

        verify_redis(redis_key)

        heading("RAG SEED")
        rag_source_path = asyncio.run(
            seed_rag_document()
        )
        print("RAG_SEED_OK")

        execution_ids.append(
            verify_general_agent(
                client,
                conversation_id,
            )
        )

        execution_ids.append(
            verify_research_agent(
                client,
                conversation_id,
            )
        )

        execution_ids.append(
            verify_agent_websocket(
                conversation_id,
            )
        )

        verify_mongodb(execution_ids)

        verify_metrics(client)
        verify_prometheus()

        heading("11. PRODUCTION E2E RESULT")

        print(
            "PRODUCTION_E2E_OK: "
            "health -> LLM REST -> LLM WebSocket -> "
            "Redis -> embeddings -> Qdrant -> RAG -> "
            "LangGraph -> MongoDB persistence -> "
            "agent WebSocket -> Prometheus verified"
        )

    finally:
        client.close()

        heading("CLEANUP")

        cleanup_mongodb(execution_ids)

        if rag_source_path is not None:
            asyncio.run(
                cleanup_rag_document(
                    rag_source_path
                )
            )

        print("E2E_TEST_DATA_CLEANED")


if __name__ == "__main__":
    main()
