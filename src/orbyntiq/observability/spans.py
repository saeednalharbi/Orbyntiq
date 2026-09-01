import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from opentelemetry.trace import (
    Span,
    SpanKind,
    Status,
    StatusCode,
)

from orbyntiq.observability.tracing import get_tracer

SAFE_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9._:/-]{1,128}$"
)


def bounded_name(
    value: object,
    *,
    default: str = "unknown",
) -> str:
    """Return a bounded safe span attribute value."""

    if (
        isinstance(value, str)
        and SAFE_NAME_PATTERN.fullmatch(value)
    ):
        return value

    return default


def mark_span_error(
    span: Span,
    error_type: str,
) -> None:
    """Mark a recording span as failed without adding sensitive data."""

    if not span.is_recording():
        return

    span.set_status(
        Status(
            StatusCode.ERROR
        )
    )

    span.set_attribute(
        "error.type",
        bounded_name(
            error_type,
            default="Error",
        ),
    )


@contextmanager
def traced_span(
    name: str,
    *,
    tracer_name: str,
    attributes: Mapping[str, object] | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
) -> Iterator[Span]:
    """Create a safe Orbyntiq span and record uncaught errors."""

    tracer = get_tracer(tracer_name)

    safe_attributes = {
        key: value
        for key, value in (
            attributes or {}
        ).items()
        if isinstance(
            value,
            (str, bool, int, float),
        )
    }

    with tracer.start_as_current_span(
        name,
        kind=kind,
        attributes=safe_attributes,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        try:
            yield span

        except Exception as exc:
            if span.is_recording():
                span.record_exception(exc)

            mark_span_error(
                span,
                type(exc).__name__,
            )

            raise
