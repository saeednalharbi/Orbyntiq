import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.testclient import TestClient

from orbyntiq.api.app import app
from orbyntiq.api.websocket_manager import (
    connection_manager,
)

client = TestClient(app)


EventCallback = Callable[
    [dict[str, Any]],
    Awaitable[None],
]


class FakeMultiAgentService:
    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        conversation_id: str | None = None,
        max_hops: int = 8,
        event_callback: EventCallback | None = None,
    ):
        assert user_query == "Explain embeddings."
        assert request_id == "agent-req-1"
        assert conversation_id == "conversation-1"
        assert max_hops == 8
        assert event_callback is not None

        execution_id = "execution-1"

        events = [
            {
                "request_id": request_id,
                "execution_id": execution_id,
                "sequence": 0,
                "event_type": "execution_started",
                "agent_name": "supervisor",
                "payload": {
                    "user_query": user_query,
                },
            },
            {
                "request_id": request_id,
                "execution_id": execution_id,
                "sequence": 1,
                "event_type": "routing_completed",
                "agent_name": "supervisor",
                "payload": {
                    "route": "general",
                },
            },
            {
                "request_id": request_id,
                "execution_id": execution_id,
                "sequence": 2,
                "event_type": "agent_result",
                "agent_name": "general",
                "payload": {
                    "agent": "general",
                    "status": "success",
                },
            },
            {
                "request_id": request_id,
                "execution_id": execution_id,
                "sequence": 3,
                "event_type": "agent_result",
                "agent_name": "synthesizer",
                "payload": {
                    "agent": "synthesizer",
                    "status": "success",
                },
            },
            {
                "request_id": request_id,
                "execution_id": execution_id,
                "sequence": 4,
                "event_type": "execution_completed",
                "agent_name": "synthesizer",
                "payload": {
                    "route": "general",
                    "hop_count": 3,
                    "final_response":
                        "Embeddings are vectors.",
                    "errors": [],
                    "sources": [],
                },
            },
        ]

        for event in events:
            await event_callback(event)

        return object()


class HangingMultiAgentService:
    def __init__(self) -> None:
        self.cancelled = False

    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        conversation_id: str | None = None,
        max_hops: int = 8,
        event_callback: EventCallback | None = None,
    ):
        del conversation_id
        del max_hops

        assert user_query == "Long agent task."
        assert event_callback is not None

        try:
            await event_callback(
                {
                    "request_id": request_id,
                    "execution_id": "execution-long",
                    "sequence": 0,
                    "event_type": "execution_started",
                    "agent_name": "supervisor",
                    "payload": {},
                }
            )

            await asyncio.sleep(60)

        except asyncio.CancelledError:
            self.cancelled = True
            raise


def test_multi_agent_websocket_emits_workflow_events() -> None:
    previous_service = getattr(
        app.state,
        "multi_agent_service",
        None,
    )

    app.state.multi_agent_service = (
        FakeMultiAgentService()
    )

    try:
        with client.websocket_connect(
            "/api/v1/ws/chat"
        ) as websocket:
            websocket.send_json(
                {
                    "type": "agent_execute",
                    "request_id": "agent-req-1",
                    "query": "Explain embeddings.",
                    "conversation_id":
                        "conversation-1",
                    "max_hops": 8,
                }
            )

            events = [
                websocket.receive_json()
                for _ in range(5)
            ]

        assert [
            event["type"]
            for event in events
        ] == [
            "agent_event",
            "agent_event",
            "agent_event",
            "agent_event",
            "agent_event",
        ]

        assert [
            event["event_type"]
            for event in events
        ] == [
            "execution_started",
            "routing_completed",
            "agent_result",
            "agent_result",
            "execution_completed",
        ]

        assert [
            event["sequence"]
            for event in events
        ] == [
            0,
            1,
            2,
            3,
            4,
        ]

        assert (
            events[1]["payload"]["route"]
            == "general"
        )

        assert (
            events[-1]["payload"][
                "final_response"
            ]
            == "Embeddings are vectors."
        )

    finally:
        app.state.multi_agent_service = (
            previous_service
        )


def test_multi_agent_websocket_rejects_invalid_request() -> None:
    with client.websocket_connect(
        "/api/v1/ws/chat"
    ) as websocket:
        websocket.send_json(
            {
                "type": "agent_execute",
                "request_id": "bad-agent-request",
                "query": "",
            }
        )

        event = websocket.receive_json()

    assert event == {
        "type": "error",
        "request_id": "bad-agent-request",
        "message":
            "Invalid multi-agent WebSocket request.",
        "code": "invalid_request",
    }


def test_multi_agent_websocket_reports_unavailable_service() -> None:
    previous_service = getattr(
        app.state,
        "multi_agent_service",
        None,
    )

    app.state.multi_agent_service = None

    try:
        with client.websocket_connect(
            "/api/v1/ws/chat"
        ) as websocket:
            websocket.send_json(
                {
                    "type": "agent_execute",
                    "request_id": "agent-unavailable",
                    "query": "Explain embeddings.",
                }
            )

            event = websocket.receive_json()

        assert event == {
            "type": "error",
            "request_id": "agent-unavailable",
            "message":
                "Multi-agent service is unavailable.",
            "code": "agent_unavailable",
        }

    finally:
        app.state.multi_agent_service = (
            previous_service
        )


def test_multi_agent_websocket_can_cancel_execution() -> None:
    service = HangingMultiAgentService()

    previous_service = getattr(
        app.state,
        "multi_agent_service",
        None,
    )

    app.state.multi_agent_service = service

    try:
        with client.websocket_connect(
            "/api/v1/ws/chat"
        ) as websocket:
            websocket.send_json(
                {
                    "type": "agent_execute",
                    "request_id": "agent-cancel",
                    "query": "Long agent task.",
                }
            )

            started = websocket.receive_json()

            assert (
                started["event_type"]
                == "execution_started"
            )

            websocket.send_json(
                {
                    "type": "cancel",
                    "request_id": "agent-cancel",
                }
            )

            cancelled = websocket.receive_json()

            assert cancelled == {
                "type": "cancelled",
                "request_id": "agent-cancel",
            }

        assert service.cancelled is True
        assert (
            connection_manager.active_connection_count
            == 0
        )

    finally:
        app.state.multi_agent_service = (
            previous_service
        )
