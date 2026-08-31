import asyncio

from pymongo import IndexModel
from pymongo.errors import OperationFailure

from orbyntiq.core.mongodb_schema import (
    AGENT_EXECUTIONS_COLLECTION,
    CONVERSATIONS_COLLECTION,
    MESSAGES_COLLECTION,
    MONGODB_COLLECTIONS,
    USERS_COLLECTION,
    WORKFLOW_HISTORY_COLLECTION,
    MongoDBSchemaError,
    ensure_mongodb_schema,
)


class FakeCollection:
    def __init__(self) -> None:
        self.indexes: list[IndexModel] = []

    async def create_indexes(
        self,
        indexes: list[IndexModel],
    ) -> list[str]:
        self.indexes.extend(indexes)

        return [
            str(index.document["name"])
            for index in indexes
        ]


class FakeDatabase:
    def __init__(self) -> None:
        self.collections = {
            name: FakeCollection()
            for name in MONGODB_COLLECTIONS
        }

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections[name]


class FailingCollection:
    async def create_indexes(
        self,
        indexes: list[IndexModel],
    ) -> list[str]:
        raise OperationFailure("index creation failed")


class FailingDatabase:
    def __getitem__(self, name: str) -> FailingCollection:
        return FailingCollection()


def index_names(collection: FakeCollection) -> set[str]:
    return {
        str(index.document["name"])
        for index in collection.indexes
    }


def test_expected_collection_names() -> None:
    assert MONGODB_COLLECTIONS == (
        "users",
        "conversations",
        "messages",
        "agent_executions",
        "workflow_history",
    )


def test_ensure_mongodb_schema_creates_expected_indexes() -> None:
    database = FakeDatabase()

    asyncio.run(
        ensure_mongodb_schema(database)  # type: ignore[arg-type]
    )

    assert index_names(database.collections[USERS_COLLECTION]) == {
        "uq_users_email",
        "ix_users_created_at",
    }

    assert index_names(
        database.collections[CONVERSATIONS_COLLECTION]
    ) == {
        "ix_conversations_user_updated",
        "ix_conversations_status_updated",
    }

    assert index_names(database.collections[MESSAGES_COLLECTION]) == {
        "ix_messages_conversation_created",
        "ix_messages_conversation_role_created",
    }

    assert index_names(
        database.collections[AGENT_EXECUTIONS_COLLECTION]
    ) == {
        "ix_agent_executions_conversation_created",
        "ix_agent_executions_status_created",
        "ix_agent_executions_agent_created",
    }

    assert index_names(
        database.collections[WORKFLOW_HISTORY_COLLECTION]
    ) == {
        "uq_workflow_history_execution_sequence",
        "ix_workflow_history_conversation_created",
    }


def test_schema_wraps_pymongo_errors() -> None:
    database = FailingDatabase()

    try:
        asyncio.run(
            ensure_mongodb_schema(database)  # type: ignore[arg-type]
        )
    except MongoDBSchemaError as exc:
        assert str(exc) == "MongoDB schema initialization failed"
    else:
        raise AssertionError("MongoDBSchemaError was not raised")