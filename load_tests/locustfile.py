from uuid import uuid4

from locust import HttpUser, User, between, task

from load_tests.config import CONFIG
from load_tests.contracts import (
    ResponseValidator,
    validate_agent_response,
    validate_health_response,
    validate_llm_response,
)
from load_tests.websocket_client import OrbyntiqWebSocketClient


def _validate_json_response(
    response: object,
    validator: ResponseValidator,
) -> None:
    try:
        payload = response.json()
    except ValueError:
        response.failure("Response is not valid JSON")
        return

    error = validator(payload)

    if error is not None:
        response.failure(error)


class OrbyntiqHttpUser(HttpUser):
    abstract = True
    host = CONFIG.host


class HealthUser(OrbyntiqHttpUser):
    """Lightweight API availability and middleware workload."""

    abstract = False
    wait_time = between(0.5, 1.5)

    @task
    def health(self) -> None:
        with self.client.get(
            "/health",
            name="GET /health",
            catch_response=True,
            timeout=CONFIG.request_timeout_seconds,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected status {response.status_code}")
                return

            _validate_json_response(
                response,
                validate_health_response,
            )


class LLMChatUser(OrbyntiqHttpUser):
    """CPU-intensive local Ollama generation workload."""

    abstract = False
    wait_time = between(2.0, 5.0)

    @task
    def chat(self) -> None:
        with self.client.post(
            "/api/v1/llm/chat",
            name="POST /api/v1/llm/chat",
            json={"prompt": ("Reply with exactly ORBYNTIQ_LOAD_OK and no additional text.")},
            catch_response=True,
            timeout=CONFIG.request_timeout_seconds,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected status {response.status_code}")
                return

            _validate_json_response(
                response,
                validate_llm_response,
            )


class AgentExecuteUser(OrbyntiqHttpUser):
    """LangGraph multi-agent orchestration workload."""

    abstract = False
    wait_time = between(4.0, 8.0)

    @task
    def execute(self) -> None:
        request_id = f"load-{uuid4().hex}"

        with self.client.post(
            "/api/v1/agents/execute",
            name="POST /api/v1/agents/execute",
            json={
                "query": ("Respond with a short greeting. Do not call external tools."),
                "request_id": request_id,
                "conversation_id": request_id,
                "max_hops": 4,
            },
            catch_response=True,
            timeout=CONFIG.request_timeout_seconds,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected status {response.status_code}")
                return

            _validate_json_response(
                response,
                validate_agent_response,
            )


class OrbyntiqWebSocketUser(User):
    abstract = True

    def on_start(self) -> None:
        self.websocket = OrbyntiqWebSocketClient(
            environment=self.environment,
            url=CONFIG.websocket_url,
            timeout_seconds=CONFIG.request_timeout_seconds,
        )

        self.websocket.connect()

    def on_stop(self) -> None:
        self.websocket.close()


class WebSocketHeartbeatUser(OrbyntiqWebSocketUser):
    """Persistent WebSocket connection and heartbeat workload."""

    abstract = False
    wait_time = between(1.0, 3.0)

    @task
    def heartbeat(self) -> None:
        self.websocket.exchange(
            name="WS ping/pong",
            payload={"type": "ping"},
            terminal_types={"pong", "error"},
            required_types={"pong"},
        )


class WebSocketStreamUser(OrbyntiqWebSocketUser):
    """Persistent WebSocket LLM streaming workload."""

    abstract = False
    wait_time = between(3.0, 6.0)

    @task
    def stream_chat(self) -> None:
        request_id = f"load-{uuid4().hex}"

        self.websocket.exchange(
            name="WS chat stream",
            payload={
                "type": "chat",
                "request_id": request_id,
                "message": ("Reply with exactly ORBYNTIQ_STREAM_OK and no additional text."),
            },
            terminal_types={"completed", "error"},
            required_types={
                "started",
                "chunk",
                "completed",
            },
            request_id=request_id,
        )
