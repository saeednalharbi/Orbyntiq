from fastapi.testclient import TestClient

from orbyntiq.api.app import app
from orbyntiq.core.config import get_settings

client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
        "service": "Orbyntiq",
        "environment": get_settings().environment,
    }