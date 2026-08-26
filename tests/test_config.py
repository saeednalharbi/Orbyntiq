from orbyntiq.core.config import Settings

ENVIRONMENT_VARIABLES = (
    "ORBYNTIQ_APP_NAME",
    "ORBYNTIQ_ENVIRONMENT",
    "ORBYNTIQ_DEBUG",
    "ORBYNTIQ_LOG_LEVEL",
    "ORBYNTIQ_API_HOST",
    "ORBYNTIQ_API_PORT",
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


def test_settings_environment_override(monkeypatch):
    monkeypatch.setenv("ORBYNTIQ_DEBUG", "false")
    monkeypatch.setenv("ORBYNTIQ_API_PORT", "9000")

    settings = Settings(_env_file=None)

    assert settings.debug is False
    assert settings.api_port == 9000