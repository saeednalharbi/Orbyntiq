from __future__ import annotations

import argparse
import csv
import json
import platform
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
API_HEALTH_URL = "http://127.0.0.1:8000/health"
LLM_CHAT_URL = "http://127.0.0.1:8000/api/v1/llm/chat"


def utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def safe_label(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value)
    return normalized.strip("-").lower()


def run_command(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    return completed.stdout.strip()


def parse_redis_info(raw_info: str) -> dict[str, int | float | str]:
    result: dict[str, int | float | str] = {}

    for line in raw_info.splitlines():
        line = line.strip()

        if not line or line.startswith("#") or ":" not in line:
            continue

        key, raw_value = line.split(":", maxsplit=1)
        raw_value = raw_value.strip()

        try:
            result[key] = int(raw_value)
            continue
        except ValueError:
            pass

        try:
            result[key] = float(raw_value)
            continue
        except ValueError:
            result[key] = raw_value

    return result


def redis_stats() -> dict[str, int | float | str]:
    raw_info = run_command(
        [
            "docker",
            "exec",
            "orbyntiq-redis",
            "redis-cli",
            "INFO",
            "stats",
        ]
    )

    return parse_redis_info(raw_info)


def redis_delta(
    before: dict[str, int | float | str],
    after: dict[str, int | float | str],
) -> dict[str, int | float | None]:
    before_hits = int(before.get("keyspace_hits", 0))
    after_hits = int(after.get("keyspace_hits", 0))
    before_misses = int(before.get("keyspace_misses", 0))
    after_misses = int(after.get("keyspace_misses", 0))

    hits = max(0, after_hits - before_hits)
    misses = max(0, after_misses - before_misses)
    total = hits + misses

    return {
        "hits": hits,
        "misses": misses,
        "hit_rate": hits / total if total else None,
    }


def api_is_healthy() -> bool:
    try:
        with urllib.request.urlopen(
            API_HEALTH_URL,
            timeout=3,
        ) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def warm_model() -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []

    for attempt_number in range(1, 3):
        started_at = time.perf_counter()
        body = json.dumps(
            {"prompt": ("Reply with exactly ORBYNTIQ_BENCHMARK_WARM and no additional text.")}
        ).encode()

        request = urllib.request.Request(
            LLM_CHAT_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=180,
            ) as response:
                payload = json.loads(response.read())

            attempts.append(
                {
                    "attempt": attempt_number,
                    "success": True,
                    "duration_seconds": (time.perf_counter() - started_at),
                    "content": payload.get("content"),
                }
            )
            break
        except (
            OSError,
            urllib.error.URLError,
            urllib.error.HTTPError,
        ) as exc:
            attempts.append(
                {
                    "attempt": attempt_number,
                    "success": False,
                    "duration_seconds": (time.perf_counter() - started_at),
                    "error": str(exc),
                }
            )

    return attempts


def docker_stats() -> list[dict[str, Any]]:
    raw_stats = run_command(
        [
            "docker",
            "stats",
            "--no-stream",
            "--format",
            "{{json .}}",
        ]
    )

    parsed: list[dict[str, Any]] = []

    for line in raw_stats.splitlines():
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return parsed


def collect_sample() -> dict[str, Any]:
    memory = psutil.virtual_memory()

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "host_cpu_percent": psutil.cpu_percent(interval=1.0),
        "host_memory_percent": memory.percent,
        "host_available_memory_bytes": memory.available,
        "api_healthy": api_is_healthy(),
        "containers": docker_stats(),
    }


