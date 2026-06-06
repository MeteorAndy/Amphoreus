"""Tests for canonical-facts hard-constraint injection into both writers."""
from __future__ import annotations

import pytest

from app.core.i18n import set_lang, Lang
from app.services.narrative.novel_writer import NovelWriter
from app.services.narrative.screenplay_writer import ScreenplayWriter
from app.services.narrative.types import CanonicalFact, CanonicalFacts, WritingOptions


@pytest.fixture(autouse=True)
def _zh():
    set_lang(Lang.ZH)
    yield


class _SpyLLM:
    """Captures the messages of the last chat() call."""

    def __init__(self):
        self.last_messages = None

    async def chat(self, messages, **kwargs):
        self.last_messages = messages
        return "<story>正文</story>"


def _canon():
    return CanonicalFacts(facts=[CanonicalFact(
        id="f-1", topic="family_truth", question="谁写进书？",
        canonical_answer_zh="母亲，第97页", canonical_answer_en="Mother, p97",
        rejected_answers=["父亲"], scope="all",
    )])


def _system_texts(messages):
    return "\n".join(m["content"] for m in messages if m["role"] == "system")


@pytest.mark.asyncio
async def test_novel_generate_injects_canon():
    llm = _SpyLLM()
    nw = NovelWriter(llm)
    opts = WritingOptions(format="novel", canonical_facts=_canon())
    from app.services.narrative.types import ChapterSpec
    spec = ChapterSpec(number=1, title="开篇", scene_ids=["s1"], summary="x")
    await nw._generate_chapter(spec, "场景日志", "", "", "2500字", opts)
    assert "绝对不可违背" in _system_texts(llm.last_messages)
    assert "母亲，第97页" in _system_texts(llm.last_messages)


@pytest.mark.asyncio
async def test_novel_enhance_injects_canon():
    llm = _SpyLLM()
    nw = NovelWriter(llm)
    await nw._enhance_prose("一段散文。", canon_block="权威设定块")
    assert "权威设定块" in _system_texts(llm.last_messages)


@pytest.mark.asyncio
async def test_novel_no_canon_no_extra_system():
    llm = _SpyLLM()
    nw = NovelWriter(llm)
    opts = WritingOptions(format="novel")  # canonical_facts=None
    from app.services.narrative.types import ChapterSpec
    spec = ChapterSpec(number=1, title="开篇", scene_ids=["s1"], summary="x")
    await nw._generate_chapter(spec, "场景日志", "", "", "2500字", opts)
    sys_msgs = [m for m in llm.last_messages if m["role"] == "system"]
    assert len(sys_msgs) == 1  # only the base system prompt


@pytest.mark.asyncio
async def test_screenplay_generate_injects_canon():
    llm = _SpyLLM()
    sw = ScreenplayWriter(llm)
    await sw._generate_screenplay("场景日志", "林辰", canon_block="权威：母亲第97页")
    assert "权威：母亲第97页" in _system_texts(llm.last_messages)


@pytest.mark.asyncio
async def test_screenplay_enhance_injects_canon():
    llm = _SpyLLM()
    sw = ScreenplayWriter(llm)
    await sw._enhance_screenplay("剧本文本", canon_block="权威约束块")
    assert "权威约束块" in _system_texts(llm.last_messages)


@pytest.mark.asyncio
async def test_screenplay_no_canon_no_extra_system():
    llm = _SpyLLM()
    sw = ScreenplayWriter(llm)
    await sw._generate_screenplay("场景日志", "林辰")
    sys_msgs = [m for m in llm.last_messages if m["role"] == "system"]
    assert len(sys_msgs) == 1
