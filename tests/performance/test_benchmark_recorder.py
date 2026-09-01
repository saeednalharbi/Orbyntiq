import csv

from scripts.run_phase11_benchmark import (
    load_locust_summary,
    parse_redis_info,
    redis_delta,
    safe_label,
    summarize_samples,
)


def test_safe_label_normalizes_text() -> None:
    assert safe_label("Health Baseline 01!") == ("health-baseline-01")


def test_parse_redis_info_converts_numbers() -> None:
    result = parse_redis_info(
        """
        # Stats
        keyspace_hits:12
        keyspace_misses:3
        instantaneous_ops_per_sec:1.5
        """
    )

    assert result["keyspace_hits"] == 12
    assert result["keyspace_misses"] == 3
    assert result["instantaneous_ops_per_sec"] == 1.5


def test_redis_delta_calculates_hit_rate() -> None:
    result = redis_delta(
        {
            "keyspace_hits": 10,
            "keyspace_misses": 5,
        },
        {
            "keyspace_hits": 16,
            "keyspace_misses": 7,
        },
    )

    assert result == {
        "hits": 6,
        "misses": 2,
        "hit_rate": 0.75,
    }


def test_summarize_samples_records_limits() -> None:
    result = summarize_samples(
        [
            {
                "host_cpu_percent": 20.0,
                "host_available_memory_bytes": 3_000,
                "api_healthy": True,
            },
            {
                "host_cpu_percent": 80.0,
                "host_available_memory_bytes": 2_000,
                "api_healthy": False,
            },
        ]
    )

    assert result["host_cpu_average_percent"] == 50.0
    assert result["host_cpu_maximum_percent"] == 80.0
    assert result["host_available_memory_minimum_bytes"] == 2_000
    assert result["api_health_failures"] == 1


def test_load_locust_summary_reads_aggregated_row(
    tmp_path,
) -> None:
    csv_path = tmp_path / "stats.csv"

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "Name",
                "Request Count",
                "Failure Count",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "Name": "GET /health",
                "Request Count": "10",
                "Failure Count": "0",
            }
        )
        writer.writerow(
            {
                "Name": "Aggregated",
                "Request Count": "10",
                "Failure Count": "0",
            }
        )

    result = load_locust_summary(csv_path)

    assert result["Name"] == "Aggregated"
    assert result["Request Count"] == "10"
