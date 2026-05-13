from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.relationship_builder import Relationship


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"


class Verdict(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    WARNING = "warning"


@dataclass
class GuardianIssue:
    severity: Severity
    dimension: str
    description: str
    suggestion: str


@dataclass
class GuardianResult:
    verdict: Verdict
    issues: list[GuardianIssue]
    can_override: bool


# ---------------------------------------------------------------------------
# Validator evaluation context
# ---------------------------------------------------------------------------


@dataclass
class EvaluationContext:
    proposed_plot: str
    characters: list[CharacterProfile] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    world_rules: list[dict[str, Any]] = field(default_factory=list)
    recent_scenes: list[str] = field(default_factory=list)
    character_arcs: dict[str, list[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base validator
# ---------------------------------------------------------------------------


class BaseValidator(ABC):
    """Abstract base for all validators."""

    def __init__(self, llm: LLMClient, memory: MemoryManager) -> None:
        self._llm = llm
        self._memory = memory

    @abstractmethod
    async def evaluate(self, context: EvaluationContext) -> list[GuardianIssue]:
        ...


# ---------------------------------------------------------------------------
# CharacterConsistencyValidator
# ---------------------------------------------------------------------------

_CHARACTER_CONSISTENCY_SYSTEM_PROMPT_EN = """\
You are a character consistency checker for a story engine. Given a proposed plot change
and a character's profile, determine whether the plot is consistent with that character.

Evaluate against these dimensions:
1. core_desire — Does the proposed plot align with what the character wants?
2. deep_fear — Does the proposed plot respect what the character fears?
3. personality — Does the proposed plot match the character's established personality?

For each inconsistency found, assign a severity:
- "critical": breaks a core character definition
- "warning": pushes against character but could be explained
- "suggestion": a minor alignment note

Respond ONLY with valid JSON:
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "dimension": "core_desire" | "deep_fear" | "personality",
      "description": "Description of the issue",
      "suggestion": "How to fix it"
    }
  ]
}

Return an empty list if no issues are found."""

_CHARACTER_CONSISTENCY_SYSTEM_PROMPT_ZH = """\
你是一个故事引擎的角色一致性检查器。给定一个提议的情节变更和一个角色的档案，判断该情节是否与该角色一致。

根据以下维度评估：
1. core_desire（核心欲望）——提议的情节是否符合角色的渴望？
2. deep_fear（深层恐惧）——提议的情节是否尊重角色的恐惧？
3. personality（性格）——提议的情节是否匹配角色已建立的性格？

对每个发现的不一致分配严重级别：
- "critical"（严重）：破坏了核心角色定义
- "warning"（警告）：与角色有所冲突但可以解释
- "suggestion"（建议）：一个微小的对齐注意

重要提示：所有文本内容（description, suggestion）必须使用简体中文。JSON 字段名保持英文。

只回复有效的 JSON：
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "dimension": "core_desire" | "deep_fear" | "personality",
      "description": "问题描述（使用中文）",
      "suggestion": "修复方法（使用中文）"
    }
  ]
}

如果未发现任何问题，返回空列表。"""


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


# ---------------------------------------------------------------------------
# RelationshipLogicValidator
# ---------------------------------------------------------------------------

_RELATIONSHIP_LOGIC_SYSTEM_PROMPT_EN = """\
You are a relationship consistency checker for a story engine. Given a proposed plot
change and the established relationships between affected characters, determine whether
the plot is consistent with their relationship history.

Relationships have a type (ALLY, RIVAL, ENEMY, FAMILY, MENTOR, ROMANTIC, UNKNOWN),
a strength (0.0 to 1.0), and a description of how they were established.

For each inconsistency found, assign a severity:
- "critical": proposes actions that fundamentally contradict the relationship
- "warning": somewhat out of character for the relationship
- "suggestion": a minor nuance to consider

Respond ONLY with valid JSON:
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "dimension": "relationship_logic",
      "description": "Description of the issue",
      "suggestion": "How to fix it"
    }
  ]
}

Return an empty list if no issues are found."""

_RELATIONSHIP_LOGIC_SYSTEM_PROMPT_ZH = """\
你是一个故事引擎的关系一致性检查器。给定一个提议的情节变更和受影响角色之间的已建立关系，判断该情节是否与其关系历史一致。

关系有类型（ALLY 盟友、RIVAL 竞争对手、ENEMY 敌人、FAMILY 家族、MENTOR 师徒、ROMANTIC 恋情、UNKNOWN 未知）、强度（0.0 到 1.0）以及关系如何建立的描述。

对每个发现的不一致分配严重级别：
- "critical"（严重）：提出从根本上与关系矛盾的行动
- "warning"（警告）：对关系来说有些不符合角色
- "suggestion"（建议）：需考虑的细微差别

重要提示：所有文本内容（description, suggestion）必须使用简体中文。JSON 字段名保持英文。

只回复有效的 JSON：
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "dimension": "relationship_logic",
      "description": "问题描述（使用中文）",
      "suggestion": "修复方法（使用中文）"
    }
  ]
}

如果未发现任何问题，返回空列表。"""


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


# ---------------------------------------------------------------------------
# WorldRulesValidator
# ---------------------------------------------------------------------------

_WORLD_RULES_SYSTEM_PROMPT_EN = """\
You are a world rules checker for a story engine. Given a proposed plot change and the
established rules of the world, determine whether the plot violates any world rules.

World rules define the fundamental physics, magic systems, constraints, or norms of the
story world. A violation breaks the internal consistency of the world.

For each violation found, assign a severity:
- "critical": directly breaks an established rule
- "warning": stretches or bends a rule
- "suggestion": a minor world-building note

Respond ONLY with valid JSON:
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "dimension": "world_rules",
      "description": "Description of the violation",
      "suggestion": "How to reconcile it"
    }
  ]
}

Return an empty list if no issues are found."""

_WORLD_RULES_SYSTEM_PROMPT_ZH = """\
你是一个故事引擎的世界规则检查器。给定一个提议的情节变更和已建立的世界规则，判断该情节是否违反了任何世界规则。

世界规则定义了故事世界的基本物理、魔法系统、约束或规范。违反规则会破坏世界的内部一致性。

对每个发现的违规分配严重级别：
- "critical"（严重）：直接违反已建立的规则
- "warning"（警告）：拉伸或扭曲了规则
- "suggestion"（建议）：一个微小的世界构建注释

重要提示：所有文本内容（description, suggestion）必须使用简体中文。JSON 字段名保持英文。

只回复有效的 JSON：
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "dimension": "world_rules",
      "description": "违规描述（使用中文）",
      "suggestion": "如何协调（使用中文）"
    }
  ]
}

如果未发现任何问题，返回空列表。"""


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


# ---------------------------------------------------------------------------
# PacingValidator
# ---------------------------------------------------------------------------

_PACING_SYSTEM_PROMPT_EN = """\
You are a pacing checker for a story engine. Given a proposed plot change and the
recent narrative history (last few scenes), determine whether the pacing is appropriate.

Consider:
1. Is the proposed plot too rushed given the preceding scenes?
2. Is the proposed plot too slow or repetitive?
3. Does the proposed plot introduce new conflict at a reasonable cadence?
4. Is there enough build-up for major events proposed?
5. Does the plot maintain dramatic tension appropriately?

For each pacing issue found, assign a severity:
- "critical": pacing would ruin the narrative flow
- "warning": pacing is somewhat off
- "suggestion": a minor pacing adjustment

Respond ONLY with valid JSON:
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "dimension": "pacing",
      "description": "Description of the pacing issue",
      "suggestion": "How to adjust pacing"
    }
  ]
}

Return an empty list if no issues are found."""

_PACING_SYSTEM_PROMPT_ZH = """\
你是一个故事引擎的节奏检查器。给定一个提议的情节变更和最近的叙事历史（最后几场戏），判断节奏是否合适。

考虑以下因素：
1. 提议的情节是否因为前面的场景而显得过于仓促？
2. 提议的情节是否太慢或重复？
3. 提议的情节是否以合理的节奏引入新的冲突？
4. 重大事件是否有足够的铺垫？
5. 情节是否恰当地保持了戏剧张力？

对每个发现的节奏问题分配严重级别：
- "critical"（严重）：节奏会破坏叙事流畅性
- "warning"（警告）：节奏有些偏差
- "suggestion"（建议）：一个微小的节奏调整

重要提示：所有文本内容（description, suggestion）必须使用简体中文。JSON 字段名保持英文。

只回复有效的 JSON：
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "dimension": "pacing",
      "description": "节奏问题描述（使用中文）",
      "suggestion": "如何调整节奏（使用中文）"
    }
  ]
}

如果未发现任何问题，返回空列表。"""


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


# ---------------------------------------------------------------------------
# ArcIntegrityValidator
# ---------------------------------------------------------------------------

_ARC_INTEGRITY_SYSTEM_PROMPT_EN = """\
You are an arc integrity checker for a story engine. Given a proposed plot change and
the planned character arc trajectories, determine whether the plot damages character arcs.

Consider:
1. Does the proposed plot flatten or undermine a character's growth trajectory?
2. Does the proposed plot reverse character development without sufficient cause?
3. Does the proposed plot advance a character's arc too quickly (skipping necessary steps)?
4. Does the proposed plot conflict with the character's current arc_stage?
5. Does the proposed plot create opportunities for meaningful character development?

For each issue found, assign a severity:
- "critical": would significantly damage or derail a character arc
- "warning": somewhat misaligned with the arc
- "suggestion": a minor improvement for arc coherence

Respond ONLY with valid JSON:
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "dimension": "arc_integrity",
      "description": "Description of the arc issue",
      "suggestion": "How to fix it"
    }
  ]
}

Return an empty list if no issues are found."""

_ARC_INTEGRITY_SYSTEM_PROMPT_ZH = """\
你是一个故事引擎的弧光完整性检查器。给定一个提议的情节变更和计划的角色弧光轨迹，判断该情节是否会损害角色弧光。

考虑以下因素：
1. 提议的情节是否削弱或破坏了角色的成长轨迹？
2. 提议的情节是否在没有充分理由的情况下逆转了角色发展？
3. 提议的情节是否过于快速地推进角色弧光（跳过必要步骤）？
4. 提议的情节是否与角色当前的弧光阶段相冲突？
5. 提议的情节是否创造了有意义的角色发展机会？

对每个发现的问题分配严重级别：
- "critical"（严重）：会严重损害或偏离角色弧光
- "warning"（警告）：与弧光有些偏差
- "suggestion"（建议）：改善弧光连贯性的微小改进

重要提示：所有文本内容（description, suggestion）必须使用简体中文。JSON 字段名保持英文。

只回复有效的 JSON：
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "dimension": "arc_integrity",
      "description": "弧光问题描述（使用中文）",
      "suggestion": "修复方法（使用中文）"
    }
  ]
}

如果未发现任何问题，返回空列表。"""


def _get_char_consistency_prompt() -> str:
    return _CHARACTER_CONSISTENCY_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _CHARACTER_CONSISTENCY_SYSTEM_PROMPT_EN


def _get_rel_logic_prompt() -> str:
    return _RELATIONSHIP_LOGIC_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _RELATIONSHIP_LOGIC_SYSTEM_PROMPT_EN


def _get_world_rules_prompt() -> str:
    return _WORLD_RULES_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _WORLD_RULES_SYSTEM_PROMPT_EN


def _get_pacing_prompt() -> str:
    return _PACING_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _PACING_SYSTEM_PROMPT_EN


def _get_arc_integrity_prompt() -> str:
    return _ARC_INTEGRITY_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _ARC_INTEGRITY_SYSTEM_PROMPT_EN


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


# ---------------------------------------------------------------------------
# StoryGuardian orchestrator
# ---------------------------------------------------------------------------

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

    def __init__(self, llm: LLMClient, memory: MemoryManager) -> None:
        self._llm = llm
        self._ov = memory.openviking
        self._kuzu = memory.kuzu

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

        return GuardianResult(
            verdict=verdict,
            issues=all_issues,
            can_override=can_override,
        )
