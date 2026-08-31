from typing import Any

from redis.asyncio import Redis

from orbyntiq.core.cache_metrics import CacheMetrics
from orbyntiq.core.config import Settings
from orbyntiq.core.redis_keys import RedisKeyBuilder
from orbyntiq.core.redis_ttl import create_redis_ttl_policy
from orbyntiq.core.serialization import deserialize_json, serialize_json


class RedisCache:
    def __init__(
        self,
        client: Redis,
        key_builder: RedisKeyBuilder,
        default_ttl_seconds: int,
        metrics: CacheMetrics | None = None,
    ) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be greater than zero")

        self._client = client
        self._key_builder = key_builder
        self._default_ttl_seconds = default_ttl_seconds
        self._metrics = metrics

    async def set(
        self,
        namespace: str,
        identifier: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        ttl = (
            self._default_ttl_seconds
            if ttl_seconds is None
            else ttl_seconds
        )

        if ttl <= 0:
            raise ValueError("ttl_seconds must be greater than zero")

        key = self._key_builder.cache(namespace, identifier)

        await self._client.set(
            key,
            value,
            ex=ttl,
        )

    async def get(
        self,
        namespace: str,
        identifier: str,
    ) -> str | None:
        key = self._key_builder.cache(namespace, identifier)
        value = await self._client.get(key)

        if self._metrics is not None:
            if value is None:
                self._metrics.record_miss()
            else:
                self._metrics.record_hit()

        return value

    async def set_json(
        self,
        namespace: str,
        identifier: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        await self.set(
            namespace=namespace,
            identifier=identifier,
            value=serialize_json(value),
            ttl_seconds=ttl_seconds,
        )

    async def get_json(
        self,
        namespace: str,
        identifier: str,
    ) -> Any:
        payload = await self.get(namespace, identifier)

        if payload is None:
            return None

        return deserialize_json(payload)

    async def delete(
        self,
        namespace: str,
        identifier: str,
    ) -> bool:
        key = self._key_builder.cache(namespace, identifier)
        deleted = await self._client.delete(key)

        return bool(deleted)

    async def exists(
        self,
        namespace: str,
        identifier: str,
    ) -> bool:
        key = self._key_builder.cache(namespace, identifier)
        exists = await self._client.exists(key)

        return bool(exists)


def create_cache(
    client: Redis,
    settings: Settings,
    metrics: CacheMetrics | None = None,
) -> RedisCache:
    keys = RedisKeyBuilder(environment=settings.environment)
    ttl = create_redis_ttl_policy(settings)

    return RedisCache(
        client=client,
        key_builder=keys,
        default_ttl_seconds=ttl.cache,
        metrics=metrics,
    )
