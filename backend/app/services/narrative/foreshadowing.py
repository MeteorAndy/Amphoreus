"""Foreshadowing registry + POV firewall — two data-shape primitives.

PART A — Foreshadowing registry:
  An immutable `Foreshadowing` record (frozen dataclass with `__post_init__`
  invariants) plus a `ForeshadowingRegistry` that owns a list of them and offers
  chapter-relative query + GC helpers. The registry is the bookkeeping layer a
  plot planner uses to track planted-but-unresolved threads, surface overdue or
  imminent payoffs, and garbage-collect stale low-stakes hints by importance.

PART B — POV firewall:
  `visible_profile` is the single chokepoint that decides what of a character is
  visible at a given chapter. The `CharacterProfile` entity itself does NOT
  self-filter — it exposes raw `public_profile` / `hidden_profile` /
  `reveal_chapter`; only this assembly-layer function evaluates the reveal
  predicate. Hidden material is appended ONLY when `reveal_chapter is None` or
  `current_chapter is not None and current_chapter >= reveal_chapter`.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from app.models.character import CharacterProfile

_IMPORTANCE_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
_VALID_STATUS = {"PLANTED", "RESOLVED", "ABANDONED"}


@dataclass(frozen=True)
class Foreshadowing:
    """One planted narrative thread tracked from setup to payoff.

    Immutable: state transitions (e.g. resolving) are made by producing a new
    instance via `dataclasses.replace`, never by mutating in place.
    """

    id: str
    planted_in_chapter: int
    description: str
    importance: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    status: str  # "PLANTED" | "RESOLVED" | "ABANDONED"
    suggested_resolve_chapter: int | None = None
    resolved_in_chapter: int | None = None

    def __post_init__(self) -> None:
        if self.importance not in _IMPORTANCE_RANK:
            raise ValueError(f"unknown importance: {self.importance!r}")
        if self.status not in _VALID_STATUS:
            raise ValueError(f"unknown status: {self.status!r}")
        if self.status == "RESOLVED" and self.resolved_in_chapter is None:
            raise ValueError("RESOLVED foreshadowing requires resolved_in_chapter")
        if (
            self.resolved_in_chapter is not None
            and self.resolved_in_chapter < self.planted_in_chapter
        ):
            raise ValueError("resolved_in_chapter must be >= planted_in_chapter")

    @property
    def importance_rank(self) -> int:
        return _IMPORTANCE_RANK[self.importance]

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Foreshadowing":
        return cls(
            id=data["id"],
            planted_in_chapter=data["planted_in_chapter"],
            description=data.get("description", ""),
            importance=data["importance"],
            status=data["status"],
            suggested_resolve_chapter=data.get("suggested_resolve_chapter"),
            resolved_in_chapter=data.get("resolved_in_chapter"),
        )


class ForeshadowingRegistry:
    """Owns a list of `Foreshadowing` records, keyed by id.

    All query helpers are chapter-relative and return plain lists; the registry
    never mutates a record in place — resolution replaces an entry with a new
    immutable instance.
    """

    def __init__(self, items: list[Foreshadowing] | None = None) -> None:
        self._items: dict[str, Foreshadowing] = {}
        for item in items or []:
            self.register(item)

    def __len__(self) -> int:
        return len(self._items)

    @property
    def items(self) -> list[Foreshadowing]:
        return list(self._items.values())

    def register(self, item: Foreshadowing) -> None:
        if item.id in self._items:
            raise ValueError(f"duplicate foreshadowing id: {item.id!r}")
        self._items[item.id] = item

    def mark_resolved(self, id: str, chapter: int) -> Foreshadowing:
        existing = self._items.get(id)
        if existing is None:
            raise KeyError(f"unknown foreshadowing id: {id!r}")
        resolved = dataclasses.replace(
            existing, status="RESOLVED", resolved_in_chapter=chapter
        )
        self._items[id] = resolved
        return resolved

    def get_unresolved(self) -> list[Foreshadowing]:
        return [i for i in self._items.values() if i.status == "PLANTED"]

    def get_ready_to_resolve(self, current: int) -> list[Foreshadowing]:
        return [
            i
            for i in self._items.values()
            if i.status == "PLANTED"
            and i.suggested_resolve_chapter is not None
            and i.suggested_resolve_chapter <= current
        ]

    def get_overdue(self, current: int) -> list[Foreshadowing]:
        return [
            i
            for i in self._items.values()
            if i.status == "PLANTED"
            and i.suggested_resolve_chapter is not None
            and i.suggested_resolve_chapter < current
        ]

    def get_upcoming(self, current: int, window: int = 3) -> list[Foreshadowing]:
        return [
            i
            for i in self._items.values()
            if i.status == "PLANTED"
            and i.suggested_resolve_chapter is not None
            and current < i.suggested_resolve_chapter <= current + window
        ]

    def apply_ttl_downgrade(self, current: int, ttl: int = 15) -> None:
        for id, item in list(self._items.items()):
            if item.status != "PLANTED":
                continue
            if item.importance in ("HIGH", "CRITICAL"):
                continue
            age = current - item.planted_in_chapter
            limit = ttl if item.importance == "LOW" else ttl * 1.2
            if age > limit:
                self._items[id] = dataclasses.replace(item, status="ABANDONED")

    def get_t0_eligible(self, current: int, max_items: int = 6) -> list[Foreshadowing]:
        """Rank still-PLANTED threads by urgency for resolution this chapter.

        Sort key per item: (bucket, -importance_rank, -age) where
        bucket = 0 overdue (suggested < current), 1 imminent (suggested >=
        current), 2 other (no suggested chapter); age = current - planted, so
        higher importance and older threads rank first. Truncated to max_items.
        """

        def bucket(item: Foreshadowing) -> int:
            s = item.suggested_resolve_chapter
            if s is None:
                return 2
            return 0 if s < current else 1

        def sort_key(item: Foreshadowing) -> tuple[int, int, int]:
            age = current - item.planted_in_chapter
            return (bucket(item), -item.importance_rank, -age)

        ranked = sorted(self.get_unresolved(), key=sort_key)
        return ranked[:max_items]

    def to_dict(self) -> dict:
        return {"items": [i.to_dict() for i in self._items.values()]}

    @classmethod
    def from_dict(cls, data: dict) -> "ForeshadowingRegistry":
        items = [Foreshadowing.from_dict(d) for d in data.get("items", [])]
        return cls(items)


def visible_profile(char: CharacterProfile, current_chapter: int | None) -> str:
    """POV-firewall chokepoint: the character's profile visible at a chapter.

    Returns `public_profile` (falling back to `appearance` when empty) and
    appends `hidden_profile` ONLY when `reveal_chapter is None` or the current
    chapter has reached the reveal point. The `CharacterProfile` entity does not
    self-filter — this assembly-layer function is the sole evaluator of the
    reveal predicate.
    """
    base = char.public_profile or char.appearance or ""
    reveal = char.reveal_chapter
    revealed = reveal is None or (
        current_chapter is not None and current_chapter >= reveal
    )
    if revealed and char.hidden_profile:
        return f"{base}\n{char.hidden_profile}".strip() if base else char.hidden_profile
    return base


def render_foreshadowing_block(
    registry: "ForeshadowingRegistry | None",
    current_chapter: int,
    is_zh: bool,
    max_items: int = 6,
) -> str:
    """Render the T0 foreshadowing reminder block for a chapter's prompt.

    Applies TTL downgrade (GC of stale low-stakes threads) then selects the
    most urgent still-PLANTED threads via get_t0_eligible. Returns "" when there
    is no registry or nothing eligible, so callers can inject unconditionally.

    Each bullet shows the thread description, importance, and an urgency tag
    (overdue / imminent / upcoming) relative to current_chapter.
    """
    if registry is None:
        return ""
    registry.apply_ttl_downgrade(current_chapter)
    eligible = registry.get_t0_eligible(current_chapter, max_items)
    if not eligible:
        return ""

    def _tag(item: Foreshadowing) -> str:
        s = item.suggested_resolve_chapter
        if s is None:
            return "待处理" if is_zh else "open"
        if s < current_chapter:
            return "逾期" if is_zh else "overdue"
        if s == current_chapter:
            return "本章" if is_zh else "due now"
        return "临近" if is_zh else "upcoming"

    if is_zh:
        header = "## 伏笔线索（需在本章或临近章节回收）\n"
        lines = [
            f"- 【{_tag(i)}·{i.importance}】{i.description}" for i in eligible
        ]
        footer = "\n请在本章自然地推进或回收上述线索，不要生硬提及。"
    else:
        header = "## Planted threads (resolve at or near this chapter)\n"
        lines = [
            f"- [{_tag(i)} · {i.importance}] {i.description}" for i in eligible
        ]
        footer = "\nAdvance or pay off these threads naturally; do not name them mechanically."
    return header + "\n".join(lines) + footer
