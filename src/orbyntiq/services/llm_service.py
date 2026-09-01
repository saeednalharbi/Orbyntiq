import asyncio
from collections.abc import AsyncIterator, Sequence
from time import perf_counter
from typing import TypeVar

from opentelemetry.trace import Span
from pydantic import BaseModel, ValidationError

from orbyntiq.llm.base import LLMProvider
from orbyntiq.llm.errors import LLMInvalidResponseError
from orbyntiq.llm.messages import build_messages
from orbyntiq.llm.models import LLMMessage, LLMResponse
from orbyntiq.llm.prompts import BASE_SYSTEM_PROMPT
from orbyntiq.observability.llm_metrics import (
    LLM_REQUEST_DURATION_SECONDS,
    LLM_REQUESTS_IN_PROGRESS,
    LLM_REQUESTS_TOTAL,
    LLM_STREAM_CHUNKS_TOTAL,
    LLM_STREAM_DURATION_SECONDS,
    LLM_STREAMS_TOTAL,
    get_llm_metric_labels,
    record_llm_tokens,
)
from orbyntiq.observability.spans import (
    bounded_name,
    traced_span,
)

ResponseModelT = TypeVar(
    "ResponseModelT",
    bound=BaseModel,
)


def _llm_span_attributes(
    provider: str,
    model: str,
    operation: str,
) -> dict[str, object]:
    return {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": provider,
        "gen_ai.request.model": model,
        "orbyntiq.llm.operation": operation,
    }


def _set_response_attributes(
    span: Span,
    response: LLMResponse,
) -> None:
    span.set_attribute(
        "gen_ai.response.model",
        bounded_name(
            response.model,
            default="unknown",
        ),
    )

    if isinstance(response.prompt_tokens, int) and response.prompt_tokens >= 0:
        span.set_attribute(
            "gen_ai.usage.input_tokens",
            response.prompt_tokens,
        )

    if isinstance(response.completion_tokens, int) and response.completion_tokens >= 0:
        span.set_attribute(
            "gen_ai.usage.output_tokens",
            response.completion_tokens,
        )


