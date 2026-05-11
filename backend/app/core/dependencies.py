from __future__ import annotations

from functools import lru_cache
from typing import AsyncIterator

from fastapi import Depends, Request

from app.core.api_keys import KeyManager
from app.core.config import Settings, settings
from app.core.llm_client import LLMClient, create_llm_client


# ---------------------------------------------------------------------------
# Settings — cached once per process
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance.

    Cached so that config file reads happen only on the first call.
    In tests, call ``get_settings.cache_clear()`` to reload.
    """
    return settings


# ---------------------------------------------------------------------------
# KeyManager — cached once per process (file I/O happens once at startup)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_key_manager() -> KeyManager:
    """Return a cached KeyManager bound to the configured data directory."""
    return KeyManager(data_dir=get_settings().THE_WORLD_DATA_DIR)


# ---------------------------------------------------------------------------
# LLM client — request-scoped (each request can use a different provider)
# ---------------------------------------------------------------------------


async def get_llm_client(
    request: Request,
    km: KeyManager = Depends(get_key_manager),
) -> AsyncIterator[LLMClient]:
    """Resolve and yield an LLM client for the current request.

    The provider is read from the ``X-LLM-Provider`` header or falls back
    to the active provider in config.  The client is closed / cleaned up
    when the request finishes.
    """
    provider = request.headers.get(
        "x-llm-provider",
        km.get_active_provider(),
    )
    client = create_llm_client(provider=provider, km=km)
    try:
        yield client
    finally:
        if hasattr(client, "_client") and hasattr(client._client, "aclose"):
            await client._client.aclose()
