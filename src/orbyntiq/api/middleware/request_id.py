import re
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from orbyntiq.core.request_context import reset_request_id, set_request_id

REQUEST_ID_HEADER = b"x-request-id"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _request_id_from_scope(scope: Scope) -> str:
    for header_name, header_value in scope.get("headers", []):
        if header_name.lower() != REQUEST_ID_HEADER:
            continue

        try:
            candidate = header_value.decode("ascii")
        except UnicodeDecodeError:
            break

        if REQUEST_ID_PATTERN.fullmatch(candidate):
            return candidate

        break

    return uuid4().hex


class RequestIDMiddleware:
    """Attach a correlation ID to every HTTP request and response."""

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

        request_id = _request_id_from_scope(scope)
        token = set_request_id(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != REQUEST_ID_HEADER
                ]

                headers.append(
                    (
                        REQUEST_ID_HEADER,
                        request_id.encode("ascii"),
                    )
                )

                message["headers"] = headers

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                send_with_request_id,
            )
        finally:
            reset_request_id(token)
