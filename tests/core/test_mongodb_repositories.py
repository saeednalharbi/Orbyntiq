import asyncio
from typing import Any

from pymongo.errors import OperationFailure

from orbyntiq.core.mongodb_schema import (
    CONVERSATIONS_COLLECTION,
    MESSAGES_COLLECTION,
)
from orbyntiq.persistence.models import Conversation, Message
from orbyntiq.persistence.repositories import (
    ConversationRepository,
    MessageRepository,
    RepositoryError,
)


class FakeCursor:
    def __init__(
        self,
        documents: list[dict[str, Any]],
        collection: "FakeCollection",
    ) -> None:
        self._documents = list(documents)
        self._collection = collection
        self._offset = 0
        self._limit: int | None = None
        self._iterator: Any = None

    def sort(
        self,
        specification: list[tuple[str, int]],
    ) -> "FakeCursor":
        self._collection.last_sort = specification
        return self

    def skip(self, offset: int) -> "FakeCursor":
        self._offset = offset
        return self

    def limit(self, limit: int) -> "FakeCursor":
        self._limit = limit
        return self

    def __aiter__(self) -> "FakeCursor":
        documents = self._documents[self._offset:]

        if self._limit is not None:
            documents = documents[:self._limit]

        self._iterator = iter(documents)

        return self

    async def __anext__(self) -> dict[str, Any]:
        try:
            return next(self._iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeCollection:
    def __init__(self) -> None:
        self.documents: list[dict[str, Any]] = []
        self.last_sort: list[tuple[str, int]] | None = None

    async def insert_one(
        self,
        document: dict[str, Any],
    ) -> object:
        self.documents.append(dict(document))
        return object()

    async def find_one(
        self,
        query: dict[str, Any],
    ) -> dict[str, Any] | None:
        for document in self.documents:
            if all(
                document.get(key) == value
                for key, value in query.items()
            ):
                return dict(document)

        return None

    def find(
        self,
        query: dict[str, Any],
    ) -> FakeCursor:
        matching = [
            dict(document)
            for document in self.documents
            if all(
                document.get(key) == value
                for key, value in query.items()
            )
        ]

        return FakeCursor(matching, self)


class FakeDatabase:
    def __init__(self) -> None:
        self.collections = {
            CONVERSATIONS_COLLECTION: FakeCollection(),
            MESSAGES_COLLECTION: FakeCollection(),
        }

    def __getitem__(
        self,
        name: str,
    ) -> FakeCollection:
        return self.collections[name]


class FailingCollection:
    async def insert_one(
        self,
        document: dict[str, Any],
    ) -> object:
        raise OperationFailure("database failure")

    async def find_one(
        self,
        query: dict[str, Any],
    ) -> dict[str, Any] | None:
        raise OperationFailure("database failure")

    def find(
        self,
        query: dict[str, Any],
    ) -> FakeCursor:
        raise OperationFailure("database failure")


class FailingDatabase:
    def __getitem__(
        self,
        name: str,
    ) -> FailingCollection:
        return FailingCollection()


def test_conversation_repository_create_get_and_list() -> None:
    async def scenario() -> None:
        database = FakeDatabase()
        repository = ConversationRepository(
            database  # type: ignore[arg-type]
        )

        first = Conversation(
            id="conversation-1",
            user_id="user-1",
            title="First",
        )
        second = Conversation(
            id="conversation-2",
            user_id="user-1",
            title="Second",
        )

        await repository.create(first)
        await repository.create(second)

        stored = database.collections[
            CONVERSATIONS_COLLECTION
        ].documents[0]

        assert stored["_id"] == "conversation-1"
        assert "id" not in stored

        fetched = await repository.get(
            "conversation-1"
        )

        assert fetched == first

        page = await repository.list_for_user(
            "user-1",
            limit=1,
            offset=1,
        )

        assert page == [second]

        assert database.collections[
            CONVERSATIONS_COLLECTION
        ].last_sort == [
            ("updated_at", -1),
            ("_id", 1),
        ]

    asyncio.run(scenario())


def test_message_repository_create_get_and_list() -> None:
    async def scenario() -> None:
        database = FakeDatabase()
        repository = MessageRepository(
            database  # type: ignore[arg-type]
        )

        first = Message(
            id="message-1",
            conversation_id="conversation-1",
            role="user",
            content="First",
        )
        second = Message(
            id="message-2",
            conversation_id="conversation-1",
            role="assistant",
            content="Second",
        )

        await repository.create(first)
        await repository.create(second)

        fetched = await repository.get("message-1")

        assert fetched == first

        page = await repository.list_for_conversation(
            "conversation-1",
            limit=1,
            offset=0,
        )

        assert page == [first]

        assert database.collections[
            MESSAGES_COLLECTION
        ].last_sort == [
            ("created_at", 1),
            ("_id", 1),
        ]

    asyncio.run(scenario())


def test_repository_rejects_invalid_pagination() -> None:
    async def scenario() -> None:
        database = FakeDatabase()
        repository = ConversationRepository(
            database  # type: ignore[arg-type]
        )

        try:
            await repository.list_for_user(
                "user-1",
                limit=0,
            )
        except ValueError as exc:
            assert "limit must be between" in str(exc)
        else:
            raise AssertionError(
                "ValueError was not raised"
            )

        try:
            await repository.list_for_user(
                "user-1",
                offset=-1,
            )
        except ValueError as exc:
            assert str(exc) == (
                "offset must be greater than or equal to 0"
            )
        else:
            raise AssertionError(
                "ValueError was not raised"
            )

    asyncio.run(scenario())


def test_repository_wraps_database_errors() -> None:
    async def scenario() -> None:
        repository = ConversationRepository(
            FailingDatabase()  # type: ignore[arg-type]
        )

        conversation = Conversation(
            user_id="user-1"
        )

        try:
            await repository.create(conversation)
        except RepositoryError as exc:
            assert str(exc) == (
                "Failed to create conversation"
            )
        else:
            raise AssertionError(
                "RepositoryError was not raised"
            )

    asyncio.run(scenario())