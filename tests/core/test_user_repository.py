import asyncio

import pytest
from pydantic import ValidationError

from orbyntiq.core.mongodb_schema import USERS_COLLECTION
from orbyntiq.persistence import User, UserRepository


class FakeCursor:
    def __init__(
        self,
        documents: list[dict[str, object]],
    ) -> None:
        self.documents = documents
        self.offset = 0
        self.page_size: int | None = None

    def sort(
        self,
        specification: list[tuple[str, int]],
    ) -> "FakeCursor":
        return self

    def skip(self, offset: int) -> "FakeCursor":
        self.offset = offset
        return self

    def limit(self, limit: int) -> "FakeCursor":
        self.page_size = limit
        return self

    def __aiter__(self) -> "FakeCursor":
        documents = self.documents[self.offset:]

        if self.page_size is not None:
            documents = documents[:self.page_size]

        self.iterator = iter(documents)

        return self

    async def __anext__(
        self,
    ) -> dict[str, object]:
        try:
            return next(self.iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeCollection:
    def __init__(self) -> None:
        self.documents: list[
            dict[str, object]
        ] = []

    async def insert_one(
        self,
        document: dict[str, object],
    ) -> object:
        self.documents.append(dict(document))
        return object()

    async def find_one(
        self,
        query: dict[str, object],
    ) -> dict[str, object] | None:
        for document in self.documents:
            if all(
                document.get(key) == value
                for key, value in query.items()
            ):
                return dict(document)

        return None

    def find(
        self,
        query: dict[str, object],
    ) -> FakeCursor:
        return FakeCursor(
            [
                dict(document)
                for document in self.documents
            ]
        )


class FakeDatabase:
    def __init__(self) -> None:
        self.collection = FakeCollection()

    def __getitem__(
        self,
        name: str,
    ) -> FakeCollection:
        assert name == USERS_COLLECTION
        return self.collection


def test_user_normalizes_email() -> None:
    user = User(
        email="  TEST@Example.COM  ",
        display_name="Test User",
    )

    assert user.email == "test@example.com"
    assert user.status == "active"


def test_user_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        User(email="invalid-email")


def test_user_repository_create_get_and_email_lookup() -> None:
    async def scenario() -> None:
        database = FakeDatabase()

        repository = UserRepository(
            database  # type: ignore[arg-type]
        )

        user = User(
            id="user-1",
            email="test@example.com",
            display_name="Test",
        )

        await repository.create(user)

        by_id = await repository.get("user-1")

        by_email = await repository.get_by_email(
            "TEST@EXAMPLE.COM"
        )

        assert by_id == user
        assert by_email == user

        page = await repository.list(
            limit=10,
            offset=0,
        )

        assert page == [user]

    asyncio.run(scenario())