"""Tests for CanonicalFacts schema: render_block scope filtering + serialization."""
from __future__ import annotations

from app.services.narrative.types import (
    CanonicalFact,
    CanonicalFacts,
    OpenConflict,
    WritingOptions,
)


def _facts():
    return CanonicalFacts(
        facts=[
            CanonicalFact(
                id="family_truth-1", topic="family_truth",
                question="谁把自己写进了书？",
                canonical_answer_zh="母亲，核心页是第97页",
                canonical_answer_en="The mother, core page 97",
                rejected_answers=["父亲", "建炉者", "第347页"],
                scope="all", rationale="源档案沉默，统一裁决",
            ),
            CanonicalFact(
                id="ending-1", topic="ending_fate",
                question="叶重霄结局？",
                canonical_answer_zh="碎裂消散",
                canonical_answer_en="Shatters and dissipates",
                scope="novel",
            ),
            CanonicalFact(
                id="slug-1", topic="format",
                question="场景头规范？",
                canonical_answer_zh="每场带时间",
                canonical_answer_en="Every scene timed",
                scope="screenplay",
            ),
        ],
        unresolved=[OpenConflict(topic="x", question="未定", candidates=["a", "b"])],
        session_id="s1", lang="zh",
    )


def test_render_block_scope_filters_to_novel():
    block = _facts().render_block("novel", is_zh=True)
    assert "母亲" in block          # scope=all included
    assert "碎裂消散" in block       # scope=novel included
    assert "每场带时间" not in block  # scope=screenplay excluded


def test_render_block_scope_filters_to_screenplay():
    block = _facts().render_block("screenplay", is_zh=True)
    assert "母亲" in block
    assert "每场带时间" in block
    assert "碎裂消散" not in block


def test_render_block_hard_constraint_wording():
    assert "绝对不可违背" in _facts().render_block("novel", is_zh=True)
    assert "NEVER contradict" in _facts().render_block("novel", is_zh=False)


def test_render_block_includes_rejected_answers():
    block = _facts().render_block("novel", is_zh=True)
    assert "禁止写成" in block and "父亲" in block


def test_render_block_never_leaks_rationale():
    # rationale is audit-only — must not appear in the injected prompt.
    assert "统一裁决" not in _facts().render_block("novel", is_zh=True)


def test_render_block_empty_when_no_facts():
    assert CanonicalFacts().render_block("novel", is_zh=True) == ""
    assert CanonicalFacts().render_block("screenplay", is_zh=False) == ""


def test_roundtrip_to_from_dict():
    cf = _facts()
    restored = CanonicalFacts.from_dict(cf.to_dict())
    assert restored == cf


def test_writing_options_defaults_none():
    assert WritingOptions(format="novel").canonical_facts is None
