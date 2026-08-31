import asyncio
import importlib

import pytest
from fastapi import FastAPI

from orbyntiq.core.mongodb import MongoDBUnavailableError
from orbyntiq.core.mongodb_schema import MongoDBSchemaError

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


def patch_qdrant(monkeypatch: pytest.MonkeyPatch) -> FakeQdrant:
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

    return qdrant_client


def test_lifespan_connects_and_closes_mongodb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = FakeRedis()
    mongodb_client = FakeMongoDB()
    qdrant_client = patch_qdrant(monkeypatch)
    schema_initialized = False

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
        nonlocal schema_initialized
        assert database is mongodb_client.database
        schema_initialized = True

    monkeypatch.setattr(app_module, "verify_redis_connection", verify_redis)
    monkeypatch.setattr(app_module, "close_redis_client", close_redis)
    monkeypatch.setattr(app_module, "verify_mongodb_connection", verify_mongodb)
    monkeypatch.setattr(app_module, "close_mongodb_client", close_mongodb)
    monkeypatch.setattr(app_module, "ensure_mongodb_schema", ensure_schema)

    async def scenario() -> None:
        test_app = FastAPI()

        async with app_module.lifespan(test_app):
            assert schema_initialized is True

            assert test_app.state.redis is redis_client
            assert test_app.state.redis_available is True

            assert test_app.state.mongodb is mongodb_client
            assert test_app.state.mongodb_database is mongodb_client.database
            assert test_app.state.mongodb_available is True

            assert test_app.state.qdrant is qdrant_client
            assert test_app.state.qdrant_available is True

            assert redis_client.closed is False
            assert mongodb_client.closed is False
            assert qdrant_client.closed is False

        assert redis_client.closed is True
        assert mongodb_client.closed is True
        assert qdrant_client.closed is True

        assert test_app.state.mongodb is None
        assert test_app.state.mongodb_database is None
        assert test_app.state.mongodb_available is False

        assert test_app.state.qdrant is None
        assert test_app.state.qdrant_available is False

    asyncio.run(scenario())


def test_lifespan_degrades_when_mongodb_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = FakeRedis()
    mongodb_client = FakeMongoDB()
    patch_qdrant(monkeypatch)

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
        raise MongoDBUnavailableError("MongoDB unavailable")

    async def close_mongodb(client: FakeMongoDB) -> None:
        client.closed = True

    async def ensure_schema(database: object) -> None:
        raise AssertionError(
            "Schema should not initialize when MongoDB is unavailable"
        )

    monkeypatch.setattr(app_module, "verify_redis_connection", verify_redis)
    monkeypatch.setattr(app_module, "close_redis_client", close_redis)
    monkeypatch.setattr(app_module, "verify_mongodb_connection", verify_mongodb)
    monkeypatch.setattr(app_module, "close_mongodb_client", close_mongodb)
    monkeypatch.setattr(app_module, "ensure_mongodb_schema", ensure_schema)

    async def scenario() -> None:
        test_app = FastAPI()

        async with app_module.lifespan(test_app):
            assert test_app.state.mongodb is None
            assert test_app.state.mongodb_database is None
            assert test_app.state.mongodb_available is False
            assert mongodb_client.closed is True

        assert redis_client.closed is True

    asyncio.run(scenario())


def test_lifespan_degrades_when_schema_initialization_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = FakeRedis()
    mongodb_client = FakeMongoDB()
    patch_qdrant(monkeypatch)

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
        raise MongoDBSchemaError(
            "MongoDB schema initialization failed"
        )

    monkeypatch.setattr(app_module, "verify_redis_connection", verify_redis)
    monkeypatch.setattr(app_module, "close_redis_client", close_redis)
    monkeypatch.setattr(app_module, "verify_mongodb_connection", verify_mongodb)
    monkeypatch.setattr(app_module, "close_mongodb_client", close_mongodb)
    monkeypatch.setattr(app_module, "ensure_mongodb_schema", ensure_schema)

    async def scenario() -> None:
        test_app = FastAPI()

        async with app_module.lifespan(test_app):
            assert test_app.state.mongodb is None
            assert test_app.state.mongodb_database is None
            assert test_app.state.mongodb_available is False
            assert mongodb_client.closed is True

        assert redis_client.closed is True

    asyncio.run(scenario())