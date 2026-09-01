from load_tests.contracts import (
    validate_agent_response,
    validate_health_response,
    validate_llm_response,
)


def test_valid_health_response() -> None:
    payload = {
        "status": "healthy",
        "service": "Orbyntiq",
        "environment": "testing",
    }

    assert validate_health_response(payload) is None


def test_invalid_health_response() -> None:
    payload = {
        "status": "degraded",
        "service": "Orbyntiq",
    }

    assert validate_health_response(payload) is not None


def test_valid_llm_response() -> None:
    payload = {
        "content": "ORBYNTIQ_LOAD_OK",
        "model": "qwen3:4b-instruct",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
        },
    }

    assert validate_llm_response(payload) is None


def test_empty_llm_content_is_invalid() -> None:
    payload = {
        "content": "",
        "model": "qwen3:4b-instruct",
        "usage": {},
    }

    assert validate_llm_response(payload) is not None


def test_valid_agent_response() -> None:
    payload = {
        "execution_id": "execution-1",
        "request_id": "request-1",
        "route": "general",
        "route_reason": "General request",
        "final_response": "Hello",
        "sources": [],
        "errors": [],
        "hop_count": 2,
    }

    assert validate_agent_response(payload) is None


def test_invalid_agent_hop_count() -> None:
    payload = {
        "execution_id": "execution-1",
        "request_id": "request-1",
        "route": "general",
        "final_response": "Hello",
        "errors": [],
        "hop_count": 0,
    }

    assert validate_agent_response(payload) is not None
