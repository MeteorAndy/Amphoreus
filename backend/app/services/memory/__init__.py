from __future__ import annotations

from app.core.config import Settings
from app.services.memory.kuzu_store import KuzuStore
from app.services.memory.openviking_store import OpenVikingStore


class MemoryManager:
    """Facade exposing both stores through a single injectable dependency."""

    def __init__(self, settings: Settings) -> None:
        self._openviking = OpenVikingStore(settings)
        self._kuzu = KuzuStore(settings)

    @property
    def openviking(self) -> OpenVikingStore:
        return self._openviking

    @property
    def kuzu(self) -> KuzuStore:
        return self._kuzu

    async def initialize(self) -> None:
        """Call ensure_schema on both stores."""
        self._openviking.ensure_schema()
        self._kuzu.ensure_schema()

    async def close(self) -> None:
        """Release resources (no-op for these stores)."""
        pass
