import pytest

from orbyntiq.core.redis_keys import RedisKeyBuilder


def test_session_key() -> None:
    keys = RedisKeyBuilder(environment="development")

    assert (
        keys.session("session-123")
        == "orbyntiq:development:session:session-123"
    )


def test_conversation_key() -> None:
    keys = RedisKeyBuilder(environment="testing")

    assert (
        keys.conversation("conversation-123")
        == "orbyntiq:testing:conversation:conversation-123"
    )


def test_agent_key() -> None:
    keys = RedisKeyBuilder(environment="production")

    assert (
        keys.agent("researcher", "session-123")
        == "orbyntiq:production:agent:researcher:session-123"
    )


def test_cache_key() -> None:
    keys = RedisKeyBuilder(environment="development")

    assert (
        keys.cache("llm", "request-123")
        == "orbyntiq:development:cache:llm:request-123"
    )


@pytest.mark.parametrize(
    ("method_name", "arguments"),
    [
        ("session", ("",)),
        ("session", ("bad:id",)),
        ("conversation", ("",)),
        ("conversation", ("bad:id",)),
        ("agent", ("", "session-123")),
        ("agent", ("researcher", "bad:id")),
        ("cache", ("", "item-123")),
        ("cache", ("llm", "bad:id")),
    ],
)
def test_invalid_key_components_raise_value_error(
    method_name: str,
    arguments: tuple[str, ...],
) -> None:
    keys = RedisKeyBuilder(environment="development")
    method = getattr(keys, method_name)

    with pytest.raises(ValueError):
        method(*arguments)


def test_invalid_builder_prefix_raises_value_error() -> None:
    with pytest.raises(ValueError):
        RedisKeyBuilder(
            environment="development",
            prefix="orbyntiq:bad",
        )


def test_invalid_builder_environment_raises_value_error() -> None:
    with pytest.raises(ValueError):
        RedisKeyBuilder(environment="")
