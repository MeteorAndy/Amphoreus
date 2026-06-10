"""Tests for T2-④: measure-only token-budget accounting.

This is the FIRST, safe increment of the token-budget feature. It sits on the
generation hot path but NEVER mutates a prompt — it only estimates per-section
token cost and emits an advisory BudgetReport. The `would_trim` list is purely
informational; the prompt-mutating allocator is a deferred follow-up.

Pure module, no LLM. Run as a targeted file (full suite hangs):
    uv run pytest tests/test_token_budget.py -v
"""

from __future__ import annotations

import json

from app.services.narrative.token_budget import (
    BudgetSection,
    ChapterBudget,
    BudgetReport,
    TokenBudgetConfig,
    PRIORITY_TIERS,
    allocate_chapter_sections,
    estimate_tokens,
    account_prompt,
)


# --- estimator ------------------------------------------------------------

def test_estimate_tokens_empty_is_zero():
    assert estimate_tokens("", is_zh=True) == 0
    assert estimate_tokens("", is_zh=False) == 0


def test_estimate_tokens_cjk_and_latin_monotonic():
    # both produce positive, sane estimates; longer text => more tokens
    small = estimate_tokens("他走了。", is_zh=True)
    big = estimate_tokens("他走了。" * 50, is_zh=True)
    assert 0 < small < big
    en_small = estimate_tokens("He left.", is_zh=False)
    en_big = estimate_tokens("He left. " * 50, is_zh=False)
    assert 0 < en_small < en_big


def test_estimate_tokens_latin_ratio_above_one():
    # Latin words cost ~1.3 tokens each, so 10 words estimate > 10
    assert estimate_tokens("alpha beta gamma delta epsilon zeta eta theta iota kappa",
                           is_zh=False) >= 10


# --- priority tiers -------------------------------------------------------

def test_priority_canon_outranks_summaries():
    assert PRIORITY_TIERS["canon"] > PRIORITY_TIERS["prev_summary"]
    assert PRIORITY_TIERS["foreshadowing"] > PRIORITY_TIERS["next_summary"]


def test_priority_critical_outranks_phase_directive():
    assert PRIORITY_TIERS["canon"] > PRIORITY_TIERS["phase"]
    assert PRIORITY_TIERS["foreshadowing"] > PRIORITY_TIERS["phase"]


# --- account_prompt (advisory, never mutates) -----------------------------

def _sections():
    return [
        BudgetSection("system", "baseline", 400),
        BudgetSection("canon", "critical", 300),
        BudgetSection("foreshadowing", "critical", 200),
        BudgetSection("phase", "high", 60),
        BudgetSection("prev_summary", "medium", 150),
        BudgetSection("next_summary", "medium", 150),
        BudgetSection("scene_logs", "baseline", 900),
    ]


def test_account_no_budget_never_trims():
    rep = account_prompt(1, _sections(), budget=None)
    assert rep.would_trim == []
    assert rep.over_by == 0
    assert rep.total_tokens == sum(s.tokens for s in _sections())


def test_account_under_budget_no_trim():
    rep = account_prompt(1, _sections(), budget=10000)
    assert rep.would_trim == []
    assert rep.over_by == 0


def test_account_over_budget_drops_lowest_value_first():
    # total = 2160; budget 2000 => need to shed 160. Lowest-value droppable
    # are the two medium summaries (150 each) and phase (60).
    rep = account_prompt(1, _sections(), budget=2000)
    assert rep.over_by == 160
    assert rep.would_trim  # non-empty
    # the first thing trimmed must be a medium summary or phase, never critical
    assert rep.would_trim[0] in {"prev_summary", "next_summary", "phase"}


def test_account_never_trims_critical():
    # absurdly tight budget; canon + foreshadowing must still never be listed
    rep = account_prompt(1, _sections(), budget=10)
    assert "canon" not in rep.would_trim
    assert "foreshadowing" not in rep.would_trim


def test_account_never_auto_trims_baseline():
    rep = account_prompt(1, _sections(), budget=10)
    assert "system" not in rep.would_trim
    assert "scene_logs" not in rep.would_trim


def test_account_flags_any_over_when_undroppable_exceeds():
    # even after dropping all droppable, critical+baseline alone exceed budget
    rep = account_prompt(1, _sections(), budget=10)
    assert rep.over_by > 0  # still over after advisory trims


# --- report serialization -------------------------------------------------

def test_budget_report_to_dict_serializable():
    cb = account_prompt(3, _sections(), budget=2000)
    report = BudgetReport(per_chapter=[cb], any_over=cb.over_by > 0,
                          total_tokens=cb.total_tokens)
    d = report.to_dict()
    assert d["per_chapter"][0]["chapter_number"] == 3
    json.dumps(d)  # serializable for the completed event


def test_config_defaults_are_noop():
    cfg = TokenBudgetConfig()
    assert cfg.enabled is False
    assert cfg.budget_tokens == 0
    assert cfg.apply_trimming is False


def test_allocate_no_budget_returns_original_parts():
    parts = {
        "system": "system", "canon": "canon", "foreshadowing": "foreshadow",
        "phase": "phase", "prev_summary": "prev", "next_summary": "next",
        "scene_logs": "scene",
    }
    allocated, report = allocate_chapter_sections(
        1, is_zh=False, budget_tokens=0, parts=parts
    )
    assert allocated == parts
    assert report.applied_trim == []
    assert report.final_tokens == report.total_tokens


def test_allocate_drops_low_value_sections_before_critical():
    parts = {
        "system": "system " * 20,
        "canon": "CANON " * 20,
        "foreshadowing": "FORESHADOW " * 20,
        "phase": "PHASE " * 80,
        "prev_summary": "PREV " * 80,
        "next_summary": "NEXT " * 80,
        "scene_logs": "SCENE " * 80,
    }
    allocated, report = allocate_chapter_sections(
        1, is_zh=False, budget_tokens=260, parts=parts
    )
    assert allocated["canon"] == parts["canon"]
    assert allocated["foreshadowing"] == parts["foreshadowing"]
    assert {"prev_summary", "next_summary"} & set(report.applied_trim)
    assert report.final_tokens is not None
    assert report.final_tokens < report.total_tokens


def test_allocate_truncates_scene_logs_only_after_droppable_context():
    parts = {
        "system": "system " * 5,
        "canon": "canon " * 5,
        "foreshadowing": "foreshadow " * 5,
        "phase": "phase " * 100,
        "prev_summary": "prev " * 100,
        "next_summary": "next " * 100,
        "scene_logs": "A " * 400 + "MIDDLE " * 400 + "Z " * 400,
    }
    allocated, report = allocate_chapter_sections(
        1, is_zh=False, budget_tokens=220, parts=parts
    )
    assert allocated["phase"] == ""
    assert allocated["prev_summary"] == ""
    assert allocated["next_summary"] == ""
    assert "scene_logs" in report.applied_trim
    assert "Context budget trim" in allocated["scene_logs"]
    assert "A " in allocated["scene_logs"]
    assert "Z " in allocated["scene_logs"]
