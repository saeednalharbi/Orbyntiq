from fastapi import FastAPI
from fastapi.testclient import TestClient

from orbyntiq.api.app import app
from orbyntiq.core.config import Settings
from orbyntiq.observability.metrics import register_metrics_endpoint


def test_metrics_endpoint_is_available() -> None:
    response = TestClient(app).get("/metrics")

    assert response.status_code == 200

    assert response.headers["content-type"].startswith(
        "text/plain"
    )

    body = response.text

    assert "# HELP" in body
    assert "python_info" in body


def test_metrics_path_is_configurable() -> None:
    test_app = FastAPI()

    settings = Settings(
        metrics_path="/internal/metrics",
    )

    register_metrics_endpoint(
        test_app,
        settings,
    )

    client = TestClient(test_app)

    assert client.get("/metrics").status_code == 404

    response = client.get("/internal/metrics")

    assert response.status_code == 200
    assert "python_info" in response.text


def test_metrics_endpoint_can_be_disabled() -> None:
    test_app = FastAPI()

    settings = Settings(
        metrics_enabled=False,
    )

    register_metrics_endpoint(
        test_app,
        settings,
    )

    response = TestClient(test_app).get("/metrics")

    assert response.status_code == 404
