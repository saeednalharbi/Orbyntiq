import asyncio
from uuid import uuid4

import pytest
from redis.exceptions import RedisError

from orbyntiq.core.config import Settings
from orbyntiq.core.redis import (
    close_redis_client,
    create_redis_client,
)
from orbyntiq.core.redis_keys import RedisKeyBuilder
from orbyntiq.services.cache import create_cache
from orbyntiq.services.session_store import create_session_store
from orbyntiq.services.state_store import (
    create_agent_state_store,
    create_conversation_state_store,
)


def expiration_settings() -> Settings:
    return Settings(
        environment="testing",
        redis_url="redis://localhost:6379/0",
        redis_session_ttl_seconds=2,
        redis_conversation_ttl_seconds=2,
        redis_agent_state_ttl_seconds=2,
        redis_cache_ttl_seconds=2,
    )


async def redis_is_available(settings: Settings) -> bool:
    client = create_redis_client(settings)

    try:
        return bool(await client.ping())
    except (RedisError, OSError):
        return False
    finally:
        await close_redis_client(client)


async def wait_until_expired(
    client,
    keys: list[str],
    timeout_seconds: float = 5.0,
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds

    while loop.time() < deadline:
        remaining = await client.exists(*keys)

        if remaining == 0:
            return

        await asyncio.sleep(0.1)

    raise AssertionError("Redis keys did not expire within expected time")


def test_redis_ttl_expiration_and_cleanup() -> None:
    settings = expiration_settings()

    if not asyncio.run(redis_is_available(settings)):
        pytest.skip("Redis integration server is unavailable")

    async def run_test() -> None:
        client = create_redis_client(settings)
        keys = RedisKeyBuilder(settings.environment)

        session_id = f"ttl-session-{uuid4()}"
        conversation_id = f"ttl-conversation-{uuid4()}"
        agent_session_id = f"ttl-agent-{uuid4()}"
        cache_id = f"ttl-cache-{uuid4()}"
        agent_name = "planner"

        session_key = keys.session(session_id)
        conversation_key = keys.conversation(conversation_id)
        agent_key = keys.agent(agent_name, agent_session_id)
        cache_key = keys.cache("ttl-test", cache_id)

        redis_keys = [
            session_key,
            conversation_key,
            agent_key,
            cache_key,
        ]

        try:
            sessions = create_session_store(client, settings)
            conversations = create_conversation_state_store(
                client,
                settings,
            )
            agents = create_agent_state_store(
                client,
                settings,
            )
            cache = create_cache(client, settings)

            await sessions.save(
                session_id,
                {"status": "active"},
            )

            await conversations.save(
                conversation_id,
                {"topic": "ttl"},
            )

            await agents.save(
                agent_name,
                agent_session_id,
                {"step": "working"},
            )

            await cache.set(
                "ttl-test",
                cache_id,
                "cached-value",
            )

            for key in redis_keys:
                assert await client.exists(key) == 1

                ttl = await client.ttl(key)

                assert 0 <= ttl <= 2

            await wait_until_expired(
                client,
                redis_keys,
            )

            assert await sessions.get(session_id) is None

            assert await conversations.get(
                conversation_id
            ) is None

            assert await agents.get(
                agent_name,
                agent_session_id,
            ) is None

            assert await cache.get(
                "ttl-test",
                cache_id,
            ) is None

            for key in redis_keys:
                assert await client.exists(key) == 0

        finally:
            if redis_keys:
                await client.delete(*redis_keys)

            await close_redis_client(client)

    asyncio.run(run_test())
