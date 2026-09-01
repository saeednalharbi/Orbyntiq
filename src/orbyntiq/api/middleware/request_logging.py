from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from orbyntiq.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware:
    """Emit one structured completion log for every HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "")
        status_code = 500
        started_at = perf_counter()

        async def capture_status(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                capture_status,
            )
        except Exception:
            duration_ms = round(
                (perf_counter() - started_at) * 1000,
                3,
            )

            logger.exception(
                "HTTP request failed",
                extra={
                    "event": "http_request_failed",
                    "http_method": method,
                    "http_path": path,
                    "http_status_code": 500,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            3,
        )

        logger.info(
            "HTTP request completed",
            extra={
                "event": "http_request_completed",
                "http_method": method,
                "http_path": path,
                "http_status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
