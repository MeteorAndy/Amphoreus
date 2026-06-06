"""Deterministic structure-parameter planner (T1-③) — zero LLM.

Given a narrative template and a target chapter count, maps to expected
act/scene counts and per-chapter word ranges. Pure function, single source
of truth — no more LLM free-form output drifting from the intended length.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import NarrativeStructure


@dataclass(frozen=True)
class StructureParams:
    """Expected dimensions for a novel of the given structure and length."""

    target_chapters: int
    total_acts: int
    scenes_per_act: int
    scenes_total: int
    words_zh: str   # e.g. "2500-4000字"
    words_en: str    # e.g. "2000-3500 words"
    template: str    # the value of the NarrativeStructure enum


def _bracket(chapters: int) -> tuple[int, int, int, str, str]:
    """Return (acts, scenes_per_act, scenes_total, words_zh, words_en)
    for a given target chapter count."""
    if chapters <= 3:
        return (1, chapters, chapters, "800-1500字", "800-1500 words")
    if chapters <= 12:
        return (3, max(chapters // 3, 2), chapters, "2500-4000字", "2000-3500 words")
    if chapters <= 30:
        return (3, chapters // 3, chapters, "2500-4000字", "2000-3500 words")
    if chapters <= 60:
        return (4, chapters // 4, chapters, "2500-3500字", "2000-3000 words")
    if chapters <= 120:
        return (5, chapters // 5, chapters, "2000-3000字", "1800-2800 words")
    return (5, max(chapters // 5, 10), chapters, "1800-2500字", "1500-2200 words")


def plan(target_chapters: int, template: NarrativeStructure) -> StructureParams:
    """Compute the canonical structure parameters for *target_chapters*."""
    acts, spa, total_scenes, words_zh, words_en = _bracket(
        max(1, target_chapters)
    )
    return StructureParams(
        target_chapters=target_chapters,
        total_acts=acts,
        scenes_per_act=spa,
        scenes_total=total_scenes,
        words_zh=words_zh,
        words_en=words_en,
        template=template.value,
    )


def format_structure_directive(params: StructureParams, is_zh: bool) -> str:
    """Render params as a compact constraint block for the plot-generation prompt.

    Returns "" when target_chapters <= 3 (short story — don't constrain structure).
    """
    if params.target_chapters <= 3:
        return ""
    if is_zh:
        return (
            f"【结构约束】预期总章数约 {params.target_chapters} 章，"
            f"约 {params.total_acts} 幕，每幕约 {params.scenes_per_act} 个场景。"
            f"每章目标字数：{params.words_zh}。"
            f"请在以上约束内生成大纲，幕数和场景数可微调，但总场景数应接近 {params.scenes_total}。"
        )
    return (
        f"[STRUCTURE CONSTRAINT] Target: ~{params.target_chapters} chapters, "
        f"~{params.total_acts} acts, ~{params.scenes_per_act} scenes per act. "
        f"Per-chapter target: {params.words_en}. "
        f"Generate the outline within these bounds; minor adjustments are fine."
    )
