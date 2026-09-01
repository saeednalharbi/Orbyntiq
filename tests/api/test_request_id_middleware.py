from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from orbyntiq.api.app import app
from orbyntiq.api.middleware.request_id import RequestIDMiddleware
from orbyntiq.core.request_context import get_request_id

client = TestClient(app)


def test_request_id_is_generated() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    request_id = response.headers["X-Request-ID"]

    parsed = UUID(hex=request_id)

    assert parsed.version == 4
    assert parsed.hex == request_id


def test_valid_incoming_request_id_is_preserved() -> None:
    request_id = "orbyntiq-test-request-123"

    response = client.get(
        "/health",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_invalid_incoming_request_id_is_replaced() -> None:
    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "invalid request id with spaces",
        },
    )

    assert response.status_code == 200

    request_id = response.headers["X-Request-ID"]

    assert request_id != "invalid request id with spaces"
    assert UUID(hex=request_id).version == 4


def test_request_id_is_available_inside_request_context() -> None:
    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware)

    @test_app.get("/context")
    async def context_endpoint() -> dict[str, str | None]:
        return {
            "request_id": get_request_id(),
        }

    test_client = TestClient(test_app)

    request_id = "correlation-test-456"

    response = test_client.get(
        "/context",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.json() == {
        "request_id": request_id,
    }
    assert response.headers["X-Request-ID"] == request_id
