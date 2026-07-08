"""Config module tests."""
import os
import pytest


def test_settings_load_defaults(monkeypatch):
    # Clear all relevant env vars
    for k in ("DATABASE_URL", "CORS_ORIGINS", "RATE_LIMIT_PER_MINUTE",
              "API_KEY", "LOG_LEVEL", "ENVIRONMENT"):
        monkeypatch.delenv(k, raising=False)

    from app.core.config import Settings
    s = Settings()
    assert s.APP_NAME == "ACTAP"
    assert s.ENVIRONMENT.value == "development"
    assert s.LOG_LEVEL == "INFO"


def test_cors_origins_list_wildcard():
    from app.core.config import Settings
    s = Settings(CORS_ORIGINS="*")
    assert s.cors_origins_list == ["*"]


def test_cors_origins_list_multi():
    from app.core.config import Settings
    s = Settings(CORS_ORIGINS="https://a.com, https://b.com")
    assert s.cors_origins_list == ["https://a.com", "https://b.com"]


def test_api_key_protected_paths():
    from app.core.config import Settings
    s = Settings(API_KEY_PROTECTED_PATHS="/a,/b , /c")
    assert s.api_key_protected_paths_list == ["/a", "/b", "/c"]


def test_invalid_log_level_rejected():
    from app.core.config import Settings
    with pytest.raises(Exception):
        Settings(LOG_LEVEL="BANANA")


def test_invalid_port_rejected():
    from app.core.config import Settings
    with pytest.raises(Exception):
        Settings(PORT=99999)


def test_production_validation_requires_api_key(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    from app.core.config import Settings, validate_production_config
    s = Settings(API_KEY="", CORS_ORIGINS="*")
    monkeypatch.setattr("app.core.config.settings", s)
    with pytest.raises(RuntimeError, match="API_KEY"):
        validate_production_config()


def test_production_validation_requires_cors(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    from app.core.config import Settings, validate_production_config
    s = Settings(
        API_KEY="secret-123",
        CORS_ORIGINS="*",
        OPENAI_API_KEY="sk-real-key",
    )
    monkeypatch.setattr("app.core.config.settings", s)
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        validate_production_config()
