from __future__ import annotations

from typing import AsyncIterator

from app.core.config import get_settings
from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager

_llm_client: LLMClient | None = None
_memory_manager: MemoryManager | None = None


async def get_llm_client() -> AsyncIterator[LLMClient]:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    yield _llm_client


async def get_memory_manager() -> AsyncIterator[MemoryManager]:
    global _memory_manager
    if _memory_manager is None:
        settings = get_settings()
        _memory_manager = MemoryManager(settings)
        await _memory_manager.initialize()
    yield _memory_manager
