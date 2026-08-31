from dataclasses import dataclass

from orbyntiq.core.config import Settings


@dataclass(frozen=True, slots=True)
class RedisTTLPolicy:
    session: int
    conversation: int
    agent_state: int
    cache: int

    def __post_init__(self) -> None:
        values = {
            "session": self.session,
            "conversation": self.conversation,
            "agent_state": self.agent_state,
            "cache": self.cache,
        }

        for name, value in values.items():
            if value <= 0:
                raise ValueError(f"{name} TTL must be greater than zero")


def create_redis_ttl_policy(settings: Settings) -> RedisTTLPolicy:
    return RedisTTLPolicy(
        session=settings.redis_session_ttl_seconds,
        conversation=settings.redis_conversation_ttl_seconds,
        agent_state=settings.redis_agent_state_ttl_seconds,
        cache=settings.redis_cache_ttl_seconds,
    )
