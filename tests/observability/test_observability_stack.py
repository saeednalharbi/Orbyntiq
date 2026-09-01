import json
from pathlib import Path

PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)


def read(path: str) -> str:
    return (
        PROJECT_ROOT
        / path
    ).read_text(
        encoding="utf-8"
    )


def test_prometheus_scrapes_orbyntiq_metrics() -> None:
    config = read(
        "infra/prometheus/prometheus.yml"
    )

    assert (
        "job_name: orbyntiq-api"
        in config
    )

    assert (
        "metrics_path: /metrics"
        in config
    )

    assert "api:8000" in config


def test_tempo_uses_local_trace_storage() -> None:
    config = read(
        "infra/tempo/tempo.yaml"
    )

    assert "http_listen_port: 3200" in config
    assert "backend: local" in config
    assert "/var/tempo/wal" in config
    assert "/var/tempo/blocks" in config
    assert "0.0.0.0:4317" in config


def test_collector_exports_traces_to_tempo() -> None:
    config = read(
        "infra/otel/collector-config.yaml"
    )

    assert "otlp/tempo:" in config
    assert "endpoint: tempo:4317" in config
    assert "- otlp/tempo" in config


def test_grafana_provisions_data_sources_and_dashboard() -> None:
    datasources = read(
        "infra/grafana/provisioning/"
        "datasources/datasources.yaml"
    )

    assert "uid: prometheus" in datasources
    assert (
        "url: http://prometheus:9090"
        in datasources
    )

    assert "uid: tempo" in datasources
    assert (
        "url: http://tempo:3200"
        in datasources
    )

    dashboard = json.loads(
        read(
            "infra/grafana/dashboards/"
            "orbyntiq-observability.json"
        )
    )

    assert (
        dashboard["uid"]
        == "orbyntiq-observability"
    )

    expressions = [
        target["expr"]
        for panel in dashboard["panels"]
        for target in panel.get(
            "targets",
            [],
        )
        if "expr" in target
    ]

    combined = "\n".join(
        expressions
    )

    assert (
        "orbyntiq_http_requests_total"
        in combined
    )

    assert (
        "orbyntiq_llm_requests_total"
        in combined
    )

    assert (
        "orbyntiq_agent_executions_total"
        in combined
    )


def test_compose_contains_observability_stack() -> None:
    compose = read(
        "compose.yaml"
    )

    expected = (
        "grafana/tempo:3.0.3",
        "prom/prometheus:v3.14.0",
        "grafana/grafana:13.2.0",
        "127.0.0.1:3200:3200",
        "127.0.0.1:9090:9090",
        "127.0.0.1:3000:3000",
        "tempo_data:",
        "prometheus_data:",
        "grafana_data:",
    )

    for value in expected:
        assert value in compose
