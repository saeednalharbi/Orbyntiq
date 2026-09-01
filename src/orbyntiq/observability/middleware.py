import json
from time import perf_counter
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from orbyntiq.observability.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
    record_websocket_connection,
    record_websocket_disconnection,
    record_websocket_message,
)


def _http_path_label(scope: Scope) -> str:
    route = scope.get("route")

    route_path = getattr(route, "path", None)

    if isinstance(route_path, str):
        return route_path

    return "__unmatched__"


def _websocket_message_type(
    message: Message,
) -> object:
    text = message.get("text")

    if isinstance(text, str):
        try:
            payload: Any = json.loads(text)
        except (TypeError, ValueError):
            return None

        if isinstance(payload, dict):
            return payload.get("type")

        return None

    raw_bytes = message.get("bytes")

    if isinstance(raw_bytes, bytes):
        try:
            payload = json.loads(
                raw_bytes.decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            TypeError,
            ValueError,
        ):
            return None

        if isinstance(payload, dict):
            return payload.get("type")

    return None


class MetricsMiddleware:
    """Collect bounded-cardinality HTTP and WebSocket metrics."""

    def __init__(
        self,
        app: ASGIApp,
        metrics_path: str = "/metrics",
    ) -> None:
        self.app = app
        self.metrics_path = metrics_path

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        scope_type = scope["type"]

        if scope_type == "http":
            await self._handle_http(
                scope,
                receive,
                send,
            )
            return

        if scope_type == "websocket":
            await self._handle_websocket(
                scope,
                receive,
                send,
            )
            return

        await self.app(scope, receive, send)

    async def _handle_http(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope.get("path") == self.metrics_path:
            await self.app(scope, receive, send)
            return

        method = str(
            scope.get("method", "UNKNOWN")
        ).upper()

        status_code = 500
        started_at = perf_counter()

        HTTP_REQUESTS_IN_PROGRESS.labels(
            method=method,
        ).inc()

        async def capture_status(
            message: Message,
        ) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = int(message["status"])

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                capture_status,
            )
        except Exception:
            path = _http_path_label(scope)
            status = "500"

            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                path=path,
                status=status,
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                path=path,
                status=status,
            ).observe(
                perf_counter() - started_at
            )

            raise
        else:
            path = _http_path_label(scope)
            status = str(status_code)

            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                path=path,
                status=status,
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                path=path,
                status=status,
            ).observe(
                perf_counter() - started_at
            )

        finally:
            HTTP_REQUESTS_IN_PROGRESS.labels(
                method=method,
            ).dec()

    async def _handle_websocket(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        endpoint = str(scope.get("path", ""))
        accepted = False
        disconnected = False

        async def receive_with_metrics() -> Message:
            message = await receive()

            if message["type"] == "websocket.receive":
                record_websocket_message(
                    endpoint,
                    "received",
                    _websocket_message_type(message),
                )

            return message

        async def send_with_metrics(
            message: Message,
        ) -> None:
            nonlocal accepted
            nonlocal disconnected

            if (
                message["type"] == "websocket.accept"
                and not accepted
            ):
                accepted = True

                record_websocket_connection(
                    endpoint
                )

            elif message["type"] == "websocket.send":
                record_websocket_message(
                    endpoint,
                    "sent",
                    _websocket_message_type(message),
                )

            elif (
                message["type"] == "websocket.close"
                and accepted
                and not disconnected
            ):
                disconnected = True

                record_websocket_disconnection(
                    endpoint
                )

            await send(message)

        try:
            await self.app(
                scope,
                receive_with_metrics,
                send_with_metrics,
            )
        finally:
            if accepted and not disconnected:
                record_websocket_disconnection(
                    endpoint
                )
