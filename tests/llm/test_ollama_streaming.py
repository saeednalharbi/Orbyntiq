import pytest

from orbyntiq.llm.errors import LLMInvalidResponseError
from orbyntiq.llm.models import LLMMessage
from orbyntiq.llm.ollama import OllamaProvider


class FakeStreamResponse:
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.status_code = 200

    async def __aenter__(self) -> "FakeStreamResponse":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class FakeAsyncClient:
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        return None

    def stream(
        self,
        method: str,
        url: str,
        *,
        json: object,
    ) -> FakeStreamResponse:
        assert method == "POST"
        assert url == "/api/chat"
        assert isinstance(json, dict)
        assert json["stream"] is True

        return FakeStreamResponse(self.lines)


@pytest.mark.anyio
async def test_ollama_stream_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = [
        '{"message":{"role":"assistant","content":"Hello"},"done":false}',
        '{"message":{"role":"assistant","content":" world"},"done":false}',
        '{"message":{"role":"assistant","content":""},"done":true}',
    ]

    monkeypatch.setattr(
        "orbyntiq.llm.ollama.httpx.AsyncClient",
        lambda **kwargs: FakeAsyncClient(lines),
    )

    provider = OllamaProvider(
        model="qwen3:4b-instruct",
        base_url="http://localhost:11434",
        timeout=60.0,
        max_retries=0,
        retry_base_delay=0.0,
    )

    messages = [
        LLMMessage(
            role="user",
            content="Hello",
        )
    ]

    chunks = [
        chunk
        async for chunk in provider.stream(messages)
    ]

    assert chunks == ["Hello", " world"]


@pytest.mark.anyio
async def test_ollama_stream_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lines = ["this-is-not-json"]

    monkeypatch.setattr(
        "orbyntiq.llm.ollama.httpx.AsyncClient",
        lambda **kwargs: FakeAsyncClient(lines),
    )

    provider = OllamaProvider(
        model="qwen3:4b-instruct",
        base_url="http://localhost:11434",
        timeout=60.0,
        max_retries=0,
        retry_base_delay=0.0,
    )

    messages = [
        LLMMessage(
            role="user",
            content="Hello",
        )
    ]

    with pytest.raises(LLMInvalidResponseError):
        async for _ in provider.stream(messages):
            pass
