import json

import pytest

from orbyntiq.core.serialization import deserialize_json, serialize_json


@pytest.mark.parametrize(
    "value",
    [
        "hello",
        42,
        3.14,
        True,
        False,
        None,
        [1, 2, 3],
        {"name": "Orbyntiq", "active": True},
    ],
)
def test_json_round_trip(value) -> None:
    payload = serialize_json(value)
    result = deserialize_json(payload)

    assert result == value


def test_nested_json_round_trip() -> None:
    value = {
        "agent": "planner",
        "step": 2,
        "tools": ["rag", "search"],
        "metadata": {
            "active": True,
            "score": 0.95,
        },
    }

    payload = serialize_json(value)
    result = deserialize_json(payload)

    assert result == value


def test_serialization_is_deterministic() -> None:
    first = serialize_json({"b": 2, "a": 1})
    second = serialize_json({"a": 1, "b": 2})

    assert first == second
    assert first == '{"a":1,"b":2}'


def test_non_json_value_is_rejected() -> None:
    with pytest.raises(TypeError):
        serialize_json({"invalid": {1, 2, 3}})


def test_invalid_json_is_rejected() -> None:
    with pytest.raises(json.JSONDecodeError):
        deserialize_json("{invalid-json}")
