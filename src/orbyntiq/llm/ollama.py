import asyncio
from collections.abc import Sequence
from typing import Any

import httpx

from orbyntiq.llm.base import LLMProvider
from orbyntiq.llm.errors import LLMConnectionError, LLMTimeoutError
from orbyntiq.llm.models import LLMMessage, LLMResponse


class OllamaProvider(LLMProvider):
    """Async LLM provider backed by a local Ollama server."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        timeout: float,
        max_retries: int,
        retry_base_delay: float,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    async def generate(
        self,
        messages: Sequence[LLMMessage],
    ) -> LLMResponse:
        return await self._generate(
            messages=messages,
        )

    async def generate_structured(
        self,
        messages: Sequence[LLMMessage],
        schema: dict[str, Any],
    ) -> LLMResponse:
        return await self._generate(
            messages=messages,
            response_format=schema,
        )

    async def _generate(
        self,
        *,
        messages: Sequence[LLMMessage],
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in messages
            ],
            "stream": False,
        }

        if response_format is not None:
            payload["format"] = response_format

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                ) as client:
                    response = await client.post("/api/chat", json=payload)
                    response.raise_for_status()

                data = response.json()

                return LLMResponse(
                    content=data["message"]["content"],
                    model=data.get("model", self.model),
                    prompt_tokens=data.get("prompt_eval_count"),
                    completion_tokens=data.get("eval_count"),
                    total_duration_ns=data.get("total_duration"),
                )

            except httpx.TimeoutException as exc:
                if attempt >= self.max_retries:
                    raise LLMTimeoutError(
                        f"LLM request timed out after {attempt + 1} attempts."
                    ) from exc

            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise LLMConnectionError(
                        f"Could not connect to Ollama after {attempt + 1} attempts."
                    ) from exc

            delay = self.retry_base_delay * (2**attempt)
            await asyncio.sleep(delay)

        raise RuntimeError("Unreachable retry state.")