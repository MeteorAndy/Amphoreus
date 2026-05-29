from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager

from .types import EvaluationContext, GuardianIssue


class BaseValidator(ABC):
    """Abstract base for all validators."""

    def __init__(self, llm: LLMClient, memory: MemoryManager) -> None:
        self._llm = llm
        self._memory = memory

    @abstractmethod
    async def evaluate(self, context: EvaluationContext) -> list[GuardianIssue]:
        ...
