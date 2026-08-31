import asyncio
from contextlib import aclosing, suppress
from typing import Annotated, Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from orbyntiq.api.dependencies import get_llm_service
from orbyntiq.api.schemas.websocket import (
    CancelStreamRequest,
    ChatStreamRequest,
    PingRequest,
    PongEvent,
    StreamCancelledEvent,
    StreamChunkEvent,
    StreamCompletedEvent,
    StreamErrorEvent,
    StreamStartedEvent,
)
from orbyntiq.api.websocket_manager import connection_manager
from orbyntiq.core.config import get_settings
from orbyntiq.core.logging import get_logger
from orbyntiq.services import LLMService

router = APIRouter(
    prefix="/api/v1/ws",
    tags=["websocket"],
)

logger = get_logger(__name__)
settings = get_settings()


async def _send_event(
    websocket: WebSocket,
    event: dict[str, Any],
) -> None:
    """Send an event and normalize disconnected-socket failures."""

    try:
        await websocket.send_json(event)
    except RuntimeError as exc:
        raise WebSocketDisconnect(code=1001) from exc


async def _receive_client_message(
    websocket: WebSocket,
    *,
    stream_active: bool,
) -> Any:
    """Receive a client message, applying timeout only while idle."""

    if stream_active:
        return await websocket.receive_json()

    try:
        return await asyncio.wait_for(
            websocket.receive_json(),
            timeout=settings.websocket_idle_timeout_seconds,
        )
    except TimeoutError as exc:
        logger.info(
            "WebSocket closed after %.1f seconds of inactivity.",
            settings.websocket_idle_timeout_seconds,
        )

        await websocket.close(
            code=1001,
            reason="Idle timeout.",
        )

        raise WebSocketDisconnect(code=1001) from exc


async def _stream_chat_response(
    websocket: WebSocket,
    service: LLMService,
    request: ChatStreamRequest,
) -> None:
    """Stream one LLM response and guarantee generator cleanup."""

    started_event = StreamStartedEvent(
        request_id=request.request_id,
        model=settings.llm_model,
    )

    await _send_event(
        websocket,
        started_event.model_dump(),
    )

    try:
        async with aclosing(service.chat_stream(request.message)) as stream:
            async for chunk in stream:
                chunk_event = StreamChunkEvent(
                    request_id=request.request_id,
                    content=chunk,
                )

                await _send_event(
                    websocket,
                    chunk_event.model_dump(),
                )

        completed_event = StreamCompletedEvent(
            request_id=request.request_id,
            model=settings.llm_model,
        )

        await _send_event(
            websocket,
            completed_event.model_dump(),
        )

    except asyncio.CancelledError:
        raise

    except WebSocketDisconnect:
        logger.info(
            "Client disconnected while request %s was streaming.",
            request.request_id,
        )

    except Exception:
        logger.exception(
            "WebSocket LLM stream failed for request %s.",
            request.request_id,
        )

        error_event = StreamErrorEvent(
            request_id=request.request_id,
            message="LLM streaming request failed.",
            code="stream_error",
        )

        await _send_event(
            websocket,
            error_event.model_dump(),
        )


async def _cancel_stream_task(task: asyncio.Task[None]) -> None:
    """Cancel an active streaming task and wait for cleanup."""

    task.cancel()

    with suppress(asyncio.CancelledError):
        await task


@router.websocket("/chat")
async def chat_websocket(
    websocket: WebSocket,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> None:
    """Stream LLM chat responses over a WebSocket connection."""

    await connection_manager.connect(websocket)

    active_task: asyncio.Task[None] | None = None
    active_request_id: str | None = None

    logger.info(
        "WebSocket client connected. Active connections: %s",
        connection_manager.active_connection_count,
    )

    try:
        while True:
            if active_task is not None and active_task.done():
                with suppress(Exception):
                    await active_task

                active_task = None
                active_request_id = None

            stream_active = (
                active_task is not None
                and not active_task.done()
            )

            data = await _receive_client_message(
                websocket,
                stream_active=stream_active,
            )

            request_id = (
                str(data.get("request_id", "unknown"))
                if isinstance(data, dict)
                else "unknown"
            )

            message_type = (
                data.get("type")
                if isinstance(data, dict)
                else None
            )

            if message_type == "ping":
                try:
                    PingRequest.model_validate(data)
                except ValidationError:
                    event = StreamErrorEvent(
                        request_id=request_id,
                        message="Invalid heartbeat request.",
                        code="invalid_request",
                    )

                    await _send_event(
                        websocket,
                        event.model_dump(),
                    )

                    continue

                await _send_event(
                    websocket,
                    PongEvent().model_dump(),
                )

                continue

            if message_type == "cancel":
                try:
                    cancel_request = CancelStreamRequest.model_validate(data)
                except ValidationError:
                    event = StreamErrorEvent(
                        request_id=request_id,
                        message="Invalid cancellation request.",
                        code="invalid_request",
                    )

                    await _send_event(
                        websocket,
                        event.model_dump(),
                    )

                    continue

                if (
                    active_task is None
                    or active_task.done()
                    or active_request_id != cancel_request.request_id
                ):
                    event = StreamErrorEvent(
                        request_id=cancel_request.request_id,
                        message="No active stream found for request.",
                        code="stream_not_found",
                    )

                    await _send_event(
                        websocket,
                        event.model_dump(),
                    )

                    continue

                await _cancel_stream_task(active_task)

                active_task = None
                active_request_id = None

                cancelled_event = StreamCancelledEvent(
                    request_id=cancel_request.request_id,
                )

                await _send_event(
                    websocket,
                    cancelled_event.model_dump(),
                )

                continue

            try:
                request = ChatStreamRequest.model_validate(data)
            except ValidationError:
                event = StreamErrorEvent(
                    request_id=request_id,
                    message="Invalid WebSocket request.",
                    code="invalid_request",
                )

                await _send_event(
                    websocket,
                    event.model_dump(),
                )

                continue

            if active_task is not None and not active_task.done():
                event = StreamErrorEvent(
                    request_id=request.request_id,
                    message="Another stream is already active.",
                    code="stream_in_progress",
                )

                await _send_event(
                    websocket,
                    event.model_dump(),
                )

                continue

            active_request_id = request.request_id

            active_task = asyncio.create_task(
                _stream_chat_response(
                    websocket,
                    service,
                    request,
                )
            )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")

    finally:
        if active_task is not None and not active_task.done():
            await _cancel_stream_task(active_task)

        connection_manager.disconnect(websocket)

        logger.info(
            "WebSocket cleanup complete. Active connections: %s",
            connection_manager.active_connection_count,
        )
