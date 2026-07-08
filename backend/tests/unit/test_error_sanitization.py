"""Error sanitization unit tests."""

from app.core.config import Settings
from app.middleware.errors import _sanitize_message


def test_sanitize_in_dev_passes_through(monkeypatch):
    s = Settings(ENVIRONMENT="development", API_KEY="x", CORS_ORIGINS="*")
    monkeypatch.setattr("app.core.config.settings", s)
    assert _sanitize_message("some api_key leak") == "some api_key leak"


def test_sanitize_in_prod_strips_sensitive(monkeypatch):
    s = Settings(ENVIRONMENT="production", API_KEY="x", CORS_ORIGINS="https://ok.com")
    monkeypatch.setattr("app.core.config.settings", s)
    # Mentions api_key
    assert "internal error" in _sanitize_message("invalid api_key provided").lower()
    # Mentions openai
    assert "internal error" in _sanitize_message("openai call failed").lower()
    # Mentions sk- (OpenAI key prefix)
    assert "internal error" in _sanitize_message("key=sk-12345 was rejected").lower()
    # Mentions token
    assert "internal error" in _sanitize_message("token expired").lower()


def test_sanitize_in_prod_passes_safe(monkeypatch):
    s = Settings(ENVIRONMENT="production", API_KEY="x", CORS_ORIGINS="https://ok.com")
    monkeypatch.setattr("app.core.config.settings", s)
    assert _sanitize_message("country not found") == "country not found"
