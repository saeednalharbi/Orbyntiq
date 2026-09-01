import json
import logging

from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from orbyntiq.api.app import app
from orbyntiq.core.config import Settings
from orbyntiq.core.logging import JsonFormatter
from orbyntiq.observability.tracing import create_tracer_provider
from orbyntiq.observability.tracing_middleware import (
    TracingMiddleware,
)


def _provider_with_exporter() -> tuple[
    TracerProvider,
    InMemorySpanExporter,
]:
    exporter = InMemorySpanExporter()

    provider = TracerProvider()

    provider.add_span_processor(
        SimpleSpanProcessor(
            exporter
        )
    )

    return provider, exporter


def test_tracer_provider_has_service_resource() -> None:
    provider = create_tracer_provider(
        Settings(
            otel_service_name="orbyntiq-test",
        )
    )

    assert (
        provider.resource.attributes[
            "service.name"
        ]
        == "orbyntiq-test"
    )


def test_invalid_trace_sample_ratio_is_rejected() -> None:
    settings = Settings(
        otel_trace_sample_ratio=1.5,
    )

    try:
        create_tracer_provider(
            settings
        )
    except ValueError as exc:
        assert (
            "between 0.0 and 1.0"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected invalid sampling ratio to fail."
        )


def test_http_request_creates_server_span() -> None:
    provider, exporter = _provider_with_exporter()

    test_app = FastAPI()

    @test_app.get("/trace")
    async def traced_endpoint() -> dict[str, str]:
        return {
            "status": "ok",
        }

    test_app.add_middleware(
        TracingMiddleware,
        tracer_provider=provider,
    )

    response = TestClient(
        test_app
    ).get("/trace")

    assert response.status_code == 200

    trace_id = response.headers[
        "X-Trace-ID"
    ]

    assert len(trace_id) == 32
    int(trace_id, 16)

    spans = exporter.get_finished_spans()

    assert len(spans) == 1

    span = spans[0]

    assert span.name == "HTTP GET /trace"

    assert (
        span.attributes[
            "http.request.method"
        ]
        == "GET"
    )

    assert (
        span.attributes[
            "http.response.status_code"
        ]
        == 200
    )

    assert (
        format(
            span.context.trace_id,
            "032x",
        )
        == trace_id
    )


def test_traceparent_is_used_as_parent_context() -> None:
    provider, exporter = _provider_with_exporter()

    test_app = FastAPI()

    @test_app.get("/parent")
    async def parent_endpoint() -> dict[str, str]:
        return {
            "status": "ok",
        }

    test_app.add_middleware(
        TracingMiddleware,
        tracer_provider=provider,
    )

    parent_trace_id = (
        "11111111111111111111111111111111"
    )
    parent_span_id = (
        "2222222222222222"
    )

    traceparent = (
        f"00-{parent_trace_id}-"
        f"{parent_span_id}-01"
    )

    response = TestClient(
        test_app
    ).get(
        "/parent",
        headers={
            "traceparent": traceparent,
        },
    )

    assert response.status_code == 200

    span = exporter.get_finished_spans()[0]

    assert (
        format(
            span.context.trace_id,
            "032x",
        )
        == parent_trace_id
    )

    assert span.parent is not None

    assert (
        format(
            span.parent.span_id,
            "016x",
        )
        == parent_span_id
    )


def test_websocket_connection_creates_span() -> None:
    provider, exporter = _provider_with_exporter()

    test_app = FastAPI()

    @test_app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()

        await websocket.receive_text()

        await websocket.send_text(
            "ok"
        )

        await websocket.close()

    test_app.add_middleware(
        TracingMiddleware,
        tracer_provider=provider,
    )

    with TestClient(
        test_app
    ).websocket_connect(
        "/ws"
    ) as websocket:
        websocket.send_text(
            "hello"
        )

        assert (
            websocket.receive_text()
            == "ok"
        )

    spans = exporter.get_finished_spans()

    assert len(spans) == 1

    span = spans[0]

    assert (
        span.name
        == "WebSocket /ws"
    )

    assert (
        span.attributes[
            "network.protocol.name"
        ]
        == "websocket"
    )


def test_json_formatter_includes_trace_context() -> None:
    provider, _ = _provider_with_exporter()

    tracer = provider.get_tracer(
        "orbyntiq.test"
    )

    with tracer.start_as_current_span(
        "test-span"
    ):
        record = logging.LogRecord(
            name="orbyntiq.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Trace log",
            args=(),
            exc_info=None,
        )

        payload = json.loads(
            JsonFormatter().format(
                record
            )
        )

    assert len(payload["trace_id"]) == 32
    assert len(payload["span_id"]) == 16


def test_tracing_middleware_is_registered_once() -> None:
    registrations = [
        middleware
        for middleware in app.user_middleware
        if middleware.cls is TracingMiddleware
    ]

    assert len(registrations) == 1
