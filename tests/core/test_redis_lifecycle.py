import asyncio

from fastapi import FastAPI

from orbyntiq.api.app import lifespan
from orbyntiq.core.redis import RedisUnavailableError


class FakeRedis:
    def __init__(self) -> None:
        self.ping_called = False
        self.closed = False

    async def ping(self) -> bool:
        self.ping_called = True
        return True

    async def aclose(self) -> None:
        self.closed = True


async def exercise_successful_lifespan(
    test_app: FastAPI,
    fake_redis: FakeRedis,
) -> None:
    async with lifespan(test_app):
        assert test_app.state.redis is fake_redis
        assert test_app.state.redis_available is True
        assert fake_redis.ping_called is True
        assert fake_redis.closed is False

    assert fake_redis.closed is True
    assert test_app.state.redis is None
    assert test_app.state.redis_available is False


def test_lifespan_connects_checks_and_closes_redis(monkeypatch) -> None:
    fake_redis = FakeRedis()

    monkeypatch.setattr(
        "orbyntiq.api.app.create_redis_client",
        lambda settings: fake_redis,
    )

    test_app = FastAPI()

    asyncio.run(
        exercise_successful_lifespan(
            test_app,
            fake_redis,
        )
    )


async def exercise_unavailable_lifespan(
    test_app: FastAPI,
    fake_redis: FakeRedis,
) -> None:
    async with lifespan(test_app):
        assert test_app.state.redis is None
        assert test_app.state.redis_available is False
        assert fake_redis.closed is True

    assert test_app.state.redis is None
    assert test_app.state.redis_available is False


def test_lifespan_continues_when_redis_is_unavailable(
    monkeypatch,
) -> None:
    fake_redis = FakeRedis()

    async def unavailable(_client) -> None:
        raise RedisUnavailableError("Redis is unavailable")

    monkeypatch.setattr(
        "orbyntiq.api.app.create_redis_client",
        lambda settings: fake_redis,
    )
    monkeypatch.setattr(
        "orbyntiq.api.app.verify_redis_connection",
        unavailable,
    )

    test_app = FastAPI()

    asyncio.run(
        exercise_unavailable_lifespan(
            test_app,
            fake_redis,
        )
    )
