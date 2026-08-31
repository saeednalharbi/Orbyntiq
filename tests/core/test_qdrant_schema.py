import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from orbyntiq.core.config import Settings
from orbyntiq.core.qdrant_schema import (
    QdrantSchemaError,
    ensure_qdrant_collection,
)


def test_creates_collection_when_missing() -> None:
    async def scenario() -> None:
        client = Mock()
        client.get_collections = AsyncMock(
            return_value=SimpleNamespace(collections=[])
        )
        client.create_collection = AsyncMock()

        settings = Settings(
            _env_file=None,
            embedding_dimension=1024,
        )

        await ensure_qdrant_collection(
            client,
            settings,
        )

        client.create_collection.assert_awaited_once()

        kwargs = client.create_collection.await_args.kwargs

        assert (
            kwargs["collection_name"]
            == "orbyntiq_documents"
        )
        assert kwargs["vectors_config"].size == 1024

    asyncio.run(scenario())


def test_existing_collection_with_correct_dimension() -> None:
    async def scenario() -> None:
        client = Mock()

        client.get_collections = AsyncMock(
            return_value=SimpleNamespace(
                collections=[
                    SimpleNamespace(
                        name="orbyntiq_documents"
                    )
                ]
            )
        )

        client.get_collection = AsyncMock(
            return_value=SimpleNamespace(
                config=SimpleNamespace(
                    params=SimpleNamespace(
                        vectors=SimpleNamespace(
                            size=1024
                        )
                    )
                )
            )
        )

        client.create_collection = AsyncMock()

        await ensure_qdrant_collection(
            client,
            Settings(_env_file=None),
        )

        client.create_collection.assert_not_awaited()

    asyncio.run(scenario())


def test_existing_collection_rejects_wrong_dimension() -> None:
    async def scenario() -> None:
        client = Mock()

        client.get_collections = AsyncMock(
            return_value=SimpleNamespace(
                collections=[
                    SimpleNamespace(
                        name="orbyntiq_documents"
                    )
                ]
            )
        )

        client.get_collection = AsyncMock(
            return_value=SimpleNamespace(
                config=SimpleNamespace(
                    params=SimpleNamespace(
                        vectors=SimpleNamespace(
                            size=384
                        )
                    )
                )
            )
        )

        with pytest.raises(
            QdrantSchemaError,
            match="vector dimension mismatch",
        ):
            await ensure_qdrant_collection(
                client,
                Settings(_env_file=None),
            )

    asyncio.run(scenario())