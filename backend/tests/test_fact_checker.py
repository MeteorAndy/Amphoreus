"""Unit tests for fact_checker — pure logic tests, no real LLM or Tavily calls.

Exercises: candidate extraction (LLM pre-filter), Tavily verdict synthesis, the
no-key skip path, graceful degradation, and the needs_rewrite gate. The LLM and
the Tavily HTTP client are both mocked, so these run in milliseconds.
"""

from __future__ import annotations

import pytest

from app.core.llm_client import LLMError, LLMErrorCode
from app.services.narrative.fact_checker import (
    FactCandidate,
    FactCheck,
    FactReport,
    FactChecker,
)


# ---- fakes -----------------------------------------------------------------


class FakeLLM:
    """Returns canned JSON payloads for chat_json, or raises.

    `payload` may be a single value (returned every call) or a list/sequence
    of values (returned in order, one per call) so the extraction call and the
    verdict call can each be scripted independently.
    """

    def __init__(self, payload):
        if isinstance(payload, list):
            self._payloads = payload
        else:
            self._payloads = [payload]
        self.calls = 0

    async def chat_json(self, messages, *, temperature=0.3):
        if self.calls >= len(self._payloads):
            # Default subsequent calls (e.g. the verdict pass) to an empty verdict.
            payload = {"verdicts": []}
        else:
            payload = self._payloads[self.calls]
        self.calls += 1
        if isinstance(payload, Exception):
            raise payload
        if isinstance(payload, dict):
            return payload
        from app.services.narrative.fact_checker import _parse_candidates_payload

        return _parse_candidates_payload(payload)


class FakeTavily:
    """In-memory stand-in for the Tavily search client.

    `responses` maps a normalized query substring -> answer snippet text.
    `fail_on` optionally raises when the query contains a given substring.
    """

    def __init__(self, responses: dict[str, str], fail_on: str | None = None):
        self._responses = responses
        self._fail_on = fail_on
        self.calls: list[str] = []

    async def search(self, query: str) -> str:
        self.calls.append(query)
        if self._fail_on and self._fail_on in query:
            raise RuntimeError("tavily network down")
        for needle, answer in self._responses.items():
            if needle in query:
                return answer
        return ""


def make_checker(
    llm_payload="skip",
    tavily: FakeTavily | None = None,
    *,
    has_key: bool = True,
) -> FactChecker:
    llm = FakeLLM(llm_payload)
    return FactChecker(llm=llm, tavily=tavily or FakeTavily({}), has_key=has_key)  # type: ignore[arg-type]


# A realistic candidate-extraction payload: one checkable real-world claim.
CANDIDATES_PAYLOAD = {
    "candidates": [
        {
            "claim": "1943年的上海街头出现了AK-47突击步枪",
            "location": "1943年的上海街头出现了AK-47突击步枪",
            "category": "武器年代",
            "query": "AK-47 突击步枪 量产年份",
        },
    ]
}


# ---- no-key skip ----------------------------------------------------------


@pytest.mark.asyncio
async def test_no_key_silently_skips_and_returns_empty():
    """Without a Tavily key the checker must no-op, never raise or call the LLM."""
    llm = FakeLLM({"candidates": []})
    fc = FactChecker(llm=llm, tavily=None, has_key=False)  # type: ignore[arg-type]
    report = await fc.check(chapter_text="随便什么内容", world_summary="", characters=[])
    assert report.candidates == []
    assert report.checks == []
    assert report.needs_rewrite is False
    assert llm.calls == 0  # no LLM call when key absent


@pytest.mark.asyncio
async def test_no_key_does_not_call_llm():
    llm = FakeLLM({"candidates": []})
    fc = FactChecker(llm=llm, tavily=None, has_key=False)  # type: ignore[arg-type]
    await fc.check(chapter_text="x", world_summary="", characters=[])
    assert llm.calls == 0


# ---- candidate extraction degradation -------------------------------------


@pytest.mark.asyncio
async def test_llm_error_during_extraction_returns_empty():
    err = LLMError(LLMErrorCode.PARSE_ERROR, "boom")
    fc = make_checker(err)
    report = await fc.check(chapter_text="x", world_summary="", characters=[])
    assert report.candidates == []
    assert report.needs_rewrite is False


