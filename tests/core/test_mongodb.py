import asyncio
from typing import Any

from pymongo.errors import ConnectionFailure

from orbyntiq.core.config import Settings
from orbyntiq.core.mongodb import (
    MongoDBUnavailableError,
    close_mongodb_client,
    create_mongodb_client,
    verify_mongodb_connection,
)


class SuccessfulAdmin:
    async def command(self, command_name: str) -> dict[str, float]:
        assert command_name == "ping"
        return {"ok": 1.0}


class FailingAdmin:
    async def command(self, command_name: str) -> dict[str, float]:
        assert command_name == "ping"
        raise ConnectionFailure("MongoDB unavailable")


class UnhealthyAdmin:
    async def command(self, command_name: str) -> dict[str, float]:
        assert command_name == "ping"
        return {"ok": 0.0}


class FakeClient:
    def __init__(self, admin: Any) -> None:
        self.admin = admin
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def test_create_mongodb_client() -> None:
    settings = Settings(
        mongodb_url="mongodb://localhost:27017",
        mongodb_database="orbyntiq",
    )

    client = create_mongodb_client(settings)

    try:
        assert client is not None
    finally:
        asyncio.run(close_mongodb_client(client))


def test_verify_mongodb_connection_succeeds() -> None:
    client = FakeClient(SuccessfulAdmin())

    asyncio.run(verify_mongodb_connection(client))  # type: ignore[arg-type]


def test_verify_mongodb_connection_wraps_driver_error() -> None:
    client = FakeClient(FailingAdmin())

    try:
        asyncio.run(
            verify_mongodb_connection(client)  # type: ignore[arg-type]
        )
    except MongoDBUnavailableError as exc:
        assert str(exc) == "MongoDB is unavailable"
    else:
        raise AssertionError("MongoDBUnavailableError was not raised")


def test_verify_mongodb_connection_rejects_unhealthy_response() -> None:
    client = FakeClient(UnhealthyAdmin())

    try:
        asyncio.run(
            verify_mongodb_connection(client)  # type: ignore[arg-type]
        )
    except MongoDBUnavailableError as exc:
        assert str(exc) == "MongoDB health check failed"
    else:
        raise AssertionError("MongoDBUnavailableError was not raised")


def test_close_mongodb_client() -> None:
    client = FakeClient(SuccessfulAdmin())

    asyncio.run(close_mongodb_client(client))  # type: ignore[arg-type]

    assert client.closed is True
