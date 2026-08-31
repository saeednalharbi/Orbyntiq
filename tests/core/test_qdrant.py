import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError
from qdrant_client.http.exceptions import ResponseHandlingException

from orbyntiq.core.config import Settings
from orbyntiq.core.qdrant import (
    QdrantUnavailableError,
    close_qdrant_client,
    create_qdrant_client,
    verify_qdrant_connection,
)


def test_create_qdrant_client_uses_settings():
    settings = Settings(_env_file=None)
    expected_client = Mock()

    with patch(
        "orbyntiq.core.qdrant.AsyncQdrantClient",
        return_value=expected_client,
    ) as client_class:
        client = create_qdrant_client(settings)

    assert client is expected_client

    client_class.assert_called_once_with(
        url="http://localhost:6333",
        grpc_port=6334,
        prefer_grpc=False,
        timeout=5.0,
    )


def test_verify_qdrant_connection_succeeds():
    client = Mock()
    client.get_collections = AsyncMock(return_value=Mock(collections=[]))

    asyncio.run(verify_qdrant_connection(client))

    client.get_collections.assert_awaited_once_with()


def test_verify_qdrant_connection_wraps_driver_error():
    client = Mock()
    client.get_collections = AsyncMock(
        side_effect=ResponseHandlingException(
            RuntimeError("connection failed")
        )
    )

    with pytest.raises(
        QdrantUnavailableError,
        match="Qdrant is unavailable",
    ):
        asyncio.run(verify_qdrant_connection(client))


def test_close_qdrant_client():
    client = Mock()
    client.close = AsyncMock()

    asyncio.run(close_qdrant_client(client))

    client.close.assert_awaited_once_with()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("qdrant_grpc_port", 0),
        ("qdrant_grpc_port", 65_536),
        ("qdrant_timeout_seconds", 0),
        ("qdrant_timeout_seconds", -1),
    ],
)
def test_settings_reject_invalid_qdrant_values(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})
