import asyncio
import importlib

import pytest
from fastapi import FastAPI

from orbyntiq.core.qdrant import QdrantUnavailableError

app_module = importlib.import_module("orbyntiq.api.app")


class FakeRedis:
    def __init__(self) -> None:
        self.closed = False


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


def patch_redis_and_mongodb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = FakeRedis()
    mongodb_client = FakeMongoDB()

    monkeypatch.setattr(
        app_module,
        "create_redis_client",
        lambda settings: redis_client,
    )
    monkeypatch.setattr(
        app_module,
        "create_mongodb_client",
        lambda settings: mongodb_client,
    )

    async def verify_redis(client: FakeRedis) -> None:
        assert client is redis_client

    async def close_redis(client: FakeRedis) -> None:
        client.closed = True

    async def verify_mongodb(client: FakeMongoDB) -> None:
        assert client is mongodb_client

    async def close_mongodb(client: FakeMongoDB) -> None:
        client.closed = True

    async def ensure_schema(database: object) -> None:
        assert database is mongodb_client.database

    monkeypatch.setattr(
        app_module,
        "verify_redis_connection",
        verify_redis,
    )
    monkeypatch.setattr(
        app_module,
        "close_redis_client",
        close_redis,
    )
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


def test_lifespan_connects_and_closes_qdrant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_redis_and_mongodb(monkeypatch)

    qdrant_client = FakeQdrant()

    monkeypatch.setattr(
        app_module,
        "create_qdrant_client",
        lambda settings: qdrant_client,
    )

    async def verify_qdrant(client: FakeQdrant) -> None:
        assert client is qdrant_client

    async def close_qdrant(client: FakeQdrant) -> None:
        client.closed = True

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

    async def scenario() -> None:
        test_app = FastAPI()

        async with app_module.lifespan(test_app):
            assert test_app.state.qdrant is qdrant_client
            assert test_app.state.qdrant_available is True
            assert qdrant_client.closed is False

        assert qdrant_client.closed is True
        assert test_app.state.qdrant is None
        assert test_app.state.qdrant_available is False

    asyncio.run(scenario())


def test_lifespan_degrades_when_qdrant_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_redis_and_mongodb(monkeypatch)

    qdrant_client = FakeQdrant()

    monkeypatch.setattr(
        app_module,
        "create_qdrant_client",
        lambda settings: qdrant_client,
    )

    async def unavailable(client: FakeQdrant) -> None:
        assert client is qdrant_client
        raise QdrantUnavailableError("Qdrant unavailable")

    async def close_qdrant(client: FakeQdrant) -> None:
        client.closed = True

    monkeypatch.setattr(
        app_module,
        "verify_qdrant_connection",
        unavailable,
    )
    monkeypatch.setattr(
        app_module,
        "close_qdrant_client",
        close_qdrant,
    )

    async def scenario() -> None:
        test_app = FastAPI()

        async with app_module.lifespan(test_app):
            assert test_app.state.qdrant is None
            assert test_app.state.qdrant_available is False
            assert qdrant_client.closed is True

        assert test_app.state.qdrant is None
        assert test_app.state.qdrant_available is False

    asyncio.run(scenario())