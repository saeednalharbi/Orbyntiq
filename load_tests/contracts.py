from collections.abc import Callable
from typing import Any

ResponseValidator = Callable[[object], str | None]


def validate_health_response(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return "Health response must be a JSON object"

    if payload.get("status") != "healthy":
        return "Health response status is not healthy"

    if payload.get("service") != "Orbyntiq":
        return "Health response contains an unexpected service"

    return None


def validate_llm_response(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return "LLM response must be a JSON object"

    content = payload.get("content")
    model = payload.get("model")
    usage = payload.get("usage")

    if not isinstance(content, str) or not content.strip():
        return "LLM response content is empty"

    if not isinstance(model, str) or not model.strip():
        return "LLM response model is empty"

    if not isinstance(usage, dict):
        return "LLM response usage is missing"

    return None


def validate_agent_response(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return "Agent response must be a JSON object"

    required_strings = (
        "execution_id",
        "request_id",
        "route",
        "final_response",
    )

    for field_name in required_strings:
        value: Any = payload.get(field_name)

        if not isinstance(value, str) or not value.strip():
            return f"Agent response field {field_name} is invalid"

    if not isinstance(payload.get("errors"), list):
        return "Agent response errors must be a list"

    hop_count = payload.get("hop_count")

    if not isinstance(hop_count, int) or hop_count < 1:
        return "Agent response hop_count is invalid"

    return None
