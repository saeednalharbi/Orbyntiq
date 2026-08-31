import asyncio
from uuid import uuid4

import pytest
from redis.exceptions import RedisError

from orbyntiq.core.cache_metrics import CacheMetrics
from orbyntiq.core.config import Settings
from orbyntiq.core.redis import (
    close_redis_client,
    create_redis_client,
)
from orbyntiq.services.cache import create_cache
from orbyntiq.services.session_store import create_session_store
from orbyntiq.services.state_store import (
    create_agent_state_store,
    create_conversation_state_store,
)


async def redis_is_available(settings: Settings) -> bool:
    client = create_redis_client(settings)

    try:
        return bool(await client.ping())
    except (RedisError, OSError):
        return False
    finally:
        await close_redis_client(client)


def integration_settings() -> Settings:
    return Settings(
        environment="testing",
        redis_url="redis://localhost:6379/0",
    )


def test_real_redis_session_round_trip() -> None:
    settings = integration_settings()

    if not asyncio.run(redis_is_available(settings)):
        pytest.skip("Redis integration server is unavailable")

    async def run_test() -> None:
        client = create_redis_client(settings)
        session_id = f"integration-{uuid4()}"

        try:
            store = create_session_store(client, settings)

            await store.save(
                session_id,
                {
                    "user_id": "integration-user",
                    "status": "active",
                },
            )

            result = await store.get(session_id)

            assert result == {
                "user_id": "integration-user",
                "status": "active",
            }

            assert await store.touch(session_id) is True
            assert await store.delete(session_id) is True
            assert await store.get(session_id) is None
        finally:
            await close_redis_client(client)

    asyncio.run(run_test())


def test_real_redis_state_stores_round_trip() -> None:
    settings = integration_settings()

    if not asyncio.run(redis_is_available(settings)):
        pytest.skip("Redis integration server is unavailable")

    async def run_test() -> None:
        client = create_redis_client(settings)

        conversation_id = f"integration-{uuid4()}"
        session_id = f"integration-{uuid4()}"
        agent_name = "planner"

        try:
            conversations = create_conversation_state_store(
                client,
                settings,
            )
            agents = create_agent_state_store(
                client,
                settings,
            )

            await conversations.save(
                conversation_id,
                {
                    "topic": "integration",
                    "status": "active",
                },
            )

            await agents.save(
                agent_name,
                session_id,
                {
                    "step": "planning",
                    "status": "working",
                },
            )

            assert await conversations.get(conversation_id) == {
                "topic": "integration",
                "status": "active",
            }

            assert await agents.get(
                agent_name,
                session_id,
            ) == {
                "step": "planning",
                "status": "working",
            }

            assert await conversations.delete(conversation_id) is True

            assert await agents.delete(
                agent_name,
                session_id,
            ) is True
        finally:
            await close_redis_client(client)

    asyncio.run(run_test())


def test_real_redis_json_cache_and_metrics() -> None:
    settings = integration_settings()

    if not asyncio.run(redis_is_available(settings)):
        pytest.skip("Redis integration server is unavailable")

    async def run_test() -> None:
        client = create_redis_client(settings)
        metrics = CacheMetrics()

        namespace = "integration"
        identifier = str(uuid4())

        value = {
            "agent": "planner",
            "ready": True,
            "step": 3,
            "tools": ["rag", "search"],
        }

        try:
            cache = create_cache(
                client,
                settings,
                metrics=metrics,
            )

            assert await cache.get(namespace, identifier) is None

            await cache.set_json(
                namespace,
                identifier,
                value,
            )

            result = await cache.get_json(
                namespace,
                identifier,
            )

            assert result == value
            assert metrics.misses == 1
            assert metrics.hits == 1
            assert metrics.total == 2
            assert metrics.hit_rate == 0.5

            assert await cache.delete(
                namespace,
                identifier,
            ) is True

            assert await cache.exists(
                namespace,
                identifier,
            ) is False
        finally:
            await close_redis_client(client)

    asyncio.run(run_test())
