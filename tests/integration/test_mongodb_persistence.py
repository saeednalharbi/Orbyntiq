import asyncio
from datetime import timedelta
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
    CONVERSATIONS_COLLECTION,
    MESSAGES_COLLECTION,
    ensure_mongodb_schema,
)
from orbyntiq.persistence.models import Conversation, Message
from orbyntiq.persistence.repositories import (
    ConversationRepository,
    MessageRepository,
)


def test_conversation_and_message_round_trip() -> None:
    async def scenario() -> None:
        settings = get_settings()
        client = create_mongodb_client(settings)
        database = client[settings.mongodb_database]

        conversation_id: str | None = None

        try:
            try:
                await verify_mongodb_connection(client)
            except MongoDBUnavailableError:
                pytest.skip("MongoDB is not available")

            await ensure_mongodb_schema(database)

            conversations = ConversationRepository(
                database
            )
            messages = MessageRepository(database)

            marker = f"phase06-{uuid4()}"

            conversation = Conversation(
                user_id=marker,
                title="Phase 06 integration",
            )
            conversation_id = conversation.id

            await conversations.create(conversation)

            first_message = Message(
                conversation_id=conversation.id,
                role="user",
                content="First message",
            )
            second_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content="Second message",
                created_at=(
                    first_message.created_at
                    + timedelta(milliseconds=1)
                ),
            )

            await messages.create(first_message)
            await messages.create(second_message)

            stored_conversation = await conversations.get(
                conversation.id
            )

            assert stored_conversation == conversation
            assert (
                stored_conversation.created_at.tzinfo
                is not None
            )

            stored_messages = (
                await messages.list_for_conversation(
                    conversation.id
                )
            )

            assert stored_messages == [
                first_message,
                second_message,
            ]

            page = await messages.list_for_conversation(
                conversation.id,
                limit=1,
                offset=1,
            )

            assert page == [second_message]

        finally:
            if conversation_id is not None:
                await database[
                    MESSAGES_COLLECTION
                ].delete_many(
                    {
                        "conversation_id":
                            conversation_id
                    }
                )

                await database[
                    CONVERSATIONS_COLLECTION
                ].delete_many(
                    {"_id": conversation_id}
                )

            await close_mongodb_client(client)

    asyncio.run(scenario())