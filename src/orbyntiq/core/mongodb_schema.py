from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError

from orbyntiq.core.mongodb import MongoDocument

USERS_COLLECTION = "users"
CONVERSATIONS_COLLECTION = "conversations"
MESSAGES_COLLECTION = "messages"
AGENT_EXECUTIONS_COLLECTION = "agent_executions"
WORKFLOW_HISTORY_COLLECTION = "workflow_history"

MONGODB_COLLECTIONS = (
    USERS_COLLECTION,
    CONVERSATIONS_COLLECTION,
    MESSAGES_COLLECTION,
    AGENT_EXECUTIONS_COLLECTION,
    WORKFLOW_HISTORY_COLLECTION,
)


class MongoDBSchemaError(RuntimeError):
    """Raised when MongoDB schema initialization fails."""


async def ensure_mongodb_schema(
    database: AsyncDatabase[MongoDocument],
) -> None:
    try:
        await database[USERS_COLLECTION].create_indexes(
            [
                IndexModel(
                    [("email", ASCENDING)],
                    name="uq_users_email",
                    unique=True,
                ),
                IndexModel(
                    [("created_at", DESCENDING)],
                    name="ix_users_created_at",
                ),
            ]
        )

        await database[CONVERSATIONS_COLLECTION].create_indexes(
            [
                IndexModel(
                    [
                        ("user_id", ASCENDING),
                        ("updated_at", DESCENDING),
                    ],
                    name="ix_conversations_user_updated",
                ),
                IndexModel(
                    [
                        ("status", ASCENDING),
                        ("updated_at", DESCENDING),
                    ],
                    name="ix_conversations_status_updated",
                ),
            ]
        )

        await database[MESSAGES_COLLECTION].create_indexes(
            [
                IndexModel(
                    [
                        ("conversation_id", ASCENDING),
                        ("created_at", ASCENDING),
                    ],
                    name="ix_messages_conversation_created",
                ),
                IndexModel(
                    [
                        ("conversation_id", ASCENDING),
                        ("role", ASCENDING),
                        ("created_at", ASCENDING),
                    ],
                    name="ix_messages_conversation_role_created",
                ),
            ]
        )

        await database[AGENT_EXECUTIONS_COLLECTION].create_indexes(
            [
                IndexModel(
                    [
                        ("conversation_id", ASCENDING),
                        ("created_at", DESCENDING),
                    ],
                    name="ix_agent_executions_conversation_created",
                ),
                IndexModel(
                    [
                        ("status", ASCENDING),
                        ("created_at", DESCENDING),
                    ],
                    name="ix_agent_executions_status_created",
                ),
                IndexModel(
                    [
                        ("agent_name", ASCENDING),
                        ("created_at", DESCENDING),
                    ],
                    name="ix_agent_executions_agent_created",
                ),
            ]
        )

        await database[WORKFLOW_HISTORY_COLLECTION].create_indexes(
            [
                IndexModel(
                    [
                        ("execution_id", ASCENDING),
                        ("sequence", ASCENDING),
                    ],
                    name="uq_workflow_history_execution_sequence",
                    unique=True,
                ),
                IndexModel(
                    [
                        ("conversation_id", ASCENDING),
                        ("created_at", ASCENDING),
                    ],
                    name="ix_workflow_history_conversation_created",
                ),
            ]
        )
    except PyMongoError as exc:
        raise MongoDBSchemaError(
            "MongoDB schema initialization failed"
        ) from exc