from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from orbyntiq.api.app import app
from orbyntiq.observability.middleware import MetricsMiddleware

client = TestClient(app)


def _sample_value(
    name: str,
    labels: dict[str, str],
) -> float:
    value = REGISTRY.get_sample_value(
        name,
        labels,
    )

    if value is None:
        return 0.0

    return float(value)


def test_http_request_metrics_increment() -> None:
    labels = {
        "method": "GET",
        "path": "/health",
        "status": "200",
    }

    before_requests = _sample_value(
        "orbyntiq_http_requests_total",
        labels,
    )

    before_duration_count = _sample_value(
        "orbyntiq_http_request_duration_seconds_count",
        labels,
    )

    before_in_progress = _sample_value(
        "orbyntiq_http_requests_in_progress",
        {"method": "GET"},
    )

    response = client.get("/health")

    assert response.status_code == 200

    after_requests = _sample_value(
        "orbyntiq_http_requests_total",
        labels,
    )

    after_duration_count = _sample_value(
        "orbyntiq_http_request_duration_seconds_count",
        labels,
    )

    after_in_progress = _sample_value(
        "orbyntiq_http_requests_in_progress",
        {"method": "GET"},
    )

    assert after_requests == before_requests + 1
    assert (
        after_duration_count
        == before_duration_count + 1
    )
    assert after_in_progress == before_in_progress


def test_metrics_endpoint_does_not_measure_itself() -> None:
    labels = {
        "method": "GET",
        "path": "/metrics",
        "status": "200",
    }

    before = _sample_value(
        "orbyntiq_http_requests_total",
        labels,
    )

    response = client.get("/metrics")

    assert response.status_code == 200

    after = _sample_value(
        "orbyntiq_http_requests_total",
        labels,
    )

    assert after == before


def test_websocket_connection_metrics_track_lifecycle() -> None:
    labels = {
        "endpoint": "/api/v1/ws/chat",
    }

    before_active = _sample_value(
        "orbyntiq_websocket_active_connections",
        labels,
    )

    before_total = _sample_value(
        "orbyntiq_websocket_connections_total",
        labels,
    )

    with client.websocket_connect(
        "/api/v1/ws/chat"
    ):
        during_active = _sample_value(
            "orbyntiq_websocket_active_connections",
            labels,
        )

        during_total = _sample_value(
            "orbyntiq_websocket_connections_total",
            labels,
        )

        assert during_active == before_active + 1
        assert during_total == before_total + 1

    after_active = _sample_value(
        "orbyntiq_websocket_active_connections",
        labels,
    )

    assert after_active == before_active


def test_websocket_message_metrics_track_ping_pong() -> None:
    received_labels = {
        "endpoint": "/api/v1/ws/chat",
        "direction": "received",
        "message_type": "ping",
    }

    sent_labels = {
        "endpoint": "/api/v1/ws/chat",
        "direction": "sent",
        "message_type": "pong",
    }

    before_received = _sample_value(
        "orbyntiq_websocket_messages_total",
        received_labels,
    )

    before_sent = _sample_value(
        "orbyntiq_websocket_messages_total",
        sent_labels,
    )

    with client.websocket_connect(
        "/api/v1/ws/chat"
    ) as websocket:
        websocket.send_json(
            {
                "type": "ping",
            }
        )

        response = websocket.receive_json()

        assert response == {
            "type": "pong",
        }

    after_received = _sample_value(
        "orbyntiq_websocket_messages_total",
        received_labels,
    )

    after_sent = _sample_value(
        "orbyntiq_websocket_messages_total",
        sent_labels,
    )

    assert after_received == before_received + 1
    assert after_sent == before_sent + 1


def test_orbyntiq_metrics_are_exposed() -> None:
    response = client.get("/metrics")

    assert response.status_code == 200

    body = response.text

    expected_metrics = (
        "orbyntiq_http_requests_total",
        "orbyntiq_http_request_duration_seconds",
        "orbyntiq_http_requests_in_progress",
        "orbyntiq_websocket_active_connections",
        "orbyntiq_websocket_connections_total",
        "orbyntiq_websocket_messages_total",
    )

    for metric in expected_metrics:
        assert metric in body


def test_metrics_middleware_is_registered_once() -> None:
    registrations = [
        middleware
        for middleware in app.user_middleware
        if middleware.cls is MetricsMiddleware
    ]

    assert len(registrations) == 1
