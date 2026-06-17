from __future__ import annotations

import json
from typing import Any

from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.relationship_builder import Relationship

from .base import BaseValidator
from .types import EvaluationContext, GuardianIssue, GuardianResult, Severity, Verdict
from .validators import (
    ArcIntegrityValidator,
    CharacterConsistencyValidator,
    PacingValidator,
    RelationshipLogicValidator,
    WorldRulesValidator,
)


_NARRATIVE_HISTORY_PATH = "story/narrative_history"
_MAX_RECENT_SCENES = 5


class StoryGuardian:
    """Orchestrates all five validators against a proposed plot change.

    Public interface:
      - async evaluate(
          proposed_plot: str,
          affected_characters: list[str],
          world_id: str | None = None
        ) -> GuardianResult
      - async evaluate_scene_intervention(
          scene_id: str,
          intervention: str,
          characters: list[str]
        ) -> GuardianResult
    """

    def __init__(self, llm: LLMClient, memory: MemoryManager,
                 *, classify_deviations: bool = False) -> None:
        self._llm = llm
        self._ov = memory.openviking
        self._kuzu = memory.kuzu
        # T3-⑤ OOC-vs-Breakout: opt-in post-verdict tagging (report-only).
        self._classify_deviations = classify_deviations

        self._validators: list[BaseValidator] = [
            CharacterConsistencyValidator(llm, memory),
            RelationshipLogicValidator(llm, memory),
            WorldRulesValidator(llm, memory),
            PacingValidator(llm, memory),
            ArcIntegrityValidator(llm, memory),
        ]

    async def evaluate(
        self,
        proposed_plot: str,
        affected_characters: list[str],
        world_id: str | None = None,
    ) -> GuardianResult:
        """Evaluate a proposed plot change against all validators."""
        context = await self._build_context(
            proposed_plot=proposed_plot,
            character_ids=affected_characters,
            world_id=world_id,
        )
        return await self._run_evaluation(context)

    async def evaluate_scene_intervention(
        self,
        scene_id: str,
        intervention: str,
        characters: list[str],
    ) -> GuardianResult:
        """Evaluate a mid-scene intervention against all validators."""
        proposed_plot = f"Intervention in scene [{scene_id}]: {intervention}"
        context = await self._build_context(
            proposed_plot=proposed_plot,
            character_ids=characters,
            world_id=None,
        )
        return await self._run_evaluation(context)

    # ------------------------------------------------------------------
    # Internal: context building
    # ------------------------------------------------------------------

    async def _build_context(
        self,
        proposed_plot: str,
        character_ids: list[str],
        world_id: str | None,
    ) -> EvaluationContext:
        characters: list[CharacterProfile] = []
        for cid in character_ids:
            char = await self._load_character(cid)
            if char is not None:
                characters.append(char)

        relationships = await self._load_relationships(character_ids)
        world_rules = await self._load_world_rules(world_id) if world_id else []
        recent_scenes = await self._load_recent_scenes()
        character_arcs = await self._load_plot_arcs(character_ids)

        return EvaluationContext(
            proposed_plot=proposed_plot,
            characters=characters,
            relationships=relationships,
            world_rules=world_rules,
            recent_scenes=recent_scenes,
            character_arcs=character_arcs,
        )

    async def _load_character(self, char_id: str) -> CharacterProfile | None:
        try:
            entry = self._ov.read_entry(f"chars/{char_id}/profile/full")
            data = json.loads(entry.l2)
            return CharacterProfile(**data)
        except Exception:
            return None

    async def _load_relationships(
        self, character_ids: list[str]
    ) -> list[Relationship]:
        """Load all relationships involving the given characters from Kuzu."""
        if not character_ids:
            return []

        relationships: list[Relationship] = []
        for cid in character_ids:
            try:
                rows = self._kuzu.query_cypher(
                    "MATCH (c:Character {name: $name})-[r:RELATES_TO]-(n:Character) "
                    "RETURN n.name AS target, r.properties AS props",
                    {"name": cid},
                )
            except Exception:
                continue

            for row in rows:
                target: str = row.get("target", "")
                props_raw: str = row.get("props", "{}")
                try:
                    props: dict[str, Any] = json.loads(props_raw)
                except (json.JSONDecodeError, TypeError):
                    props = {}

                relationships.append(
                    Relationship(
                        from_id=cid,
                        to_id=target,
                        rel_type=props.get("rel_type", "UNKNOWN"),
                        strength=float(props.get("strength", 0.5)),
                        description=props.get("description", ""),
                        established_event=props.get("established_event", ""),
                    )
                )

        return relationships

    async def _load_world_rules(
        self, world_id: str
    ) -> list[dict[str, Any]]:
        """Load world rules from an OpenViking world session."""
        try:
            entry = self._ov.read_entry(f"world/sessions/{world_id}/state")
            data = json.loads(entry.l2)
            extracted = data.get("extracted_data", {})
            return extracted.get("rules", [])
        except Exception:
            return []

    async def _load_recent_scenes(self) -> list[str]:
        """Load the last _MAX_RECENT_SCENES from narrative history."""
        try:
            entry = self._ov.read_entry(_NARRATIVE_HISTORY_PATH)
            data = json.loads(entry.l2)
            history: list[str] = data.get("scenes", [])
            return history[-_MAX_RECENT_SCENES:]
        except Exception:
            return []

    async def _load_plot_arcs(
        self, character_ids: list[str]
    ) -> dict[str, list[str]]:
        """Scan stored plots for character arc milestones."""
        arcs: dict[str, list[str]] = {}
        for cid in character_ids:
            arcs[cid] = []
            for label in ("story/plots",):
                try:
                    items = self._ov.search(
                        cid, scope="story"
                    )
                    for item in items:
                        if "/plots/" in item.path:
                            try:
                                entry = self._ov.read_entry(item.path)
                                data = json.loads(entry.l2)
                                char_arcs: dict[str, list[str]] = data.get(
                                    "character_arcs", {}
                                )
                                if cid in char_arcs:
                                    arcs[cid].extend(char_arcs[cid])
                            except Exception:
                                continue
                except Exception:
                    continue
        return arcs

    # ------------------------------------------------------------------
    # Internal: evaluation
    # ------------------------------------------------------------------

    async def _run_evaluation(self, context: EvaluationContext) -> GuardianResult:
        import asyncio

        tasks = [v.evaluate(context) for v in self._validators]
        results: list[list[GuardianIssue]] = await asyncio.gather(*tasks)

        all_issues: list[GuardianIssue] = []
        for issues in results:
            all_issues.extend(issues)

        if not all_issues:
            return GuardianResult(
                verdict=Verdict.APPROVED,
                issues=[],
                can_override=True,
            )

        severities = {i.severity for i in all_issues}
        if Severity.CRITICAL in severities:
            verdict = Verdict.REJECTED
            can_override = False
        elif Severity.WARNING in severities:
            verdict = Verdict.WARNING
            can_override = True
        else:
            verdict = Verdict.APPROVED
            can_override = True

        # T3-⑤ OOC-vs-Breakout (report-only): when opted in, tag each issue's
        # deviation_kind using arc-beat evidence already in the context. Verdict
        # and severities are NEVER changed — only the tag is stamped.
        if self._classify_deviations:
            from .deviation_classifier import classify_issues
            evidence = [beat for beats in context.character_arcs.values()
                        for beat in (beats or [])]
            kinds = classify_issues(all_issues, evidence)
            for issue, kind in zip(all_issues, kinds):
                issue.deviation_kind = kind.value

        return GuardianResult(
            verdict=verdict,
            issues=all_issues,
            can_override=can_override,
        )
