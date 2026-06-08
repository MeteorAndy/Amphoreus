"""Shared types and constants for the pipeline package.

Leaf module — imported by the orchestrator and its mixins, imports nothing
from them (keeps the package free of import cycles).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.services.plot_architect import NarrativeStructure


class PipelineStage(str, Enum):
    WORLD = "world"
    CHARACTERS = "characters"
    RELATIONSHIPS = "relationships"
    PLOT = "plot"
    SCENES = "scenes"
    CANON = "canon"
    WRITING = "writing"
    DONE = "done"


@dataclass
class PipelineConfig:
    seed_idea: str
    lang: str = "zh"
    character_count: int = 5
    narrative_structure: str = "three_act"
    output_format: str = "novel"
    max_rounds_per_scene: int = 15
    auto_refine: bool = True
    adjudicate: bool = True  # run the CANON stage to lock cross-product facts
    session_id: str | None = None


@dataclass
class PipelineEvent:
    stage: str
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0
    session_id: str = ""


_STRUCTURE_MAP: dict[str, NarrativeStructure] = {
    "three_act": NarrativeStructure.THREE_ACT,
    "hero_journey": NarrativeStructure.HERO_JOURNEY,
    "save_the_cat": NarrativeStructure.SAVE_THE_CAT,
    "qi_cheng_zhuan_he": NarrativeStructure.QI_CHENG_ZHUAN_HE,
}

_STAGE_SEVERITY: dict[PipelineStage, str] = {
    PipelineStage.WORLD: "critical",
    PipelineStage.CHARACTERS: "critical",
    PipelineStage.RELATIONSHIPS: "critical",
    PipelineStage.PLOT: "critical",
    PipelineStage.SCENES: "critical",
    PipelineStage.CANON: "optional",
    PipelineStage.WRITING: "critical",
}

_AUTO_ANSWER_PROMPT_ZH = """\
你是一个创意写作助手，正在帮助构建一个故事世界。
根据以下种子创意，为世界构建问题提供一个富有创意、详细的回答。
你的回答应该扩展种子创意，增加具体细节，使世界更加丰富生动。
直接回答问题，不要解释你在做什么。回答长度适中（2-4句话）。"""

_AUTO_ANSWER_PROMPT_EN = """\
You are a creative writing assistant helping to build a story world.
Based on the seed idea below, provide a creative and detailed answer to the world-building question.
Your answer should expand on the seed idea, adding specific details to make the world richer.
Answer the question directly without explaining what you are doing. Keep answers moderate length (2-4 sentences)."""
