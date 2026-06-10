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


@pytest.fixture
def real_kuzu(tmp_path):
    """A REAL embedded KuzuStore on a temp dir — for round-trip tests that must
    execute actual Cypher (mock tests can't catch a CONTAINS fragment that
    matches nothing). Teardown drops the connection/database references so
    Windows releases the file locks before tmp_path cleanup."""
    from app.core.config import Settings
    from app.services.memory.kuzu_store import KuzuStore

    settings = Settings(data_dir=tmp_path)
    store = KuzuStore(settings)
    store.ensure_schema()
    yield store
    store._conn = None
    store._db = None
