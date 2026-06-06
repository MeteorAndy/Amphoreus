from __future__ import annotations

import json
from typing import Any

from app.models.character import CharacterProfile
from app.services.relationship_builder import Relationship

from .base import BaseValidator
from .prompts import _get_char_consistency_prompt, _get_rel_logic_prompt
from .types import EvaluationContext, GuardianIssue, Severity


class CharacterConsistencyValidator(BaseValidator):
    """Checks if proposed plot matches character core_desire, deep_fear, and personality."""

    DIMENSION = "character_consistency"

    async def evaluate(self, context: EvaluationContext) -> list[GuardianIssue]:
        if not context.characters:
            return []

        issues: list[GuardianIssue] = []
        for character in context.characters:
            char_issues = await self._evaluate_character(
                context.proposed_plot, character
            )
            issues.extend(char_issues)
        return issues

    async def _evaluate_character(
        self, proposed_plot: str, character: CharacterProfile
    ) -> list[GuardianIssue]:
        prompt = [
            {
                "role": "system",
                "content": _get_char_consistency_prompt(),
            },
            {
                "role": "user",
                "content": (
                    f"Proposed plot:\n{proposed_plot}\n\n"
                    f"Character profile:\n{character.model_dump_json(indent=2, ensure_ascii=False)}\n\n"
                    "Evaluate character consistency."
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


class RelationshipLogicValidator(BaseValidator):
    """Checks if character interactions respect their relationship history. Uses Kuzu path queries."""

    DIMENSION = "relationship_logic"

    async def evaluate(self, context: EvaluationContext) -> list[GuardianIssue]:
        if not context.characters or len(context.characters) < 2:
            return []

        issues: list[GuardianIssue] = []

        for i, c1 in enumerate(context.characters):
            for c2 in context.characters[i + 1:]:
                relationships = self._find_relationships(c1.id, c2.id, context.relationships)
                if not relationships:
                    continue
                path_issue = await self._evaluate_relationship_arc(
                    context.proposed_plot, c1, c2, relationships
                )
                if path_issue:
                    issues.append(path_issue)

        return issues

    def _find_relationships(
        self, char_id_a: str, char_id_b: str, relationships: list[Relationship]
    ) -> list[Relationship]:
        """Find all direct relationships between two characters."""
        return [
            r
            for r in relationships
            if (r.from_id == char_id_a and r.to_id == char_id_b)
            or (r.from_id == char_id_b and r.to_id == char_id_a)
        ]

    async def _evaluate_relationship_arc(
        self,
        proposed_plot: str,
        char_a: CharacterProfile,
        char_b: CharacterProfile,
        relationships: list[Relationship],
    ) -> GuardianIssue | None:
        rel_summary = json.dumps(
            [
                {
                    "from": r.from_id,
                    "to": r.to_id,
                    "type": r.rel_type,
                    "strength": r.strength,
                    "description": r.description,
                    "established_event": r.established_event,
                }
                for r in relationships
            ],
            indent=2,
            ensure_ascii=False,
        )

        prompt = [
            {
                "role": "system",
                "content": _get_rel_logic_prompt(),
            },
            {
                "role": "user",
                "content": (
                    f"Proposed plot:\n{proposed_plot}\n\n"
                    f"Character A:\n{char_a.name} ({char_a.id})\n"
                    f"Core desire: {char_a.core_desire}\n\n"
                    f"Character B:\n{char_b.name} ({char_b.id})\n"
                    f"Core desire: {char_b.core_desire}\n\n"
                    f"Relationships between them:\n{rel_summary}\n\n"
                    "Evaluate relationship consistency."
                ),
            },
        ]

        try:
            result = await self._llm.chat_json(prompt)
        except Exception:
            return None

        raw_issues: list[dict[str, Any]] = result.get("issues", [])
        if not raw_issues:
            return None

        worst = raw_issues[0]
        return GuardianIssue(
            severity=Severity(worst["severity"]),
            dimension=self.DIMENSION,
            description=worst.get("description", ""),
            suggestion=worst.get("suggestion", ""),
        )
