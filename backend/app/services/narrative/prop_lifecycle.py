"""Prop lifecycle / Chekhov-gun tracking — post-write consistency diagnostic (T2-⑦).

The consistency SIBLING to foreshadowing, but at the opposite end of the
pipeline. A foreshadowing thread is an authorial PROMISE tracked pre-write and
injected into prompts to steer generation; a PROP is a concrete narrative
OBJECT (a key, a letter, a blade) read back OUT of the finished prose and
checked only for Chekhov-gun consistency: was an introduced object ever used /
fired, or deliberately abandoned? It never shapes generation and (in this MVP)
is never persisted — it twins the T2-⑤ tension report: post-write, report-only,
opt-in, transient.

Layers:
- PropMentionExtractor — ONE LLM call over the assembled prose, tagging object
  mentions with a predicate (INTRODUCE/USE/RESOLVE/ABANDON) and chapter. Mirrors
  ProseFactExtractor's graceful degrade: any error or malformed payload -> [].
- classify_props — pure, deterministic: groups mentions per normalized object
  name and derives a single lifecycle status. Zero-LLM, side-effect-free.
- build_prop_lifecycle_report — async orchestrator (awaits the extractor only);
  NEVER raises. Empty extraction -> empty report, so the write path is safe.

The predicate set is deliberately SEPARATE from the knowledge-graph _EDGE_SCHEMA
(types_post_write): props are not graph edges, and polluting that contract would
emit invalid edges into Kuzu.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from app.core.llm_client import LLMClient, LLMError

from .prompts import _get_prop_extractor_prompt

_VALID_PREDICATE = {"INTRODUCE", "USE", "RESOLVE", "ABANDON"}
_VALID_STATUS = {"PAID_OFF", "UNRESOLVED", "ABANDONED"}
# Leading articles stripped during same-language name normalization. Cross-
# language and synonym coreference are explicitly out of scope (MVP).
_ARTICLES = ("the ", "a ", "an ", "那把", "那个", "这把", "这个", "那", "这")


# --- data shapes (mirror Foreshadowing / TensionReport conventions) -------

@dataclass(frozen=True)
class PropMention:
    """One raw object mention pulled from prose by the extractor."""

    object_name: str
    predicate: str  # INTRODUCE | USE | RESOLVE | ABANDON
    chapter: int
    evidence: str = ""

    def __post_init__(self) -> None:
        if self.predicate not in _VALID_PREDICATE:
            raise ValueError(f"unknown predicate: {self.predicate!r}")


@dataclass(frozen=True)
class PropLifecycle:
    """Derived per-object lifecycle. status is computed, never stored raw."""

    object_name: str
    introduced_in_chapter: int
    status: str  # PAID_OFF | UNRESOLVED | ABANDONED
    use_count: int
    mention_chapters: list[int] = field(default_factory=list)
    last_chapter: int = 0

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATUS:
            raise ValueError(f"unknown status: {self.status!r}")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PropLifecycle":
        return cls(
            object_name=data["object_name"],
            introduced_in_chapter=data["introduced_in_chapter"],
            status=data["status"],
            use_count=data["use_count"],
            mention_chapters=list(data.get("mention_chapters", [])),
            last_chapter=data.get("last_chapter", 0),
        )


@dataclass(frozen=True)
class PropLifecycleReport:
    """The diagnostic: every tracked prop + the Chekhov-violation shortlist."""

    props: list[PropLifecycle] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)  # object_names, UNRESOLVED

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


# --- name normalization ---------------------------------------------------

def _normalize(name: str) -> str:
    """Same-language de-dupe key: trim, casefold, strip a leading article."""
    n = " ".join(name.strip().split()).casefold()
    for art in _ARTICLES:
        a = art.casefold()
        if n.startswith(a):
            n = n[len(a):].strip()
            break
    return n


# --- deterministic classifier ---------------------------------------------

def classify_props(mentions: list[PropMention]) -> list[PropLifecycle]:
    """Group mentions by normalized name and derive one lifecycle each. Pure.

    Status rule: any ABANDON -> ABANDONED (deliberate red herring, not a defect);
    else any USE/RESOLVE -> PAID_OFF (the gun fired); else (introduced, never
    used) -> UNRESOLVED (the Chekhov violation). introduced_in_chapter is the
    earliest mention chapter, so a USE seen before its INTRODUCE still anchors
    correctly."""
    grouped: dict[str, list[PropMention]] = {}
    display: dict[str, str] = {}
    for m in mentions:
        key = _normalize(m.object_name)
        if not key:
            continue
        grouped.setdefault(key, []).append(m)
        display.setdefault(key, m.object_name.strip())

    out: list[PropLifecycle] = []
    for key, ms in grouped.items():
        chapters = sorted(m.chapter for m in ms)
        preds = [m.predicate for m in ms]
        use_count = sum(1 for p in preds if p in ("USE", "RESOLVE"))
        if "ABANDON" in preds:
            status = "ABANDONED"
        elif use_count > 0:
            status = "PAID_OFF"
        else:
            status = "UNRESOLVED"
        out.append(PropLifecycle(
            object_name=display[key],
            introduced_in_chapter=chapters[0],
            status=status,
            use_count=use_count,
            mention_chapters=chapters,
            last_chapter=chapters[-1],
        ))
    return out


# --- LLM extractor (graceful degrade, mirrors ProseFactExtractor) ---------

class PropMentionExtractor:
    """Extracts object mentions + predicates from prose via one LLM call."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def extract(self, prose: str) -> list[PropMention]:
        """Return object mentions asserted by *prose*. Never raises."""
        if not prose or not prose.strip():
            return []

        messages = [
            {"role": "system", "content": _get_prop_extractor_prompt()},
            {"role": "user", "content": prose},
        ]
        try:
            payload = await self._llm.chat_json(messages, temperature=0.1)
        except (LLMError, Exception):
            return []

        rows = payload.get("mentions") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return []

        mentions: list[PropMention] = []
        seen: set[tuple[str, str, int]] = set()
        for row in rows:
            mention = _parse_mention(row)
            if mention is None:
                continue
            key = (mention.object_name, mention.predicate, mention.chapter)
            if key in seen:
                continue
            seen.add(key)
            mentions.append(mention)
        return mentions


def _parse_mention(row: object) -> PropMention | None:
    """Coerce one raw JSON row into a PropMention, or None if unusable."""
    if not isinstance(row, dict):
        return None
    name = str(row.get("object_name", "")).strip()
    predicate = str(row.get("predicate", "")).strip().upper()
    if not name or predicate not in _VALID_PREDICATE:
        return None
    try:
        chapter = int(row.get("chapter", 0))
    except (TypeError, ValueError):
        chapter = 0
    evidence = str(row.get("evidence", "")).strip()
    return PropMention(object_name=name, predicate=predicate, chapter=chapter, evidence=evidence)


# --- async orchestrator ----------------------------------------------------

async def build_prop_lifecycle_report(llm: LLMClient, prose: str) -> PropLifecycleReport:
    """Extract -> classify -> report. Never raises; degrades to an empty report."""
    mentions = await PropMentionExtractor(llm).extract(prose)
    props = classify_props(mentions)
    unresolved = [p.object_name for p in props if p.status == "UNRESOLVED"]
    return PropLifecycleReport(props=props, unresolved=unresolved)
