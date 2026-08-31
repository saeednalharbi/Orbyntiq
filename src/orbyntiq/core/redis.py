from redis.asyncio import Redis
from redis.exceptions import RedisError

from orbyntiq.core.config import Settings


class RedisUnavailableError(RuntimeError):
    """Raised when Redis cannot be reached or fails its health check."""


def create_redis_client(settings: Settings) -> Redis:
    return Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=settings.redis_connect_timeout_seconds,
        socket_timeout=settings.redis_operation_timeout_seconds,
    )


async def verify_redis_connection(client: Redis) -> None:
    try:
        healthy = await client.ping()
    except (RedisError, OSError) as exc:
        raise RedisUnavailableError("Redis is unavailable") from exc

    if not healthy:
        raise RedisUnavailableError("Redis health check failed")


async def close_redis_client(client: Redis) -> None:
    await client.aclose()
