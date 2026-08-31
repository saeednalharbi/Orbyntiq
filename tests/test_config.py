from orbyntiq.core.config import Settings

ENVIRONMENT_VARIABLES = (
    "ORBYNTIQ_APP_NAME",
    "ORBYNTIQ_ENVIRONMENT",
    "ORBYNTIQ_DEBUG",
    "ORBYNTIQ_LOG_LEVEL",
    "ORBYNTIQ_API_HOST",
    "ORBYNTIQ_API_PORT",
    "ORBYNTIQ_QDRANT_URL",
    "ORBYNTIQ_QDRANT_GRPC_PORT",
    "ORBYNTIQ_QDRANT_PREFER_GRPC",
    "ORBYNTIQ_QDRANT_TIMEOUT_SECONDS",
    "ORBYNTIQ_QDRANT_COLLECTION",
)


def test_settings_defaults(monkeypatch):
    for variable in ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable, raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "Orbyntiq"
    assert settings.environment == "development"
    assert settings.debug is True
    assert settings.log_level == "INFO"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000

    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_grpc_port == 6334
    assert settings.qdrant_prefer_grpc is False
    assert settings.qdrant_timeout_seconds == 5.0
    assert settings.qdrant_collection == "orbyntiq_documents"


def test_settings_environment_override(monkeypatch):
    monkeypatch.setenv("ORBYNTIQ_DEBUG", "false")
    monkeypatch.setenv("ORBYNTIQ_API_PORT", "9000")
    monkeypatch.setenv("ORBYNTIQ_QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("ORBYNTIQ_QDRANT_PREFER_GRPC", "true")

    settings = Settings(_env_file=None)

    assert settings.debug is False
    assert settings.api_port == 9000
    assert settings.qdrant_url == "http://qdrant:6333"
    assert settings.qdrant_prefer_grpc is True
