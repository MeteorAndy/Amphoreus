"""Wiring tests for PR2: foreshadowing T0 block injection into the writers.

The registry/render primitives are unit-tested in test_foreshadowing.py; these
tests prove the WIRING — that NovelWriter and ScreenplayWriter inject the block
as a system message (after the canon block), and skip it when no registry is set.
"""
from __future__ import annotations

import pytest

from app.core.i18n import set_lang, Lang
from app.services.narrative.foreshadowing import Foreshadowing, ForeshadowingRegistry
from app.services.narrative.novel_writer import NovelWriter
from app.services.narrative.screenplay_writer import ScreenplayWriter
from app.services.narrative.types import (
    CanonicalFact, CanonicalFacts, ChapterSpec, WritingOptions,
)


@pytest.fixture(autouse=True)
def _zh():
    set_lang(Lang.ZH)
    yield


class _SpyLLM:
    def __init__(self):
        self.last_messages = None

    async def chat(self, messages, **kwargs):
        self.last_messages = messages
        return "<story>正文</story>"


def _system_texts(messages):
    return "\n".join(m["content"] for m in messages if m["role"] == "system")


def _registry():
    return ForeshadowingRegistry([Foreshadowing(
        id="f1", planted_in_chapter=1, description="断剑之谜尚未揭晓",
        importance="HIGH", status="PLANTED", suggested_resolve_chapter=3,
    )])


def _canon():
    return CanonicalFacts(facts=[CanonicalFact(
        id="c1", topic="t", question="q",
        canonical_answer_zh="母亲", canonical_answer_en="Mother",
        rejected_answers=["父亲"], scope="all",
    )])


def _spec():
    return ChapterSpec(number=2, title="试炼", scene_ids=["s1"], summary="x")


@pytest.mark.asyncio
async def test_novel_injects_foreshadowing_block():
    llm = _SpyLLM()
    nw = NovelWriter(llm)
    from app.services.narrative.foreshadowing import render_foreshadowing_block
    block = render_foreshadowing_block(_registry(), 2, True)
    await nw._generate_chapter(_spec(), "场景日志", "", "", "2500字",
                               WritingOptions(format="novel"),
                               foreshadowing_block=block)
    assert "断剑之谜" in _system_texts(llm.last_messages)


@pytest.mark.asyncio
async def test_novel_no_registry_no_foreshadowing():
    llm = _SpyLLM()
    nw = NovelWriter(llm)
    await nw._generate_chapter(_spec(), "场景日志", "", "", "2500字",
                               WritingOptions(format="novel"))
    sys_msgs = [m for m in llm.last_messages if m["role"] == "system"]
    assert len(sys_msgs) == 1  # base prompt only


@pytest.mark.asyncio
async def test_novel_foreshadowing_after_canon():
    """Injection order contract: base -> canon -> foreshadowing -> user."""
    llm = _SpyLLM()
    nw = NovelWriter(llm)
    from app.services.narrative.foreshadowing import render_foreshadowing_block
    block = render_foreshadowing_block(_registry(), 2, True)
    await nw._generate_chapter(_spec(), "场景日志", "", "", "2500字",
                               WritingOptions(format="novel", canonical_facts=_canon()),
                               foreshadowing_block=block)
    msgs = [m["content"] for m in llm.last_messages]
    canon_idx = next(i for i, c in enumerate(msgs) if "母亲" in c)
    fore_idx = next(i for i, c in enumerate(msgs) if "断剑之谜" in c)
    assert canon_idx < fore_idx


@pytest.mark.asyncio
async def test_screenplay_injects_foreshadowing_block():
    llm = _SpyLLM()
    sw = ScreenplayWriter(llm)
    from app.services.narrative.foreshadowing import render_foreshadowing_block
    block = render_foreshadowing_block(_registry(), 2, True)
    await sw._generate_screenplay("场景日志", "林辰", "", block)
    assert "断剑之谜" in _system_texts(llm.last_messages)


@pytest.mark.asyncio
async def test_screenplay_no_block_when_empty():
    llm = _SpyLLM()
    sw = ScreenplayWriter(llm)
    await sw._generate_screenplay("场景日志", "林辰")
    sys_msgs = [m for m in llm.last_messages if m["role"] == "system"]
    assert len(sys_msgs) == 1

