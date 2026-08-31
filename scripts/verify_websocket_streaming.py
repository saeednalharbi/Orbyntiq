import asyncio
import json
import os
from typing import Any

import websockets

WS_URL = os.getenv(
    "ORBYNTIQ_WS_URL",
    "ws://127.0.0.1:8000/api/v1/ws/chat",
)

RESPONSE_TIMEOUT_SECONDS = 120.0


def parse_event(message: str | bytes) -> dict[str, Any]:
    """Decode and validate one WebSocket JSON event."""

    if isinstance(message, bytes):
        message = message.decode("utf-8")

    data = json.loads(message)

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Expected JSON object, received: {data!r}"
        )

    return data


async def receive_event(
    websocket: Any,
) -> dict[str, Any]:
    """Receive one server event with a timeout."""

    message = await asyncio.wait_for(
        websocket.recv(),
        timeout=RESPONSE_TIMEOUT_SECONDS,
    )

    return parse_event(message)


async def verify_ping() -> None:
    """Verify the heartbeat protocol."""

    async with websockets.connect(WS_URL) as websocket:
        await websocket.send(
            json.dumps(
                {
                    "type": "ping",
                }
            )
        )

        event = await receive_event(websocket)

        if event != {"type": "pong"}:
            raise RuntimeError(
                f"Unexpected heartbeat response: {event}"
            )

    print("Heartbeat verification passed.")


async def run_stream(
    *,
    request_id: str,
    prompt: str,
) -> str:
    """Run one real streamed LLM request."""

    chunks: list[str] = []

    async with websockets.connect(WS_URL) as websocket:
        await websocket.send(
            json.dumps(
                {
                    "type": "chat",
                    "request_id": request_id,
                    "message": prompt,
                }
            )
        )

        while True:
            event = await receive_event(websocket)

            event_type = event.get("type")

            if event_type == "started":
                if event.get("request_id") != request_id:
                    raise RuntimeError(
                        f"Wrong request id in started event: {event}"
                    )

                print(
                    f"[{request_id}] started "
                    f"with model {event.get('model')}"
                )

            elif event_type == "chunk":
                if event.get("request_id") != request_id:
                    raise RuntimeError(
                        f"Wrong request id in chunk event: {event}"
                    )

                content = event.get("content")

                if not isinstance(content, str):
                    raise RuntimeError(
                        f"Invalid chunk content: {event}"
                    )

                chunks.append(content)

                print(
                    f"[{request_id}] chunk: "
                    f"{content!r}"
                )

            elif event_type == "completed":
                if event.get("request_id") != request_id:
                    raise RuntimeError(
                        f"Wrong request id in completed event: {event}"
                    )

                break

            elif event_type == "error":
                raise RuntimeError(
                    f"Streaming failed for {request_id}: {event}"
                )

            else:
                raise RuntimeError(
                    f"Unexpected event for {request_id}: {event}"
                )

    response = "".join(chunks).strip()

    if not response:
        raise RuntimeError(
            f"{request_id} completed without streamed content."
        )

    print(
        f"[{request_id}] completed with "
        f"{len(chunks)} chunks."
    )

    return response


async def verify_single_stream() -> None:
    """Verify one real Ollama stream end to end."""

    response = await run_stream(
        request_id="verify-single",
        prompt=(
            "Reply with one short sentence confirming "
            "that real-time streaming works."
        ),
    )

    print()
    print("Single-stream response:")
    print(response)
    print()
    print("Single-client streaming verification passed.")


async def verify_simultaneous_streams() -> None:
    """Verify that two independent clients can stream concurrently."""

    first_task = asyncio.create_task(
        run_stream(
            request_id="verify-client-a",
            prompt=(
                "Reply briefly with the exact prefix "
                "'CLIENT_A:' followed by a short sentence."
            ),
        )
    )

    second_task = asyncio.create_task(
        run_stream(
            request_id="verify-client-b",
            prompt=(
                "Reply briefly with the exact prefix "
                "'CLIENT_B:' followed by a short sentence."
            ),
        )
    )

    first_response, second_response = await asyncio.gather(
        first_task,
        second_task,
    )

    print()
    print("Client A response:")
    print(first_response)

    print()
    print("Client B response:")
    print(second_response)

    print()
    print(
        "Simultaneous-client streaming verification passed."
    )


async def main() -> None:
    print(f"Connecting to: {WS_URL}")
    print()

    await verify_ping()

    print()

    await verify_single_stream()

    print()

    await verify_simultaneous_streams()

    print()
    print("=" * 60)
    print("ORBYNTIQ WEBSOCKET VERIFICATION PASSED")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (
        ConnectionRefusedError,
        OSError,
    ) as exc:
        raise SystemExit(
            "\nCould not connect to the Orbyntiq API.\n"
            "Start FastAPI first with:\n\n"
            "python -m uvicorn orbyntiq.api.app:app "
            "--host 127.0.0.1 --port 8000\n"
        ) from exc
