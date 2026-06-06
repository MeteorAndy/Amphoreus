"""Wiring tests for PR1: post-generation diagnostics on WrittenOutput.

The cliche_scanner and canon_verifier modules are unit-tested elsewhere; these
tests prove the WIRING — that NarrativeWriter populates cliche_report/canon_report
and that the pipeline event envelope carries them.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.i18n import set_lang, Lang
from app.services.narrative.types import (
    CanonicalFact, CanonicalFacts, ChapterPlan, ChapterSpec,
    WritingOptions, WrittenOutput,
)
from app.services.narrative.writer import NarrativeWriter


@pytest.fixture(autouse=True)
def _zh():
    set_lang(Lang.ZH)
    yield


# A cliche-dense Chinese passage that should trip multiple scanner rules.
_SLOP = (
    "他的心中一紧，仿佛时间静止了。她的眼中闪过一丝复杂的神色，"
    "嘴角勾起一抹意味深长的微笑。不知为何，空气仿佛凝固了一般，"
    "一丝寒意爬上脊背，仿佛有什么东西即将发生。"
)


def _canon():
    return CanonicalFacts(facts=[CanonicalFact(
        id="f-1", topic="family_truth", question="谁写进书？",
        canonical_answer_zh="母亲，第97页", canonical_answer_en="Mother, p97",
        rejected_answers=["父亲写进了书"], scope="all",
    )])


def _writer():
    return NarrativeWriter(llm=AsyncMock(), memory=AsyncMock())


@pytest.mark.asyncio
async def test_convert_novel_populates_reports(monkeypatch):
    """_convert_novel must attach cliche_report (always) and canon_report (when
    canonical_facts present), computed on the assembled content."""
    w = _writer()
    plan = ChapterPlan(chapters=[ChapterSpec(1, "开篇", ["s1"], "x")])
    w._planner.plan_chapters = AsyncMock(return_value=plan)
    w._novel_writer.write_chapters = AsyncMock(return_value=[_SLOP])
    monkeypatch.setattr(w._post_processor, "process", lambda ch: ch)
    monkeypatch.setattr(NarrativeWriter, "_assemble_novel",
                        staticmethod(lambda *a, **k: _SLOP))

    result = await w._convert_novel(
        scene_archives=[MagicMock()], characters=[MagicMock()],
        options=WritingOptions(format="novel", canonical_facts=_canon()),
        plot_outline=None, selected_title="书", title_candidates=["书"],
    )
    assert result.cliche_report is not None
    assert result.cliche_report.ai_flavor_score > 0
    assert result.cliche_report.hits, "slop passage should trip scanner rules"
    assert result.canon_report is not None
    assert result.canon_report.checked >= 1


@pytest.mark.asyncio
async def test_convert_novel_no_canon_skips_canon_report(monkeypatch):
    """Without canonical_facts, canon_report stays None but cliche still runs."""
    w = _writer()
    plan = ChapterPlan(chapters=[ChapterSpec(1, "开篇", ["s1"], "x")])
    w._planner.plan_chapters = AsyncMock(return_value=plan)
    w._novel_writer.write_chapters = AsyncMock(return_value=[_SLOP])
    monkeypatch.setattr(w._post_processor, "process", lambda ch: ch)
    monkeypatch.setattr(NarrativeWriter, "_assemble_novel",
                        staticmethod(lambda *a, **k: _SLOP))

    result = await w._convert_novel(
        scene_archives=[MagicMock()], characters=[MagicMock()],
        options=WritingOptions(format="novel"), plot_outline=None,
        selected_title="书", title_candidates=["书"],
    )
    assert result.cliche_report is not None
    assert result.canon_report is None



@pytest.mark.asyncio
async def test_written_output_carries_report_fields():
    """WrittenOutput must expose the two PR1 diagnostic fields, default None."""
    out = WrittenOutput(content="", format="novel", word_count=0, scene_count=0)
    assert out.cliche_report is None
    assert out.canon_report is None


def test_event_envelope_serializes_reports():
    """to_dict() on both reports yields the shapes the pipeline event carries."""
    from app.services.narrative.cliche_scanner import scan
    from app.services.narrative.canon_verifier import verify
    cr = scan(_SLOP)
    assert isinstance(cr.to_dict()["ai_flavor_score"], float)
    assert isinstance(cr.to_dict()["hits"], list)
    canon = verify(_SLOP, _canon(), "novel")
    d = canon.to_dict()
    assert "violations" in d and isinstance(d["violations"], list)


def test_empty_content_clean_report():
    """Wiring on empty content yields an empty, zero-score report."""
    from app.services.narrative.cliche_scanner import scan
    rep = scan("")
    assert rep.hits == [] and rep.ai_flavor_score == 0.0

