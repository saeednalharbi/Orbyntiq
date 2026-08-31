import asyncio
import time
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import orbyntiq.api.routes.websocket as websocket_route
from orbyntiq.api.app import app
from orbyntiq.api.dependencies import get_llm_service
from orbyntiq.api.websocket_manager import connection_manager

client = TestClient(app)


class SlowStreamingService:
    async def chat_stream(self, prompt: str) -> AsyncIterator[str]:
        assert prompt == "Heartbeat test"

        yield "working"

        await asyncio.sleep(60)


def test_websocket_ping_returns_pong() -> None:
    with client.websocket_connect("/api/v1/ws/chat") as websocket:
        websocket.send_json(
            {
                "type": "ping",
            }
        )

        response = websocket.receive_json()

        assert response == {
            "type": "pong",
        }


def test_idle_websocket_closes_after_timeout() -> None:
    original_timeout = (
        websocket_route.settings.websocket_idle_timeout_seconds
    )

    websocket_route.settings.websocket_idle_timeout_seconds = 0.05

    try:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/api/v1/ws/chat") as websocket:
                websocket.receive_json()

        assert exc_info.value.code == 1001

    finally:
        websocket_route.settings.websocket_idle_timeout_seconds = (
            original_timeout
        )

    assert connection_manager.active_connection_count == 0


def test_idle_timeout_does_not_interrupt_active_stream() -> None:
    original_timeout = (
        websocket_route.settings.websocket_idle_timeout_seconds
    )

    websocket_route.settings.websocket_idle_timeout_seconds = 0.05

    fake_service = SlowStreamingService()

    app.dependency_overrides[get_llm_service] = lambda: fake_service

    try:
        with client.websocket_connect("/api/v1/ws/chat") as websocket:
            websocket.send_json(
                {
                    "type": "chat",
                    "request_id": "req-heartbeat",
                    "message": "Heartbeat test",
                }
            )

            started = websocket.receive_json()
            chunk = websocket.receive_json()

            assert started["type"] == "started"

            assert chunk == {
                "type": "chunk",
                "request_id": "req-heartbeat",
                "content": "working",
            }

            time.sleep(0.1)

            websocket.send_json(
                {
                    "type": "cancel",
                    "request_id": "req-heartbeat",
                }
            )

            cancelled = websocket.receive_json()

            assert cancelled == {
                "type": "cancelled",
                "request_id": "req-heartbeat",
            }

    finally:
        app.dependency_overrides.pop(get_llm_service, None)

        websocket_route.settings.websocket_idle_timeout_seconds = (
            original_timeout
        )
