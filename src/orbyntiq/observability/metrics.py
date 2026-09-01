from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from orbyntiq.core.config import Settings

HTTP_REQUESTS_TOTAL = Counter(
    "orbyntiq_http_requests_total",
    "Total number of Orbyntiq HTTP requests.",
    ("method", "path", "status"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "orbyntiq_http_request_duration_seconds",
    "Orbyntiq HTTP request duration in seconds.",
    ("method", "path", "status"),
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "orbyntiq_http_requests_in_progress",
    "Number of Orbyntiq HTTP requests currently being processed.",
    ("method",),
)

WEBSOCKET_ACTIVE_CONNECTIONS = Gauge(
    "orbyntiq_websocket_active_connections",
    "Number of currently active Orbyntiq WebSocket connections.",
    ("endpoint",),
)

WEBSOCKET_CONNECTIONS_TOTAL = Counter(
    "orbyntiq_websocket_connections_total",
    "Total number of accepted Orbyntiq WebSocket connections.",
    ("endpoint",),
)

WEBSOCKET_MESSAGES_TOTAL = Counter(
    "orbyntiq_websocket_messages_total",
    "Total number of Orbyntiq WebSocket messages.",
    ("endpoint", "direction", "message_type"),
)


KNOWN_WEBSOCKET_ENDPOINTS = {
    "/api/v1/ws/chat",
}

KNOWN_WEBSOCKET_MESSAGE_TYPES = {
    "agent_event",
    "agent_execute",
    "cancel",
    "cancelled",
    "chat",
    "chunk",
    "completed",
    "error",
    "ping",
    "pong",
    "started",
}


def normalize_websocket_endpoint(endpoint: str) -> str:
    """Return a bounded WebSocket endpoint label."""

    if endpoint in KNOWN_WEBSOCKET_ENDPOINTS:
        return endpoint

    return "other"


def normalize_websocket_message_type(
    message_type: object,
) -> str:
    """Return a bounded WebSocket message-type label."""

    if (
        isinstance(message_type, str)
        and message_type in KNOWN_WEBSOCKET_MESSAGE_TYPES
    ):
        return message_type

    return "unknown"


def record_websocket_connection(endpoint: str) -> None:
    endpoint_label = normalize_websocket_endpoint(endpoint)

    WEBSOCKET_ACTIVE_CONNECTIONS.labels(
        endpoint=endpoint_label,
    ).inc()

    WEBSOCKET_CONNECTIONS_TOTAL.labels(
        endpoint=endpoint_label,
    ).inc()


def record_websocket_disconnection(endpoint: str) -> None:
    endpoint_label = normalize_websocket_endpoint(endpoint)

    WEBSOCKET_ACTIVE_CONNECTIONS.labels(
        endpoint=endpoint_label,
    ).dec()


def record_websocket_message(
    endpoint: str,
    direction: str,
    message_type: object,
) -> None:
    endpoint_label = normalize_websocket_endpoint(endpoint)

    direction_label = (
        direction
        if direction in {"received", "sent"}
        else "unknown"
    )

    message_type_label = normalize_websocket_message_type(
        message_type
    )

    WEBSOCKET_MESSAGES_TOTAL.labels(
        endpoint=endpoint_label,
        direction=direction_label,
        message_type=message_type_label,
    ).inc()


def register_metrics_endpoint(
    app: FastAPI,
    settings: Settings,
) -> None:
    """Register the Prometheus scrape endpoint when metrics are enabled."""

    if not settings.observability_enabled:
        return

    if not settings.metrics_enabled:
        return

    @app.get(
        settings.metrics_path,
        include_in_schema=False,
    )
    def prometheus_metrics() -> Response:
        return Response(
            content=generate_latest(REGISTRY),
            headers={
                "Content-Type": CONTENT_TYPE_LATEST,
            },
        )