class LLMService:
    """Application service for interacting with language models."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        metrics_enabled: bool = True,
    ) -> None:
        self.provider = provider
        self.metrics_enabled = metrics_enabled

    async def generate(
        self,
        messages: Sequence[LLMMessage],
    ) -> LLMResponse:
        provider, model = get_llm_metric_labels(self.provider)

        operation = "generate"
        status = "success"
        started_at = perf_counter()

        with traced_span(
            "llm.generate",
            tracer_name="orbyntiq.llm",
            attributes=_llm_span_attributes(
                provider,
                model,
                operation,
            ),
        ) as span:
            if self.metrics_enabled:
                LLM_REQUESTS_IN_PROGRESS.labels(
                    provider=provider,
                    model=model,
                    operation=operation,
                ).inc()

            try:
                response = await self.provider.generate(messages)

            except asyncio.CancelledError:
                status = "cancelled"
                raise

            except Exception:
                status = "error"
                raise

            else:
                _set_response_attributes(
                    span,
                    response,
                )

                if self.metrics_enabled:
                    record_llm_tokens(
                        provider=provider,
                        model=model,
                        prompt_tokens=response.prompt_tokens,
                        completion_tokens=response.completion_tokens,
                    )

                return response

            finally:
                span.set_attribute(
                    "orbyntiq.operation.status",
                    status,
                )

                if self.metrics_enabled:
                    duration = perf_counter() - started_at

                    LLM_REQUESTS_TOTAL.labels(
                        provider=provider,
                        model=model,
                        operation=operation,
                        status=status,
                    ).inc()

                    LLM_REQUEST_DURATION_SECONDS.labels(
                        provider=provider,
                        model=model,
                        operation=operation,
                        status=status,
                    ).observe(duration)

                    LLM_REQUESTS_IN_PROGRESS.labels(
                        provider=provider,
                        model=model,
                        operation=operation,
                    ).dec()

    async def generate_stream(
        self,
        messages: Sequence[LLMMessage],
    ) -> AsyncIterator[str]:
        """Stream text chunks from the configured LLM provider."""

        provider, model = get_llm_metric_labels(self.provider)

        operation = "stream"
        status = "success"
        chunk_count = 0
        started_at = perf_counter()

        with traced_span(
            "llm.stream",
            tracer_name="orbyntiq.llm",
            attributes=_llm_span_attributes(
                provider,
                model,
                operation,
            ),
        ) as span:
            if self.metrics_enabled:
                LLM_REQUESTS_IN_PROGRESS.labels(
                    provider=provider,
                    model=model,
                    operation=operation,
                ).inc()

            try:
                async for chunk in self.provider.stream(messages):
                    chunk_count += 1

                    if self.metrics_enabled:
                        LLM_STREAM_CHUNKS_TOTAL.labels(
                            provider=provider,
                            model=model,
                        ).inc()

                    yield chunk

            except (
                asyncio.CancelledError,
                GeneratorExit,
            ):
                status = "cancelled"
                raise

            except Exception:
                status = "error"
                raise

            finally:
                span.set_attribute(
                    "orbyntiq.operation.status",
                    status,
                )

                span.set_attribute(
                    "orbyntiq.stream.chunk_count",
                    chunk_count,
                )

                if self.metrics_enabled:
                    duration = perf_counter() - started_at

                    LLM_REQUESTS_TOTAL.labels(
                        provider=provider,
                        model=model,
                        operation=operation,
                        status=status,
                    ).inc()

                    LLM_REQUEST_DURATION_SECONDS.labels(
                        provider=provider,
                        model=model,
                        operation=operation,
                        status=status,
                    ).observe(duration)

                    LLM_STREAMS_TOTAL.labels(
                        provider=provider,
                        model=model,
                        status=status,
                    ).inc()

                    LLM_STREAM_DURATION_SECONDS.labels(
                        provider=provider,
                        model=model,
                        status=status,
                    ).observe(duration)

                    LLM_REQUESTS_IN_PROGRESS.labels(
                        provider=provider,
                        model=model,
                        operation=operation,
                    ).dec()

    async def chat(
        self,
        prompt: str,
        *,
        system_prompt: str = BASE_SYSTEM_PROMPT,
        history: Sequence[LLMMessage] = (),
    ) -> LLMResponse:
        messages = build_messages(
            prompt,
            system_prompt=system_prompt,
            history=history,
        )

        return await self.generate(messages)

    async def chat_stream(
        self,
        prompt: str,
        *,
        system_prompt: str = BASE_SYSTEM_PROMPT,
        history: Sequence[LLMMessage] = (),
    ) -> AsyncIterator[str]:
        """Build chat messages and stream the generated response."""

        messages = build_messages(
            prompt,
            system_prompt=system_prompt,
            history=history,
        )

        async for chunk in self.generate_stream(messages):
            yield chunk

    async def chat_structured(
        self,
        prompt: str,
        response_model: type[ResponseModelT],
        *,
        system_prompt: str = BASE_SYSTEM_PROMPT,
        history: Sequence[LLMMessage] = (),
    ) -> ResponseModelT:
        messages = build_messages(
            prompt,
            system_prompt=system_prompt,
            history=history,
        )

        provider, model = get_llm_metric_labels(self.provider)

        operation = "structured"
        status = "success"
        started_at = perf_counter()

        with traced_span(
            "llm.structured",
            tracer_name="orbyntiq.llm",
            attributes=_llm_span_attributes(
                provider,
                model,
                operation,
            ),
        ) as span:
            if self.metrics_enabled:
                LLM_REQUESTS_IN_PROGRESS.labels(
                    provider=provider,
                    model=model,
                    operation=operation,
                ).inc()

            try:
                response = await self.provider.generate_structured(
                    messages,
                    response_model.model_json_schema(),
                )

                try:
                    result = response_model.model_validate_json(response.content)

                except ValidationError as exc:
                    raise LLMInvalidResponseError(
                        "LLM structured response failed schema validation."
                    ) from exc

            except asyncio.CancelledError:
                status = "cancelled"
                raise

            except Exception:
                status = "error"
                raise

            else:
                _set_response_attributes(
                    span,
                    response,
                )

                if self.metrics_enabled:
                    record_llm_tokens(
                        provider=provider,
                        model=model,
                        prompt_tokens=response.prompt_tokens,
                        completion_tokens=response.completion_tokens,
                    )

                return result

            finally:
                span.set_attribute(
                    "orbyntiq.operation.status",
                    status,
                )

                if self.metrics_enabled:
                    duration = perf_counter() - started_at

                    LLM_REQUESTS_TOTAL.labels(
                        provider=provider,
                        model=model,
                        operation=operation,
                        status=status,
                    ).inc()

                    LLM_REQUEST_DURATION_SECONDS.labels(
                        provider=provider,
                        model=model,
                        operation=operation,
                        status=status,
                    ).observe(duration)

                    LLM_REQUESTS_IN_PROGRESS.labels(
                        provider=provider,
                        model=model,
                        operation=operation,
                    ).dec()

    async def close(self) -> None:
        """Release the underlying provider resources."""
        await self.provider.close()
