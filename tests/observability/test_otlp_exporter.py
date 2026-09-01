from pathlib import Path

import pytest
from opentelemetry.sdk.trace.export import (
    SpanExporter,
    SpanExportResult,
)

import orbyntiq.observability.tracing as tracing_module
from orbyntiq.core.config import Settings
from orbyntiq.observability.tracing import (
    create_otlp_span_exporter,
    create_tracer_provider,
    normalize_otlp_endpoint,
)

PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)


class CapturingExporter(
    SpanExporter
):
    def __init__(self) -> None:
        self.spans = []

    def export(
        self,
        spans,
    ) -> SpanExportResult:
        self.spans.extend(
            spans
        )

        return (
            SpanExportResult.SUCCESS
        )

    def shutdown(self) -> None:
        return None


def test_otlp_exporter_uses_configured_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    sentinel = object()

    def fake_exporter(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return sentinel

    monkeypatch.setattr(
        tracing_module,
        "OTLPSpanExporter",
        fake_exporter,
    )

    settings = Settings(
        _env_file=None,
        otel_exporter_otlp_endpoint=(
            "http://collector:4317"
        ),
        otel_exporter_otlp_insecure=True,
        otel_export_timeout_seconds=7.5,
    )

    exporter = (
        create_otlp_span_exporter(
            settings
        )
    )

    assert exporter is sentinel

    assert captured == {
        "endpoint": (
            "http://collector:4317"
        ),
        "insecure": True,
        "timeout": 7.5,
    }


def test_exporter_enabled_adds_batch_processor() -> None:
    exporter = CapturingExporter()

    provider = create_tracer_provider(
        Settings(
            _env_file=None,
            otel_exporter_enabled=True,
        ),
        span_exporter=exporter,
    )

    tracer = provider.get_tracer(
        "orbyntiq.test"
    )

    with tracer.start_as_current_span(
        "otlp-test-span"
    ):
        pass

    assert provider.force_flush()

    assert [
        span.name
        for span in exporter.spans
    ] == [
        "otlp-test-span"
    ]

    provider.shutdown()


def test_exporter_disabled_skips_export() -> None:
    exporter = CapturingExporter()

    provider = create_tracer_provider(
        Settings(
            _env_file=None,
            otel_exporter_enabled=False,
        ),
        span_exporter=exporter,
    )

    tracer = provider.get_tracer(
        "orbyntiq.test"
    )

    with tracer.start_as_current_span(
        "disabled-export-span"
    ):
        pass

    assert provider.force_flush()

    assert exporter.spans == []

    provider.shutdown()


def test_invalid_otlp_endpoint_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="http or https",
    ):
        normalize_otlp_endpoint(
            "collector:4317"
        )

    with pytest.raises(
        ValueError,
        match="port",
    ):
        normalize_otlp_endpoint(
            "http://collector"
        )


def test_collector_and_compose_configuration() -> None:
    collector = (
        PROJECT_ROOT
        / "infra"
        / "otel"
        / "collector-config.yaml"
    ).read_text(
        encoding="utf-8"
    )

    compose = (
        PROJECT_ROOT
        / "compose.yaml"
    ).read_text(
        encoding="utf-8"
    )

    expected_collector_values = (
        "grpc:",
        "0.0.0.0:4317",
        "http:",
        "0.0.0.0:4318",
        "memory_limiter:",
        "batch:",
        "debug:",
        "health_check:",
        "0.0.0.0:13133",
        "traces:",
    )

    for value in expected_collector_values:
        assert value in collector

    expected_compose_values = (
        (
            "otel/opentelemetry-"
            "collector-contrib:0.159.0"
        ),
        "127.0.0.1:4317:4317",
        "127.0.0.1:4318:4318",
        "127.0.0.1:13133:13133",
        (
            "http://"
            "otel-collector:4317"
        ),
    )

    for value in expected_compose_values:
        assert value in compose



def test_default_otlp_endpoint_is_plain_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "ORBYNTIQ_OTEL_EXPORTER_OTLP_ENDPOINT",
        raising=False,
    )

    settings = Settings(
        _env_file=None
    )

    assert (
        settings.otel_exporter_otlp_endpoint
        == "http://localhost:4317"
    )

    assert "[" not in (
        settings.otel_exporter_otlp_endpoint
    )

    assert "](" not in (
        settings.otel_exporter_otlp_endpoint
    )
