"""Tests for T3-1: multi-level structure tree provenance (planning_status/source).

Additive fields on SceneSpec/Act let refine_plot preserve USER_EDITED nodes.
Default-off: every node defaults to AI_GENERATED, so existing outlines (which
never carry USER_EDITED) yield byte-identical refine_plot behavior.

Run as a targeted file (full suite hangs on integration tests):
    uv run pytest tests/test_structure_status.py -v
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.i18n import set_lang, Lang
from app.services.plot_architect.architect import PlotArchitect
from app.services.plot_architect.types import (
    Act,
    NarrativeStructure,
    PlanningStatus,
    PlotOutline,
    PlotSource,
    SceneSpec,
    status_label,
)


def _scene(sid: str, status: PlanningStatus = PlanningStatus.AI_GENERATED) -> SceneSpec:
    return SceneSpec(
        id=sid, title=f"T-{sid}", location="L", cast=["c1"],
        conflict="x", goal="g", expected_outcome="o", planning_status=status,
    )


def _outline(scene_statuses: dict[str, PlanningStatus]) -> PlotOutline:
    scenes = [_scene(sid, st) for sid, st in scene_statuses.items()]
    return PlotOutline(
        structure=NarrativeStructure.THREE_ACT,
        acts=[Act(name="A1", description="d", scenes=scenes)],
    )


# --- defaults + enums -----------------------------------------------------

def test_scene_spec_defaults_to_ai_generated():
    s = SceneSpec(id="s1", title="t", location="l", cast=[], conflict="c",
                  goal="g", expected_outcome="o")
    assert s.planning_status == PlanningStatus.AI_GENERATED
    assert s.source == PlotSource.LLM


def test_act_defaults_to_ai_generated():
    a = Act(name="A", description="d")
    assert a.planning_status == PlanningStatus.AI_GENERATED
    assert a.source == PlotSource.LLM


def test_status_label_bilingual():
    set_lang(Lang.ZH)
    assert "用户" in status_label(PlanningStatus.USER_EDITED) or status_label(PlanningStatus.USER_EDITED)
    set_lang(Lang.EN)
    assert status_label(PlanningStatus.USER_EDITED)


# --- round-trip losslessness ----------------------------------------------

def test_old_outline_dict_round_trips_losslessly():
    """A persisted outline dict WITHOUT planning_status hydrates to defaults."""
    old = {
        "structure": "three_act",
        "acts": [{
            "name": "A1", "description": "d",
            "scenes": [{
                "id": "s1", "title": "t", "location": "l", "cast": [],
                "conflict": "c", "goal": "g", "expected_outcome": "o",
                "causal_chain": [],
            }],
        }],
        "character_arcs": {},
    }
    outline = PlotArchitect._dict_to_outline(old)
    assert outline.acts[0].scenes[0].planning_status == PlanningStatus.AI_GENERATED
    assert outline.acts[0].planning_status == PlanningStatus.AI_GENERATED


# --- refine_plot preserves USER_EDITED nodes ------------------------------

def _llm_returning(outline: PlotOutline) -> dict:
    """Simulate the LLM regenerating the outline, CHANGING every scene's title."""
    return {
        "structure": outline.structure.value,
        "acts": [
            {
                "name": a.name, "description": a.description,
                "scenes": [
                    {
                        "id": s.id, "title": f"REWRITTEN-{s.id}", "location": s.location,
                        "cast": s.cast, "conflict": s.conflict, "goal": s.goal,
                        "expected_outcome": s.expected_outcome,
                        "causal_chain": s.causal_chain,
                    }
                    for s in a.scenes
                ],
            }
            for a in outline.acts
        ],
        "character_arcs": outline.character_arcs,
    }


@pytest.mark.asyncio
async def test_refine_plot_preserves_user_edited_scenes():
    before = _outline({"s1": PlanningStatus.USER_EDITED, "s2": PlanningStatus.AI_GENERATED})
    arch = PlotArchitect(AsyncMock(), AsyncMock())
    arch._llm.chat_json = AsyncMock(return_value=_llm_returning(before))

    after = await arch.refine_plot(before, "tighten pacing")

    scenes = {s.id: s for s in after.acts[0].scenes}
    # USER_EDITED scene is preserved byte-for-byte (NOT rewritten)
    assert scenes["s1"].title == "T-s1"
    assert scenes["s1"].planning_status == PlanningStatus.USER_EDITED
    # AI_GENERATED scene WAS regenerated
    assert scenes["s2"].title == "REWRITTEN-s2"


@pytest.mark.asyncio
async def test_refine_plot_no_user_edits_is_passthrough_rewrite():
    """With zero USER_EDITED nodes, refine rewrites everything (current behavior)."""
    before = _outline({"s1": PlanningStatus.AI_GENERATED})
    arch = PlotArchitect(AsyncMock(), AsyncMock())
    arch._llm.chat_json = AsyncMock(return_value=_llm_returning(before))

    after = await arch.refine_plot(before, "feedback")
    assert after.acts[0].scenes[0].title == "REWRITTEN-s1"


def test_merge_user_edited_is_pure_helper():
    before = _outline({"s1": PlanningStatus.USER_EDITED})
    after = _outline({"s1": PlanningStatus.AI_GENERATED})
    # mutate after's scene title to simulate LLM change
    after.acts[0].scenes[0] = SceneSpec(
        id="s1", title="CHANGED", location="L", cast=["c1"],
        conflict="x", goal="g", expected_outcome="o")
    merged = PlotArchitect._merge_user_edited(before, after)
    assert merged.acts[0].scenes[0].title == "T-s1"  # before's USER_EDITED won
