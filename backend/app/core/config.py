"""Application configuration management.

Centralized configuration using environment variables with type validation.
Supports multi-environment setup (dev / staging / prod).

Environment variables are loaded from .env (dev) or system env (prod).
"""

from __future__ import annotations

from enum import Enum

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env at import time (backward compatible with existing code)
load_dotenv()


class Environment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings are validated at startup. Missing required values cause
    immediate failure with a clear error message.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Application ===
    APP_NAME: str = "ACTAP"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = Field(default=False)

    # === Server ===
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    WORKERS: int = 1

    # === Database ===
    DATABASE_URL: str = "sqlite:///./actap.db"
    # When using SQLite, the database file is stored in DATA_DIR
    DATA_DIR: str = "./data"

    # === Security ===
    # Comma-separated list of allowed origins for CORS
    # In development, defaults to "*" for convenience
    CORS_ORIGINS: str = "*"
    # API Key for protected endpoints. If empty, authentication is disabled.
    API_KEY: str | None = None
    # Paths that require API key (comma-separated patterns)
    API_KEY_PROTECTED_PATHS: str = "/api/datasources/refresh,/api/chat"

    # === Rate Limiting ===
    # Global rate limit (requests per minute per IP)
    RATE_LIMIT_PER_MINUTE: int = 120
    # Strict limit for sensitive endpoints
    RATE_LIMIT_STRICT_PER_MINUTE: int = 10

    # === AI Service (OpenAI-compatible) ===
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.deepseek.com"
    MODEL_NAME: str = "deepseek-chat"

    # === Logging ===
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    # === CORS parsed ===
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list.

        Returns:
            List of allowed origins, or ["*"] for wildcard
        """
        if not self.CORS_ORIGINS or self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def api_key_protected_paths_list(self) -> list[str]:
        """Parse API_KEY_PROTECTED_PATHS into a list."""
        if not self.API_KEY_PROTECTED_PATHS:
            return []
        return [p.strip() for p in self.API_KEY_PROTECTED_PATHS.split(",") if p.strip()]

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid LOG_LEVEL: {v}. Must be one of {valid_levels}")
        return v_upper

    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Ensure port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError(f"Invalid PORT: {v}. Must be between 1 and 65535.")
        return v


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """FastAPI dependency for accessing settings."""
    return settings


def validate_production_config() -> None:
    """Validate that production-critical configuration is properly set.

    Called at application startup. Fails fast with a clear error message
    if any production-required setting is missing.
    """
    if not settings.is_production:
        return

    errors: list[str] = []

    # CORS must be restricted in production
    if settings.cors_origins_list == ["*"]:
        errors.append(
            "CORS_ORIGINS must be set to specific origins in production "
            "(wildcard '*' is not allowed)"
        )

    # API key should be set in production
    if not settings.API_KEY:
        errors.append("API_KEY must be set in production to protect sensitive endpoints")

    # OpenAI key must not be the placeholder
    if settings.OPENAI_API_KEY in ("", "sk-your-key-here"):
        errors.append("OPENAI_API_KEY must be set to a real key in production")

    if errors:
        raise RuntimeError(
            "Production configuration validation failed:\n  - " + "\n  - ".join(errors)
        )
