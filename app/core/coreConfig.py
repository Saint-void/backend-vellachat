"""
Application configuration.

Settings are loaded once at import time and fail fast if anything
required is missing or malformed. Every other module reads config
through this object -- nothing reads os.environ directly.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "Vella Business API"
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    # Pooled connection (Supabase Supavisor, port 6543). Used by the
    # running app -- FastAPI's async workers open many short-lived
    # connections, and pooling keeps that from exhausting Postgres'
    # connection limit.
    DATABASE_URL: str

    # Direct connection (port 5432). Used only by Alembic. Migrations
    # issue DDL and prepared statements that don't reliably survive a
    # transaction-mode pooler -- give Alembic its own unpooled path.
    DIRECT_DATABASE_URL: str

    # --- Auth ---
    # e.g. https://xxxxx.supabase.co -- used to discover the project's
    # JWKS endpoint for verifying Supabase-issued session JWTs locally.
    # No secret key needed for this: Supabase signs session JWTs with
    # an asymmetric key by default, so verification only needs the
    # public key, which this URL leads to.
    SUPABASE_URL: str
    SUPABASE_PUBLISHABLE_KEY: str

    # --- AI ---
    # "ollama" for local development, "openai" for production.
    AI_PROVIDER: str = Field(default="ollama", pattern="^(ollama|openai)$")
    AI_EMBEDDING_DIMENSIONS: int = 768

    # Ollama (local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "qwen2.5:3b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # OpenAI
    OPENAI_API_KEY: str | None = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    # --- Knowledge ---
    KNOWLEDGE_STORAGE_DIR: str = ".data/knowledge_uploads"
    KNOWLEDGE_MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024

    # --- CORS ---
    # Comma-separated, e.g. "http://localhost:3000,https://app.example.com".
    # Kept as a plain str field on purpose: pydantic-settings tries to
    # JSON-decode env vars for List[str] fields before any validator
    # runs, which raises on an ordinary comma-separated string. Use
    # cors_origins_list below wherever an actual list is needed.
    CORS_ORIGINS: str = ""

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, str) and value.lower() in {"release", "prod", "production"}:
            return False
        return value

    @field_validator("DATABASE_URL", "DIRECT_DATABASE_URL")
    @classmethod
    def validate_postgres_url(cls, value: str) -> str:
        if not value.startswith("postgresql"):
            raise ValueError("must be a postgresql:// (or postgresql+asyncpg://) connection string")
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor.

    lru_cache means Settings() is constructed exactly once per process,
    so a missing or malformed env var raises immediately on first
    access (which happens at import time in main.py) instead of
    surfacing later as a confusing runtime error mid-request.
    """
    return Settings()


settings = get_settings()
