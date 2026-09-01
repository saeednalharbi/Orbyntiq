import json
from collections.abc import Callable
from contextlib import suppress
from time import perf_counter
from typing import Any

from websocket import WebSocket, create_connection

ConnectionFactory = Callable[..., WebSocket]


class OrbyntiqWebSocketClient:
    def __init__(
        self,
        *,
        environment: Any,
        url: str,
        timeout_seconds: float,
        connection_factory: ConnectionFactory = create_connection,
    ) -> None:
        self._environment = environment
        self._url = url
        self._timeout_seconds = timeout_seconds
        self._connection_factory = connection_factory
        self._socket: WebSocket | None = None

    @property
    def connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> bool:
        if self._socket is not None:
            return True

        started_at = perf_counter()

        try:
            self._socket = self._connection_factory(
                self._url,
                timeout=self._timeout_seconds,
                http_no_proxy=[
                    "localhost",
                    "127.0.0.1",
                    "::1",
                ],
            )
        except Exception as exc:
            self._fire_request(
                name="CONNECT /api/v1/ws/chat",
                started_at=started_at,
                response_length=0,
                exception=exc,
            )
            return False

        self._fire_request(
            name="CONNECT /api/v1/ws/chat",
            started_at=started_at,
            response_length=0,
            exception=None,
        )

        return True

    def exchange(
        self,
        *,
        name: str,
        payload: dict[str, Any],
        terminal_types: set[str],
        required_types: set[str],
        request_id: str | None = None,
    ) -> list[dict[str, Any]] | None:
        if not self.connect():
            return None

        started_at = perf_counter()
        response_length = 0
        received_events: list[dict[str, Any]] = []

        try:
            if self._socket is None:
                raise RuntimeError("WebSocket is not connected")

            self._socket.send(json.dumps(payload))

            while True:
                raw_event = self._socket.recv()

                if not isinstance(raw_event, (str, bytes)):
                    raise RuntimeError("WebSocket returned an unsupported frame")

                response_length += len(raw_event)
                decoded_event = json.loads(raw_event)

                if not isinstance(decoded_event, dict):
                    raise RuntimeError("WebSocket event must be a JSON object")

                event_type = decoded_event.get("type")

                if not isinstance(event_type, str):
                    raise RuntimeError("WebSocket event type is missing")

                event_request_id = decoded_event.get("request_id")

                if (
                    request_id is not None
                    and event_request_id is not None
                    and event_request_id != request_id
                ):
                    raise RuntimeError("WebSocket response request_id mismatch")

                received_events.append(decoded_event)

                if event_type not in terminal_types:
                    continue

                if event_type == "error":
                    message = decoded_event.get(
                        "message",
                        "Unknown WebSocket error",
                    )
                    raise RuntimeError(str(message))

                received_types = {str(event.get("type")) for event in received_events}

                missing_types = required_types - received_types

                if missing_types:
                    missing = ", ".join(sorted(missing_types))
                    raise RuntimeError(f"Missing WebSocket event types: {missing}")

                self._fire_request(
                    name=name,
                    started_at=started_at,
                    response_length=response_length,
                    exception=None,
                )

                return received_events
        except Exception as exc:
            self._fire_request(
                name=name,
                started_at=started_at,
                response_length=response_length,
                exception=exc,
            )
            self.close()

            return None

    def close(self) -> None:
        socket = self._socket
        self._socket = None

        if socket is not None:
            with suppress(Exception):
                socket.close()

    def _fire_request(
        self,
        *,
        name: str,
        started_at: float,
        response_length: int,
        exception: Exception | None,
    ) -> None:
        self._environment.events.request.fire(
            request_type="WebSocket",
            name=name,
            response_time=(perf_counter() - started_at) * 1000,
            response_length=response_length,
            exception=exception,
            context={},
        )
