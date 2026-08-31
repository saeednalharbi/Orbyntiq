import asyncio
import importlib

import pytest
from fastapi import FastAPI

from orbyntiq.core.redis import RedisUnavailableError

app_module = importlib.import_module("orbyntiq.api.app")


class FakeRedis:
    def __init__(self) -> None:
        self.ping_called = False
        self.closed = False

    async def ping(self) -> bool:
        self.ping_called = True
        return True

    async def aclose(self) -> None:
        self.closed = True


class FakeMongoDB:
    def __init__(self) -> None:
        self.closed = False
        self.database = object()

    def __getitem__(self, name: str) -> object:
        assert name == app_module.settings.mongodb_database
        return self.database


class FakeQdrant:
    def __init__(self) -> None:
        self.closed = False


def patch_supporting_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mongodb_client = FakeMongoDB()
    qdrant_client = FakeQdrant()

    monkeypatch.setattr(
        app_module,
        "create_mongodb_client",
        lambda settings: mongodb_client,
    )
    monkeypatch.setattr(
        app_module,
        "create_qdrant_client",
        lambda settings: qdrant_client,
    )

    async def verify_mongodb(client: FakeMongoDB) -> None:
        assert client is mongodb_client

    async def close_mongodb(client: FakeMongoDB) -> None:
        client.closed = True

    async def ensure_schema(database: object) -> None:
        assert database is mongodb_client.database

    async def verify_qdrant(client: FakeQdrant) -> None:
        assert client is qdrant_client

    async def close_qdrant(client: FakeQdrant) -> None:
        client.closed = True

    monkeypatch.setattr(
        app_module,
        "verify_mongodb_connection",
        verify_mongodb,
    )
    monkeypatch.setattr(
        app_module,
        "close_mongodb_client",
        close_mongodb,
    )
    monkeypatch.setattr(
        app_module,
        "ensure_mongodb_schema",
        ensure_schema,
    )
    monkeypatch.setattr(
        app_module,
        "verify_qdrant_connection",
        verify_qdrant,
    )
    monkeypatch.setattr(
        app_module,
        "close_qdrant_client",
        close_qdrant,
    )


def test_lifespan_connects_checks_and_closes_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    patch_supporting_services(monkeypatch)

    monkeypatch.setattr(
        app_module,
        "create_redis_client",
        lambda settings: fake_redis,
    )

    async def scenario() -> None:
        test_app = FastAPI()

        async with app_module.lifespan(test_app):
            assert test_app.state.redis is fake_redis
            assert test_app.state.redis_available is True
            assert fake_redis.ping_called is True
            assert fake_redis.closed is False

        assert fake_redis.closed is True
        assert test_app.state.redis is None
        assert test_app.state.redis_available is False

    asyncio.run(scenario())


def test_lifespan_continues_when_redis_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    patch_supporting_services(monkeypatch)

    monkeypatch.setattr(
        app_module,
        "create_redis_client",
        lambda settings: fake_redis,
    )

    async def unavailable(_client: FakeRedis) -> None:
        raise RedisUnavailableError("Redis is unavailable")

    monkeypatch.setattr(
        app_module,
        "verify_redis_connection",
        unavailable,
    )

    async def scenario() -> None:
        test_app = FastAPI()

        async with app_module.lifespan(test_app):
            assert test_app.state.redis is None
            assert test_app.state.redis_available is False
            assert fake_redis.closed is True

        assert test_app.state.redis is None
        assert test_app.state.redis_available is False

    asyncio.run(scenario())