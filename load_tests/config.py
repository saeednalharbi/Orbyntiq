import os
from dataclasses import dataclass


def _positive_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    value = float(raw_value)

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")

    return value


@dataclass(frozen=True, slots=True)
class LoadTestConfig:
    host: str
    request_timeout_seconds: float

    @classmethod
    def from_environment(cls) -> "LoadTestConfig":
        host = os.getenv(
            "ORBYNTIQ_LOAD_HOST",
            "http://127.0.0.1:8000",
        ).rstrip("/")

        return cls(
            host=host,
            request_timeout_seconds=_positive_float(
                "ORBYNTIQ_LOAD_REQUEST_TIMEOUT_SECONDS",
                120.0,
            ),
        )

    @property
    def websocket_url(self) -> str:
        if self.host.startswith("https://"):
            base_url = f"wss://{self.host.removeprefix('https://')}"
        elif self.host.startswith("http://"):
            base_url = f"ws://{self.host.removeprefix('http://')}"
        else:
            raise ValueError("Load-test host must begin with http:// or https://")

        return f"{base_url}/api/v1/ws/chat"


CONFIG = LoadTestConfig.from_environment()
