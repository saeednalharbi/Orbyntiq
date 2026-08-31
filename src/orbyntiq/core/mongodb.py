from typing import Any

from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from pymongo.server_api import ServerApi

from orbyntiq.core.config import Settings

MongoDocument = dict[str, Any]


class MongoDBUnavailableError(RuntimeError):
    """Raised when MongoDB cannot be reached or fails its health check."""


def create_mongodb_client(
    settings: Settings,
) -> AsyncMongoClient[MongoDocument]:
    client: AsyncMongoClient[MongoDocument] = AsyncMongoClient(
        settings.mongodb_url,
        connectTimeoutMS=int(
            settings.mongodb_connect_timeout_seconds * 1000
        ),
        serverSelectionTimeoutMS=int(
            settings.mongodb_server_selection_timeout_seconds * 1000
        ),
        socketTimeoutMS=int(
            settings.mongodb_operation_timeout_seconds * 1000
        ),
        server_api=ServerApi("1"),
        tz_aware=True,
    )

    return client


async def verify_mongodb_connection(
    client: AsyncMongoClient[MongoDocument],
) -> None:
    try:
        response = await client.admin.command("ping")
    except (PyMongoError, OSError) as exc:
        raise MongoDBUnavailableError(
            "MongoDB is unavailable"
        ) from exc

    if response.get("ok") != 1.0:
        raise MongoDBUnavailableError(
            "MongoDB health check failed"
        )


async def close_mongodb_client(
    client: AsyncMongoClient[MongoDocument],
) -> None:
    await client.close()