from __future__ import annotations

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet

from app.core.config import Settings, _default_config_path


def _get_or_create_key(config_path: str) -> bytes:
    key_path = config_path + ".key"

    if os.path.exists(key_path):
        return open(key_path, "rb").read()

    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    return key


class KeyManager:
    """Encrypts and persists API keys in the local user config directory.

    Uses Fernet symmetric encryption. The encryption key is stored
    alongside the config file (~/.amphoreus/config.json.key).

    This is NOT defense against a determined attacker with filesystem
    access. It protects against casual snooping and accidental exposure.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._fernet = Fernet(
            _get_or_create_key(str(settings.config_path))
        )
        self._config_path = str(settings.config_path)

    def _read_raw(self) -> dict:
        import json

        path = self._config_path
        if os.path.exists(path):
            try:
                return json.loads(open(path, "r", encoding="utf-8").read())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _write_raw(self, data: dict) -> None:
        import json
        import os as _os

        path = self._config_path
        _os.makedirs(_os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── public API ──────────────────────────────────────────────

    def get_deepseek_key(self) -> str:
        data = self._read_raw()
        encrypted = data.get("deepseek_api_key_enc", "")
        if encrypted:
            try:
                return self._fernet.decrypt(encrypted.encode()).decode()
            except Exception:
                return ""
        return data.get("deepseek_api_key", "")

    def set_deepseek_key(self, key: str) -> None:
        data = self._read_raw()
        data["deepseek_api_key_enc"] = (
            self._fernet.encrypt(key.encode()).decode()
        )
        data.pop("deepseek_api_key", None)
        self._write_raw(data)
        self._settings.deepseek_api_key = key

    def get_volcengine_key(self) -> str:
        data = self._read_raw()
        encrypted = data.get("volcengine_api_key_enc", "")
        if encrypted:
            try:
                return self._fernet.decrypt(encrypted.encode()).decode()
            except Exception:
                return ""
        return data.get("volcengine_api_key", "")

    def set_volcengine_key(self, key: str) -> None:
        data = self._read_raw()
        data["volcengine_api_key_enc"] = (
            self._fernet.encrypt(key.encode()).decode()
        )
        data.pop("volcengine_api_key", None)
        self._write_raw(data)
        self._settings.volcengine_api_key = key

    def is_deepseek_configured(self) -> bool:
        return bool(self.get_deepseek_key())

    def is_volcengine_configured(self) -> bool:
        return bool(self.get_volcengine_key())

    @staticmethod
    def has_stored_keys() -> bool:
        """Check if any keys have been stored (for first-launch detection)."""
        data = {}
        path = str(_default_config_path())
        if os.path.exists(path):
            import json

            try:
                data = json.loads(open(path, "r", encoding="utf-8").read())
            except (json.JSONDecodeError, OSError):
                return False
        return bool(
            data.get("deepseek_api_key")
            or data.get("deepseek_api_key_enc")
            or data.get("volcengine_api_key")
            or data.get("volcengine_api_key_enc")
        )
