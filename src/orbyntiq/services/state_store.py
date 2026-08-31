from collections.abc import Mapping

from redis.asyncio import Redis

from orbyntiq.core.config import Settings
from orbyntiq.core.redis_keys import RedisKeyBuilder
from orbyntiq.core.redis_ttl import create_redis_ttl_policy


class _RedisHashStateStore:
    def __init__(
        self,
        client: Redis,
        ttl_seconds: int,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")

        self._client = client
        self._ttl_seconds = ttl_seconds

    async def _save(
        self,
        key: str,
        data: Mapping[str, str],
    ) -> None:
        if not data:
            raise ValueError("state data cannot be empty")

        async with self._client.pipeline(transaction=True) as pipeline:
            pipeline.delete(key)
            pipeline.hset(key, mapping=dict(data))
            pipeline.expire(key, self._ttl_seconds)
            await pipeline.execute()

    async def _get(self, key: str) -> dict[str, str] | None:
        data = await self._client.hgetall(key)

        if not data:
            return None

        return dict(data)

    async def _delete(self, key: str) -> bool:
        deleted = await self._client.delete(key)
        return bool(deleted)

    async def _touch(self, key: str) -> bool:
        refreshed = await self._client.expire(
            key,
            self._ttl_seconds,
        )
        return bool(refreshed)


class RedisConversationStateStore(_RedisHashStateStore):
    def __init__(
        self,
        client: Redis,
        key_builder: RedisKeyBuilder,
        ttl_seconds: int,
    ) -> None:
        super().__init__(client, ttl_seconds)
        self._key_builder = key_builder

    async def save(
        self,
        conversation_id: str,
        data: Mapping[str, str],
    ) -> None:
        await self._save(
            self._key_builder.conversation(conversation_id),
            data,
        )

    async def get(
        self,
        conversation_id: str,
    ) -> dict[str, str] | None:
        return await self._get(
            self._key_builder.conversation(conversation_id)
        )

    async def delete(self, conversation_id: str) -> bool:
        return await self._delete(
            self._key_builder.conversation(conversation_id)
        )

    async def touch(self, conversation_id: str) -> bool:
        return await self._touch(
            self._key_builder.conversation(conversation_id)
        )


class RedisAgentStateStore(_RedisHashStateStore):
    def __init__(
        self,
        client: Redis,
        key_builder: RedisKeyBuilder,
        ttl_seconds: int,
    ) -> None:
        super().__init__(client, ttl_seconds)
        self._key_builder = key_builder

    async def save(
        self,
        agent_name: str,
        session_id: str,
        data: Mapping[str, str],
    ) -> None:
        await self._save(
            self._key_builder.agent(agent_name, session_id),
            data,
        )

    async def get(
        self,
        agent_name: str,
        session_id: str,
    ) -> dict[str, str] | None:
        return await self._get(
            self._key_builder.agent(agent_name, session_id)
        )

    async def delete(
        self,
        agent_name: str,
        session_id: str,
    ) -> bool:
        return await self._delete(
            self._key_builder.agent(agent_name, session_id)
        )

    async def touch(
        self,
        agent_name: str,
        session_id: str,
    ) -> bool:
        return await self._touch(
            self._key_builder.agent(agent_name, session_id)
        )


def create_conversation_state_store(
    client: Redis,
    settings: Settings,
) -> RedisConversationStateStore:
    keys = RedisKeyBuilder(environment=settings.environment)
    ttl = create_redis_ttl_policy(settings)

    return RedisConversationStateStore(
        client=client,
        key_builder=keys,
        ttl_seconds=ttl.conversation,
    )


def create_agent_state_store(
    client: Redis,
    settings: Settings,
) -> RedisAgentStateStore:
    keys = RedisKeyBuilder(environment=settings.environment)
    ttl = create_redis_ttl_policy(settings)

    return RedisAgentStateStore(
        client=client,
        key_builder=keys,
        ttl_seconds=ttl.agent_state,
    )
