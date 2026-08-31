import pytest

from orbyntiq.core.config import Settings
from orbyntiq.core.redis_ttl import RedisTTLPolicy, create_redis_ttl_policy


def test_default_redis_ttl_policy() -> None:
    settings = Settings()
    policy = create_redis_ttl_policy(settings)

    assert policy.session == 86_400
    assert policy.conversation == 21_600
    assert policy.agent_state == 3_600
    assert policy.cache == 300


def test_custom_redis_ttl_policy() -> None:
    settings = Settings(
        redis_session_ttl_seconds=100,
        redis_conversation_ttl_seconds=200,
        redis_agent_state_ttl_seconds=300,
        redis_cache_ttl_seconds=400,
    )

    policy = create_redis_ttl_policy(settings)

    assert policy.session == 100
    assert policy.conversation == 200
    assert policy.agent_state == 300
    assert policy.cache == 400


@pytest.mark.parametrize(
    "field_name",
    [
        "redis_session_ttl_seconds",
        "redis_conversation_ttl_seconds",
        "redis_agent_state_ttl_seconds",
        "redis_cache_ttl_seconds",
    ],
)
def test_settings_reject_non_positive_redis_ttl(field_name: str) -> None:
    with pytest.raises(ValueError):
        Settings(**{field_name: 0})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("session", 0),
        ("conversation", 0),
        ("agent_state", -1),
        ("cache", -1),
    ],
)
def test_policy_rejects_non_positive_ttl(
    field_name: str,
    value: int,
) -> None:
    values = {
        "session": 10,
        "conversation": 10,
        "agent_state": 10,
        "cache": 10,
    }
    values[field_name] = value

    with pytest.raises(ValueError):
        RedisTTLPolicy(**values)
