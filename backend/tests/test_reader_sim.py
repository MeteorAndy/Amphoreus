"""Tests for T2-⑥: reader simulation (LLM judge + deterministic grounding).

Twins T2-⑤/⑦: post-write, report-only, opt-in, rides the completed event. One
LLM call at low temp judges the subjective reader experience; a pure
_ground_signals layer feeds it concrete anchors. Everything degrades to an empty
report — never raises. Run as a targeted file (full suite hangs):
    uv run pytest tests/test_reader_sim.py -v
"""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock

from app.services.narrative.reader_sim import (
    ConfusionPoint,
    DanglingThread,
    EngagementPoint,
    ReaderSimReport,
    ReaderSimulator,
    _ground_signals,
    build_reader_sim_report,
)
from app.services.narrative.types import ChapterSpec, ChapterPlan


# --- builders -------------------------------------------------------------

def _plan(n: int) -> ChapterPlan:
    return ChapterPlan(chapters=[
        ChapterSpec(number=i, title=f"T{i}", scene_ids=[f"s{i}"], summary="")
        for i in range(1, n + 1)
    ])


def _full_payload() -> dict:
    return {
        "confusion_points": [
            {"chapter": 2, "description": "时间线跳跃未交代", "severity": "high"},
            {"chapter": 2, "description": "时间线跳跃未交代", "severity": "high"},  # dupe
            {"chapter": 5, "description": "vague pronoun", "severity": "low"},
            {"description": "missing chapter", "severity": "low"},  # bad: no chapter
            {"chapter": 3, "description": "bad sev", "severity": "EXTREME"},  # bad sev
        ],
        "dangling_threads": [
            {"question": "谁是真正的凶手？", "introduced_chapter": 1, "severity": "high"},
            {"question": "谁是真正的凶手？", "introduced_chapter": 1, "severity": "high"},  # dupe
        ],
        "engagement_curve": [
            {"chapter": 1, "momentum": 0.6, "note": "strong open"},
            {"chapter": 1, "momentum": 0.2, "note": "dupe chapter, dropped"},
            {"chapter": 2, "momentum": 1.8, "note": "clamped"},  # >1 clamp
            {"chapter": 3, "momentum": -0.5},  # <0 clamp
        ],
        "predicted_retention": 0.72,
        "summary": "Solid but front-loaded.",
    }


def _sim(payload):
    llm = AsyncMock()
    llm.chat_json = AsyncMock(return_value=payload)
    return ReaderSimulator(llm)


# --- record invariants ----------------------------------------------------

def test_confusion_point_rejects_bad_severity():
    with pytest.raises(ValueError):
        ConfusionPoint(chapter=1, description="x", severity="EXTREME")


def test_report_to_dict_shape():
    rep = ReaderSimReport(
        confusion_points=[ConfusionPoint(1, "x", "low")],
        dangling_threads=[DanglingThread("q?", 1, "medium")],
        engagement_curve=[EngagementPoint(1, 0.5, "n")],
        predicted_retention=0.5, summary="s",
    )
    d = rep.to_dict()
    assert set(d) >= {"confusion_points", "dangling_threads", "engagement_curve",
                      "predicted_retention", "summary"}
    json.dumps(d)  # serializable for the completed event


# --- deterministic grounding ----------------------------------------------

def test_grounding_counts_chapters_and_questions_zh():
    prose = "# 书名\n\n## 第1章 起\n\n他在哪里？真的吗？\n\n## 第2章 承\n\n平静。\n"
    signals = _ground_signals(prose, _plan(2))
    assert "2" in signals  # chapter total
    # chapter 1 has 2 question marks; the grounded block should mention questions
    assert "?" in signals or "问" in signals or "question" in signals.lower()


def test_grounding_falls_back_to_plan_when_no_headings():
    signals = _ground_signals("just flat prose, no headings, no marks", _plan(4))
    assert "4" in signals  # falls back to len(chapter_plan.chapters)


def test_grounding_never_raises_on_empty():
    assert isinstance(_ground_signals("", _plan(0)), str)


# --- LLM simulate: parsing, dedup, clamping, degrade ----------------------

@pytest.mark.asyncio
async def test_simulate_parses_and_dedups_and_clamps():
    rep = await _sim(_full_payload()).simulate("prose", "signals")
    # confusion: dupe collapsed, 2 bad rows dropped -> 2 valid
    assert len(rep.confusion_points) == 2
    # dangling: dupe collapsed -> 1
    assert len(rep.dangling_threads) == 1
    # engagement: one point per chapter (ch1 dupe dropped) -> 3 chapters
    assert len(rep.engagement_curve) == 3
    assert all(0.0 <= e.momentum <= 1.0 for e in rep.engagement_curve)
    ch2 = next(e for e in rep.engagement_curve if e.chapter == 2)
    assert ch2.momentum == 1.0  # clamped from 1.8
    assert rep.predicted_retention == 0.72


@pytest.mark.asyncio
async def test_predicted_retention_clamped():
    rep = await _sim({"predicted_retention": 5.0}).simulate("prose", "sig")
    assert rep.predicted_retention == 1.0
    rep2 = await _sim({"predicted_retention": -3.0}).simulate("prose", "sig")
    assert rep2.predicted_retention == 0.0


@pytest.mark.asyncio
async def test_simulate_degrades_on_llm_error():
    llm = AsyncMock()
    llm.chat_json = AsyncMock(side_effect=RuntimeError("boom"))
    rep = await ReaderSimulator(llm).simulate("prose", "sig")
    assert rep.confusion_points == [] and rep.predicted_retention == 0.0


@pytest.mark.asyncio
async def test_simulate_degrades_on_malformed_payload():
    rep = await _sim(["not", "a", "dict"]).simulate("prose", "sig")
    assert rep.confusion_points == [] and rep.dangling_threads == []


# --- orchestrator ---------------------------------------------------------

@pytest.mark.asyncio
async def test_build_empty_prose_no_llm_call():
    llm = AsyncMock()
    llm.chat_json = AsyncMock(return_value=_full_payload())
    rep = await build_reader_sim_report(llm, "   ", _plan(2))
    assert rep.confusion_points == [] and rep.predicted_retention == 0.0
    llm.chat_json.assert_not_called()


@pytest.mark.asyncio
async def test_build_end_to_end_and_degrades():
    llm = AsyncMock()
    llm.chat_json = AsyncMock(return_value=_full_payload())
    rep = await build_reader_sim_report(llm, "## 第1章 起\n\n内容？\n", _plan(1))
    assert rep.predicted_retention == 0.72
    json.dumps(rep.to_dict())

    bad = AsyncMock()
    bad.chat_json = AsyncMock(side_effect=RuntimeError("boom"))
    empty = await build_reader_sim_report(bad, "## 第1章 起\n\n内容\n", _plan(1))
    assert empty.confusion_points == [] and empty.predicted_retention == 0.0
