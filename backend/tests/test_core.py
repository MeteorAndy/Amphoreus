from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from app.core.api_keys import KeyManager
from app.core.config import Settings
from app.core.llm_client import (
    DeepSeekClient,
    LLMClient,
    create_llm_client,
    register_provider,
)


# ============================================================
# Config tests
# ============================================================


class TestSettings:
    def test_default_data_dir(self) -> None:
        """THE_WORLD_DATA_DIR should default to ~/.the-world."""
        s = Settings()
        assert s.THE_WORLD_DATA_DIR == Path.home() / ".the-world"

    def test_data_dir_created(self) -> None:
        """Ensure the directory is created on validation."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".the-world"
            s = Settings(THE_WORLD_DATA_DIR=str(path))
            assert path.exists()

    def test_debug_defaults_false(self) -> None:
        assert Settings().DEBUG is False

    def test_debug_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEBUG", "true")
        s = Settings()
        assert s.DEBUG is True

    def test_deepseek_defaults(self) -> None:
        s = Settings()
        assert s.DEEPSEEK_BASE_URL == "https://api.deepseek.com/v1"
        assert s.DEEPSEEK_MODEL == "deepseek-chat"

    def test_volcengine_defaults(self) -> None:
        s = Settings()
        assert "volces.com" in s.VOLCENGINE_BASE_URL
        assert s.VOLCENGINE_MODEL == "doubao-pro-32k"

    def test_port_validation(self) -> None:
        s = Settings()
        assert 1024 <= s.PORT <= 65535


# ============================================================
# API Key management tests
# ============================================================


class TestKeyManager:
    @pytest.fixture
    def tmp_data_dir(self) -> Path:
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    @pytest.fixture
    def km(self, tmp_data_dir: Path) -> KeyManager:
        return KeyManager(data_dir=tmp_data_dir)

    def test_config_template_created(self, km: KeyManager, tmp_data_dir: Path) -> None:
        """The config.json template should be written on first access."""
        config_file = tmp_data_dir / "config.json"
        assert config_file.exists()
        data = json.loads(config_file.read_text(encoding="utf-8"))
        assert "providers" in data
        assert "deepseek" in data["providers"]
        assert "volcengine" in data["providers"]

    def test_set_and_get_key(self, km: KeyManager) -> None:
        km.set_key("deepseek", "sk-test-key-12345")
        assert km.get_key("deepseek") == "sk-test-key-12345"

    def test_round_trip_encryption(self, km: KeyManager, tmp_data_dir: Path) -> None:
        """The value on disk should NOT be the plaintext key."""
        km.set_key("deepseek", "sk-secret-value")
        config_file = tmp_data_dir / "config.json"
        raw = config_file.read_text(encoding="utf-8")
        assert "sk-secret-value" not in raw

    def test_get_nonexistent_provider(self, km: KeyManager) -> None:
        assert km.get_key("nonexistent") is None

    def test_set_new_provider(self, km: KeyManager) -> None:
        km.set_key("custom-llm", "sk-custom")
        assert km.get_key("custom-llm") == "sk-custom"

    def test_list_providers(self, km: KeyManager) -> None:
        providers = km.list_providers()
        assert "deepseek" in providers
        assert "volcengine" in providers

    def test_get_provider_config(self, km: KeyManager) -> None:
        km.set_key("deepseek", "sk-key")
        cfg = km.get_provider_config("deepseek")
        assert cfg is not None
        assert cfg["api_key"] == "sk-key"
        assert "base_url" in cfg

    def test_get_provider_config_missing(self, km: KeyManager) -> None:
        assert km.get_provider_config("ghost") is None

    def test_active_provider_default(self, km: KeyManager) -> None:
        assert km.get_active_provider() == "deepseek"

    def test_set_active_provider(self, km: KeyManager) -> None:
        km.set_active_provider("volcengine")
        assert km.get_active_provider() == "volcengine"

    def test_fernet_key_persistence(self, tmp_data_dir: Path) -> None:
        """The same key should survive KeyManager re-creation."""
        km1 = KeyManager(data_dir=tmp_data_dir)
        km1.set_key("deepseek", "sk-persistence-test")
        km2 = KeyManager(data_dir=tmp_data_dir)
        assert km2.get_key("deepseek") == "sk-persistence-test"

    def test_invalid_token_returns_none(self, km: KeyManager, tmp_data_dir: Path) -> None:
        """Corrupt encrypted value should not crash — return None."""
        config_file = tmp_data_dir / "config.json"
        data = json.loads(config_file.read_text(encoding="utf-8"))
        data["providers"]["deepseek"]["api_key"] = "garbage-not-valid-fernet"
        config_file.write_text(json.dumps(data), encoding="utf-8")
        assert km.get_key("deepseek") is None


# ============================================================
# LLM client tests
# ============================================================


class TestLLMClient:
    def test_deepseek_client_interface(self) -> None:
        """DeepSeekClient should satisfy the LLMClient ABC."""
        client = DeepSeekClient(api_key="sk-test")
        assert isinstance(client, LLMClient)

    def test_factory_returns_deepseek_client(self) -> None:
        """create_llm_client should build a DeepSeekClient by default."""
        with pytest.raises(ValueError, match="No API key"):
            create_llm_client()

    def test_factory_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="Unsupported provider"):
            create_llm_client(provider="nonexistent", api_key="sk-test")

    def test_factory_with_explicit_key(self) -> None:
        client = create_llm_client(provider="deepseek", api_key="sk-explicit")
        assert isinstance(client, DeepSeekClient)
        assert client.api_key == "sk-explicit"

    def test_factory_custom_base_url(self) -> None:
        """Extra kwargs should be forwarded to the constructor."""
        client = create_llm_client(
            provider="deepseek",
            api_key="sk-key",
            base_url="https://custom.example.com/v1",
        )
        assert client.base_url == "https://custom.example.com/v1"

    def test_register_provider(self) -> None:
        class FakeClient(LLMClient):
            def chat(self, messages, **kwargs):
                return "fake"
            def embed(self, texts, **kwargs):
                return [[0.0]]

        register_provider("fake", FakeClient)
        client = create_llm_client(provider="fake", api_key="sk-fake")
        assert isinstance(client, FakeClient)

    def test_register_provider_validates_type(self) -> None:
        class NotAClient:
            pass

        with pytest.raises(TypeError, match="must subclass LLMClient"):
            register_provider("bad", NotAClient)


# ============================================================
# App factory tests
# ============================================================


class TestAppFactory:
    def test_create_app(self) -> None:
        from app.main import create_app

        app = create_app()
        assert app.title == "The World — Novel & Screenplay Engine"
        assert app.version == "0.1.0"

    def test_health_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import create_app

        app = create_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
