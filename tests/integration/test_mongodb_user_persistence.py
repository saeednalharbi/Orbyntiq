import asyncio
from uuid import uuid4

import pytest

from orbyntiq.core.config import get_settings
from orbyntiq.core.mongodb import (
    MongoDBUnavailableError,
    close_mongodb_client,
    create_mongodb_client,
    verify_mongodb_connection,
)
from orbyntiq.core.mongodb_schema import (
    USERS_COLLECTION,
    ensure_mongodb_schema,
)
from orbyntiq.persistence import (
    RepositoryConflictError,
    User,
    UserRepository,
)


def test_user_round_trip_and_unique_email() -> None:
    async def scenario() -> None:
        settings = get_settings()
        client = create_mongodb_client(settings)
        database = client[settings.mongodb_database]

        user_id: str | None = None

        try:
            try:
                await verify_mongodb_connection(client)
            except MongoDBUnavailableError:
                pytest.skip("MongoDB is not available")

            await ensure_mongodb_schema(database)

            repository = UserRepository(database)

            marker = uuid4().hex

            user = User(
                email=f"{marker}@example.com",
                display_name="Phase 06 User",
            )

            user_id = user.id

            await repository.create(user)

            stored = await repository.get(user.id)

            assert stored == user

            by_email = await repository.get_by_email(
                user.email.upper()
            )

            assert by_email == user

            duplicate = User(
                email=user.email.upper(),
                display_name="Duplicate",
            )

            with pytest.raises(
                RepositoryConflictError
            ):
                await repository.create(duplicate)

        finally:
            if user_id is not None:
                await database[
                    USERS_COLLECTION
                ].delete_many(
                    {"_id": user_id}
                )

            await close_mongodb_client(client)

    asyncio.run(scenario())