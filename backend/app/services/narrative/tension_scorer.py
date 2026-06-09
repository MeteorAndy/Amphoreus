"""Deterministic dramatic-tension scorer — zero-LLM, pure, side-effect free (T2-⑤).

Complements the existing quality signals: the phase directive (novel_writer)
*shapes* generation, the cliche/canon reports *catch defects*, and this scorer
answers the one question neither does — does the drama actually escalate where
the structure says it should?

It reads only fields SceneResolution already populates on SceneArchive
(rounds, final_environment.atmosphere, character_changes), so no new data is
collected. Like cliche_scanner it is a pure function over assembled artifacts
and attaches a report; it never touches the LLM generation path.

`phase_for_chapter` is the single source of truth for pacing boundaries; it
mirrors novel_writer._render_phase_directive exactly so a chapter's tension is
judged against the same phase its generation directive assumed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.services.narrative.types import ChapterPlan
from app.services.scene_engine.resolution import SceneArchive

# --- tuning constants -----------------------------------------------------

_ROUND_CAP = 10          # rounds beyond this add no further intensity
_W_ROUNDS = 0.35         # weight of scene duration/intensity proxy
_W_RELATIONSHIP = 0.30   # weight of relationship upheaval
_W_EMOTION = 0.25        # weight of emotional volatility
_W_GOAL = 0.10           # weight of unmet/contested goals
_HIGH_ROUND_FRAC = 0.6   # fraction of cap that marks a "high_round_count" scene

# Phase floors: the minimum tension a chapter in this phase should carry.
# A chapter scoring more than _FLAT_MARGIN below its floor reads "flat".
_PHASE_FLOOR = {"opening": 0.2, "development": 0.4, "convergence": 0.7, "finale": 0.75}
_FLAT_MARGIN = 0.15

# Bilingual keyword tables (cliche_scanner style). Substring match — kept short
# and high-signal so a single tasteful word does not over-fire.
_ESCALATION_KW = (
    "紧张", "危机", "对峙", "升级", "逼近", "一触即发", "冲突", "爆发", "高潮", "决战",
    "tension", "crisis", "escalat", "climax", "confront", "showdown", "imminent", "erupt",
)
_RESOLUTION_KW = (
    "平静", "释然", "落定", "归于", "和解", "尘埃落定", "安宁", "舒缓",
    "calm", "resolv", "settle", "peace", "aftermath", "relief", "reconcil",
)
_VOLATILE_EMOTION_KW = (
    "愤怒", "绝望", "恐惧", "崩溃", "狂", "悲痛", "震惊", "仇恨", "痛苦",
    "rage", "fury", "despair", "terror", "panic", "grief", "shock", "hatred", "anguish",
)
_UNMET_GOAL_KW = (
    "失败", "受挫", "破灭", "未能", "落空", "阻挠",
    "fail", "thwart", "denied", "lost", "unable", "frustrat",
)


# --- data shapes (mirror ClicheReport.to_dict convention) -----------------

@dataclass(frozen=True)
class TensionScore:
    """Per-scene tension diagnosis. Immutable, like ClicheHit."""

    scene_id: str
    intensity: float                                  # 0-1 aggregate measure
    direction: str                                    # rising | stable | falling
    conflict_signals: list[str] = field(default_factory=list)


@dataclass
class ChapterTension:
    """Per-chapter aggregate, judged against its expected pacing phase."""

    chapter_number: int
    tension: float                                    # 0-1 rising-weighted mean
    expected_phase: str                               # opening | … | finale
    expected_min: float                               # phase floor
    flat: bool                                        # reads flat vs its phase
    scene_scores: list[TensionScore] = field(default_factory=list)


@dataclass
class TensionReport:
    """Scan result: every scene score plus per-chapter aggregates."""

    scenes: list[TensionScore] = field(default_factory=list)
    chapters: list[ChapterTension] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# --- helpers --------------------------------------------------------------

def phase_for_chapter(chapter_num: int, total: int) -> str:
    """Map (chapter, total) to a pacing phase. SINGLE SOURCE OF TRUTH for the
    boundaries used by novel_writer._render_phase_directive (opening<=0.25,
    development<=0.75, convergence<=0.90, finale otherwise)."""
    ratio = chapter_num / max(total, 1)
    if ratio <= 0.25:
        return "opening"
    if ratio <= 0.75:
        return "development"
    if ratio <= 0.90:
        return "convergence"
    return "finale"


def _hits(text: str, keywords: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(kw.lower() in low for kw in keywords)


def _safe_changes(character_changes: dict[str, dict]) -> list[dict]:
    """Yield only non-error reflection entries. SceneResolution stores
    {"error": ..., emotion_change:"", ...} when a reflection raises; those carry
    no real signal and must be skipped (and never crash the scan)."""
    out: list[dict] = []
    for entry in (character_changes or {}).values():
        if not isinstance(entry, dict) or "error" in entry:
            continue
        out.append(entry)
    return out


# --- scene scoring --------------------------------------------------------

def score_scene_tension(archive: SceneArchive) -> TensionScore:
    """Score one scene's tension from data already on its archive. Pure."""
    signals: list[str] = []

    # 1) Round count — duration/intensity proxy, saturating at _ROUND_CAP.
    n_rounds = min(len(archive.rounds), _ROUND_CAP)
    round_factor = n_rounds / _ROUND_CAP
    if round_factor >= _HIGH_ROUND_FRAC:
        signals.append("high_round_count")

    entries = _safe_changes(archive.character_changes)

    # 2) Relationship upheaval — any non-empty relationship_changes across cast.
    rel_count = sum(len(e.get("relationship_changes") or {}) for e in entries)
    rel_factor = min(rel_count / 3.0, 1.0)
    if rel_count:
        signals.append("relationship_shift")

    # 3) Emotional volatility — volatile-emotion keywords in emotion_change.
    emo_hits = sum(1 for e in entries if _hits(e.get("emotion_change", "") or "", _VOLATILE_EMOTION_KW))
    emo_factor = min(emo_hits / 2.0, 1.0)
    if emo_hits:
        signals.append("emotional_volatility")

    # 4) Contested goals — unmet/thwarted-goal keywords in goal_update.
    goal_hits = sum(1 for e in entries if _hits(e.get("goal_update", "") or "", _UNMET_GOAL_KW))
    goal_factor = min(goal_hits / 2.0, 1.0)
    if goal_hits:
        signals.append("goal_unmet")

    intensity = (
        _W_ROUNDS * round_factor
        + _W_RELATIONSHIP * rel_factor
        + _W_EMOTION * emo_factor
        + _W_GOAL * goal_factor
    )
    intensity = max(0.0, min(1.0, intensity))

    # Direction from closing atmosphere keywords.
    atmosphere = archive.final_environment.atmosphere if archive.final_environment else ""
    rising = _hits(atmosphere, _ESCALATION_KW)
    falling = _hits(atmosphere, _RESOLUTION_KW)
    if rising and not falling:
        direction = "rising"
        signals.append("climactic_atmosphere")
    elif falling and not rising:
        direction = "falling"
    else:
        direction = "stable"

    return TensionScore(
        scene_id=archive.scene_id,
        intensity=round(intensity, 4),
        direction=direction,
        conflict_signals=signals,
    )


