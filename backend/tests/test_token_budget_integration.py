"""Integration tests for T2-④ token-budget measurement in NovelWriter.

The critical guarantee: with token_budget unset (the default), the messages sent
to the LLM are byte-for-byte identical to the pre-feature assembly, and no report
is produced. When enabled, the SAME messages are still sent (measure-only) and a
ChapterBudget is accumulated.

    uv run pytest tests/test_token_budget_integration.py -v
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.services.narrative.novel_writer import NovelWriter
from app.services.narrative.token_budget import TokenBudgetConfig
from app.services.narrative.types import (
    ChapterPlan,
    ChapterSpec,
    WritingOptions,
)


def _plan() -> ChapterPlan:
    return ChapterPlan(chapters=[
        ChapterSpec(number=1, title="起", scene_ids=[], summary="开端"),
        ChapterSpec(number=2, title="承", scene_ids=[], summary="发展"),
    ])


def _writer_with_capture():
    """NovelWriter whose LLM records every messages list it is sent."""
    captured: list[list[dict]] = []

    async def _chat(messages, **kwargs):
        captured.append([dict(m) for m in messages])
        return "## 正文\n\n这是生成的章节内容。"

    llm = AsyncMock()
    llm.chat = AsyncMock(side_effect=_chat)
    return NovelWriter(llm), captured


@pytest.mark.asyncio
async def test_budget_off_messages_are_baseline():
    """Capture the exact messages sent when the feature is OFF (the golden)."""
    writer, captured = _writer_with_capture()
    opts = WritingOptions(format="novel")
    await writer.write_chapters(_plan(), [], [], opts)
    assert len(captured) == 2  # one chat call per chapter
    # baseline: system + user only (no canon/foreshadowing/phase here)
    assert [m["role"] for m in captured[0]] == ["system", "user"]


@pytest.mark.asyncio
async def test_budget_on_does_not_change_messages():
    """Enabling the budget must send the IDENTICAL messages as when off."""
    off_writer, off_cap = _writer_with_capture()
    await off_writer.write_chapters(_plan(), [], [], WritingOptions(format="novel"))

    on_writer, on_cap = _writer_with_capture()
    budget = TokenBudgetConfig(enabled=True, budget_tokens=8000)
    acc: list = []
    await on_writer.write_chapters(
        _plan(), [], [], WritingOptions(format="novel", token_budget=budget),
        budget_acc=acc,
    )

    # byte-for-byte identical message lists
    assert on_cap == off_cap
    # and measurement happened
    assert len(acc) == 2
    assert acc[0].chapter_number == 1
    assert acc[0].total_tokens > 0


@pytest.mark.asyncio
async def test_budget_acc_none_when_disabled_config():
    """A config attached but enabled=False stays a no-op (no accumulation)."""
    writer, _ = _writer_with_capture()
    acc: list = []
    cfg = TokenBudgetConfig(enabled=False)
    await writer.write_chapters(
        _plan(), [], [], WritingOptions(format="novel", token_budget=cfg),
        budget_acc=acc,
    )
    assert acc == []
