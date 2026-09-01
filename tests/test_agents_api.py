from fastapi.testclient import TestClient

from orbyntiq.api.app import app
from orbyntiq.api.dependencies import get_multi_agent_service
from orbyntiq.services import (
    MultiAgentExecution,
    MultiAgentExecutionError,
    MultiAgentUnavailableError,
)


class FakeMultiAgentService:
    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        max_hops: int = 8,
    ) -> MultiAgentExecution:
        assert user_query == "Explain embeddings."
        assert request_id == "request-api-123"
        assert max_hops == 6

        return MultiAgentExecution(
            execution_id="execution-123",
            request_id="request-api-123",
            route="general",
            route_reason="Direct LLM response is sufficient.",
            final_response="An embedding is a numerical representation.",
            sources=(),
            errors=(),
            agent_results=(),
            hop_count=3,
        )


class FailingMultiAgentService:
    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        max_hops: int = 8,
    ) -> MultiAgentExecution:
        del user_query, request_id, max_hops

        raise MultiAgentExecutionError(
            "Execution failed."
        )


def unavailable_service():
    raise MultiAgentUnavailableError(
        "Unavailable."
    )


def test_agent_execute_endpoint() -> None:
    app.dependency_overrides[
        get_multi_agent_service
    ] = lambda: FakeMultiAgentService()

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/agents/execute",
            json={
                "query": "Explain embeddings.",
                "request_id": "request-api-123",
                "max_hops": 6,
            },
        )

        assert response.status_code == 200

        assert response.json() == {
            "execution_id": "execution-123",
            "request_id": "request-api-123",
            "route": "general",
            "route_reason": (
                "Direct LLM response is sufficient."
            ),
            "final_response": (
                "An embedding is a numerical representation."
            ),
            "sources": [],
            "errors": [],
            "hop_count": 3,
        }

    finally:
        app.dependency_overrides.clear()


def test_agent_execute_rejects_empty_query() -> None:
    app.dependency_overrides[
        get_multi_agent_service
    ] = lambda: FakeMultiAgentService()

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/agents/execute",
            json={
                "query": "   ",
            },
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


def test_agent_execute_rejects_invalid_max_hops() -> None:
    app.dependency_overrides[
        get_multi_agent_service
    ] = lambda: FakeMultiAgentService()

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/agents/execute",
            json={
                "query": "Hello",
                "max_hops": 0,
            },
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


def test_agent_execute_unavailable_returns_503() -> None:
    app.dependency_overrides[
        get_multi_agent_service
    ] = unavailable_service

    try:
        client = TestClient(
            app,
            raise_server_exceptions=False,
        )

        response = client.post(
            "/api/v1/agents/execute",
            json={
                "query": "Hello",
            },
        )

        assert response.status_code == 503

        assert response.json() == {
            "detail": (
                "The multi-agent service is unavailable."
            )
        }

    finally:
        app.dependency_overrides.clear()


def test_agent_execution_failure_returns_500() -> None:
    app.dependency_overrides[
        get_multi_agent_service
    ] = lambda: FailingMultiAgentService()

    try:
        client = TestClient(
            app,
            raise_server_exceptions=False,
        )

        response = client.post(
            "/api/v1/agents/execute",
            json={
                "query": "Hello",
            },
        )

        assert response.status_code == 500

        assert response.json() == {
            "detail": (
                "The multi-agent execution failed."
            )
        }

    finally:
        app.dependency_overrides.clear()
