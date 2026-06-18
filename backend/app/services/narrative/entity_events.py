"""Entity event sourcing — read-only auditable event stream (T3-⑥).

Derives an append-only EntityEvent stream from the per-scene
`character_changes` that SceneResolution ALREADY writes onto each SceneArchive
(emotion_change / goal_update / relationship_changes), plus a `reveal` event on
a character's first appearance. This is a READ-ONLY view: zero write-path
change, zero persistence mutation in the first slice — it turns the deltas the
engine already captures into a replayable audit trail + a state-reconstruction
query.

Downstream consumers: T3-⑤ (OOC-vs-Breakout) reads get_arc_transitions to judge
whether a deviation was an earned arc moment; reconstruct_state supports
future state machines. Kinds: emotion_shift | goal_update | relationship_delta |
reveal. (A true arc_transition inferred from CharacterProfile.arc_stage
snapshots is a future extension — the engine doesn't persist per-chapter
snapshots yet; get_arc_transitions returns the emotion/relationship state
changes as the arc signal in the meantime.)
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Literal

from app.services.scene_engine.resolution import SceneArchive

from .types import ChapterPlan

EventKind = Literal["emotion_shift", "goal_update", "relationship_delta", "reveal"]


@dataclass(frozen=True)
class EntityEvent:
    """One character state-change observation, anchored to a chapter/scene."""

    event_id: str
    character_id: str
    chapter: int
    scene_id: str
    kind: EventKind
    after: Any = None        # the new value/text (before is not captured per-scene)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class CharacterEventHistory:
    """Append-only event stream for the cast, with replay/query helpers."""

    events: list[EntityEvent] = field(default_factory=list)

    def get_events(
        self, character_id: str,
        from_chapter: int | None = None, to_chapter: int | None = None,
    ) -> list[EntityEvent]:
        out: list[EntityEvent] = []
        for e in self.events:
            if e.character_id != character_id:
                continue
            if from_chapter is not None and e.chapter < from_chapter:
                continue
            if to_chapter is not None and e.chapter > to_chapter:
                continue
            out.append(e)
        return out

    def get_arc_transitions(
        self, character_id: str, up_to_chapter: int | None = None,
    ) -> list[EntityEvent]:
        """Notable state changes (emotion/relationship) — the arc signal.

        reveal is excluded (it's an appearance, not a transition). Used by the
        OOC-vs-Breakout classifier (T3-⑤) to tell an earned arc moment from a
        regression."""
        return [
            e for e in self.get_events(character_id, to_chapter=up_to_chapter)
            if e.kind in ("emotion_shift", "relationship_delta")
        ]

    def reconstruct_state(self, character_id: str, at_chapter: int) -> dict[str, Any]:
        """Replay events up to and including `at_chapter` into a state snapshot."""
        emotion = ""
        goal = ""
        relationships: dict[str, Any] = {}
        for e in self.get_events(character_id, to_chapter=at_chapter):
            if e.kind == "emotion_shift" and e.after:
                emotion = e.after
            elif e.kind == "goal_update" and e.after:
                goal = e.after
            elif e.kind == "relationship_delta":
                other = e.evidence.get("other_id", "")
                if other:
                    relationships[other] = e.after
        return {"emotion": emotion, "goal": goal, "relationships": relationships}

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterEventHistory":
        events = [
            EntityEvent(
                event_id=e["event_id"], character_id=e["character_id"],
                chapter=e["chapter"], scene_id=e["scene_id"], kind=e["kind"],
                after=e.get("after"), evidence=e.get("evidence", {}),
            )
            for e in data.get("events", [])
        ]
        return cls(events=events)


def _scene_to_chapter(chapter_plan: ChapterPlan) -> dict[str, int]:
    out: dict[str, int] = {}
    for spec in chapter_plan.chapters:
        for sid in spec.scene_ids:
            out[sid] = spec.number
    return out


def build_entity_event_history(
    archives: list[SceneArchive], chapter_plan: ChapterPlan
) -> CharacterEventHistory:
    """Derive the event stream from scene archives. Pure; empty archives => empty.

    Archives are mapped to chapters via ChapterSpec.scene_ids (an archive in no
    chapter spec is skipped, mirroring tension_scorer/relationship_trend).
    character_changes entries carrying an 'error' key are skipped. Within a
    chapter, events are ordered by scene order; a character's first appearance
    across the whole book emits a single `reveal`."""
    scene_to_chapter = _scene_to_chapter(chapter_plan)

    # chapter -> list[(scene_id, char_id, changes)] in scene order
    per_chapter: dict[int, list[tuple[str, str, dict]]] = {}
    for archive in archives:
        ch = scene_to_chapter.get(archive.scene_id)
        if ch is None:
            continue
        for char_id, changes in (archive.character_changes or {}).items():
            if not isinstance(changes, dict) or "error" in changes:
                continue
            per_chapter.setdefault(ch, []).append((archive.scene_id, char_id, changes))

    events: list[EntityEvent] = []
    seen: set[str] = set()
    for ch in sorted(per_chapter):
        for scene_id, char_id, changes in per_chapter[ch]:
            if char_id not in seen:
                seen.add(char_id)
                events.append(EntityEvent(
                    event_id=f"{char_id}:ch{ch}:reveal", character_id=char_id,
                    chapter=ch, scene_id=scene_id, kind="reveal",
                ))
            emotion = str(changes.get("emotion_change", "") or "").strip()
            if emotion:
                events.append(EntityEvent(
                    event_id=f"{char_id}:{scene_id}:emotion", character_id=char_id,
                    chapter=ch, scene_id=scene_id, kind="emotion_shift",
                    after=emotion,
                ))
            goal = str(changes.get("goal_update", "") or "").strip()
            if goal:
                events.append(EntityEvent(
                    event_id=f"{char_id}:{scene_id}:goal", character_id=char_id,
                    chapter=ch, scene_id=scene_id, kind="goal_update", after=goal,
                ))
            rel = changes.get("relationship_changes") or {}
            if isinstance(rel, dict):
                for other_id, text in rel.items():
                    after = text if isinstance(text, str) else str(text)
                    events.append(EntityEvent(
                        event_id=f"{char_id}:{scene_id}:rel:{other_id}",
                        character_id=char_id, chapter=ch, scene_id=scene_id,
                        kind="relationship_delta", after=after,
                        evidence={"other_id": str(other_id)},
                    ))
    return CharacterEventHistory(events=events)
