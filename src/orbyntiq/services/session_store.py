from collections.abc import Mapping

from redis.asyncio import Redis

from orbyntiq.core.config import Settings
from orbyntiq.core.redis_keys import RedisKeyBuilder
from orbyntiq.core.redis_ttl import create_redis_ttl_policy


class RedisSessionStore:
    def __init__(
        self,
        client: Redis,
        key_builder: RedisKeyBuilder,
        ttl_seconds: int,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")

        self._client = client
        self._key_builder = key_builder
        self._ttl_seconds = ttl_seconds

    async def save(
        self,
        session_id: str,
        data: Mapping[str, str],
    ) -> None:
        if not data:
            raise ValueError("session data cannot be empty")

        key = self._key_builder.session(session_id)

        async with self._client.pipeline(transaction=True) as pipeline:
            pipeline.delete(key)
            pipeline.hset(key, mapping=dict(data))
            pipeline.expire(key, self._ttl_seconds)
            await pipeline.execute()

    async def get(self, session_id: str) -> dict[str, str] | None:
        key = self._key_builder.session(session_id)
        data = await self._client.hgetall(key)

        if not data:
            return None

        return dict(data)

    async def delete(self, session_id: str) -> bool:
        key = self._key_builder.session(session_id)
        deleted = await self._client.delete(key)

        return bool(deleted)

    async def touch(self, session_id: str) -> bool:
        key = self._key_builder.session(session_id)
        refreshed = await self._client.expire(
            key,
            self._ttl_seconds,
        )

        return bool(refreshed)


def create_session_store(
    client: Redis,
    settings: Settings,
) -> RedisSessionStore:
    key_builder = RedisKeyBuilder(
        environment=settings.environment,
    )
    ttl_policy = create_redis_ttl_policy(settings)

    return RedisSessionStore(
        client=client,
        key_builder=key_builder,
        ttl_seconds=ttl_policy.session,
    )
