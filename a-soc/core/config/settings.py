"""
core/config/settings.py
Typed configuration for the A-SOC backend.

Additions over the previous revision: an environment marker, CORS origins (they
were hardcoded to two localhost ports in api.py), an optional WebSocket token,
log settings, and simulation pacing. Everything remains environment-driven.
"""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEV_ORIGINS = ["http://localhost:3000", "http://localhost:3001"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- Application -------------------------------------------------------
    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    JSON_LOGS: bool = False
    BIND_HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Browser origins permitted to call the API. Comma-separated or a JSON
    # array. NoDecode is required: pydantic-settings would otherwise try to
    # json.loads a plain comma-separated value at the env source and raise.
    CORS_ALLOW_ORIGINS: Annotated[list[str], NoDecode] = []

    # Shared secret for the WebSocket. Optional in development; the readiness
    # probe reports the service unready in production without it.
    WS_AUTH_TOKEN: str | None = None

    # Seconds between simulation steps. Lower it in tests.
    SIMULATION_STEP_SECONDS: float = 1.5

    # ---- LLM ---------------------------------------------------------------
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None

    # ---- AWS ---------------------------------------------------------------
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    # ---- Data stores -------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/asoc"
    REDIS_URL: str = "redis://localhost:6379/0"
    PINECONE_API_KEY: str | None = None
    PINECONE_ENVIRONMENT: str | None = None

    # ---- Policy ------------------------------------------------------------
    OPA_URL: str = "http://localhost:8181"
    VAULT_ADDR: str = "http://localhost:8200"

    @field_validator("CORS_ALLOW_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v):
        if not isinstance(v, str):
            return v
        raw = v.strip()
        if not raw:
            return []
        if raw.startswith("{"):
            raise ValueError("CORS_ALLOW_ORIGINS must be a list, not an object")
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"CORS_ALLOW_ORIGINS is not valid JSON: {exc}") from exc
            return [str(o).strip() for o in parsed if str(o).strip()]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @field_validator("LOG_LEVEL")
    @classmethod
    def _upper_level(cls, v: str) -> str:
        level = v.upper()
        if level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError(f"invalid LOG_LEVEL: {v}")
        return level

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins(self) -> list[str]:
        """Configured origins, or localhost defaults outside production."""
        if self.CORS_ALLOW_ORIGINS:
            return self.CORS_ALLOW_ORIGINS
        return [] if self.is_production else DEV_ORIGINS


settings = Settings()
