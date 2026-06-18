"""Relationship trend analysis — post-write diagnostic (T2-⑧).

Report-only (the cheap T2-⑤/⑥/⑦ shape): pure, zero-LLM, zero-Kuzu. Derives a
per-pair sentiment series from the free-text
`character_changes[*]['relationship_changes']` that SceneResolution already
writes onto each SceneArchive, then classifies a deterministic 4-way trend
(IMPROVING / DETERIORATING / VOLATILE / STABLE) and emits a bilingual
development suggestion. It does NOT touch the write path or Kuzu; history
recording is a deferred follow-up (see notes in the backlog memory).

Distinct from narrative_debt (unmet reader obligations) and tension_scorer
(which collapses relationship_changes to a per-scene boolean count): this is
the only component that keys by character PAIR, assembles a per-chapter
sentiment SERIES, and derives a pair-level trend.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from app.services.scene_engine.resolution import SceneArchive

from .types import ChapterPlan

# --- tuning constants (named so a calibration pass changes one line) -------

# Bilingual sentiment lexicons, substring match (case-insensitive for Latin),
# mirroring tension_scorer's keyword style.
_POSITIVE_KW = (
    "信任加深", "重归于好", "和解", "牺牲", "守护", "支持", "理解", "信任", "亲近",
    "trust", "reconcil", "ally", "support", "sacrifice", "protect", "warmth",
    "grateful", "loyalty",
)
_NEGATIVE_KW = (
    "背叛", "决裂", "反目", "愤怒", "仇恨", "敌意", "猜忌", "疏远", "指责", "伤害",
    "betray", "breakup", "hostile", "enmity", "rival", "estrang", "distrust",
    "accuse", "wound",
)
# A positive keyword is flipped to negative when a negation prefix appears
# in the ~10 chars immediately before it — guards against "不再信任" / "no
# longer trusts" without over-triggering on distant unrelated negations.
_NEGATION_PREFIX = ("不再", "没有", "不曾", "不", "没", "no longer", "not ", "never")
_NEGATION_WINDOW = 10

# Trend thresholds over the sentiment series.
_TREND_SLOPE = 0.20        # |slope| >= this => IMPROVING / DETERIORATING
_VOLATILE_REVERSALS = 2   # >= this many sign flips => VOLATILE (takes precedence)
_SCALE = 0.5              # each net positive signal contributes this much


# --- data shapes (mirror TensionReport conventions) -----------------------

@dataclass(frozen=True)
class StrengthPoint:
    """One chapter's sentiment for a pair."""

    chapter_number: int
    sentiment: float        # -1.0 .. +1.0
    signal: str             # positive | negative | neutral


@dataclass(frozen=True)
class RelationshipPairTrend:
    """A pair's per-chapter sentiment series + derived trend."""

    pair_key: str           # sorted "A|B"
    from_id: str
    to_id: str
    series: tuple[StrengthPoint, ...]
    trend: str              # IMPROVING | DETERIORATING | VOLATILE | STABLE
    delta_first_last: float
    observation_count: int
    suggestion_zh: str = ""
    suggestion_en: str = ""


@dataclass
class RelationshipTrendReport:
    """Whole-novel relationship trends, attached to WrittenOutput."""

    pairs: list[RelationshipPairTrend] = field(default_factory=list)
    chapter_count: int = 0
    schema_version: int = 1

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


# --- sentiment of free text (pure) ----------------------------------------

def _find_all(text: str, kw: str) -> list[int]:
    out: list[int] = []
    low = text.lower()
    needle = kw.lower()
    start = 0
    while True:
        i = low.find(needle, start)
        if i < 0:
            break
        out.append(i)
        start = i + 1
    return out


def sentiment_of_text(text: str) -> float:
    """Net sentiment of one relationship-change description in [-1, +1].

    Positive keywords flipped to negative when a negation prefix sits in the
    preceding window. Zero when no signal. Pure."""
    if not text:
        return 0.0

    pos = 0
    neg = 0
    for kw in _POSITIVE_KW:
        for i in _find_all(text, kw):
            # Check only the ~10 chars immediately before the keyword for a
            # negation prefix. Checking the entire preceding text over-triggers
            # on unrelated negations ("他们没有放弃，最终信任了彼此").
            window = text[max(0, i - _NEGATION_WINDOW):i].lower()
            if any(p.strip() and p in window for p in _NEGATION_PREFIX):
                neg += 1
            else:
                pos += 1
    for kw in _NEGATIVE_KW:
        neg += len(_find_all(text, kw))

    if pos == 0 and neg == 0:
        return 0.0
    return max(-1.0, min(1.0, (pos - neg) * _SCALE))


# --- pair series extraction (pure) ----------------------------------------

def _pair_key(a: str, b: str) -> tuple[str, str, str]:
    lo, hi = (a, b) if a <= b else (b, a)
    return f"{lo}|{hi}", lo, hi


