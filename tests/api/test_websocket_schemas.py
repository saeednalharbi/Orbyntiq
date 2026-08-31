import pytest
from pydantic import ValidationError

from orbyntiq.api.schemas.websocket import (
    CancelStreamRequest,
    ChatStreamRequest,
    StreamCancelledEvent,
    StreamChunkEvent,
    StreamCompletedEvent,
    StreamErrorEvent,
    StreamStartedEvent,
)


def test_chat_stream_request() -> None:
    request = ChatStreamRequest(
        request_id="req-123",
        message="Hello Orbyntiq",
    )

    assert request.type == "chat"
    assert request.request_id == "req-123"
    assert request.message == "Hello Orbyntiq"


def test_chat_stream_request_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        ChatStreamRequest(
            request_id="req-123",
            message="",
        )


def test_cancel_stream_request() -> None:
    request = CancelStreamRequest(request_id="req-123")

    assert request.type == "cancel"
    assert request.request_id == "req-123"


def test_stream_started_event() -> None:
    event = StreamStartedEvent(
        request_id="req-123",
        model="qwen3:4b-instruct",
    )

    assert event.type == "started"
    assert event.request_id == "req-123"
    assert event.model == "qwen3:4b-instruct"


def test_stream_chunk_event() -> None:
    event = StreamChunkEvent(
        request_id="req-123",
        content="Hello",
    )

    assert event.type == "chunk"
    assert event.request_id == "req-123"
    assert event.content == "Hello"


def test_stream_completed_event() -> None:
    event = StreamCompletedEvent(
        request_id="req-123",
        model="qwen3:4b-instruct",
    )

    assert event.type == "completed"
    assert event.request_id == "req-123"
    assert event.model == "qwen3:4b-instruct"


def test_stream_cancelled_event() -> None:
    event = StreamCancelledEvent(
        request_id="req-123",
    )

    assert event.type == "cancelled"
    assert event.request_id == "req-123"


def test_stream_error_event() -> None:
    event = StreamErrorEvent(
        request_id="req-123",
        message="LLM connection failed",
    )

    assert event.type == "error"
    assert event.request_id == "req-123"
    assert event.message == "LLM connection failed"
    assert event.code == "stream_error"
