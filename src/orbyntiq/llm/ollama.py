import asyncio
import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

import httpx

from orbyntiq.llm.base import LLMProvider
from orbyntiq.llm.errors import (
    LLMConnectionError,
    LLMHTTPError,
    LLMInvalidResponseError,
    LLMModelNotFoundError,
    LLMTimeoutError,
)
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

    async def stream(
        self,
        messages: Sequence[LLMMessage],
    ) -> AsyncIterator[str]:
        """Stream text chunks from Ollama as they are generated."""

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in messages
            ],
            "stream": True,
        }

        for attempt in range(self.max_retries + 1):
            emitted_chunk = False

            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                ) as client:
                    async with client.stream(
                        "POST",
                        "/api/chat",
                        json=payload,
                    ) as response:
                        response.raise_for_status()

                        async for line in response.aiter_lines():
                            if not line:
                                continue

                            try:
                                data = json.loads(line)
                            except json.JSONDecodeError as exc:
                                raise LLMInvalidResponseError(
                                    "Ollama returned an invalid streaming response."
                                ) from exc

                            if not isinstance(data, dict):
                                raise LLMInvalidResponseError(
                                    "Ollama returned an invalid streaming response."
                                )

                            if data.get("error"):
                                raise LLMHTTPError(str(data["error"]))

                            message = data.get("message")

                            if message is None and data.get("done") is True:
                                return

                            if not isinstance(message, dict):
                                raise LLMInvalidResponseError(
                                    "Ollama streaming response is missing a message."
                                )

                            content = message.get("content", "")

                            if not isinstance(content, str):
                                raise LLMInvalidResponseError(
                                    "Ollama streaming content is invalid."
                                )

                            if content:
                                emitted_chunk = True
                                yield content

                            if data.get("done") is True:
                                return

                raise LLMInvalidResponseError(
                    "Ollama stream ended before completion."
                )

            except httpx.TimeoutException as exc:
                if emitted_chunk or attempt >= self.max_retries:
                    raise LLMTimeoutError(
                        f"LLM stream timed out after {attempt + 1} attempts."
                    ) from exc

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise LLMModelNotFoundError(
                        f"LLM model '{self.model}' was not found."
                    ) from exc

                raise LLMHTTPError(
                    f"Ollama returned HTTP {exc.response.status_code}."
                ) from exc

            except httpx.TransportError as exc:
                if emitted_chunk or attempt >= self.max_retries:
                    raise LLMConnectionError(
                        f"Could not connect to Ollama after {attempt + 1} attempts."
                    ) from exc

            delay = self.retry_base_delay * (2**attempt)
            await asyncio.sleep(delay)

        raise RuntimeError("Unreachable retry state.")

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

                try:
                    data = response.json()
                    content = data["message"]["content"]
                except (ValueError, KeyError, TypeError) as exc:
                    raise LLMInvalidResponseError(
                        "Ollama returned an invalid response."
                    ) from exc

                return LLMResponse(
                    content=content,
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

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise LLMModelNotFoundError(
                        f"LLM model '{self.model}' was not found."
                    ) from exc

                raise LLMHTTPError(
                    f"Ollama returned HTTP {exc.response.status_code}."
                ) from exc

            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise LLMConnectionError(
                        f"Could not connect to Ollama after {attempt + 1} attempts."
                    ) from exc

            delay = self.retry_base_delay * (2**attempt)
            await asyncio.sleep(delay)

        raise RuntimeError("Unreachable retry state.")
