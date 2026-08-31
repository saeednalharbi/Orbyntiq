import asyncio
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from orbyntiq.api.app import app
from orbyntiq.api.dependencies import get_llm_service
from orbyntiq.api.websocket_manager import connection_manager

client = TestClient(app)


class FakeStreamingService:
    async def chat_stream(self, prompt: str) -> AsyncIterator[str]:
        assert prompt == "Hello Orbyntiq"

        yield "Hello"
        yield " from Orbyntiq"


class FailingStreamingService:
    async def chat_stream(self, prompt: str) -> AsyncIterator[str]:
        assert prompt == "Hello Orbyntiq"

        yield "partial"

        raise RuntimeError("Simulated provider failure.")


class ClosableStreamingService:
    def __init__(self) -> None:
        self.stream_closed = False

    async def chat_stream(self, prompt: str) -> AsyncIterator[str]:
        assert prompt == "Hello Orbyntiq"

        try:
            yield "first"

            await asyncio.sleep(60)
        finally:
            self.stream_closed = True


def test_chat_websocket_accepts_connection() -> None:
    with client.websocket_connect("/api/v1/ws/chat"):
        assert connection_manager.active_connection_count == 1

    assert connection_manager.active_connection_count == 0


def test_chat_websocket_tracks_connection_lifecycle() -> None:
    assert connection_manager.active_connection_count == 0

    with client.websocket_connect("/api/v1/ws/chat"):
        assert connection_manager.active_connection_count == 1

    assert connection_manager.active_connection_count == 0


def test_chat_websocket_tracks_multiple_connections() -> None:
    assert connection_manager.active_connection_count == 0

    with client.websocket_connect("/api/v1/ws/chat"):
        assert connection_manager.active_connection_count == 1

        with client.websocket_connect("/api/v1/ws/chat"):
            assert connection_manager.active_connection_count == 2

        assert connection_manager.active_connection_count == 1

    assert connection_manager.active_connection_count == 0


def test_chat_websocket_streams_typed_events() -> None:
    fake_service = FakeStreamingService()

    app.dependency_overrides[get_llm_service] = lambda: fake_service

    try:
        with client.websocket_connect("/api/v1/ws/chat") as websocket:
            websocket.send_json(
                {
                    "type": "chat",
                    "request_id": "req-123",
                    "message": "Hello Orbyntiq",
                }
            )

            started = websocket.receive_json()
            first_chunk = websocket.receive_json()
            second_chunk = websocket.receive_json()
            completed = websocket.receive_json()

            assert started == {
                "type": "started",
                "request_id": "req-123",
                "model": "qwen3:4b-instruct",
            }

            assert first_chunk == {
                "type": "chunk",
                "request_id": "req-123",
                "content": "Hello",
            }

            assert second_chunk == {
                "type": "chunk",
                "request_id": "req-123",
                "content": " from Orbyntiq",
            }

            assert completed == {
                "type": "completed",
                "request_id": "req-123",
                "model": "qwen3:4b-instruct",
            }

    finally:
        app.dependency_overrides.pop(get_llm_service, None)


def test_chat_websocket_rejects_invalid_request() -> None:
    with client.websocket_connect("/api/v1/ws/chat") as websocket:
        websocket.send_json(
            {
                "type": "chat",
                "request_id": "req-invalid",
                "message": "",
            }
        )

        response = websocket.receive_json()

        assert response == {
            "type": "error",
            "request_id": "req-invalid",
            "message": "Invalid WebSocket request.",
            "code": "invalid_request",
        }


def test_chat_websocket_sends_error_when_stream_fails() -> None:
    fake_service = FailingStreamingService()

    app.dependency_overrides[get_llm_service] = lambda: fake_service

    try:
        with client.websocket_connect("/api/v1/ws/chat") as websocket:
            websocket.send_json(
                {
                    "type": "chat",
                    "request_id": "req-error",
                    "message": "Hello Orbyntiq",
                }
            )

            started = websocket.receive_json()
            partial_chunk = websocket.receive_json()
            error = websocket.receive_json()

            assert started["type"] == "started"

            assert partial_chunk == {
                "type": "chunk",
                "request_id": "req-error",
                "content": "partial",
            }

            assert error == {
                "type": "error",
                "request_id": "req-error",
                "message": "LLM streaming request failed.",
                "code": "stream_error",
            }

    finally:
        app.dependency_overrides.pop(get_llm_service, None)


def test_disconnect_closes_active_stream() -> None:
    fake_service = ClosableStreamingService()

    app.dependency_overrides[get_llm_service] = lambda: fake_service

    try:
        with client.websocket_connect("/api/v1/ws/chat") as websocket:
            websocket.send_json(
                {
                    "type": "chat",
                    "request_id": "req-disconnect",
                    "message": "Hello Orbyntiq",
                }
            )

            started = websocket.receive_json()
            chunk = websocket.receive_json()

            assert started["type"] == "started"

            assert chunk == {
                "type": "chunk",
                "request_id": "req-disconnect",
                "content": "first",
            }

        assert fake_service.stream_closed is True
        assert connection_manager.active_connection_count == 0

    finally:
        app.dependency_overrides.pop(get_llm_service, None)


def test_chat_websocket_can_cancel_active_stream() -> None:
    fake_service = ClosableStreamingService()

    app.dependency_overrides[get_llm_service] = lambda: fake_service

    try:
        with client.websocket_connect("/api/v1/ws/chat") as websocket:
            websocket.send_json(
                {
                    "type": "chat",
                    "request_id": "req-cancel",
                    "message": "Hello Orbyntiq",
                }
            )

            started = websocket.receive_json()
            chunk = websocket.receive_json()

            assert started["type"] == "started"

            assert chunk == {
                "type": "chunk",
                "request_id": "req-cancel",
                "content": "first",
            }

            websocket.send_json(
                {
                    "type": "cancel",
                    "request_id": "req-cancel",
                }
            )

            cancelled = websocket.receive_json()

            assert cancelled == {
                "type": "cancelled",
                "request_id": "req-cancel",
            }

            assert fake_service.stream_closed is True

            websocket.send_json(
                {
                    "type": "chat",
                    "request_id": "invalid-after-cancel",
                    "message": "",
                }
            )

            response = websocket.receive_json()

            assert response["type"] == "error"
            assert response["code"] == "invalid_request"

    finally:
        app.dependency_overrides.pop(get_llm_service, None)


def test_chat_websocket_rejects_unknown_cancellation() -> None:
    with client.websocket_connect("/api/v1/ws/chat") as websocket:
        websocket.send_json(
            {
                "type": "cancel",
                "request_id": "req-missing",
            }
        )

        response = websocket.receive_json()

        assert response == {
            "type": "error",
            "request_id": "req-missing",
            "message": "No active stream found for request.",
            "code": "stream_not_found",
        }
