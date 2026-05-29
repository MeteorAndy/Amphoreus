from __future__ import annotations

from app.core.i18n import get_lang, Lang
from app.services.plot_architect.types import NarrativeStructure

# ---------------------------------------------------------------------------
# Narrative structure templates
# ---------------------------------------------------------------------------

_STRUCTURE_TEMPLATES_ZH: dict[NarrativeStructure, str] = {
    NarrativeStructure.THREE_ACT: (
        "三幕结构：第一幕 建置 (25%) — 建立世界、角色与核心冲突。"
        "第二幕 对抗 (50%) — 升级危机、障碍与中点转折。"
        "第三幕 解决 (25%) — 高潮与余波。"
    ),
    NarrativeStructure.HERO_JOURNEY: (
        "英雄之旅 (12步)：平凡世界 → 冒险召唤 → 拒绝召唤 → 遇见导师 → "
        "跨越第一道门槛 → 考验、盟友、敌人 → 接近最深洞穴 → 磨难 → "
        "奖赏 → 返回之路 → 复活 → 携万能药归来。"
    ),
    NarrativeStructure.SAVE_THE_CAT: (
        "Save the Cat (15拍)：开篇画面 → 主题陈述 → 铺垫 → 催化剂 → "
        "犹豫 → 第二幕开启 → B故事 → 趣味与游戏 → 中点 → 反派逼近 → "
        "一无所有 → 灵魂黑夜 → 第三幕开启 → 终场 → 终场画面。"
    ),
    NarrativeStructure.QI_CHENG_ZHUAN_HE: (
        "起承转合 (4段)：起 — 建立角色与设定。"
        "承 — 发展冲突与角色关系。"
        "转 — 意外转折或逆转，升级危机。"
        "合 — 所有线索汇聚与解决。"
    ),
}

_STRUCTURE_TEMPLATES_EN: dict[NarrativeStructure, str] = {
    NarrativeStructure.THREE_ACT: (
        "Three-Act Structure: Setup (25%) — Establish the world, characters, and "
        "central conflict. Confrontation (50%) — Rising stakes, obstacles, and midpoint "
        "reversal. Resolution (25%) — Climax and aftermath."
    ),
    NarrativeStructure.HERO_JOURNEY: (
        "Hero's Journey (12 steps): Ordinary World → Call to Adventure → Refusal of "
        "the Call → Meeting the Mentor → Crossing the Threshold → Tests, Allies, Enemies "
        "→ Approach to the Inmost Cave → Ordeal → Reward → The Road Back → Resurrection "
        "→ Return with the Elixir."
    ),
    NarrativeStructure.SAVE_THE_CAT: (
        "Save the Cat (15 beats): Opening Image → Theme Stated → Set-Up → Catalyst → "
        "Debate → Break into Two → B Story → Fun and Games → Midpoint → Bad Guys Close "
        "In → All Is Lost → Dark Night of the Soul → Break into Three → Finale → "
        "Final Image."
    ),
    NarrativeStructure.QI_CHENG_ZHUAN_HE: (
        "Qi Cheng Zhuan He (4 parts): 起 (Qi/Introduction) — Establish characters and "
        "setting. 承 (Cheng/Development) — Build the conflict and develop relationships. "
        "转 (Zhuan/Twist) — Unexpected turn or reversal that raises stakes. "
        "合 (He/Resolution) — Convergence and resolution of all threads."
    ),
}


_PLOT_SYSTEM_PROMPT_EN = """\
You are a master plot architect for a story engine. Given a world state, character \
profiles, and a narrative structure template, generate a complete plot outline.

Rules:
1. Fill the template with concrete scenes based on character conflicts and world elements.
2. Each scene MUST have a clear dramatic purpose — no filler scenes.
3. Every scene must include a specific conflict, a goal, and an expected outcome.
4. Character arcs MUST show progression through the scenes — each character should \
change or be challenged across the arc.
5. Scenes should have causal chains — each scene builds on or reacts to prior scenes.
6. Assign locations from the world state where possible.
7. Cast only characters that have a meaningful role in each scene.

The story should feel organic, driven by character desires and world constraints, not \
just a mechanical filling of plot beats.

You MUST respond ONLY with valid JSON in this format:
{
  "acts": [
    {
      "name": "Act 1: ...",
      "description": "Overview of this act's purpose",
      "scenes": [
        {
          "id": "scene_1",
          "title": "Scene title",
          "location": "Where it happens",
          "cast": ["character_id_1", "character_id_2"],
          "conflict": "The dramatic conflict",
          "goal": "What this scene accomplishes",
          "expected_outcome": "How the scene resolves",
          "causal_chain": []
        }
      ]
    }
  ],
  "character_arcs": {
    "character_id": ["arc milestone 1", "arc milestone 2"]
  }
}"""