@pytest.mark.asyncio
async def test_no_candidates_means_no_tavily_calls():
    """A clean chapter (no checkable real-world claims) spends zero credits."""
    tavily = FakeTavily({})
    fc = make_checker({"candidates": []}, tavily)
    report = await fc.check(chapter_text="纯虚构的废土设定", world_summary="", characters=[])
    assert report.candidates == []
    assert tavily.calls == []
    assert report.needs_rewrite is False


# ---- end-to-end with mocked Tavily ----------------------------------------


@pytest.mark.asyncio
async def test_contradiction_flagged_when_tavily_supports_it():
    """Tavily returns evidence that the claim is wrong -> contradiction check."""
    tavily = FakeTavily({
        "AK-47": "AK-47（也称AK-47）由卡拉什尼科夫于1947年设计，1949年开始量产装备苏军。",
    })
    verdict_payload = {"verdicts": [{"claim": CANDIDATES_PAYLOAD["candidates"][0]["claim"],
                                     "verdict": "contradiction"}]}
    fc = make_checker([CANDIDATES_PAYLOAD, verdict_payload], tavily)
    report = await fc.check(chapter_text="x", world_summary="", characters=[])
    assert len(report.checks) == 1
    check = report.checks[0]
    assert check.verdict == "contradiction"
    assert report.needs_rewrite is True


@pytest.mark.asyncio
async def test_confirmed_when_tavily_supports_claim():
    tavily = FakeTavily({
        "青霉素": "青霉素由弗莱明于1928年发现，1942年开始大规模生产。",
    })
    extract_payload = {"candidates": [{
        "claim": "1943年他用青霉素给伤员消炎",
        "location": "1943年他用青霉素给伤员消炎",
        "category": "医疗史",
        "query": "青霉素 发现 年代 大规模生产",
    }]}
    verdict_payload = {"verdicts": [{"claim": "1943年他用青霉素给伤员消炎",
                                     "verdict": "confirmed"}]}
    fc = make_checker([extract_payload, verdict_payload], tavily)
    report = await fc.check(chapter_text="x", world_summary="", characters=[])
    assert report.checks[0].verdict == "confirmed"
    assert report.needs_rewrite is False


@pytest.mark.asyncio
async def test_unverifiable_when_tavily_returns_nothing():
    tavily = FakeTavily({})  # no matching evidence
    verdict_payload = {"verdicts": [{"claim": CANDIDATES_PAYLOAD["candidates"][0]["claim"],
                                     "verdict": "unverifiable"}]}
    fc = make_checker([CANDIDATES_PAYLOAD, verdict_payload], tavily)
    report = await fc.check(chapter_text="x", world_summary="", characters=[])
    assert report.checks[0].verdict == "unverifiable"
    assert report.needs_rewrite is False  # can't confirm a contradiction


# ---- degradation: Tavily failure never fatal ------------------------------


@pytest.mark.asyncio
async def test_tavily_network_error_drops_check_not_raises():
    tavily = FakeTavily({}, fail_on="AK-47")
    fc = make_checker(CANDIDATES_PAYLOAD, tavily)
    report = await fc.check(chapter_text="x", world_summary="", characters=[])
    # The check is dropped (not turned into a false contradiction), report clean.
    assert report.checks == []
    assert report.needs_rewrite is False


# ---- bounding -------------------------------------------------------------


@pytest.mark.asyncio
async def test_candidate_count_capped_at_max_queries():
    """An unlimited chapter must not fire an unbounded number of Tavily calls."""
    many = {
        "candidates": [
            {"claim": f"claim{i}", "location": f"loc{i}",
             "category": "历史", "query": f"query{i}"}
            for i in range(20)
        ]
    }
    tavily = FakeTavily({})
    fc = make_checker(many, tavily)
    await fc.check(chapter_text="x", world_summary="", characters=[], max_queries=3)
    assert len(tavily.calls) == 3


# ---- FactReport.needs_rewrite ---------------------------------------------


def test_empty_report_not_needs_rewrite():
    assert FactReport(candidates=[], checks=[]).needs_rewrite is False


def test_only_unverifiable_not_needs_rewrite():
    """Unverifiable is a note, not a blocker — must not cost an LLM rewrite."""
    rep = FactReport(
        candidates=[],
        checks=[FactCheck(claim="x", query="q", verdict="unverifiable", evidence="")],
    )
    assert rep.needs_rewrite is False


def test_contradiction_triggers_rewrite():
    rep = FactReport(
        candidates=[],
        checks=[FactCheck(claim="x", query="q", verdict="contradiction", evidence="e")],
    )
    assert rep.needs_rewrite is True
