import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orbyntiq.core.redis_keys import RedisKeyBuilder
from orbyntiq.services.state_store import (
    RedisAgentStateStore,
    RedisConversationStateStore,
)


def create_conversation_store(
    client: MagicMock,
    ttl_seconds: int = 600,
) -> RedisConversationStateStore:
    return RedisConversationStateStore(
        client=client,
        key_builder=RedisKeyBuilder(environment="testing"),
        ttl_seconds=ttl_seconds,
    )


def create_agent_store(
    client: MagicMock,
    ttl_seconds: int = 300,
) -> RedisAgentStateStore:
    return RedisAgentStateStore(
        client=client,
        key_builder=RedisKeyBuilder(environment="testing"),
        ttl_seconds=ttl_seconds,
    )


def configure_pipeline(client: MagicMock) -> MagicMock:
    pipeline = MagicMock()

    client.pipeline.return_value = pipeline
    pipeline.__aenter__ = AsyncMock(return_value=pipeline)
    pipeline.__aexit__ = AsyncMock(return_value=False)
    pipeline.delete.return_value = pipeline
    pipeline.hset.return_value = pipeline
    pipeline.expire.return_value = pipeline
    pipeline.execute = AsyncMock(return_value=[1, 1, True])

    return pipeline


def test_save_conversation_state() -> None:
    client = MagicMock()
    pipeline = configure_pipeline(client)
    store = create_conversation_store(client, ttl_seconds=600)

    asyncio.run(
        store.save(
            "conversation-123",
            {
                "topic": "redis",
                "status": "active",
            },
        )
    )

    key = "orbyntiq:testing:conversation:conversation-123"

    pipeline.delete.assert_called_once_with(key)
    pipeline.hset.assert_called_once_with(
        key,
        mapping={
            "topic": "redis",
            "status": "active",
        },
    )
    pipeline.expire.assert_called_once_with(key, 600)


def test_get_conversation_state() -> None:
    client = MagicMock()
    client.hgetall = AsyncMock(
        return_value={
            "topic": "redis",
            "status": "active",
        }
    )

    store = create_conversation_store(client)

    result = asyncio.run(store.get("conversation-123"))

    assert result == {
        "topic": "redis",
        "status": "active",
    }


def test_missing_conversation_returns_none() -> None:
    client = MagicMock()
    client.hgetall = AsyncMock(return_value={})

    store = create_conversation_store(client)

    assert asyncio.run(store.get("missing")) is None


def test_delete_and_touch_conversation() -> None:
    client = MagicMock()
    client.delete = AsyncMock(return_value=1)
    client.expire = AsyncMock(return_value=True)

    store = create_conversation_store(client, ttl_seconds=600)

    assert asyncio.run(store.touch("conversation-123")) is True
    assert asyncio.run(store.delete("conversation-123")) is True


def test_save_agent_state() -> None:
    client = MagicMock()
    pipeline = configure_pipeline(client)
    store = create_agent_store(client, ttl_seconds=300)

    asyncio.run(
        store.save(
            "planner",
            "session-123",
            {
                "step": "2",
                "status": "working",
            },
        )
    )

    key = "orbyntiq:testing:agent:planner:session-123"

    pipeline.delete.assert_called_once_with(key)
    pipeline.hset.assert_called_once_with(
        key,
        mapping={
            "step": "2",
            "status": "working",
        },
    )
    pipeline.expire.assert_called_once_with(key, 300)


def test_get_agent_state() -> None:
    client = MagicMock()
    client.hgetall = AsyncMock(
        return_value={
            "step": "2",
            "status": "working",
        }
    )

    store = create_agent_store(client)

    result = asyncio.run(
        store.get(
            "planner",
            "session-123",
        )
    )

    assert result == {
        "step": "2",
        "status": "working",
    }


def test_missing_agent_state_returns_none() -> None:
    client = MagicMock()
    client.hgetall = AsyncMock(return_value={})

    store = create_agent_store(client)

    result = asyncio.run(
        store.get(
            "planner",
            "missing",
        )
    )

    assert result is None


def test_delete_and_touch_agent_state() -> None:
    client = MagicMock()
    client.delete = AsyncMock(return_value=1)
    client.expire = AsyncMock(return_value=True)

    store = create_agent_store(client, ttl_seconds=300)

    assert asyncio.run(
        store.touch(
            "planner",
            "session-123",
        )
    ) is True

    assert asyncio.run(
        store.delete(
            "planner",
            "session-123",
        )
    ) is True


@pytest.mark.parametrize(
    "store_type",
    [
        RedisConversationStateStore,
        RedisAgentStateStore,
    ],
)
def test_invalid_state_ttl_is_rejected(store_type) -> None:
    client = MagicMock()
    keys = RedisKeyBuilder(environment="testing")

    with pytest.raises(
        ValueError,
        match="ttl_seconds must be greater than zero",
    ):
        store_type(
            client=client,
            key_builder=keys,
            ttl_seconds=0,
        )


def test_empty_conversation_state_is_rejected() -> None:
    client = MagicMock()
    store = create_conversation_store(client)

    with pytest.raises(
        ValueError,
        match="state data cannot be empty",
    ):
        asyncio.run(
            store.save(
                "conversation-123",
                {},
            )
        )


def test_empty_agent_state_is_rejected() -> None:
    client = MagicMock()
    store = create_agent_store(client)

    with pytest.raises(
        ValueError,
        match="state data cannot be empty",
    ):
        asyncio.run(
            store.save(
                "planner",
                "session-123",
                {},
            )
        )
