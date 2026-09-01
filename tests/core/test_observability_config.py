from orbyntiq.core.config import Settings


def test_observability_defaults() -> None:
    settings = Settings()

    assert settings.observability_enabled is True
    assert settings.metrics_enabled is True
    assert settings.tracing_enabled is True

    assert settings.otel_service_name == "orbyntiq-api"
    assert settings.otel_exporter_otlp_endpoint == "http://localhost:4317"
    assert settings.otel_trace_sample_ratio == 1.0

    assert settings.metrics_path == "/metrics"


def test_observability_environment_overrides(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "ORBYNTIQ_OBSERVABILITY_ENABLED",
        "false",
    )
    monkeypatch.setenv(
        "ORBYNTIQ_METRICS_ENABLED",
        "false",
    )
    monkeypatch.setenv(
        "ORBYNTIQ_TRACING_ENABLED",
        "false",
    )
    monkeypatch.setenv(
        "ORBYNTIQ_OTEL_SERVICE_NAME",
        "orbyntiq-test",
    )
    monkeypatch.setenv(
        "ORBYNTIQ_OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://collector:4317",
    )
    monkeypatch.setenv(
        "ORBYNTIQ_OTEL_TRACE_SAMPLE_RATIO",
        "0.25",
    )
    monkeypatch.setenv(
        "ORBYNTIQ_METRICS_PATH",
        "/internal/metrics",
    )

    settings = Settings()

    assert settings.observability_enabled is False
    assert settings.metrics_enabled is False
    assert settings.tracing_enabled is False

    assert settings.otel_service_name == "orbyntiq-test"
    assert (
        settings.otel_exporter_otlp_endpoint
        == "http://collector:4317"
    )
    assert settings.otel_trace_sample_ratio == 0.25

    assert settings.metrics_path == "/internal/metrics"
