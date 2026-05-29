from __future__ import annotations

from app.core.i18n import get_lang, Lang


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
