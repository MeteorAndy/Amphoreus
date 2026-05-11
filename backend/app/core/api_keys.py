from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

# ---------------------------------------------------------------------------
# Fernet helpers — a machine-local key that stays stable across restarts.
# ---------------------------------------------------------------------------

_KEY_FILE = "fernet.key"


def _load_or_create_fernet_key(data_dir: Path) -> bytes:
    """Return a stable Fernet key stored under *data_dir*.

    The key is created once on first access and reused thereafter so that
    previously encrypted values remain decryptable.
    """
    key_path = data_dir / _KEY_FILE
    if key_path.exists():
        return key_path.read_bytes()
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    return key


def _build_fernet(data_dir: Path) -> Fernet:
    return Fernet(_load_or_create_fernet_key(data_dir))


# ---------------------------------------------------------------------------
# Config file schema
# ---------------------------------------------------------------------------

_CONFIG_FILE = "config.json"

_DEFAULT_CONFIG: dict = {
    "providers": {
        "deepseek": {
            "api_key": "",
            "base_url": settings.DEEPSEEK_BASE_URL,
            "model": settings.DEEPSEEK_MODEL,
        },
        "volcengine": {
            "api_key": "",
            "base_url": settings.VOLCENGINE_BASE_URL,
            "model": settings.VOLCENGINE_MODEL,
        },
    },
    "active_provider": settings.DEFAULT_LLM_PROVIDER,
}


def _config_path(data_dir: Path) -> Path:
    return data_dir / _CONFIG_FILE


def _ensure_config(data_dir: Path) -> dict:
    """Return the config dict; create a default template if the file is missing."""
    path = _config_path(data_dir)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(_DEFAULT_CONFIG, indent=2), encoding="utf-8")
    return dict(_DEFAULT_CONFIG)  # shallow copy so callers can mutate safely


def ensure_config_skeleton() -> None:
    """Public entry point: write the default config template if missing.

    Idempotent — safe to call at startup and in lifespan hooks.
    """
    _ensure_config(settings.THE_WORLD_DATA_DIR)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class KeyManager:
    """Persistent, encrypted API-key storage.

    Keys are written to ``~/.the-world/config.json`` with the ``api_key``
    field encrypted via Fernet (AES-128-CBC + HMAC-SHA256).  Non-secret
    fields such as *base_url* and *model* are stored in plain text.

    Usage
    -----
    >>> km = KeyManager()
    >>> km.set_key("deepseek", "sk-…")
    >>> km.get_key("deepseek")
    'sk-…'
    >>> km.list_providers()
    ['deepseek', 'volcengine']
    """

    data_dir: Path = field(default_factory=lambda: settings.THE_WORLD_DATA_DIR)
    _fernet: Fernet = field(init=False)
    _config: dict = field(init=False)

    def __post_init__(self) -> None:
        self._fernet = _build_fernet(self.data_dir)
        self._config = _ensure_config(self.data_dir)

    # -- public helpers -------------------------------------------------------

    def get_key(self, provider: str) -> Optional[str]:
        """Return the decrypted API key for *provider*, or *None*."""
        encrypted = self._config.get("providers", {}).get(provider, {}).get("api_key")
        if not encrypted:
            return None
        try:
            return self._fernet.decrypt(encrypted.encode()).decode()
        except InvalidToken:
            return None

    def set_key(self, provider: str, api_key: str) -> None:
        """Encrypt and persist *api_key* for *provider*.

        If the provider does not yet exist in config a minimal entry is
        created with empty *base_url* and *model*.
        """
        providers = self._config.setdefault("providers", {})
        if provider not in providers:
            providers[provider] = {"api_key": "", "base_url": "", "model": ""}
        providers[provider]["api_key"] = self._fernet.encrypt(api_key.encode()).decode()
        self._flush()

    def list_providers(self) -> list[str]:
        """Return the list of known provider names."""
        return list(self._config.get("providers", {}).keys())

    def get_provider_config(self, provider: str) -> Optional[dict]:
        """Return the full (plain-text) config dict for *provider*.

        The ``api_key`` field is decrypted; all other fields are returned
        as stored.
        """
        raw = self._config.get("providers", {}).get(provider)
        if raw is None:
            return None
        cfg = dict(raw)
        raw_key = cfg.get("api_key", "")
        if raw_key:
            try:
                cfg["api_key"] = self._fernet.decrypt(raw_key.encode()).decode()
            except InvalidToken:
                cfg["api_key"] = None
        return cfg

    def get_active_provider(self) -> str:
        """Return the currently active provider name."""
        return self._config.get("active_provider", settings.DEFAULT_LLM_PROVIDER)

    def set_active_provider(self, provider: str) -> None:
        """Switch the active provider."""
        self._config["active_provider"] = provider
        self._flush()

    # -- internal -------------------------------------------------------------

    def _flush(self) -> None:
        _config_path(self.data_dir).write_text(
            json.dumps(self._config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
