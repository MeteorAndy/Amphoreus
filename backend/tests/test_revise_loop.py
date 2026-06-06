"""Tests for the T1-① post-generation quality loop (reviser + NovelWriter wiring).

Pure reviser logic is zero-LLM and runs in milliseconds; the wiring tests mock
the LLM so no network/integration path is touched (per project test discipline).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.narrative.canon_verifier import CanonReport, Violation
from app.services.narrative.cliche_scanner import ClicheHit, ClicheReport
from app.services.narrative.novel_writer import NovelWriter
from app.services.narrative.reviser import build_revise_directive, needs_revision
from app.services.narrative.types import ReviseConfig, WritingOptions


CFG = ReviseConfig()


def _cliche(score=0.0, hits=None):
    return ClicheReport(hits=hits or [], ai_flavor_score=score)


def _hit(name, severity):
    return ClicheHit(name, severity, "cat", "勾起嘴角", "改写为具体动作")


def _canon(*kinds):
    vs = [Violation("f1", "出身", k, "high" if k == "contradiction" else "low", "ev")
          for k in kinds]
    return CanonReport(violations=vs, checked=len(vs), clean="contradiction" not in kinds)


# --- needs_revision -------------------------------------------------------

def test_clean_chapter_needs_no_revision():
    assert needs_revision(_cliche(), _canon(), [], CFG) is False


def test_disabled_config_never_triggers():
    cfg = ReviseConfig(enabled=False)
    assert needs_revision(_cliche(score=99), _canon("contradiction"), [("x" * 9, 9)], cfg) is False


def test_canon_contradiction_triggers():
    assert needs_revision(_cliche(), _canon("contradiction"), [], CFG) is True


def test_unconfirmed_canon_does_not_trigger():
    assert needs_revision(_cliche(), _canon("unconfirmed"), [], CFG) is False


def test_critical_cliche_triggers():
    assert needs_revision(_cliche(hits=[_hit("a", "critical")]), None, [], CFG) is True


def test_score_over_threshold_triggers():
    assert needs_revision(_cliche(score=12.0), None, [], CFG) is True


def test_repeat_at_trigger_count_triggers():
    assert needs_revision(_cliche(), None, [("像干涸的血迹", 3)], CFG) is True


def test_repeat_below_trigger_does_not():
    assert needs_revision(_cliche(), None, [("像干涸的血迹", 2)], CFG) is False


# --- build_revise_directive ----------------------------------------------

def test_clean_yields_empty_directive():
    assert build_revise_directive(_cliche(), _canon(), [], CFG, is_zh=True) == ""


def test_directive_includes_replacement_hint():
    d = build_revise_directive(
        _cliche(hits=[_hit("mouth", "critical")]), None, [], CFG, is_zh=True
    )
    assert "改写为具体动作" in d and d.startswith("以下是")


def test_directive_lists_canon_topic():
    d = build_revise_directive(_cliche(), _canon("contradiction"), [], CFG, is_zh=False)
    assert "Canon conflict" in d and "出身" in d


def test_directive_dedupes_repeated_hit_names():
    hits = [_hit("mouth", "critical"), _hit("mouth", "critical")]
    d = build_revise_directive(_cliche(hits=hits), None, [], CFG, is_zh=True)
    assert d.count("改写为具体动作") == 1


def test_directive_capped_at_max():
    cfg = ReviseConfig(max_directives=3)
    hits = [
        ClicheHit(f"n{i}", "critical", "c", f"ex{i}", f"hint{i}") for i in range(10)
    ]
    d = build_revise_directive(_cliche(hits=hits), None, [], cfg, is_zh=True)
    assert d.count("\n- ") == 3


def test_directive_cap_preserves_canon_priority():
    # canon contradictions are appended first, so truncation must keep them.
    cfg = ReviseConfig(max_directives=2)
    hits = [ClicheHit(f"n{i}", "critical", "c", f"ex{i}", f"h{i}") for i in range(10)]
    d = build_revise_directive(_cliche(hits=hits), _canon("contradiction"), [], cfg, True)
    assert "事实冲突" in d and d.count("\n- ") == 2


def test_directive_repeats_zh_and_en():
    dz = build_revise_directive(_cliche(), None, [("像干涸的血迹", 3)], CFG, is_zh=True)
    assert "重复" in dz and "出现3次" in dz
    de = build_revise_directive(_cliche(), None, [("dried blood", 3)], CFG, is_zh=False)
    assert "Repetition" in de and "3×" in de


def test_directive_cliche_en_rendering():
    d = build_revise_directive(
        _cliche(hits=[_hit("mouth", "critical")]), None, [], CFG, is_zh=False
    )
    assert d.startswith("The following") and "Cliche ·" in d and "改写为具体动作" in d



def test_warning_hits_only_when_score_high():
    warn = [_hit("seems", "warning")]
    # score below threshold: warning not listed (and nothing triggers)
    assert build_revise_directive(_cliche(score=0, hits=warn), None, [], CFG, True) == ""
    # score over threshold: warning is included
    d = build_revise_directive(_cliche(score=20, hits=warn), None, [], CFG, True)
    assert "改写为具体动作" in d


# --- NovelWriter._revise_chapter wiring (mocked LLM) ----------------------

@pytest.mark.asyncio
async def test_revise_skips_llm_when_clean():
    llm = AsyncMock()
    nw = NovelWriter(llm)
    opts = WritingOptions(format="novel", revise=ReviseConfig())
    out = await nw._revise_chapter("一段干净的正文，没有任何问题。", opts)
    assert out == "一段干净的正文，没有任何问题。"
    llm.chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_revise_rewrites_when_flagged():
    llm = AsyncMock()
    llm.chat.return_value = "<story>改写后的干净正文。</story>"
    nw = NovelWriter(llm)
    opts = WritingOptions(format="novel", revise=ReviseConfig(max_rounds=1))
    flagged = "他嘴角勾起，心中一紧。" * 3
    out = await nw._revise_chapter(flagged, opts)
    assert out == "改写后的干净正文。"
    llm.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_revise_keeps_draft_on_empty_rewrite():
    llm = AsyncMock()
    llm.chat.return_value = "   "
    nw = NovelWriter(llm)
    opts = WritingOptions(format="novel", revise=ReviseConfig(max_rounds=1))
    flagged = "他嘴角勾起，心中一紧。" * 3
    out = await nw._revise_chapter(flagged, opts)
    assert out == flagged


@pytest.mark.asyncio
async def test_revise_disabled_is_noop():
    llm = AsyncMock()
    nw = NovelWriter(llm)
    opts = WritingOptions(format="novel", revise=ReviseConfig(enabled=False))
    flagged = "他嘴角勾起，心中一紧。" * 3
    out = await nw._revise_chapter(flagged, opts)
    assert out == flagged
    llm.chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_revise_directive_reaches_llm_as_system():
    llm = AsyncMock()
    llm.chat.return_value = "<story>干净正文。</story>"
    nw = NovelWriter(llm)
    opts = WritingOptions(format="novel", revise=ReviseConfig(max_rounds=1))
    flagged = "他嘴角勾起，心中一紧。" * 3
    await nw._revise_chapter(flagged, opts)
    messages = llm.chat.call_args.args[0]
    assert messages[0]["role"] == "system" and "改写为具体动作" in messages[0]["content"]
    assert messages[-1]["role"] == "user" and messages[-1]["content"] == flagged


@pytest.mark.asyncio
async def test_revise_multiround_breaks_early_when_clean():
    # round 1 rewrites the flagged draft into clean prose; round 2 detects clean
    # and breaks without a second LLM call.
    llm = AsyncMock()
    llm.chat.return_value = "<story>一段干净的正文，没有任何问题。</story>"
    nw = NovelWriter(llm)
    opts = WritingOptions(format="novel", revise=ReviseConfig(max_rounds=3))
    out = await nw._revise_chapter("他嘴角勾起，心中一紧。" * 3, opts)
    assert out == "一段干净的正文，没有任何问题。"
    llm.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_revise_multiround_runs_until_max_when_dirty():
    # every rewrite is still flagged -> loop runs the full max_rounds and
    # re-diagnoses the rewritten text each round (not the original).
    llm = AsyncMock()
    llm.chat.return_value = "<story>他嘴角勾起，心中一紧。</story>"
    nw = NovelWriter(llm)
    opts = WritingOptions(format="novel", revise=ReviseConfig(max_rounds=2))
    await nw._revise_chapter("他嘴角勾起，心中一紧。" * 3, opts)
    assert llm.chat.await_count == 2


@pytest.mark.asyncio
async def test_revise_injects_canon_block_and_triggers_on_contradiction():
    from app.services.narrative.types import CanonicalFact, CanonicalFacts

    facts = CanonicalFacts(facts=[CanonicalFact(
        id="f1", topic="出身", question="主角出身？",
        canonical_answer_zh="平民", canonical_answer_en="commoner",
        rejected_answers=["他是皇室血脉"],
    )])
    llm = AsyncMock()
    llm.chat.return_value = "<story>他出身平民。</story>"
    nw = NovelWriter(llm)
    opts = WritingOptions(
        format="novel", canonical_facts=facts, revise=ReviseConfig(max_rounds=1)
    )
    out = await nw._revise_chapter("他是皇室血脉，无人不知。", opts)
    assert out == "他出身平民。"
    msgs = llm.chat.call_args.args[0]
    roles = [m["role"] for m in msgs]
    # directive (system) + canon render_block (system) + prose (user)
    assert roles == ["system", "system", "user"]
    assert "事实冲突" in msgs[0]["content"]
    assert "平民" in msgs[1]["content"]  # the correct answer, not just "avoid X"


