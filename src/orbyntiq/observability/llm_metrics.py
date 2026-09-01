import re

from prometheus_client import Counter, Gauge, Histogram

LLM_REQUESTS_TOTAL = Counter(
    "orbyntiq_llm_requests_total",
    "Total number of Orbyntiq LLM operations.",
    ("provider", "model", "operation", "status"),
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "orbyntiq_llm_request_duration_seconds",
    "Duration of Orbyntiq LLM operations in seconds.",
    ("provider", "model", "operation", "status"),
    buckets=(
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        30.0,
        60.0,
        120.0,
    ),
)

LLM_REQUESTS_IN_PROGRESS = Gauge(
    "orbyntiq_llm_requests_in_progress",
    "Number of Orbyntiq LLM operations currently running.",
    ("provider", "model", "operation"),
)

LLM_TOKENS_TOTAL = Counter(
    "orbyntiq_llm_tokens_total",
    "Total number of tokens reported by LLM providers.",
    ("provider", "model", "token_type"),
)

LLM_STREAMS_TOTAL = Counter(
    "orbyntiq_llm_streams_total",
    "Total number of Orbyntiq LLM streams.",
    ("provider", "model", "status"),
)

LLM_STREAM_CHUNKS_TOTAL = Counter(
    "orbyntiq_llm_stream_chunks_total",
    "Total number of chunks emitted by Orbyntiq LLM streams.",
    ("provider", "model"),
)

LLM_STREAM_DURATION_SECONDS = Histogram(
    "orbyntiq_llm_stream_duration_seconds",
    "Duration of Orbyntiq LLM streams in seconds.",
    ("provider", "model", "status"),
    buckets=(
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        30.0,
        60.0,
        120.0,
    ),
)


MODEL_LABEL_PATTERN = re.compile(
    r"^[A-Za-z0-9._:/-]{1,128}$"
)


def get_llm_metric_labels(
    provider: object,
) -> tuple[str, str]:
    """Return bounded provider/model labels."""

    provider_name = (
        "ollama"
        if provider.__class__.__name__ == "OllamaProvider"
        else "other"
    )

    model = getattr(
        provider,
        "model",
        None,
    )

    if (
        not isinstance(model, str)
        or not MODEL_LABEL_PATTERN.fullmatch(model)
    ):
        model = "unknown"

    return provider_name, model


def record_llm_tokens(
    *,
    provider: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> None:
    """Record provider-reported token usage when available."""

    if (
        isinstance(prompt_tokens, int)
        and prompt_tokens >= 0
    ):
        LLM_TOKENS_TOTAL.labels(
            provider=provider,
            model=model,
            token_type="prompt",
        ).inc(prompt_tokens)

    if (
        isinstance(completion_tokens, int)
        and completion_tokens >= 0
    ):
        LLM_TOKENS_TOTAL.labels(
            provider=provider,
            model=model,
            token_type="completion",
        ).inc(completion_tokens)