def extract_pair_series(
    archives: list[SceneArchive], chapter_plan: ChapterPlan
) -> list[RelationshipPairTrend]:
    """Build a per-pair, per-chapter sentiment series from scene archives.

    Archives are mapped to chapters via ChapterSpec.scene_ids; an archive in no
    chapter spec is skipped (mirrors tension_scorer). character_changes entries
    carrying an 'error' key are skipped. other_id is treated opaquely (may be a
    name or an id) — the pair key is the sorted lexical join."""
    scene_to_chapter: dict[str, int] = {}
    for spec in chapter_plan.chapters:
        for sid in spec.scene_ids:
            scene_to_chapter[sid] = spec.number

    # pair_key -> {chapter -> [sentiments]}
    agg: dict[str, dict[int, list[float]]] = {}
    identity: dict[str, tuple[str, str]] = {}

    for archive in archives:
        chapter = scene_to_chapter.get(archive.scene_id)
        if chapter is None:
            continue
        for char_id, changes in (archive.character_changes or {}).items():
            if not isinstance(changes, dict) or "error" in changes:
                continue
            rel = changes.get("relationship_changes") or {}
            if not isinstance(rel, dict):
                continue
            for other_id, desc in rel.items():
                text = desc if isinstance(desc, str) else str(desc)
                s = sentiment_of_text(text)
                pk, lo, hi = _pair_key(str(char_id), str(other_id))
                identity.setdefault(pk, (lo, hi))
                agg.setdefault(pk, {}).setdefault(chapter, []).append(s)

    result: list[RelationshipPairTrend] = []
    for pk, by_chapter in agg.items():
        series = tuple(
            StrengthPoint(ch, _chapter_sentiment(vals), _tag(vals))
            for ch, vals in sorted(by_chapter.items())
        )
        lo, hi = identity[pk]
        result.append(_build_trend(pk, lo, hi, series))
    return result


def _chapter_sentiment(vals: list[float]) -> float:
    """Average of the sentiments recorded for a pair in one chapter."""
    if not vals:
        return 0.0
    return max(-1.0, min(1.0, sum(vals) / len(vals)))


def _tag(vals: list[float]) -> str:
    s = _chapter_sentiment(vals)
    if s > 0:
        return "positive"
    if s < 0:
        return "negative"
    return "neutral"


# --- trend classification (pure) ------------------------------------------

_SUGGESTIONS = {
    "IMPROVING": ("顺势推进这段和解，让它带来回报。", "Lean into the reconciliation; let it pay off."),
    "DETERIORATING": ("为冲突安排一次对峙，或一个转圜的契机。", "Set up a confrontation or a bridge moment."),
    "VOLATILE": ("该选定一个方向了，反复摇摆正在拖慢节奏。", "Choose a direction; the oscillation is stalling momentum."),
    "STABLE": ("可留在背景，或注入一个扰动。", "Safe to leave in background, or inject a perturbation."),
}


def _classify(series: tuple[StrengthPoint, ...]) -> tuple[str, float]:
    """Return (trend, delta_first_last). Pure."""
    n = len(series)
    if n < 2:
        return "STABLE", 0.0
    first, last = series[0].sentiment, series[-1].sentiment
    delta = round(last - first, 4)
    slope = (last - first) / (n - 1)

    diffs = [series[i + 1].sentiment - series[i].sentiment for i in range(n - 1)]
    reversals = 0
    prev_sign = 0
    for d in diffs:
        sign = (d > 0) - (d < 0)
        if sign != 0:
            if prev_sign != 0 and sign != prev_sign:
                reversals += 1
            prev_sign = sign

    if reversals >= _VOLATILE_REVERSALS:
        trend = "VOLATILE"
    elif slope >= _TREND_SLOPE:
        trend = "IMPROVING"
    elif slope <= -_TREND_SLOPE:
        trend = "DETERIORATING"
    else:
        trend = "STABLE"
    return trend, delta


def classify_trend(series: list[StrengthPoint]) -> RelationshipPairTrend:
    """Public pure entry: classify a series into a trend (identity fields empty
    — extract_pair_series fills them). Useful for unit-testing the algorithm."""
    series_t = tuple(series)
    trend, delta = _classify(series_t)
    zh, en = _SUGGESTIONS[trend]
    return RelationshipPairTrend(
        pair_key="", from_id="", to_id="", series=series_t,
        trend=trend, delta_first_last=delta, observation_count=len(series_t),
        suggestion_zh=zh, suggestion_en=en,
    )


def _build_trend(
    pair_key: str, from_id: str, to_id: str, series: tuple[StrengthPoint, ...]
) -> RelationshipPairTrend:
    trend, delta = _classify(series)
    zh, en = _SUGGESTIONS[trend]
    return RelationshipPairTrend(
        pair_key=pair_key, from_id=from_id, to_id=to_id, series=series,
        trend=trend, delta_first_last=delta, observation_count=len(series),
        suggestion_zh=zh, suggestion_en=en,
    )


def build_relationship_trend_report(
    archives: list[SceneArchive], chapter_plan: ChapterPlan
) -> RelationshipTrendReport:
    """Assemble the whole-novel report. Pure; empty archives => empty report."""
    pairs = extract_pair_series(archives, chapter_plan)
    chapter_count = len(chapter_plan.chapters)
    return RelationshipTrendReport(pairs=pairs, chapter_count=chapter_count)
