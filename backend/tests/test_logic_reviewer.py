"""Unit tests for logic_reviewer — pure logic tests, no real LLM calls.

Exercises JSON parsing, graceful degradation, and the needs_rewrite gate.
The LLM is mocked, so these run in milliseconds (matching the project's
zero-LLM diagnostic test discipline).
"""

from __future__ import annotations

import pytest

from app.core.llm_client import LLMClient, LLMError, LLMErrorCode
from app.services.narrative.logic_reviewer import (
    LogicIssue,
    LogicReport,
    LogicReviewer,
)


# ---- fakes -----------------------------------------------------------------


class FakeLLM:
    """Stand-in for LLMClient that returns a canned JSON payload."""

    def __init__(self, payload: str | dict | Exception):
        self._payload = payload
        self.calls = 0

    async def chat_json(self, messages, *, temperature=0.3):
        self.calls += 1
        if isinstance(self._payload, Exception):
            raise self._payload
        if isinstance(self._payload, dict):
            return self._payload
        # raw string — exercise the extractor's robustness
        from app.services.narrative.logic_reviewer import _parse_payload

        return _parse_payload(self._payload)


def make_reviewer(payload) -> LogicReviewer:
    return LogicReviewer(llm=FakeLLM(payload))  # type: ignore[arg-type]


# ---- LogicReport.needs_rewrite --------------------------------------------


def test_empty_report_does_not_need_rewrite():
    assert LogicReport(issues=[]).needs_rewrite is False


def test_minor_only_does_not_trigger_rewrite():
    """minor issues are notes, not blockers — they must not cost an LLM rewrite."""
    rep = LogicReport(issues=[
        LogicIssue("minor", "常识错误", "x", "p", "h"),
    ])
    assert rep.needs_rewrite is False


def test_major_and_critical_trigger_rewrite():
    for sev in ("critical", "major"):
        rep = LogicReport(issues=[
            LogicIssue(sev, "逻辑矛盾", "x", "p", "h"),  # type: ignore[arg-type]
        ])
        assert rep.needs_rewrite is True, sev


# ---- parsing: well-formed payload -----------------------------------------


WELL_FORMED = {
    "issues": [
        {
            "severity": "critical",
            "category": "常识错误",
            "location": "名字刻在军靴后跟上",
            "problem": "军靴后跟刻字是工厂标识，不构成个人身份识别",
            "fix_hint": "改为随身铭牌或旧证件",
        },
        {
            "severity": "minor",
            "category": "动机不通",
            "location": "陈漠轻易信任苏静",
            "problem": "失忆者对陌生人缺乏合理的戒备",
            "fix_hint": "增加试探与戒备描写",
        },
    ]
}


@pytest.mark.asyncio
async def test_well_formed_payload_parses_to_issues():
    r = make_reviewer(WELL_FORMED)
    report = await r.review(chapter_text="...", world_summary="...", characters=[])
    assert len(report.issues) == 2
    assert report.issues[0].severity == "critical"
    assert report.issues[0].category == "常识错误"
    assert "军靴" in report.issues[0].location
    assert report.needs_rewrite is True  # one critical present


@pytest.mark.asyncio
async def test_payload_wrapped_in_markdown_fence_still_parses():
    """LLMs often wrap JSON in ```json fences; the extractor must cope."""
    fenced = "```json\n" + '{\n  "issues": []\n}\n' + "```"
    r = make_reviewer(fenced)
    report = await r.review(chapter_text="x", world_summary="", characters=[])
    assert report.issues == []
    assert report.needs_rewrite is False


# ---- degradation: never fatal ---------------------------------------------


@pytest.mark.asyncio
async def test_llm_error_returns_empty_report_not_raised():
    """A PARSE_ERROR from chat_json must not break the write path."""
    err = LLMError(LLMErrorCode.PARSE_ERROR, "boom")
    r = make_reviewer(err)
    report = await r.review(chapter_text="x", world_summary="", characters=[])
    assert report.issues == []
    assert report.needs_rewrite is False


@pytest.mark.asyncio
async def test_unexpected_exception_returns_empty_report():
    r = make_reviewer(RuntimeError("network down"))
    report = await r.review(chapter_text="x", world_summary="", characters=[])
    assert report.issues == []


@pytest.mark.asyncio
async def test_malformed_payload_missing_fields_dropped_not_fatal():
    """A row missing required keys is dropped; the rest are kept."""
    bad_then_good = {
        "issues": [
            {"severity": "critical"},  # missing category/location/problem/fix_hint
            WELL_FORMED["issues"][0],
        ]
    }
    r = make_reviewer(bad_then_good)
    report = await r.review(chapter_text="x", world_summary="", characters=[])
    assert len(report.issues) == 1  # only the well-formed row survives
    assert report.issues[0].location == "名字刻在军靴后跟上"


@pytest.mark.asyncio
async def test_invalid_severity_drops_the_row():
    """Unknown severity strings are rejected, not silently coerced."""
    payload = {
        "issues": [
            {**WELL_FORMED["issues"][0], "severity": "CATACLYSMIC"},
        ]
    }
    r = make_reviewer(payload)
    report = await r.review(chapter_text="x", world_summary="", characters=[])
    assert report.issues == []


# ---- bounding --------------------------------------------------------------


@pytest.mark.asyncio
async def test_issues_capped_at_max_issues():
    """A chapter must not produce an unbounded directive that bloats the prompt."""
    many = {"issues": [WELL_FORMED["issues"][0] for _ in range(50)]}
    r = make_reviewer(many)
    report = await r.review(
        chapter_text="x", world_summary="", characters=[], max_issues=5
    )
    assert len(report.issues) == 5


@pytest.mark.asyncio
async def test_max_issues_keeps_highest_severity_first():
    """When capping, critical/major must survive over minor."""
    payload = {
        "issues": [
            {"severity": "minor", "category": "c", "location": "l",
             "problem": "p", "fix_hint": "h"},
            {"severity": "critical", "category": "c", "location": "l2",
             "problem": "p", "fix_hint": "h"},
            {"severity": "minor", "category": "c", "location": "l3",
             "problem": "p", "fix_hint": "h"},
        ]
    }
    r = make_reviewer(payload)
    report = await r.review(
        chapter_text="x", world_summary="", characters=[], max_issues=1
    )
    assert len(report.issues) == 1
    assert report.issues[0].severity == "critical"
