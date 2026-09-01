from urllib.parse import urlparse

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.sampling import (
    ParentBased,
    TraceIdRatioBased,
)
from opentelemetry.trace import Tracer

from orbyntiq.core.config import Settings

_tracer_provider: TracerProvider | None = None


def normalize_otlp_endpoint(
    endpoint: str,
) -> str:
    """Validate and normalize an OTLP collector endpoint."""

    normalized = endpoint.strip().rstrip("/")

    parsed = urlparse(normalized)

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise ValueError(
            "OTLP endpoint must use http or https"
        )

    if not parsed.hostname:
        raise ValueError(
            "OTLP endpoint must contain a hostname"
        )

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(
            "OTLP endpoint contains an invalid port"
        ) from exc

    if port is None:
        raise ValueError(
            "OTLP endpoint must contain a port"
        )

    return normalized


def create_otlp_span_exporter(
    settings: Settings,
) -> OTLPSpanExporter:
    """Create the configured OTLP/gRPC span exporter."""

    endpoint = normalize_otlp_endpoint(
        settings.otel_exporter_otlp_endpoint
    )

    return OTLPSpanExporter(
        endpoint=endpoint,
        insecure=settings.otel_exporter_otlp_insecure,
        timeout=settings.otel_export_timeout_seconds,
    )


def create_tracer_provider(
    settings: Settings,
    *,
    span_exporter: SpanExporter | None = None,
) -> TracerProvider:
    """Create the Orbyntiq OpenTelemetry tracer provider."""

    sample_ratio = settings.otel_trace_sample_ratio

    if not 0.0 <= sample_ratio <= 1.0:
        raise ValueError(
            "otel_trace_sample_ratio must be between 0.0 and 1.0"
        )

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment.name": settings.environment,
        }
    )

    sampler = ParentBased(
        TraceIdRatioBased(
            sample_ratio
        )
    )

    provider = TracerProvider(
        resource=resource,
        sampler=sampler,
    )

    if settings.otel_exporter_enabled:
        exporter = (
            span_exporter
            if span_exporter is not None
            else create_otlp_span_exporter(
                settings
            )
        )

        provider.add_span_processor(
            BatchSpanProcessor(
                exporter
            )
        )

    return provider


def configure_tracing(
    settings: Settings,
) -> TracerProvider | None:
    """Configure the process-level Orbyntiq tracing provider."""

    global _tracer_provider

    if not settings.observability_enabled:
        return None

    if not settings.tracing_enabled:
        return None

    if _tracer_provider is None:
        _tracer_provider = (
            create_tracer_provider(
                settings
            )
        )

    return _tracer_provider


def get_tracer(name: str) -> Tracer:
    """Return a tracer using the configured Orbyntiq provider."""

    if _tracer_provider is None:
        return trace.get_tracer(
            name
        )

    return _tracer_provider.get_tracer(
        name
    )
