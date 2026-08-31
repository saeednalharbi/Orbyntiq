import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orbyntiq.core.redis_keys import RedisKeyBuilder
from orbyntiq.services.cache import RedisCache


def create_cache(
    client: MagicMock,
    ttl_seconds: int = 300,
) -> RedisCache:
    return RedisCache(
        client=client,
        key_builder=RedisKeyBuilder(environment="testing"),
        default_ttl_seconds=ttl_seconds,
    )


def test_set_uses_default_ttl() -> None:
    client = MagicMock()
    client.set = AsyncMock(return_value=True)

    cache = create_cache(client, ttl_seconds=300)

    asyncio.run(
        cache.set(
            "llm",
            "request-123",
            "cached-response",
        )
    )

    client.set.assert_awaited_once_with(
        "orbyntiq:testing:cache:llm:request-123",
        "cached-response",
        ex=300,
    )


def test_set_supports_custom_ttl() -> None:
    client = MagicMock()
    client.set = AsyncMock(return_value=True)

    cache = create_cache(client)

    asyncio.run(
        cache.set(
            "llm",
            "request-123",
            "cached-response",
            ttl_seconds=60,
        )
    )

    client.set.assert_awaited_once_with(
        "orbyntiq:testing:cache:llm:request-123",
        "cached-response",
        ex=60,
    )


def test_get_existing_value() -> None:
    client = MagicMock()
    client.get = AsyncMock(return_value="cached-response")

    cache = create_cache(client)

    result = asyncio.run(
        cache.get(
            "llm",
            "request-123",
        )
    )

    assert result == "cached-response"


def test_get_missing_value_returns_none() -> None:
    client = MagicMock()
    client.get = AsyncMock(return_value=None)

    cache = create_cache(client)

    result = asyncio.run(
        cache.get(
            "llm",
            "missing",
        )
    )

    assert result is None


def test_delete_existing_value() -> None:
    client = MagicMock()
    client.delete = AsyncMock(return_value=1)

    cache = create_cache(client)

    deleted = asyncio.run(
        cache.delete(
            "llm",
            "request-123",
        )
    )

    assert deleted is True


def test_delete_missing_value_returns_false() -> None:
    client = MagicMock()
    client.delete = AsyncMock(return_value=0)

    cache = create_cache(client)

    deleted = asyncio.run(
        cache.delete(
            "llm",
            "missing",
        )
    )

    assert deleted is False


def test_exists_returns_true_for_existing_key() -> None:
    client = MagicMock()
    client.exists = AsyncMock(return_value=1)

    cache = create_cache(client)

    exists = asyncio.run(
        cache.exists(
            "llm",
            "request-123",
        )
    )

    assert exists is True


def test_exists_returns_false_for_missing_key() -> None:
    client = MagicMock()
    client.exists = AsyncMock(return_value=0)

    cache = create_cache(client)

    exists = asyncio.run(
        cache.exists(
            "llm",
            "missing",
        )
    )

    assert exists is False


def test_invalid_default_ttl_is_rejected() -> None:
    client = MagicMock()

    with pytest.raises(
        ValueError,
        match="default_ttl_seconds must be greater than zero",
    ):
        create_cache(client, ttl_seconds=0)


@pytest.mark.parametrize("ttl_seconds", [0, -1])
def test_invalid_custom_ttl_is_rejected(
    ttl_seconds: int,
) -> None:
    client = MagicMock()
    client.set = AsyncMock(return_value=True)

    cache = create_cache(client)

    with pytest.raises(
        ValueError,
        match="ttl_seconds must be greater than zero",
    ):
        asyncio.run(
            cache.set(
                "llm",
                "request-123",
                "cached-response",
                ttl_seconds=ttl_seconds,
            )
        )


def test_cache_records_hit() -> None:
    from orbyntiq.core.cache_metrics import CacheMetrics

    client = MagicMock()
    client.get = AsyncMock(return_value="cached-response")
    metrics = CacheMetrics()

    cache = RedisCache(
        client=client,
        key_builder=RedisKeyBuilder(environment="testing"),
        default_ttl_seconds=300,
        metrics=metrics,
    )

    result = asyncio.run(
        cache.get(
            "llm",
            "request-123",
        )
    )

    assert result == "cached-response"
    assert metrics.hits == 1
    assert metrics.misses == 0


def test_cache_records_miss() -> None:
    from orbyntiq.core.cache_metrics import CacheMetrics

    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    metrics = CacheMetrics()

    cache = RedisCache(
        client=client,
        key_builder=RedisKeyBuilder(environment="testing"),
        default_ttl_seconds=300,
        metrics=metrics,
    )

    result = asyncio.run(
        cache.get(
            "llm",
            "missing",
        )
    )

    assert result is None
    assert metrics.hits == 0
    assert metrics.misses == 1
