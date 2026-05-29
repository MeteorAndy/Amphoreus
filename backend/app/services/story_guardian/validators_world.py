from __future__ import annotations

import json
from typing import Any

from app.models.character import CharacterProfile

from .base import BaseValidator
from .prompts import (
    _get_arc_integrity_prompt,
    _get_pacing_prompt,
    _get_world_rules_prompt,
)
from .types import EvaluationContext, GuardianIssue, Severity


class WorldRulesValidator(BaseValidator):
    """Checks if proposed plot respects established world rules from OpenViking."""

    DIMENSION = "world_rules"

    async def evaluate(self, context: EvaluationContext) -> list[GuardianIssue]:
        if not context.world_rules:
            return []

        prompt = [
            {"role": "system", "content": _get_world_rules_prompt()},
            {
                "role": "user",
                "content": (
                    f"Proposed plot:\n{context.proposed_plot}\n\n"
                    f"World rules:\n{json.dumps(context.world_rules, indent=2, ensure_ascii=False)}\n\n"
                    "Evaluate world rule compliance."
                ),
            },
        ]

        try:
            result = await self._llm.chat_json(prompt)
        except Exception:
            return []

        raw_issues: list[dict[str, Any]] = result.get("issues", [])
        return [
            GuardianIssue(
                severity=Severity(i["severity"]),
                dimension=self.DIMENSION,
                description=i.get("description", ""),
                suggestion=i.get("suggestion", ""),
            )
            for i in raw_issues
        ]


class PacingValidator(BaseValidator):
    """Checks if proposed plot has reasonable pacing relative to recent story beats."""

    DIMENSION = "pacing"

    async def evaluate(self, context: EvaluationContext) -> list[GuardianIssue]:
        if not context.recent_scenes:
            return []

        recent_history = "\n---\n".join(
            f"Scene {i + 1}: {s}"
            for i, s in enumerate(context.recent_scenes)
        )

        prompt = [
            {"role": "system", "content": _get_pacing_prompt()},
            {
                "role": "user",
                "content": (
                    f"Proposed plot:\n{context.proposed_plot}\n\n"
                    f"Recent narrative history (last {len(context.recent_scenes)} scenes):\n"
                    f"{recent_history}\n\n"
                    "Evaluate pacing."
                ),
            },
        ]

        try:
            result = await self._llm.chat_json(prompt)
        except Exception:
            return []

        raw_issues: list[dict[str, Any]] = result.get("issues", [])
        return [
            GuardianIssue(
                severity=Severity(i["severity"]),
                dimension=self.DIMENSION,
                description=i.get("description", ""),
                suggestion=i.get("suggestion", ""),
            )
            for i in raw_issues
        ]


class ArcIntegrityValidator(BaseValidator):
    """Checks if proposed plot damages planned character arcs."""

    DIMENSION = "arc_integrity"

    async def evaluate(self, context: EvaluationContext) -> list[GuardianIssue]:
        if not context.characters:
            return []

        issues: list[GuardianIssue] = []
        for character in context.characters:
            char_arc = context.character_arcs.get(character.id, [])
            char_issues = await self._evaluate_arc(
                context.proposed_plot, character, char_arc
            )
            issues.extend(char_issues)
        return issues

    async def _evaluate_arc(
        self,
        proposed_plot: str,
        character: CharacterProfile,
        planned_arc: list[str],
    ) -> list[GuardianIssue]:
        arc_summary = "No specific arc milestones planned."
        if planned_arc:
            arc_summary = "Planned arc milestones:\n" + "\n".join(
                f"- {m}" for m in planned_arc
            )

        prompt = [
            {
                "role": "system",
                "content": _get_arc_integrity_prompt(),
            },
            {
                "role": "user",
                "content": (
                    f"Proposed plot:\n{proposed_plot}\n\n"
                    f"Character:\n{character.name} ({character.id})\n"
                    f"Arc stage: {character.arc_stage}\n"
                    f"Core desire: {character.core_desire}\n"
                    f"Deep fear: {character.deep_fear}\n\n"
                    f"{arc_summary}\n\n"
                    "Evaluate arc integrity."
                ),
            },
        ]

        try:
            result = await self._llm.chat_json(prompt)
        except Exception:
            return []

        raw_issues: list[dict[str, Any]] = result.get("issues", [])
        return [
            GuardianIssue(
                severity=Severity(i["severity"]),
                dimension=self.DIMENSION,
                description=i.get("description", ""),
                suggestion=i.get("suggestion", ""),
            )
            for i in raw_issues
        ]

