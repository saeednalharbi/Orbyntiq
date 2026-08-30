from fastapi.testclient import TestClient

from orbyntiq.api.app import app

client = TestClient(app)


def test_cors_allows_angular_development_origin():
    response = client.options(
        "/api/v1/llm/chat",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:4200"
    )


def test_cors_does_not_allow_unknown_origin():
    response = client.options(
        "/api/v1/llm/chat",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers
