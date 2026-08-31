from typing import Any

from pydantic import ValidationError
from pymongo import ASCENDING, DESCENDING
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError, PyMongoError

from orbyntiq.core.mongodb import MongoDocument
from orbyntiq.core.mongodb_schema import (
    AGENT_EXECUTIONS_COLLECTION,
    CONVERSATIONS_COLLECTION,
    MESSAGES_COLLECTION,
    USERS_COLLECTION,
    WORKFLOW_HISTORY_COLLECTION,
)
from orbyntiq.persistence.models import (
    AgentExecution,
    Conversation,
    Message,
    User,
    WorkflowHistory,
)

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 50


class RepositoryError(RuntimeError):
    """Raised when a persistence operation fails."""


class RepositoryConflictError(RepositoryError):
    """Raised when a persistence uniqueness constraint is violated."""


class RepositoryDataError(RepositoryError):
    """Raised when stored MongoDB data is invalid."""


def _validate_pagination(
    *,
    limit: int,
    offset: int,
) -> None:
    if limit < 1 or limit > MAX_PAGE_SIZE:
        raise ValueError(
            f"limit must be between 1 and {MAX_PAGE_SIZE}"
        )

    if offset < 0:
        raise ValueError(
            "offset must be greater than or equal to 0"
        )


def _model_document(
    model: (
        User
        | Conversation
        | Message
        | AgentExecution
        | WorkflowHistory
    ),
) -> MongoDocument:
    document = model.model_dump(mode="python")

    document["_id"] = document.pop("id")

    return document


def _document_payload(
    document: MongoDocument,
) -> dict[str, Any]:
    payload = dict(document)

    payload["id"] = str(payload.pop("_id"))

    return payload


def _user_from_document(
    document: MongoDocument,
) -> User:
    try:
        return User.model_validate(
            _document_payload(document)
        )
    except ValidationError as exc:
        raise RepositoryDataError(
            "Invalid user document"
        ) from exc


def _conversation_from_document(
    document: MongoDocument,
) -> Conversation:
    try:
        return Conversation.model_validate(
            _document_payload(document)
        )
    except ValidationError as exc:
        raise RepositoryDataError(
            "Invalid conversation document"
        ) from exc


def _message_from_document(
    document: MongoDocument,
) -> Message:
    try:
        return Message.model_validate(
            _document_payload(document)
        )
    except ValidationError as exc:
        raise RepositoryDataError(
            "Invalid message document"
        ) from exc


def _agent_execution_from_document(
    document: MongoDocument,
) -> AgentExecution:
    try:
        return AgentExecution.model_validate(
            _document_payload(document)
        )
    except ValidationError as exc:
        raise RepositoryDataError(
            "Invalid agent execution document"
        ) from exc


def _workflow_history_from_document(
    document: MongoDocument,
) -> WorkflowHistory:
    try:
        return WorkflowHistory.model_validate(
            _document_payload(document)
        )
    except ValidationError as exc:
        raise RepositoryDataError(
            "Invalid workflow history document"
        ) from exc


class UserRepository:
    def __init__(
        self,
        database: AsyncDatabase[MongoDocument],
    ) -> None:
        self._collection = database[
            USERS_COLLECTION
        ]

    async def create(
        self,
        user: User,
    ) -> User:
        try:
            await self._collection.insert_one(
                _model_document(user)
            )
        except DuplicateKeyError as exc:
            raise RepositoryConflictError(
                "User already exists"
            ) from exc
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to create user"
            ) from exc

        return user

    async def get(
        self,
        user_id: str,
    ) -> User | None:
        try:
            document = await self._collection.find_one(
                {"_id": user_id}
            )
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to read user"
            ) from exc

        if document is None:
            return None

        return _user_from_document(document)

    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        normalized_email = email.strip().lower()

        try:
            document = await self._collection.find_one(
                {"email": normalized_email}
            )
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to read user"
            ) from exc

        if document is None:
            return None

        return _user_from_document(document)

    async def list(
        self,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[User]:
        _validate_pagination(
            limit=limit,
            offset=offset,
        )

        try:
            cursor = (
                self._collection.find({})
                .sort(
                    [
                        ("created_at", DESCENDING),
                        ("_id", ASCENDING),
                    ]
                )
                .skip(offset)
                .limit(limit)
            )

            return [
                _user_from_document(document)
                async for document in cursor
            ]
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to list users"
            ) from exc


class ConversationRepository:
    def __init__(
        self,
        database: AsyncDatabase[MongoDocument],
    ) -> None:
        self._collection = database[
            CONVERSATIONS_COLLECTION
        ]

    async def create(
        self,
        conversation: Conversation,
    ) -> Conversation:
        try:
            await self._collection.insert_one(
                _model_document(conversation)
            )
        except DuplicateKeyError as exc:
            raise RepositoryConflictError(
                "Conversation already exists"
            ) from exc
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to create conversation"
            ) from exc

        return conversation

    async def get(
        self,
        conversation_id: str,
    ) -> Conversation | None:
        try:
            document = await self._collection.find_one(
                {"_id": conversation_id}
            )
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to read conversation"
            ) from exc

        if document is None:
            return None

        return _conversation_from_document(document)

    async def list_for_user(
        self,
        user_id: str,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Conversation]:
        _validate_pagination(
            limit=limit,
            offset=offset,
        )

        try:
            cursor = (
                self._collection.find(
                    {"user_id": user_id}
                )
                .sort(
                    [
                        ("updated_at", DESCENDING),
                        ("_id", ASCENDING),
                    ]
                )
                .skip(offset)
                .limit(limit)
            )

            return [
                _conversation_from_document(document)
                async for document in cursor
            ]
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to list conversations"
            ) from exc


class MessageRepository:
    def __init__(
        self,
        database: AsyncDatabase[MongoDocument],
    ) -> None:
        self._collection = database[
            MESSAGES_COLLECTION
        ]

    async def create(
        self,
        message: Message,
    ) -> Message:
        try:
            await self._collection.insert_one(
                _model_document(message)
            )
        except DuplicateKeyError as exc:
            raise RepositoryConflictError(
                "Message already exists"
            ) from exc
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to create message"
            ) from exc

        return message

    async def get(
        self,
        message_id: str,
    ) -> Message | None:
        try:
            document = await self._collection.find_one(
                {"_id": message_id}
            )
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to read message"
            ) from exc

        if document is None:
            return None

        return _message_from_document(document)

    async def list_for_conversation(
        self,
        conversation_id: str,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Message]:
        _validate_pagination(
            limit=limit,
            offset=offset,
        )

        try:
            cursor = (
                self._collection.find(
                    {
                        "conversation_id":
                            conversation_id
                    }
                )
                .sort(
                    [
                        ("created_at", ASCENDING),
                        ("_id", ASCENDING),
                    ]
                )
                .skip(offset)
                .limit(limit)
            )

            return [
                _message_from_document(document)
                async for document in cursor
            ]
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to list messages"
            ) from exc


class AgentExecutionRepository:
    def __init__(
        self,
        database: AsyncDatabase[MongoDocument],
    ) -> None:
        self._collection = database[
            AGENT_EXECUTIONS_COLLECTION
        ]

    async def create(
        self,
        execution: AgentExecution,
    ) -> AgentExecution:
        try:
            await self._collection.insert_one(
                _model_document(execution)
            )
        except DuplicateKeyError as exc:
            raise RepositoryConflictError(
                "Agent execution already exists"
            ) from exc
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to create agent execution"
            ) from exc

        return execution

    async def get(
        self,
        execution_id: str,
    ) -> AgentExecution | None:
        try:
            document = await self._collection.find_one(
                {"_id": execution_id}
            )
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to read agent execution"
            ) from exc

        if document is None:
            return None

        return _agent_execution_from_document(document)

    async def list_for_conversation(
        self,
        conversation_id: str,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[AgentExecution]:
        _validate_pagination(
            limit=limit,
            offset=offset,
        )

        try:
            cursor = (
                self._collection.find(
                    {
                        "conversation_id":
                            conversation_id
                    }
                )
                .sort(
                    [
                        ("created_at", DESCENDING),
                        ("_id", ASCENDING),
                    ]
                )
                .skip(offset)
                .limit(limit)
            )

            return [
                _agent_execution_from_document(
                    document
                )
                async for document in cursor
            ]
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to list agent executions"
            ) from exc


class WorkflowHistoryRepository:
    def __init__(
        self,
        database: AsyncDatabase[MongoDocument],
    ) -> None:
        self._collection = database[
            WORKFLOW_HISTORY_COLLECTION
        ]

    async def create(
        self,
        event: WorkflowHistory,
    ) -> WorkflowHistory:
        try:
            await self._collection.insert_one(
                _model_document(event)
            )
        except DuplicateKeyError as exc:
            raise RepositoryConflictError(
                "Workflow history sequence already exists"
            ) from exc
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to create workflow history"
            ) from exc

        return event

    async def get(
        self,
        history_id: str,
    ) -> WorkflowHistory | None:
        try:
            document = await self._collection.find_one(
                {"_id": history_id}
            )
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to read workflow history"
            ) from exc

        if document is None:
            return None

        return _workflow_history_from_document(
            document
        )

    async def list_for_execution(
        self,
        execution_id: str,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[WorkflowHistory]:
        _validate_pagination(
            limit=limit,
            offset=offset,
        )

        try:
            cursor = (
                self._collection.find(
                    {"execution_id": execution_id}
                )
                .sort(
                    [
                        ("sequence", ASCENDING),
                        ("_id", ASCENDING),
                    ]
                )
                .skip(offset)
                .limit(limit)
            )

            return [
                _workflow_history_from_document(
                    document
                )
                async for document in cursor
            ]
        except PyMongoError as exc:
            raise RepositoryError(
                "Failed to list workflow history"
            ) from exc