def aggregate_chapter_tension(
    scene_scores: list[TensionScore], chapter_number: int, total: int
) -> ChapterTension:
    """Aggregate scene scores into a chapter tension, judged vs its phase.

    Rising scenes are weighted up and falling scenes down, so a chapter that
    escalates reads hotter than one of equal mean intensity that deflates."""
    phase = phase_for_chapter(chapter_number, total)
    floor = _PHASE_FLOOR[phase]

    if scene_scores:
        weighted = 0.0
        for s in scene_scores:
            bump = {"rising": 0.1, "falling": -0.1}.get(s.direction, 0.0)
            weighted += max(0.0, min(1.0, s.intensity + bump))
        tension = round(weighted / len(scene_scores), 4)
    else:
        tension = 0.0

    flat = tension < (floor - _FLAT_MARGIN)
    return ChapterTension(
        chapter_number=chapter_number,
        tension=tension,
        expected_phase=phase,
        expected_min=floor,
        flat=flat,
        scene_scores=scene_scores,
    )


def build_tension_report(
    archives: list[SceneArchive], chapter_plan: ChapterPlan
) -> TensionReport:
    """Score every scene and group into per-chapter aggregates by scene_id.

    A chapter whose scene_ids match no archive yields tension 0.0 (no crash);
    an archive in no chapter spec is still scored in `scenes` but contributes
    to no chapter aggregate (acceptable — surfaced in the flat scene list)."""
    by_id = {a.scene_id: score_scene_tension(a) for a in archives}
    total = len(chapter_plan.chapters)

    chapters: list[ChapterTension] = []
    for spec in chapter_plan.chapters:
        scores = [by_id[sid] for sid in spec.scene_ids if sid in by_id]
        chapters.append(aggregate_chapter_tension(scores, spec.number, total))

    return TensionReport(scenes=list(by_id.values()), chapters=chapters)
