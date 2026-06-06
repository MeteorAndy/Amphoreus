from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    return Path.home() / ".amphoreus"


def _default_config_path() -> Path:
    return _default_data_dir() / "config.json"


def _load_user_config() -> dict:
    path = _default_config_path()
    if path.exists():
        try:
            return json.loads(path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_user_config(data: dict) -> None:
    path = _default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Data paths ──────────────────────────────────────────────
    data_dir: Path = Field(default_factory=_default_data_dir)
    config_path: Path = Field(default_factory=_default_config_path)

    # ── LLM: DeepSeek (story engine) ────────────────────────────
    deepseek_api_key: str = Field(
        default="",
        description="DeepSeek API key for story engine (deepseek-v4-flash)",
    )
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/v1",
    )
    deepseek_model: str = Field(default="deepseek-v4-flash")
    deepseek_timeout: float = Field(
        default=120.0,
        description="Per-request timeout in seconds for DeepSeek calls "
        "(also the max idle gap between streaming chunks).",
    )
    deepseek_max_retries: int = Field(
        default=3,
        description="Number of attempts for a retryable DeepSeek failure "
        "(timeout / 5xx / network). Owned by LLMClient; SDK retries are disabled.",
    )

    # ── LLM: Volcengine (OpenViking VLM + Embedding) ────────────
    volcengine_api_key: str = Field(
        default="",
        description="Volcengine API key for OpenViking VLM/Embedding",
    )
    volcengine_vlm_model: str = Field(default="doubao-seed-2-0-pro-260215")
    volcengine_embedding_model: str = Field(default="doubao-embedding-vision-251215")

    # ── LLM fallback flags ──────────────────────────────────────
    openviking_use_deepseek: bool = Field(
        default=False,
        description="Fall back to DeepSeek for OpenViking VLM (skip Volcengine)",
    )
    embedding_use_local: bool = Field(
        default=False,
        description="Use local Ollama bge-m3 for embeddings (skip Volcengine)",
    )

    # ── Server ──────────────────────────────────────────────────
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=5001)
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "tauri://localhost",
        ],
    )

    # ── Runtime ─────────────────────────────────────────────────
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # ── Validation ──────────────────────────────────────────────

    @field_validator("data_dir", mode="before")
    @classmethod
    def _resolve_data_dir(cls, v: str | Path | None) -> Path:
        if v is None:
            return _default_data_dir()
        return Path(v).expanduser().resolve()

    def load_from_user_config(self) -> None:
        """Merge values from ~/.amphoreus/config.json (user-facing keys)."""
        data = _load_user_config()
        if not data:
            return
        for key in ("deepseek_api_key", "volcengine_api_key"):
            if data.get(key) and not getattr(self, key):
                object.__setattr__(self, key, data[key])

    def save_user_config(self) -> None:
        """Persist API keys to ~/.amphoreus/config.json."""
        existing = _load_user_config()
        existing["deepseek_api_key"] = self.deepseek_api_key or existing.get("deepseek_api_key", "")
        existing["volcengine_api_key"] = self.volcengine_api_key or existing.get("volcengine_api_key", "")
        _save_user_config(existing)

    @property
    def deepseek_api_key_effective(self) -> str:
        return self.deepseek_api_key or os.environ.get("DEEPSEEK_API_KEY", "")

    @property
    def volcengine_api_key_effective(self) -> str:
        return self.volcengine_api_key or os.environ.get("VOLCENGINE_API_KEY", "")


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.load_from_user_config()
    return _settings
