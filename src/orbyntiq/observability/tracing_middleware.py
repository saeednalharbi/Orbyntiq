
from opentelemetry import propagate
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import (
    Span,
    SpanKind,
    Status,
    StatusCode,
)
from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)

TRACE_ID_HEADER = b"x-trace-id"


def _carrier_from_scope(
    scope: Scope,
) -> dict[str, str]:
    carrier: dict[str, str] = {}

    for name, value in scope.get(
        "headers",
        [],
    ):
        try:
            key = name.decode("latin-1")
            decoded_value = value.decode(
                "latin-1"
            )
        except UnicodeDecodeError:
            continue

        carrier[key] = decoded_value

    return carrier


def _resolved_route(
    scope: Scope,
) -> str:
    route = scope.get("route")

    route_path = getattr(
        route,
        "path",
        None,
    )

    if isinstance(route_path, str):
        return route_path

    return "__unmatched__"


def _trace_id(span: Span) -> str | None:
    context = span.get_span_context()

    if not context.is_valid:
        return None

    return format(
        context.trace_id,
        "032x",
    )


class TracingMiddleware:
    """Create OpenTelemetry server spans for HTTP and WebSocket traffic."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        tracer_provider: TracerProvider,
    ) -> None:
        self.app = app
        self.tracer = tracer_provider.get_tracer(
            "orbyntiq.api"
        )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        scope_type = scope["type"]

        if scope_type == "http":
            await self._trace_http(
                scope,
                receive,
                send,
            )
            return

        if scope_type == "websocket":
            await self._trace_websocket(
                scope,
                receive,
                send,
            )
            return

        await self.app(
            scope,
            receive,
            send,
        )

    async def _trace_http(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        method = str(
            scope.get(
                "method",
                "UNKNOWN",
            )
        ).upper()

        parent_context = propagate.extract(
            carrier=_carrier_from_scope(scope)
        )

        status_code = 500

        with self.tracer.start_as_current_span(
            f"HTTP {method}",
            context=parent_context,
            kind=SpanKind.SERVER,
            attributes={
                "http.request.method": method,
            },
        ) as span:

            async def send_with_trace(
                message: Message,
            ) -> None:
                nonlocal status_code

                if (
                    message["type"]
                    == "http.response.start"
                ):
                    status_code = int(
                        message["status"]
                    )

                    span.set_attribute(
                        "http.response.status_code",
                        status_code,
                    )

                    trace_id = _trace_id(span)

                    if trace_id is not None:
                        headers = [
                            (name, value)
                            for name, value in message.get(
                                "headers",
                                [],
                            )
                            if (
                                name.lower()
                                != TRACE_ID_HEADER
                            )
                        ]

                        headers.append(
                            (
                                TRACE_ID_HEADER,
                                trace_id.encode(
                                    "ascii"
                                ),
                            )
                        )

                        message["headers"] = (
                            headers
                        )

                await send(message)

            try:
                await self.app(
                    scope,
                    receive,
                    send_with_trace,
                )

            except Exception as exc:
                span.set_status(
                    Status(
                        StatusCode.ERROR
                    )
                )

                span.set_attribute(
                    "error.type",
                    type(exc).__name__,
                )

                raise

            finally:
                route = _resolved_route(
                    scope
                )

                span.update_name(
                    f"HTTP {method} {route}"
                )

                span.set_attribute(
                    "http.route",
                    route,
                )

                if status_code >= 500:
                    span.set_status(
                        Status(
                            StatusCode.ERROR
                        )
                    )

    async def _trace_websocket(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        parent_context = propagate.extract(
            carrier=_carrier_from_scope(scope)
        )

        with self.tracer.start_as_current_span(
            "WebSocket",
            context=parent_context,
            kind=SpanKind.SERVER,
        ) as span:
            try:
                await self.app(
                    scope,
                    receive,
                    send,
                )

            except Exception as exc:
                span.set_status(
                    Status(
                        StatusCode.ERROR
                    )
                )

                span.set_attribute(
                    "error.type",
                    type(exc).__name__,
                )

                raise

            finally:
                route = _resolved_route(
                    scope
                )

                span.update_name(
                    f"WebSocket {route}"
                )

                span.set_attribute(
                    "network.protocol.name",
                    "websocket",
                )

                span.set_attribute(
                    "http.route",
                    route,
                )