_PLOT_SYSTEM_PROMPT_ZH = """\
你是一个故事引擎的首席剧情架构师。根据给定的世界状态、角色档案和叙事结构模板，生成一份完整的剧情大纲。

规则：
1. 用基于角色冲突和世界元素的具体场景来填充模板。
2. 每个场景必须有清晰的戏剧目的——不要填充场景。
3. 每个场景必须包含具体的冲突、目标和预期结果。
4. 角色弧光必须贯穿所有场景——每个角色都应该在剧情弧线中发生变化或受到挑战。
5. 场景之间应有因果链——每个场景都建立在前序场景之上或对其做出反应。
6. 尽可能使用世界状态中的地点。
7. 只安排对场景有重要意义的角色出场。

故事应感觉有机自然，由角色的欲望和世界约束驱动，而非机械地填充剧情节拍。

重要提示：
- 所有文本内容（场景标题、描述、冲突、目标、预期结果、角色弧光里程碑）必须使用简体中文
- JSON 字段名保持英文，字段值使用中文
- 场景标题应富有文采，体现中国文学风格
- 地点名称使用中文

你必须严格按照以下 JSON 格式回复，且只回复 JSON：
{
  "acts": [
    {
      "name": "第X幕：...",
      "description": "本幕目的概述（使用中文）",
      "scenes": [
        {
          "id": "scene_1",
          "title": "场景标题（使用中文）",
          "location": "地点（使用中文）",
          "cast": ["character_id_1", "character_id_2"],
          "conflict": "戏剧冲突（使用中文）",
          "goal": "场景目标（使用中文）",
          "expected_outcome": "场景预期结果（使用中文）",
          "causal_chain": []
        }
      ]
    }
  ],
  "character_arcs": {
    "character_id": ["弧光里程碑1（使用中文）", "弧光里程碑2（使用中文）"]
  }
}"""

_REFINE_SYSTEM_PROMPT_EN = """\
You are a plot editor. Given an existing plot outline and user feedback, revise the \
outline to address the feedback while preserving the core narrative. You may reorder \
scenes, rewrite scene details, adjust character arcs, or change act descriptions.

Preserve all scene IDs so existing references remain valid.

You MUST respond ONLY with valid JSON in the same format as the original outline:
{
  "acts": [...],
  "character_arcs": {...}
}"""

_REFINE_SYSTEM_PROMPT_ZH = """\
你是一个剧情编辑器。根据已有的剧情大纲和用户反馈，修改大纲以响应用户意见，同时保留核心叙事。你可以重新排序场景、重写场景细节、调整角色弧光或修改幕的描述。

保留所有 scene ID 以确保现有引用仍然有效。

所有文本内容必须使用简体中文。JSON 字段名保持英文，字段值使用中文。

你必须严格按照与原始大纲相同的 JSON 格式回复：
{
  "acts": [...],
  "character_arcs": {...}
}"""

_CHECK_SYSTEM_PROMPT_EN = """\
You are a plot consistency checker. Given a plot outline and a specific scene, analyze \
whether the scene is consistent with all character arcs across the outline.

Consider:
1. Does each character's arc progression logically lead into and out of this scene?
2. Does this scene contradict any established character trait, desire, or fear?
3. Does the scene's causal chain connect properly to prerequisite scenes?
4. Does the emotional/logical outcome match character trajectories?

You MUST respond ONLY with valid JSON in this format:
{
  "consistent": true or false,
  "issues": ["Description of issue 1", "Description of issue 2"],
  "suggested_fixes": ["Fix for issue 1", "Fix for issue 2"]
}"""

_CHECK_SYSTEM_PROMPT_ZH = """\
你是一个剧情一致性检查器。根据给定的剧情大纲和特定场景，分析该场景是否与大纲中所有的角色弧光保持一致。

考虑以下方面：
1. 每个角色的弧光进展在逻辑上是否能自然地进入和离开该场景？
2. 该场景是否与任何已建立的角色特质、欲望或恐惧相矛盾？
3. 场景的因果链是否正确连接到前置场景？
4. 情感/逻辑结果是否与角色的发展轨迹一致？

所有文本内容必须使用简体中文。JSON 字段名保持英文，字段值使用中文。

你必须严格按照以下 JSON 格式回复，且只回复 JSON：
{
  "consistent": true or false,
  "issues": ["问题描述1（使用中文）", "问题描述2（使用中文）"],
  "suggested_fixes": ["修复建议1（使用中文）", "修复建议2（使用中文）"]
}"""


def _get_plot_prompt() -> str:
    return _PLOT_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _PLOT_SYSTEM_PROMPT_EN


def _get_refine_prompt() -> str:
    return _REFINE_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _REFINE_SYSTEM_PROMPT_EN


def _get_check_prompt() -> str:
    return _CHECK_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _CHECK_SYSTEM_PROMPT_EN
