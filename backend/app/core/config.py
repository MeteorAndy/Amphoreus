from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    All configuration flows through this single source of truth.
    Secrets (API keys) are managed separately by KeyManager — not stored here.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        validate_default=False,
    )

    # -- Paths -----------------------------------------------------------------
    THE_WORLD_DATA_DIR: Path = Field(
        default=Path.home() / ".the-world",
        description="Directory for config, keys, and persistent data",
    )

    # -- Runtime behaviour ----------------------------------------------------
    DEBUG: bool = Field(
        default=False,
        description="Enable debug-level logging and verbose error responses",
    )

    # -- LLM provider defaults ------------------------------------------------
    DEFAULT_LLM_PROVIDER: str = Field(
        default="deepseek",
        description="Default LLM provider name (deepseek, volcengine, …)",
    )

    DEEPSEEK_BASE_URL: str = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek API base URL (OpenAI-compatible endpoint)",
    )

    DEEPSEEK_MODEL: str = Field(
        default="deepseek-chat",
        description="DeepSeek model identifier for story generation",
    )

    DEEPSEEK_EMBED_MODEL: str = Field(
        default="deepseek-embed",
        description="DeepSeek model identifier for embeddings",
    )

    VOLCENGINE_BASE_URL: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3",
        description="Volcengine/Doubao API base URL (OpenAI-compatible)",
    )

    VOLCENGINE_MODEL: str = Field(
        default="doubao-pro-32k",
        description="Volcengine model identifier for VLM / embedding",
    )

    # -- Server ---------------------------------------------------------------
    HOST: str = Field(default="127.0.0.1", description="Server bind address")
    PORT: int = Field(default=8000, description="Server bind port", ge=1024, le=65535)

    # --------------------------------------------------------------------------
    @field_validator("THE_WORLD_DATA_DIR", mode="before")
    @classmethod
    def expand_user_dir(cls, v: Path | str) -> Path:
        return Path(v).expanduser().resolve()

    @field_validator("THE_WORLD_DATA_DIR")
    @classmethod
    def ensure_data_dir(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v


# Module-level singleton — importers get a pre-loaded, validated config.
settings = Settings()
