import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orbyntiq.core.redis_keys import RedisKeyBuilder
from orbyntiq.services.session_store import RedisSessionStore


def create_store(
    client: MagicMock,
    ttl_seconds: int = 300,
) -> RedisSessionStore:
    return RedisSessionStore(
        client=client,
        key_builder=RedisKeyBuilder(environment="testing"),
        ttl_seconds=ttl_seconds,
    )


def test_save_session_uses_hash_and_ttl() -> None:
    client = MagicMock()
    pipeline = MagicMock()

    client.pipeline.return_value = pipeline

    pipeline.__aenter__ = AsyncMock(return_value=pipeline)
    pipeline.__aexit__ = AsyncMock(return_value=False)
    pipeline.delete.return_value = pipeline
    pipeline.hset.return_value = pipeline
    pipeline.expire.return_value = pipeline
    pipeline.execute = AsyncMock(return_value=[1, 1, True])

    store = create_store(client, ttl_seconds=600)

    asyncio.run(
        store.save(
            "session-123",
            {
                "user_id": "user-1",
                "status": "active",
            },
        )
    )

    key = "orbyntiq:testing:session:session-123"

    client.pipeline.assert_called_once_with(transaction=True)
    pipeline.delete.assert_called_once_with(key)
    pipeline.hset.assert_called_once_with(
        key,
        mapping={
            "user_id": "user-1",
            "status": "active",
        },
    )
    pipeline.expire.assert_called_once_with(key, 600)
    pipeline.execute.assert_awaited_once()


def test_get_existing_session() -> None:
    client = MagicMock()
    client.hgetall = AsyncMock(
        return_value={
            "user_id": "user-1",
            "status": "active",
        }
    )

    store = create_store(client)

    result = asyncio.run(store.get("session-123"))

    assert result == {
        "user_id": "user-1",
        "status": "active",
    }

    client.hgetall.assert_awaited_once_with(
        "orbyntiq:testing:session:session-123"
    )


def test_get_missing_session_returns_none() -> None:
    client = MagicMock()
    client.hgetall = AsyncMock(return_value={})

    store = create_store(client)

    result = asyncio.run(store.get("missing"))

    assert result is None


def test_delete_session() -> None:
    client = MagicMock()
    client.delete = AsyncMock(return_value=1)

    store = create_store(client)

    deleted = asyncio.run(store.delete("session-123"))

    assert deleted is True
    client.delete.assert_awaited_once_with(
        "orbyntiq:testing:session:session-123"
    )


def test_delete_missing_session_returns_false() -> None:
    client = MagicMock()
    client.delete = AsyncMock(return_value=0)

    store = create_store(client)

    deleted = asyncio.run(store.delete("missing"))

    assert deleted is False


def test_touch_session_refreshes_ttl() -> None:
    client = MagicMock()
    client.expire = AsyncMock(return_value=True)

    store = create_store(client, ttl_seconds=900)

    refreshed = asyncio.run(store.touch("session-123"))

    assert refreshed is True
    client.expire.assert_awaited_once_with(
        "orbyntiq:testing:session:session-123",
        900,
    )


def test_touch_missing_session_returns_false() -> None:
    client = MagicMock()
    client.expire = AsyncMock(return_value=False)

    store = create_store(client)

    refreshed = asyncio.run(store.touch("missing"))

    assert refreshed is False


def test_empty_session_data_is_rejected() -> None:
    client = MagicMock()
    store = create_store(client)

    with pytest.raises(
        ValueError,
        match="session data cannot be empty",
    ):
        asyncio.run(store.save("session-123", {}))


def test_invalid_ttl_is_rejected() -> None:
    client = MagicMock()

    with pytest.raises(
        ValueError,
        match="ttl_seconds must be greater than zero",
    ):
        create_store(client, ttl_seconds=0)
