import json
import logging
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from orbyntiq.api.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
)
from orbyntiq.core.logging import JsonFormatter
from orbyntiq.core.request_context import (
    reset_request_id,
    set_request_id,
)


def test_json_formatter_includes_request_id() -> None:
    token = set_request_id("request-log-test")

    try:
        record = logging.LogRecord(
            name="orbyntiq.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Test log",
            args=(),
            exc_info=None,
        )

        formatted = JsonFormatter().format(record)
        payload = json.loads(formatted)
    finally:
        reset_request_id(token)

    assert payload["message"] == "Test log"
    assert payload["request_id"] == "request-log-test"


def test_json_formatter_includes_structured_fields() -> None:
    record = logging.LogRecord(
        name="orbyntiq.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="HTTP request completed",
        args=(),
        exc_info=None,
    )

    record.event = "http_request_completed"
    record.http_method = "GET"
    record.http_path = "/health"
    record.http_status_code = 200
    record.duration_ms = 12.5

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "http_request_completed"
    assert payload["http_method"] == "GET"
    assert payload["http_path"] == "/health"
    assert payload["http_status_code"] == 200
    assert payload["duration_ms"] == 12.5


def test_request_logging_emits_completion_record(
    caplog,
) -> None:
    test_app = FastAPI()

    @test_app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    test_app.add_middleware(RequestLoggingMiddleware)
    test_app.add_middleware(RequestIDMiddleware)

    client = TestClient(test_app)

    with caplog.at_level(
        logging.INFO,
        logger=(
            "orbyntiq.api.middleware.request_logging"
        ),
    ):
        response = client.get(
            "/test",
            headers={
                "X-Request-ID": "structured-log-request",
            },
        )

    assert response.status_code == 200
    assert (
        response.headers["X-Request-ID"]
        == "structured-log-request"
    )

    records = [
        record
        for record in caplog.records
        if getattr(record, "event", None)
        == "http_request_completed"
    ]

    assert len(records) == 1

    record = records[0]

    assert record.http_method == "GET"
    assert record.http_path == "/test"
    assert record.http_status_code == 200
    assert isinstance(record.duration_ms, float)
    assert record.duration_ms >= 0


def test_generated_request_id_remains_valid_with_logging() -> None:
    test_app = FastAPI()

    @test_app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    test_app.add_middleware(RequestLoggingMiddleware)
    test_app.add_middleware(RequestIDMiddleware)

    response = TestClient(test_app).get("/test")

    assert response.status_code == 200

    request_id = response.headers["X-Request-ID"]

    assert UUID(hex=request_id).version == 4
