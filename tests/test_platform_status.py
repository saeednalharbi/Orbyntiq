from types import SimpleNamespace

from fastapi.testclient import TestClient

import orbyntiq.api.routes.platform as platform_routes
from orbyntiq.api.app import app

client = TestClient(app)


def _configure_runtime(
    *,
    redis: bool,
    mongodb: bool,
    qdrant: bool,
    multi_agent: bool,
) -> None:
    app.state.redis_available = redis
    app.state.mongodb_available = mongodb
    app.state.qdrant_available = qdrant

    app.state.multi_agent_service = (
        object()
        if multi_agent
        else None
    )


def test_platform_status_reports_healthy_runtime(
    monkeypatch,
):
    _configure_runtime(
        redis=True,
        mongodb=True,
        qdrant=True,
        multi_agent=True,
    )

    monkeypatch.setattr(
        platform_routes,
        "get_mcp_services",
        lambda: SimpleNamespace(
            retriever=object(),
            rag_service=object(),
        ),
    )

    response = client.get(
        "/api/v1/platform/status"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "healthy"
    assert body["service"] == "Orbyntiq"
    assert body["components"]["api"]["status"] == "healthy"
    assert body["components"]["redis"]["status"] == "healthy"
    assert body["components"]["mongodb"]["status"] == "healthy"
    assert body["components"]["qdrant"]["status"] == "healthy"
    assert (
        body["components"]["multi_agent"]["status"]
        == "healthy"
    )
    assert body["components"]["mcp"]["status"] == "healthy"


def test_platform_status_reports_degraded_runtime(
    monkeypatch,
):
    _configure_runtime(
        redis=False,
        mongodb=True,
        qdrant=False,
        multi_agent=False,
    )

    monkeypatch.setattr(
        platform_routes,
        "get_mcp_services",
        lambda: SimpleNamespace(
            retriever=None,
            rag_service=None,
        ),
    )

    response = client.get(
        "/api/v1/platform/status"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "degraded"
    assert (
        body["components"]["redis"]["status"]
        == "unavailable"
    )
    assert (
        body["components"]["qdrant"]["status"]
        == "unavailable"
    )
    assert (
        body["components"]["multi_agent"]["status"]
        == "unavailable"
    )
    assert (
        body["components"]["mcp"]["status"]
        == "unavailable"
    )


def test_platform_status_exposes_runtime_metadata(
    monkeypatch,
):
    _configure_runtime(
        redis=True,
        mongodb=True,
        qdrant=True,
        multi_agent=True,
    )

    monkeypatch.setattr(
        platform_routes,
        "get_mcp_services",
        lambda: SimpleNamespace(
            retriever=object(),
            rag_service=object(),
        ),
    )

    response = client.get(
        "/api/v1/platform/status"
    )

    body = response.json()

    assert body["environment"] in {
        "development",
        "testing",
        "production",
    }

    llm = body["components"]["llm"]

    assert llm["status"] == "configured"
    assert llm["provider"] == "ollama"
    assert llm["model"]

    observability = body["components"][
        "observability"
    ]

    assert isinstance(
        observability["metrics_enabled"],
        bool,
    )
    assert isinstance(
        observability["tracing_enabled"],
        bool,
    )
