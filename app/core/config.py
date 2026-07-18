"""
Centralized configuration via Pydantic Settings.
All secrets are sourced from environment variables — never hardcoded.
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    TEST = "test"
    DEV = "dev"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "AI Travel Planner"
    APP_VERSION: str = "1.0.0"
    ENV: Environment = Environment.DEV
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api/v1"

    # ── LLM ──────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: SecretStr = Field(..., description="OpenAI API key")
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT_SECONDS: int = 60

    # ── External APIs ─────────────────────────────────────────────────────────
    SERPER_API_KEY: SecretStr = Field(..., description="Serper.dev API key for web search")
    SERPER_BASE_URL: str = "https://google.serper.dev/search"
    SERPER_TIMEOUT_SECONDS: int = 10
    SERPER_NUM_RESULTS: int = 5

    WEATHER_API_KEY: SecretStr = Field(..., description="OpenWeatherMap API key")
    WEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5"
    WEATHER_TIMEOUT_SECONDS: int = 8

    # ── Database / Checkpointer ───────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="sqlite:///./dev_checkpoint.db",
        description="Postgres URL for production, SQLite for dev",
    )
    CHECKPOINT_TABLE_PREFIX: str = "travel_planner_"

    # ── Graph / HITL ──────────────────────────────────────────────────────────
    MAX_REVISIONS: int = Field(default=5, ge=1, le=20)
    GRAPH_RECURSION_LIMIT: int = 50

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://localhost:5173"],
        description="Allowed CORS origins. Override via CORS_ORIGINS env var in production (e.g. https://yourdomain.com).",
    )

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}")
        return upper

    @property
    def is_production(self) -> bool:
        return self.ENV == Environment.PRODUCTION

    @property
    def is_test(self) -> bool:
        return self.ENV == Environment.TEST


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton — call this everywhere instead of instantiating Settings()."""
    return Settings()