def summarize_samples(
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    if not samples:
        return {}

    cpu_values = [float(sample["host_cpu_percent"]) for sample in samples]
    available_values = [int(sample["host_available_memory_bytes"]) for sample in samples]

    return {
        "sample_count": len(samples),
        "host_cpu_average_percent": (sum(cpu_values) / len(cpu_values)),
        "host_cpu_maximum_percent": max(cpu_values),
        "host_available_memory_minimum_bytes": min(available_values),
        "api_health_failures": sum(not bool(sample["api_healthy"]) for sample in samples),
    }


def load_locust_summary(
    csv_path: Path,
) -> dict[str, str]:
    if not csv_path.exists():
        return {}

    with csv_path.open(
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    for row in reversed(rows):
        if row.get("Name") == "Aggregated":
            return dict(row)

    return dict(rows[-1]) if rows else {}


def system_configuration() -> dict[str, Any]:
    memory = psutil.virtual_memory()

    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python": sys.version,
        "physical_cpu_cores": psutil.cpu_count(logical=False),
        "logical_cpu_cores": psutil.cpu_count(logical=True),
        "total_memory_bytes": memory.total,
        "available_memory_bytes": memory.available,
        "docker_engine": run_command(
            [
                "docker",
                "version",
                "--format",
                "{{.Server.Version}}",
            ]
        ),
        "docker_compose": run_command(["docker", "compose", "version", "--short"]),
        "ollama_process": run_command(["ollama", "ps"]),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run and record an Orbyntiq Phase 11 benchmark.")
    parser.add_argument("--user-class", required=True)
    parser.add_argument("--users", type=int, required=True)
    parser.add_argument("--spawn-rate", type=float, required=True)
    parser.add_argument("--run-time", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument(
        "--minimum-memory-gb",
        type=float,
        default=1.5,
    )
    parser.add_argument(
        "--warm-model",
        action="store_true",
    )
    parser.add_argument(
        "--result-root",
        type=Path,
        default=Path("docs/load-testing/results"),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    if arguments.users < 1:
        raise ValueError("--users must be at least one")

    label = safe_label(arguments.label)

    if not label:
        raise ValueError("--label must contain a safe character")

    result_directory = REPOSITORY_ROOT / arguments.result_root / f"{utc_timestamp()}-{label}"
    result_directory.mkdir(parents=True, exist_ok=False)

    configuration = system_configuration()
    minimum_memory_bytes = int(arguments.minimum_memory_gb * 1024**3)

    if configuration["available_memory_bytes"] < minimum_memory_bytes:
        raise RuntimeError("Available memory is below the configured safety limit")

    if not api_is_healthy():
        raise RuntimeError("Orbyntiq API is not healthy")

    warmup_attempts = warm_model() if arguments.warm_model else []

    if arguments.warm_model and not any(attempt["success"] for attempt in warmup_attempts):
        raise RuntimeError("Model warm-up failed")

    redis_before = redis_stats()
    locust_prefix = result_directory / "locust"
    locust_log = result_directory / "locust.log"

    command = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        "load_tests/locustfile.py",
        arguments.user_class,
        "--headless",
        "--users",
        str(arguments.users),
        "--spawn-rate",
        str(arguments.spawn_rate),
        "--run-time",
        arguments.run_time,
        "--stop-timeout",
        "180",
        "--only-summary",
        "--exit-code-on-error",
        "1",
        "--csv",
        str(locust_prefix),
        "--csv-full-history",
        "--html",
        str(result_directory / "report.html"),
    ]

    samples: list[dict[str, Any]] = []
    aborted_reason: str | None = None

    with locust_log.open(
        "w",
        encoding="utf-8",
    ) as log_file:
        process = subprocess.Popen(
            command,
            cwd=REPOSITORY_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

        while process.poll() is None:
            sample = collect_sample()
            samples.append(sample)

            if sample["host_available_memory_bytes"] < minimum_memory_bytes:
                aborted_reason = "Available memory fell below the safety limit"
                process.terminate()
                break

        try:
            exit_code = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            exit_code = process.wait()

    redis_after = redis_stats()
    locust_stats = load_locust_summary(Path(f"{locust_prefix}_stats.csv"))

    summary = {
        "label": arguments.label,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "configuration": configuration,
        "workload": {
            "user_class": arguments.user_class,
            "users": arguments.users,
            "spawn_rate": arguments.spawn_rate,
            "run_time": arguments.run_time,
            "warm_model": arguments.warm_model,
        },
        "warmup_attempts": warmup_attempts,
        "locust_exit_code": exit_code,
        "aborted_reason": aborted_reason,
        "locust": locust_stats,
        "resources": summarize_samples(samples),
        "redis": {
            "before": redis_before,
            "after": redis_after,
            "delta": redis_delta(
                redis_before,
                redis_after,
            ),
        },
    }

    (result_directory / "samples.json").write_text(
        json.dumps(samples, indent=2),
        encoding="utf-8",
    )
    (result_directory / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(locust_log.read_text(encoding="utf-8"))
    print(f"Results: {result_directory}")
    print(json.dumps(summary, indent=2))

    if aborted_reason is not None or exit_code != 0:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
