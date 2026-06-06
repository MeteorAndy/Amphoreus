"""Shared test fixtures for Amphoreus backend tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock(spec=LLMClient)
    llm.chat.return_value = '{"answer": "test response"}'
    llm.chat_json.return_value = {"answer": "test response"}
    return llm


@pytest.fixture
def mock_memory() -> MagicMock:
    memory = MagicMock(spec=MemoryManager)
    memory.ov = MagicMock()
    memory.ov.write_entry = MagicMock()
    memory.ov.read_entry = MagicMock(return_value=None)
    return memory
