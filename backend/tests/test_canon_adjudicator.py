"""Tests for CanonAdjudicator: parsing, validation, and graceful degradation."""
from __future__ import annotations

import pytest

from app.core.i18n import set_lang, Lang
from app.core.llm_client import LLMError, LLMErrorCode
from app.services.narrative.canon_adjudicator import CanonAdjudicator


@pytest.fixture(autouse=True)
def _zh():
    set_lang(Lang.ZH)
    yield


class _FakeLLM:
    """Stands in for LLMClient.chat_json."""

    def __init__(self, result=None, raise_error=False):
        self._result = result
        self._raise = raise_error
        self.calls = 0

    async def chat_json(self, messages, *, temperature=0.3):
        self.calls += 1
        if self._raise:
            raise LLMError(LLMErrorCode.PARSE_ERROR, "boom")
        return self._result


async def _adjudicate(llm):
    adj = CanonAdjudicator(llm)
    return await adj.adjudicate(archives=[], outline=None, characters=[], session_id="s1")


@pytest.mark.asyncio
async def test_parses_valid_facts():
    llm = _FakeLLM({
        "facts": [{
            "topic": "family_truth", "question": "谁写进书？",
            "canonical_answer_zh": "母亲，第97页", "canonical_answer_en": "Mother, p97",
            "rejected_answers": ["父亲", "第347页"], "scope": "all", "rationale": "源档案沉默",
        }],
        "unresolved": [],
    })
    cf = await _adjudicate(llm)
    assert len(cf.facts) == 1
    f = cf.facts[0]
    assert f.topic == "family_truth" and f.scope == "all"
    assert f.id == "family_truth-1"
    assert f.rejected_answers == ["父亲", "第347页"]


@pytest.mark.asyncio
async def test_illegal_scope_coerced_to_all():
    llm = _FakeLLM({"facts": [{
        "topic": "t", "question": "q",
        "canonical_answer_zh": "a", "canonical_answer_en": "a", "scope": "bogus",
    }]})
    cf = await _adjudicate(llm)
    assert cf.facts[0].scope == "all"


@pytest.mark.asyncio
async def test_empty_answer_demoted_to_unresolved():
    llm = _FakeLLM({"facts": [{
        "topic": "t", "question": "undecided",
        "canonical_answer_zh": "", "canonical_answer_en": "",
    }]})
    cf = await _adjudicate(llm)
    assert cf.facts == []
    assert len(cf.unresolved) == 1 and cf.unresolved[0].topic == "t"


@pytest.mark.asyncio
async def test_unresolved_passthrough():
    llm = _FakeLLM({"facts": [], "unresolved": [
        {"topic": "ending", "question": "生死?", "candidates": ["活", "死"]},
    ]})
    cf = await _adjudicate(llm)
    assert len(cf.unresolved) == 1 and cf.unresolved[0].candidates == ["活", "死"]


@pytest.mark.asyncio
async def test_llm_failure_degrades_to_empty():
    llm = _FakeLLM(raise_error=True)
    cf = await _adjudicate(llm)
    assert cf.facts == [] and cf.unresolved == []
    assert cf.session_id == "s1"


@pytest.mark.asyncio
async def test_garbage_rows_dropped():
    llm = _FakeLLM({"facts": ["not a dict", {"no_topic": "x"}, 42]})
    cf = await _adjudicate(llm)
    assert cf.facts == []
