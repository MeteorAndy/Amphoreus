from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.core.i18n import get_lang, Lang


class NarrativeStructure(str, Enum):
    THREE_ACT = "three_act"
    HERO_JOURNEY = "hero_journey"
    SAVE_THE_CAT = "save_the_cat"
    QI_CHENG_ZHUAN_HE = "qi_cheng_zhuan_he"


class PlanningStatus(str, Enum):
    """Provenance of an outline node — drives refine_plot's skip-filter (T3-①).

    AI_GENERATED is the default for every LLM-produced node, so existing
    outlines (which never carry USER_EDITED) yield byte-identical refine
    behavior. USER_EDITED nodes are preserved verbatim across re-refinement."""

    DRAFT = "DRAFT"
    AI_GENERATED = "AI_GENERATED"
    USER_EDITED = "USER_EDITED"
    CONFIRMED = "CONFIRMED"


class PlotSource(str, Enum):
    """Who produced a node: the LLM, an automated step, or a human (manual)."""

    AUTO = "AUTO"
    MANUAL = "MANUAL"
    LLM = "LLM"


_STATUS_LABEL_ZH = {
    PlanningStatus.DRAFT: "草稿",
    PlanningStatus.AI_GENERATED: "AI 生成",
    PlanningStatus.USER_EDITED: "用户已编辑",
    PlanningStatus.CONFIRMED: "已确认",
}
_STATUS_LABEL_EN = {
    PlanningStatus.DRAFT: "Draft",
    PlanningStatus.AI_GENERATED: "AI-generated",
    PlanningStatus.USER_EDITED: "User-edited",
    PlanningStatus.CONFIRMED: "Confirmed",
}


def status_label(status: PlanningStatus) -> str:
    return _STATUS_LABEL_ZH[status] if get_lang() == Lang.ZH else _STATUS_LABEL_EN[status]


def _coerce_status(value: object) -> PlanningStatus:
    if isinstance(value, PlanningStatus):
        return value
    try:
        return PlanningStatus(str(value))
    except ValueError:
        return PlanningStatus.AI_GENERATED


def _coerce_source(value: object) -> PlotSource:
    if isinstance(value, PlotSource):
        return value
    try:
        return PlotSource(str(value))
    except ValueError:
        return PlotSource.LLM


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
    planning_status: PlanningStatus = PlanningStatus.AI_GENERATED
    source: PlotSource = PlotSource.LLM

    def __post_init__(self) -> None:
        self.planning_status = _coerce_status(self.planning_status)
        self.source = _coerce_source(self.source)


@dataclass
class Act:
    name: str
    description: str
    scenes: list[SceneSpec] = field(default_factory=list)
    planning_status: PlanningStatus = PlanningStatus.AI_GENERATED
    source: PlotSource = PlotSource.LLM

    def __post_init__(self) -> None:
        self.planning_status = _coerce_status(self.planning_status)
        self.source = _coerce_source(self.source)


@dataclass
class PlotOutline:
    structure: NarrativeStructure
    acts: list[Act] = field(default_factory=list)
    character_arcs: dict[str, list[str]] = field(default_factory=dict)
