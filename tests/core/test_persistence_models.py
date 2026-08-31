from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from orbyntiq.persistence.models import (
    AgentExecution,
    Conversation,
    Message,
    WorkflowHistory,
)


def test_conversation_generates_id_and_utc_timestamps() -> None:
    conversation = Conversation(
        user_id="user-1",
        title="Test conversation",
    )

    assert str(UUID(conversation.id)) == conversation.id
    assert conversation.status == "active"
    assert conversation.created_at.tzinfo is UTC
    assert conversation.updated_at.tzinfo is UTC
    assert conversation.created_at.microsecond % 1000 == 0
    assert conversation.updated_at.microsecond % 1000 == 0


def test_message_generates_id_and_utc_timestamp() -> None:
    message = Message(
        conversation_id="conversation-1",
        role="user",
        content="Hello",
    )

    assert str(UUID(message.id)) == message.id
    assert message.created_at.tzinfo is UTC
    assert message.created_at.microsecond % 1000 == 0
    assert message.metadata == {}


def test_agent_execution_defaults() -> None:
    execution = AgentExecution(
        conversation_id="conversation-1",
        agent_name="research",
    )

    assert str(UUID(execution.id)) == execution.id
    assert execution.status == "queued"
    assert execution.input == {}
    assert execution.output == {}
    assert execution.error is None
    assert execution.created_at.tzinfo is UTC
    assert execution.created_at.microsecond % 1000 == 0


def test_workflow_history_defaults() -> None:
    event = WorkflowHistory(
        execution_id="execution-1",
        conversation_id="conversation-1",
        sequence=0,
        event_type="execution_created",
    )

    assert str(UUID(event.id)) == event.id
    assert event.sequence == 0
    assert event.payload == {}
    assert event.created_at.tzinfo is UTC


def test_timestamp_is_normalized_to_utc_and_milliseconds() -> None:
    dubai_timezone = timezone(
        timedelta(hours=4)
    )

    timestamp = datetime(
        2026,
        8,
        31,
        17,
        30,
        15,
        123456,
        tzinfo=dubai_timezone,
    )

    conversation = Conversation(
        user_id="user-1",
        created_at=timestamp,
        updated_at=timestamp,
    )

    expected = datetime(
        2026,
        8,
        31,
        13,
        30,
        15,
        123000,
        tzinfo=UTC,
    )

    assert conversation.created_at == expected
    assert conversation.updated_at == expected


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Conversation(
            user_id="user-1",
            created_at=datetime(
                2026,
                8,
                31,
                13,
                30,
            ),
        )


def test_message_rejects_empty_content() -> None:
    with pytest.raises(ValidationError):
        Message(
            conversation_id="conversation-1",
            role="user",
            content="",
        )


def test_workflow_history_rejects_negative_sequence() -> None:
    with pytest.raises(ValidationError):
        WorkflowHistory(
            execution_id="execution-1",
            conversation_id="conversation-1",
            sequence=-1,
            event_type="invalid",
        )