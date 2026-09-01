import asyncio
from typing import Any

from pytest import MonkeyPatch

from orbyntiq.llm.models import LLMMessage
from orbyntiq.llm.ollama import OllamaProvider


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "model": "test-model",
            "message": {"content": "ok"},
        }


class FakeAsyncClient:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.is_closed = False
        self.payloads: list[dict[str, Any]] = []
        self.active_requests = 0
        self.maximum_active_requests = 0

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any],
    ) -> FakeResponse:
        del path

        self.payloads.append(json)
        self.active_requests += 1
        self.maximum_active_requests = max(
            self.maximum_active_requests,
            self.active_requests,
        )

        await asyncio.sleep(0.01)
        self.active_requests -= 1

        return FakeResponse()

    async def aclose(self) -> None:
        self.is_closed = True


def test_provider_reuses_pool_limits_concurrency_and_reopens(
    monkeypatch: MonkeyPatch,
) -> None:
    clients: list[FakeAsyncClient] = []

    def create_client(**kwargs: Any) -> FakeAsyncClient:
        client = FakeAsyncClient(**kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(
        "orbyntiq.llm.ollama.httpx.AsyncClient",
        create_client,
    )

    provider = OllamaProvider(
        model="test-model",
        base_url="http://localhost:11434",
        timeout=60.0,
        max_retries=0,
        retry_base_delay=0.0,
        max_concurrency=2,
        keep_alive="10m",
    )

    messages = [
        LLMMessage(
            role="user",
            content="hello",
        )
    ]

    async def run_test() -> None:
        await asyncio.gather(
            provider.generate(messages),
            provider.generate(messages),
            provider.generate(messages),
        )

        assert len(clients) == 1
        assert clients[0].maximum_active_requests == 2
        assert all(payload["keep_alive"] == "10m" for payload in clients[0].payloads)

        await provider.close()

        assert clients[0].is_closed is True

        await provider.generate(messages)

        assert len(clients) == 2

        await provider.close()

    asyncio.run(run_test())
