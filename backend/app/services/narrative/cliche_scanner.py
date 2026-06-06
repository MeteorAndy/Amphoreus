"""Deterministic cliche / AI-flavor scanner — zero-LLM, pure, side-effect free.

Ported from PlotPilot's anti_ai_audit. Flags common LLM-prose tics (ZH + EN)
as diagnostics, not hard bans. Scoring mirrors anti_ai_audit:

    ai_flavor_score = min(100, (sum(weights) / max(len(text), 1)) * _SCALE)

with critical=3.0 / warning=1.0 / info=0.3 and _SCALE=1000.0. The scale is
chosen so a clean page scores near 0 while a cliche-dense page scores high
(a single critical in a 200-char page yields (3/200)*1000 = 15.0).

char_count uses raw len(text) — NOT count_words() — to keep parity with the
ported formula and avoid skewing EN vs ZH scores.

Overuse rules (一丝/一抹/仿佛 …) are count-thresholded via _Rule.min_count so a
single tasteful occurrence never fires; only repeated reliance does.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

_WEIGHTS = {"critical": 3.0, "warning": 1.0, "info": 0.3}
_SCALE = 1000.0
_EXCERPT_WINDOW = 20
_EXCERPT_CAP = 60


@dataclass(frozen=True)
class ClicheHit:
    """One detected cliche occurrence with context and a remediation hint."""

    name: str
    severity: str
    category: str
    span_excerpt: str
    replacement_hint: str


@dataclass
class ClicheReport:
    """Scan result: the hit list and an aggregate AI-flavor score (0-100)."""

    hits: list[ClicheHit] = field(default_factory=list)
    ai_flavor_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class _Rule:
    """A compiled scan rule. min_count > 1 marks a count-thresholded overuse rule."""

    pattern: re.Pattern
    name: str
    severity: str
    category: str
    replacement_hint: str
    min_count: int = 1


def _zh(pat: str) -> re.Pattern:
    return re.compile(pat)


def _en(pat: str) -> re.Pattern:
    return re.compile(pat, re.IGNORECASE)


_RULES: list[_Rule] = [
    # ---- ZH facial / mouth cliches --------------------------------------
    _Rule(_zh(r"嘴角(?:微微)?勾起"), "mouth_corner_curl", "critical",
          "facial_cliche", "改写为具体动作或省略；避免千篇一律的'嘴角勾起'。"),
    _Rule(_zh(r"勾起(?:一抹|一丝)?(?:弧度|笑意|冷笑|弧线)"), "curl_arc", "critical",
          "facial_cliche", "用人物特有的反应替换程式化弧度描写。"),
    _Rule(_zh(r"勾(?:了勾|起)嘴角"), "hooked_lip", "warning",
          "facial_cliche", "换一个更具体的表情或留白。"),
    _Rule(_zh(r"挑(?:了挑|起)?(?:眉|眉梢)"), "raised_brow", "info",
          "facial_cliche", "偶尔可用，频繁则套路化。"),
    # ---- ZH eye metaphors ------------------------------------------------
    _Rule(_zh(r"眸光"), "eye_light", "warning",
          "eye_metaphor", "'眸光'易堆砌；改用具体目光动作。"),
    _Rule(_zh(r"眸子"), "eye_pupil", "warning",
          "eye_metaphor", "'眸子'网文味重；用'眼睛/目光'更克制。"),
    _Rule(_zh(r"眼底(?:闪过|划过|掠过)"), "eye_flash", "warning",
          "eye_metaphor", "情绪闪过眼底是高频套话，改为外显动作。"),
    # ---- ZH narrator / perception ---------------------------------------
    _Rule(_zh(r"不易察觉(?:的|地)"), "imperceptible", "critical",
          "narrator_intrusion", "若读者察觉不到就不必写；删除或改为可见细节。"),
    _Rule(_zh(r"不知为(?:何|什么)"), "unknown_why", "warning",
          "narrator_intrusion", "'不知为何'回避动机，给出真实理由或删去。"),
    _Rule(_zh(r"似乎(?:有些|有点)?"), "seems_hedge", "info",
          "narrator_intrusion", "过多'似乎'削弱叙述确定性。", 3),
    # ---- ZH breath / body ------------------------------------------------
    _Rule(_zh(r"深(?:深)?吸(?:了)?一口气"), "deep_breath", "warning",
          "breath", "'深吸一口气'是情绪填充语，换具体身体反应。"),
    _Rule(_zh(r"(?:倒|猛)吸(?:了)?一口(?:凉|冷)气"), "gasp_cold", "warning",
          "breath", "惊讶的程式化写法，改为独特细节。"),
    _Rule(_zh(r"心(?:中|里|头)一(?:紧|沉|颤)"), "heart_tighten", "critical",
          "breath", "'心中一紧'是最高频情绪套话，必改。"),
    # ---- ZH atmosphere ---------------------------------------------------
    _Rule(_zh(r"空气(?:仿佛|似乎)?(?:瞬间)?凝(?:固|滞)"), "air_freeze", "critical",
          "atmosphere", "'空气凝固'陈词；用具体的静默或声音刻画紧张。"),
    _Rule(_zh(r"(?:时间|时光)(?:仿佛)?(?:凝固|静止)"), "time_freeze", "warning",
          "atmosphere", "时间静止是套路，改写为感官细节。"),
    _Rule(_zh(r"鸦雀无声"), "dead_silence", "info",
          "atmosphere", "成语堆砌，偶用可、勿滥。", 2),
    # ---- ZH simile overuse (count-thresholded) ---------------------------
    _Rule(_zh(r"仿佛"), "fangfu_overuse", "warning",
          "simile_overuse", "'仿佛'反复出现显机械；控制频次。", 3),
    _Rule(_zh(r"宛如"), "wanru_overuse", "info",
          "simile_overuse", "'宛如'多用则匠气。", 3),
    _Rule(_zh(r"一丝"), "yisi_overuse", "info",
          "simile_overuse", "'一丝X'高频量词套话，分散替换。", 3),
    _Rule(_zh(r"一抹"), "yimo_overuse", "info",
          "simile_overuse", "'一抹X'同上，过量则程式化。", 3),
    _Rule(_zh(r"眸"), "mou_overuse", "info",
          "eye_metaphor", "'眸'字密度过高即网文腔。", 4),
    # ---- EN cliches (case-insensitive) -----------------------------------
    _Rule(_en(r"a shiver (?:ran|went|crept) (?:down|up) (?:his|her|their|its) spine"),
          "shiver_spine", "critical", "en_cliche",
          "Replace with a concrete physical detail."),
    _Rule(_en(r"could(?:n't|n’t| not) help but"), "couldnt_help_but", "warning",
          "en_cliche", "Often filler — state the action directly."),
    _Rule(_en(r"little did (?:he|she|they|i|we) know"), "little_did_know",
          "critical", "narrator_intrusion",
          "Foreshadowing crutch; trust the reader."),
    _Rule(_en(r"(?:his|her|their|my) heart (?:skipped a beat|skipped|pounded in (?:his|her|their|my) chest)"),
          "heart_skipped", "critical", "en_cliche",
          "Tired beat — show the reaction specifically."),
    _Rule(_en(r"a (?:wave|surge) of (?:emotion|relief|fear|anger) (?:washed|swept) over"),
          "wave_of_emotion", "warning", "en_cliche",
          "Name the feeling through behavior, not a wave."),
    _Rule(_en(r"\bbarely (?:above )?a whisper\b"), "barely_whisper", "info",
          "en_cliche", "Common dialogue tag cliche."),
    _Rule(_en(r"\beyes (?:widened|narrowed)\b"), "eyes_widened", "info",
          "en_cliche", "Frequent face-acting; vary or cut.", 2),
]


def _excerpt(text: str, start: int, end: int) -> str:
    """Return a windowed slice around [start, end), capped for readability."""
    lo = max(0, start - _EXCERPT_WINDOW)
    hi = min(len(text), end + _EXCERPT_WINDOW)
    return text[lo:hi].strip()[:_EXCERPT_CAP]


def scan(text: str) -> ClicheReport:
    """Scan text for cliche / AI-flavor tics. Pure, deterministic, zero LLM.

    Empty/whitespace-safe. Overuse rules (min_count > 1) fire only when the
    pattern occurs at least min_count times; other rules emit one hit per
    match with a windowed span excerpt. Identical (name, excerpt) pairs are
    deduped before scoring to avoid double-counting overlapping patterns.
    """
    if not text or not text.strip():
        return ClicheReport()

    hits: list[ClicheHit] = []
    seen: set[tuple[str, str]] = set()

    for rule in _RULES:
        if rule.min_count > 1:
            matches = list(rule.pattern.finditer(text))
            if len(matches) < rule.min_count:
                continue
        else:
            matches = list(rule.pattern.finditer(text))
        for m in matches:
            excerpt = _excerpt(text, m.start(), m.end())
            key = (rule.name, excerpt)
            if key in seen:
                continue
            seen.add(key)
            hits.append(
                ClicheHit(
                    name=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    span_excerpt=excerpt,
                    replacement_hint=rule.replacement_hint,
                )
            )

    weight_sum = sum(_WEIGHTS[h.severity] for h in hits)
    score = min(100.0, (weight_sum / max(len(text), 1)) * _SCALE)
    return ClicheReport(hits=hits, ai_flavor_score=score)
