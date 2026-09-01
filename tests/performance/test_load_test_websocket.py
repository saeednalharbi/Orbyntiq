import json

from load_tests.config import LoadTestConfig
from load_tests.websocket_client import OrbyntiqWebSocketClient


class CapturingRequestEvent:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def fire(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


class FakeEvents:
    def __init__(self) -> None:
        self.request = CapturingRequestEvent()


class FakeEnvironment:
    def __init__(self) -> None:
        self.events = FakeEvents()


class FakeSocket:
    def __init__(self, events: list[dict[str, object]]) -> None:
        self.events = [json.dumps(event) for event in events]
        self.sent: list[str] = []
        self.closed = False

    def send(self, payload: str) -> None:
        self.sent.append(payload)

    def recv(self) -> str:
        return self.events.pop(0)

    def close(self) -> None:
        self.closed = True


def test_http_host_creates_ws_url() -> None:
    config = LoadTestConfig(
        host="http://127.0.0.1:8000",
        request_timeout_seconds=10.0,
    )

    assert config.websocket_url == "ws://127.0.0.1:8000/api/v1/ws/chat"


def test_https_host_creates_secure_ws_url() -> None:
    config = LoadTestConfig(
        host="https://example.test",
        request_timeout_seconds=10.0,
    )

    assert config.websocket_url == "wss://example.test/api/v1/ws/chat"


def test_websocket_ping_is_recorded() -> None:
    environment = FakeEnvironment()
    socket = FakeSocket([{"type": "pong"}])

    client = OrbyntiqWebSocketClient(
        environment=environment,
        url="ws://localhost/test",
        timeout_seconds=5.0,
        connection_factory=lambda *args, **kwargs: socket,
    )

    result = client.exchange(
        name="WS ping/pong",
        payload={"type": "ping"},
        terminal_types={"pong", "error"},
        required_types={"pong"},
    )

    assert result == [{"type": "pong"}]
    assert len(environment.events.request.calls) == 2
    assert environment.events.request.calls[-1]["exception"] is None


def test_websocket_error_is_recorded_as_failure() -> None:
    environment = FakeEnvironment()
    socket = FakeSocket(
        [
            {
                "type": "error",
                "request_id": "request-1",
                "message": "Stream failed",
            }
        ]
    )

    client = OrbyntiqWebSocketClient(
        environment=environment,
        url="ws://localhost/test",
        timeout_seconds=5.0,
        connection_factory=lambda *args, **kwargs: socket,
    )

    result = client.exchange(
        name="WS chat stream",
        payload={
            "type": "chat",
            "request_id": "request-1",
            "message": "Hello",
        },
        terminal_types={"completed", "error"},
        required_types={"started", "completed"},
        request_id="request-1",
    )

    assert result is None
    assert socket.closed is True
    assert isinstance(
        environment.events.request.calls[-1]["exception"],
        RuntimeError,
    )
