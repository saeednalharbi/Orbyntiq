import json
from typing import Any


def serialize_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def deserialize_json(payload: str) -> Any:
    return json.loads(payload)
