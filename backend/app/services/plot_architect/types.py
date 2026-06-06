from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NarrativeStructure(str, Enum):
    THREE_ACT = "three_act"
    HERO_JOURNEY = "hero_journey"
    SAVE_THE_CAT = "save_the_cat"
    QI_CHENG_ZHUAN_HE = "qi_cheng_zhuan_he"


@dataclass
class SceneSpec:
    id: str
    title: str
    location: str
    cast: list[str]
    conflict: str
    goal: str
    expected_outcome: str
    causal_chain: list[str] = field(default_factory=list)


@dataclass
class Act:
    name: str
    description: str
    scenes: list[SceneSpec] = field(default_factory=list)


@dataclass
class PlotOutline:
    structure: NarrativeStructure
    acts: list[Act] = field(default_factory=list)
    character_arcs: dict[str, list[str]] = field(default_factory=dict)
