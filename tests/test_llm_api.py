from fastapi.testclient import TestClient

from orbyntiq.api.app import app
from orbyntiq.api.dependencies import get_llm_service
from orbyntiq.llm import LLMModelNotFoundError, LLMResponse


class FakeLLMService:
    async def chat(self, prompt: str) -> LLMResponse:
        return LLMResponse(
            content="ORBYNTIQ_API_TEST_OK",
            model="fake-model",
            prompt_tokens=12,
            completion_tokens=4,
        )


class MissingModelLLMService:
    async def chat(self, prompt: str) -> LLMResponse:
        raise LLMModelNotFoundError("Model unavailable")


def test_llm_chat_endpoint():
    app.dependency_overrides[get_llm_service] = lambda: FakeLLMService()

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/llm/chat",
            json={"prompt": "Hello"},
        )

        assert response.status_code == 200

        assert response.json() == {
            "content": "ORBYNTIQ_API_TEST_OK",
            "model": "fake-model",
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 4,
            },
        }
    finally:
        app.dependency_overrides.clear()


def test_llm_chat_rejects_empty_prompt():
    client = TestClient(app)

    response = client.post(
        "/api/v1/llm/chat",
        json={"prompt": "   "},
    )

    assert response.status_code == 422


def test_missing_model_returns_503():
    app.dependency_overrides[get_llm_service] = (
        lambda: MissingModelLLMService()
    )

    try:
        client = TestClient(
            app,
            raise_server_exceptions=False,
        )

        response = client.post(
            "/api/v1/llm/chat",
            json={"prompt": "Hello"},
        )

        assert response.status_code == 503
        assert response.json() == {
            "detail": "The configured local LLM model is unavailable."
        }
    finally:
        app.dependency_overrides.clear()