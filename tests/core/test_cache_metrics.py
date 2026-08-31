from orbyntiq.core.cache_metrics import CacheMetrics


def test_initial_metrics_are_zero() -> None:
    metrics = CacheMetrics()

    assert metrics.hits == 0
    assert metrics.misses == 0
    assert metrics.total == 0
    assert metrics.hit_rate == 0.0


def test_record_hit() -> None:
    metrics = CacheMetrics()

    metrics.record_hit()

    assert metrics.hits == 1
    assert metrics.misses == 0
    assert metrics.total == 1
    assert metrics.hit_rate == 1.0


def test_record_miss() -> None:
    metrics = CacheMetrics()

    metrics.record_miss()

    assert metrics.hits == 0
    assert metrics.misses == 1
    assert metrics.total == 1
    assert metrics.hit_rate == 0.0


def test_hit_rate() -> None:
    metrics = CacheMetrics()

    metrics.record_hit()
    metrics.record_hit()
    metrics.record_miss()

    assert metrics.hits == 2
    assert metrics.misses == 1
    assert metrics.total == 3
    assert metrics.hit_rate == 2 / 3
