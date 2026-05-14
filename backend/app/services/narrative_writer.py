"""Narrative Writer — convert scene logs to novel or screenplay format.

Public types:
  - WritingOptions, WrittenOutput
  - ChapterSpec, ChapterPlan
  - TitleGenerator (LLM title candidate generation)
  - ChapterPlanner (scene-to-chapter mapping)
  - PostProcessor (text normalisation per language)
  - NovelWriter (scene logs -> literary prose, chapter by chapter)
  - ScreenplayWriter (scene logs -> screenplay format)
  - NarrativeWriter (facade dispatching to the correct writer)

DI: LLMClient + MemoryManager injected at construction.
"""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.i18n import get_lang, Lang, t
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.plot_architect import PlotOutline, SceneSpec
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate, Reaction, RoundEntry

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class WritingOptions:
    """Configuration for the narrative conversion process."""

    format: str  # "novel" or "screenplay"
    narrative_voice: str = "third_person_limited"
    enhance: bool = False
    chapter_title: str | None = None


@dataclass
class WrittenOutput:
    """Result of a narrative conversion."""

    content: str
    format: str
    word_count: int
    scene_count: int
    title: str = ""
    title_candidates: list[str] = field(default_factory=list)
    export_formats: list[str] = field(default_factory=list)


@dataclass
class ChapterSpec:
    """One chapter in a chapter plan."""

    number: int
    title: str
    scene_ids: list[str]
    summary: str


@dataclass
class ChapterPlan:
    """Complete chapter plan — groups scenes into chapters."""

    chapters: list[ChapterSpec] = field(default_factory=list)

    @property
    def is_short_story(self) -> bool:
        total = sum(len(c.scene_ids) for c in self.chapters)
        return total < 3


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

# --- Title generation ---

_TITLE_SYSTEM_PROMPT_ZH = """\
你是一位小说标题生成专家。根据以下世界观总结、角色档案和剧情大纲，\
生成3到5个小说标题候选。

风格要求：金庸/古龙/网络文学风格，富有中国文学韵味。
每个标题应体现故事的核心冲突或主题。
标题应简洁有力，富有吸引力和市场价值。

你必须严格按照以下 JSON 格式回复，且只回复 JSON：
["标题1", "标题2", "标题3"]"""

_TITLE_SYSTEM_PROMPT_EN = """\
You are a novel title generation expert. Based on the following world summary, \
character profiles, and plot outline, generate 3 to 5 title candidates.

Style: literary, suspense, or direct — genre-appropriate.
Each title should reflect the core conflict or theme.
Titles should be compelling, memorable, and marketable.

You MUST respond ONLY with valid JSON in this format:
["Title 1", "Title 2", "Title 3"]"""

# --- Chapter planning ---

_CHAPTER_PLAN_SYSTEM_PROMPT_ZH = """\
你是一位故事引擎的章节规划师。根据以下场景列表和角色档案，\
将场景合理地分组到章节中。

要求：
1. 每个章节应有清晰的戏剧主题和叙事弧线
2. 每章包含2到4个场景（根据字数目标自动调整）
3. 章节标题格式：第X章 篇名
4. 目标字数：正常2500-4000字/章（短篇故事800-1500字）
   - 每场景预估输出约1000字
   - 根据总场景数计算所需章节数
5. 如果总场景数少于3个，视为短篇故事，只设一章

你必须严格按照以下 JSON 格式回复，且只回复 JSON：
{
  "chapters": [
    {
      "number": 1,
      "title": "篇名",
      "scene_ids": ["scene_1", "scene_2"],
      "summary": "本章内容概述（使用中文）"
    }
  ]
}"""

_CHAPTER_PLAN_SYSTEM_PROMPT_EN = """\
You are a chapter planner for a story engine. Based on the following scene list \
and character profiles, group scenes into well-structured chapters.

Requirements:
1. Each chapter should have a clear dramatic theme and narrative arc
2. Each chapter should contain 2 to 4 scenes (adjust based on word count target)
3. Chapter title format: Chapter X: Title
4. Target word count: 2000-3500 words/chapter (short story 800-1500 words)
   - Estimated output per scene: ~600 words
   - Calculate needed chapters based on total scene count
5. If fewer than 3 total scenes, treat as a short story — single chapter only

You MUST respond ONLY with valid JSON in this format:
{
  "chapters": [
    {
      "number": 1,
      "title": "Chapter Title",
      "scene_ids": ["scene_1", "scene_2"],
      "summary": "Summary of this chapter's content"
    }
  ]
}"""

# --- Chapter writing (system) ---

_CHAPTER_WRITE_SYSTEM_PROMPT_ZH = """\
你是一位文学小说家。根据给定的章节规划、场景日志和角色档案，\
写出完整的文学章节。

写作流程：
1. 首先像读者一样审阅章节计划——找出逻辑漏洞、节奏问题、改进方向
2. 在<思考>标签中写出你的分析
3. 在<story>标签中写出完整的章节正文

写作要求：
- 生动的语言，富有中国文学韵味
- 人物深度——通过行动与对话展现角色内心世界
- 出人意料的 climax——让高潮有冲击力和感染力
- 节奏控制——张弛有度，长短句交替
- 场景间的自然过渡——必须用过渡段落连接各场景，不能简单拼接
- 保留所有关键对话和动作，不得遗漏重要情节
- 叙事视角：{voice}"""

_CHAPTER_WRITE_SYSTEM_PROMPT_EN = """\
You are a literary novelist. Based on the given chapter plan, scene logs, \
and character profiles, write a complete literary chapter.

Writing process:
1. First, review the chapter plan as a reader — identify logical gaps, pacing \
issues, improvement areas
2. Write analysis in <thinking> tag
3. Write full chapter prose in <story> tag

Requirements:
- Vivid language with literary quality
- Character depth — reveal inner worlds through action and dialogue
- Unexpected climax — make the peak impactful and resonant
- Pacing control — vary rhythm with sentence length and structure
- Natural scene transitions — connect scenes with transitional paragraphs, \
do not simply concatenate
- Preserve all key dialogue and actions — do not omit important plot points
- Narrative voice: {voice}"""

# --- Enhance prompts (kept from original) ---

_NOVEL_ENHANCE_PROMPT_EN = """\
Review the narrative above and enhance it for:
1. Pacing — vary sentence length and structure for rhythm
2. Sensory richness — deepen the sensory experience (sights, sounds, smells, textures)
3. Dialogue polish — ensure dialogue sounds natural and distinct per character

Rewrite the passage below with these improvements. Return ONLY the rewritten prose, no explanations."""

_NOVEL_ENHANCE_PROMPT_ZH = """\
审查以上叙事并进行以下增强：
1. 节奏——变化句子长度和结构以形成韵律
2. 感官丰富度——加深感官体验（视觉、声音、气味、质感）
3. 对话润色——确保对话自然且每个角色各有特色

用以上改进重写下面的段落。只返回改写后的散文，不要解释。

重要提示：所有输出必须使用简体中文。"""

_SCREENPLAY_SYSTEM_PROMPT_EN = """\
You are a professional screenwriter. You need to create an engaging, creative screenplay for a feature film or web series.

Before writing:
1. Review all scenes — understand each character's motivation, background, and relationships
2. Identify the narrative arc across scenes — where is setup, confrontation, climax

Writing requirements:
- Craft compelling character dialogue, with each character's speech matching their personality
- Create plot lines full of twists and suspense, keeping the audience tense and expectant until the end
- Before writing, put your thoughts on character motivation and plot structure inside <thinking> tags

Formatting rules (strictly follow):
- Scene headings: [INT.] Location - Time or [EXT.] Location - Time
- Keep character names in their original language. Chinese names must be written in Chinese, never converted to pinyin or English uppercase
- Dialogue format: character name on its own line, dialogue on a new line
- Use (parenthetical) before dialogue for tone/action when necessary

## Strictly forbidden formatting (already handled by the system)
- Do NOT add any headings (#, ##, ###) — the system automatically adds act titles and scene numbers
- Do NOT add separators (---) — do not use horizontal lines within scene content
- Do NOT add scene-end markers such as "(End of Act 1, Scene 1)" — the system does not recognize this format
- Do NOT bold character names with ** marks — just write names in plain text
- Only output the body content of the scene: descriptions, dialogue, and action lines"""

_SCREENPLAY_SYSTEM_PROMPT_ZH = """\
你是一个专业编剧。你需要为一部故事长片或网络系列剧创作一个有趣、有创意的剧本。


## 关键规则：你必须使用简体中文进行所有创作。所有场景描述、角色对白、动作指示一律使用简体中文。禁止使用英文。
在开始写作之前：
1. 先审视所有场景——理解每个角色的动机、背景、与其他角色的关系
2. 找出场景间的叙事弧——哪里是建置、哪里是对抗、哪里是高潮

写作要求：
- 构思引人入胜的角色对白，每个角色的说话方式应与其性格一致
- 创作充满转折与悬念的情节主线，让观众保持紧张和期待直到最后
- 开始写作前，在<构思>标签中写下你对角色动机和情节结构的思考

格式规则（严格遵守）：
- 场景标题统一使用：[内景] 地点 - 时间 或 [外景] 地点 - 时间
- 角色名必须保持中文原文。例如：林辰，不能写成 LIN CHEN。沈天机，不能写成 SHEN TIANJI。这是硬性规定，违反将导致剧本不合格。
- 对话格式：角色名单独一行，对话另起一行
- 必要时在对话前用（括号）标注表情或动作指示

内心独白处理：
- [内心] 标记表示角色此时的心理活动
- 将其转化为剧本格式：（旁白）、（OS）、画外音、或括弧内的动作/表情指示
- 例如：[内心] 林辰心想：不能暴露修为 → （林辰强压灵力，面无表情）或 林辰（OS）：不能暴露修为...

## 严格禁止的格式（代码已自动处理）
- 不要添加任何标题（#、##、###）——代码会自动添加幕标题和场次编号
- 不要添加分隔线（---）——不要在场景内容中使用水平分隔线
- 不要添加场景结束标记（如"第一幕·场景一完"）——代码不识别此格式
- 中文模式下角色名使用纯文本（如"林辰"），不要加粗（不要用**林辰**）
- 你只需要输出场景的正文内容：场景描述、角色对话、动作指示

## 关键规则：你必须使用简体中文进行所有创作。所有场景描述、角色对白、动作指示一律使用简体中文。禁止使用英文。"""

_SCREENPLAY_ENHANCE_PROMPT_EN = """\
Review the screenplay above for formatting consistency and quality:

1. Verify all scene headings use correct INT./EXT. notation
2. Ensure character names are properly formatted in ALL CAPS
3. Check action descriptions are in present tense
4. Fix any formatting inconsistencies
5. Ensure proper spacing between elements

Return ONLY the corrected screenplay, no explanations."""

_SCREENPLAY_ENHANCE_PROMPT_ZH = """\
审查以上剧本的格式一致性和质量：

1. 验证所有场景标题使用正确的内景/外景标记
2. 确保角色名正确使用全大写格式
3. 检查动作描述是否使用现在时
4. 修复任何格式不一致之处
5. 确保元素之间的间距正确

只返回修正后的剧本，不要解释。

重要提示：所有对话和动作描述使用简体中文。"""

# --- Prompt lookup ---

_NARRATIVE_PROMPTS = {
    "title_system": {
        Lang.ZH: _TITLE_SYSTEM_PROMPT_ZH,
        Lang.EN: _TITLE_SYSTEM_PROMPT_EN,
    },
    "chapter_plan_system": {
        Lang.ZH: _CHAPTER_PLAN_SYSTEM_PROMPT_ZH,
        Lang.EN: _CHAPTER_PLAN_SYSTEM_PROMPT_EN,
    },
    "chapter_write_system": {
        Lang.ZH: _CHAPTER_WRITE_SYSTEM_PROMPT_ZH,
        Lang.EN: _CHAPTER_WRITE_SYSTEM_PROMPT_EN,
    },
    "novel_enhance": {
        Lang.ZH: _NOVEL_ENHANCE_PROMPT_ZH,
        Lang.EN: _NOVEL_ENHANCE_PROMPT_EN,
    },
    "screenplay_system": {
        Lang.ZH: _SCREENPLAY_SYSTEM_PROMPT_ZH,
        Lang.EN: _SCREENPLAY_SYSTEM_PROMPT_EN,
    },
    "screenplay_enhance": {
        Lang.ZH: _SCREENPLAY_ENHANCE_PROMPT_ZH,
        Lang.EN: _SCREENPLAY_ENHANCE_PROMPT_EN,
    },
}


def _get_title_prompt() -> str:
    return _NARRATIVE_PROMPTS["title_system"][get_lang()]


def _get_chapter_plan_prompt() -> str:
    return _NARRATIVE_PROMPTS["chapter_plan_system"][get_lang()]


def _get_chapter_write_system_prompt() -> str:
    return _NARRATIVE_PROMPTS["chapter_write_system"][get_lang()]


def _get_novel_enhance_prompt() -> str:
    return _NARRATIVE_PROMPTS["novel_enhance"][get_lang()]


def _get_screenplay_system_prompt() -> str:
    return _NARRATIVE_PROMPTS["screenplay_system"][get_lang()]


def _get_screenplay_enhance_prompt() -> str:
    return _NARRATIVE_PROMPTS["screenplay_enhance"][get_lang()]


def _get_chapter_write_target() -> str:
    lang = get_lang()
    if lang == Lang.ZH:
        return "2500-4000字"
    return "2000-3500 words"


def _get_chapter_write_short_target() -> str:
    lang = get_lang()
    if lang == Lang.ZH:
        return "800-1500字"
    return "800-1500 words"


# ---------------------------------------------------------------------------
# Archive parsing helpers
# ---------------------------------------------------------------------------


def _parse_archive_json(l2_content: str) -> SceneArchive:
    """Reconstruct a SceneArchive dataclass from stored JSON."""
    data: dict[str, Any] = json.loads(l2_content)

    rounds: list[RoundEntry] = [
        RoundEntry(
            round_num=r["round_num"],
            actor_id=r["actor_id"],
            actor_name=r["actor_name"],
            dialogue=r.get("dialogue", ""),
            action=r.get("action", ""),
            inner_thought=r.get("inner_thought", ""),
            emotion=r.get("emotion", ""),
            reactions=[
                Reaction(
                    reactor_id=rx["reactor_id"],
                    reactor_name=rx["reactor_name"],
                    visible_reaction=rx.get("visible_reaction", ""),
                    inner_thought=rx.get("inner_thought", ""),
                )
                for rx in r.get("reactions", [])
            ],
        )
        for r in data.get("rounds", [])
    ]

    fe_data = data.get("final_environment", {})
    final_environment = EnvironmentUpdate(
        atmosphere=fe_data.get("atmosphere", ""),
        changes=fe_data.get("changes", []),
        background_activity=fe_data.get("background_activity", ""),
    )

    return SceneArchive(
        scene_id=data["scene_id"],
        rounds=rounds,
        final_environment=final_environment,
        character_changes=data.get("character_changes", {}),
    )


def _load_scene_archive(memory: MemoryManager, scene_id: str) -> SceneArchive:
    """Load a single scene archive from OpenViking and return a SceneArchive."""
    entry = memory.openviking.read_entry(f"story/scenes/{scene_id}")
    return _parse_archive_json(entry.l2)


def _flatten_scenes(outline: PlotOutline) -> dict[str, SceneSpec]:
    """Flatten all SceneSpecs from a PlotOutline into a scene_id -> SceneSpec map."""
    result: dict[str, SceneSpec] = {}
    for act in outline.acts:
        for scene in act.scenes:
            result[scene.id] = scene
    return result


def _extract_chapter_story(raw: str) -> str:
    """Extract content between <story>...</story> tags from an LLM chapter response.

    Falls back to the full response with any <thinking>/<思考> blocks removed.
    """
    story_match = re.search(r"<story>(.*?)</story>", raw, re.DOTALL)
    if story_match:
        return story_match.group(1).strip()
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    cleaned = re.sub(r"<思考>.*?</思考>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# TitleGenerator
# ---------------------------------------------------------------------------


class TitleGenerator:
    """Generates 3-5 novel/screenplay title candidates via LLM.

    ZH mode: Chinese titles (金庸/古龙/网络文学风格).
    EN mode: English titles (literary/suspense/direct).
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def generate_titles(
        self,
        world_summary: str,
        characters: list[CharacterProfile],
        plot_outline: PlotOutline | None = None,
    ) -> list[str]:
        """Call LLM and return 3-5 title candidates.

        If plot_outline is None, title generation uses only world and character info.
        """
        char_json = json.dumps(
            [
                {"name": c.name, "role": c.role, "core_desire": c.core_desire, "deep_fear": c.deep_fear}
                for c in characters
            ],
            indent=2,
            ensure_ascii=False,
        )

        outline_text = ""
        if plot_outline:
            parts: list[str] = []
            for act in plot_outline.acts:
                parts.append(f"{act.name}: {act.description}")
                for scene in act.scenes:
                    parts.append(f"  - {scene.title}: {scene.conflict}")
            outline_text = "\n".join(parts)

        user_content = (
            f"World summary:\n{world_summary}\n\n"
            f"Characters:\n{char_json}\n\n"
            f"Plot outline:\n{outline_text if outline_text else '(not provided)'}\n\n"
            "Generate 3-5 title candidates."
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_title_prompt()},
            {"role": "user", "content": user_content},
        ]

        result = await self._llm.chat_json(messages, temperature=0.8)
        if isinstance(result, list):
            return [str(item) for item in result]
        for val in result.values():
            if isinstance(val, list):
                return [str(item) for item in val]
        return [str(result)]


# ---------------------------------------------------------------------------
# ChapterPlanner
# ---------------------------------------------------------------------------


class ChapterPlanner:
    """Plans scene-to-chapter mapping using LLM.

    Output: ChapterPlan with ChapterSpec entries describing grouping, titles,
    and summaries. Word count targeting per the spec.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def plan_chapters(
        self,
        plot_outline: PlotOutline,
        characters: list[CharacterProfile],
    ) -> ChapterPlan:
        """Build a chapter plan from the plot outline and character profiles."""
        scenes_json = json.dumps(
            [
                {
                    "id": s.id,
                    "title": s.title,
                    "location": s.location,
                    "conflict": s.conflict,
                    "goal": s.goal,
                    "cast": s.cast,
                }
                for act in plot_outline.acts
                for s in act.scenes
            ],
            indent=2,
            ensure_ascii=False,
        )

        char_json = json.dumps(
            [{"name": c.name, "role": c.role, "core_desire": c.core_desire} for c in characters],
            indent=2,
            ensure_ascii=False,
        )

        user_content = (
            f"Scene list:\n{scenes_json}\n\n"
            f"Characters:\n{char_json}\n\n"
            "Plan the chapter structure."
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_chapter_plan_prompt()},
            {"role": "user", "content": user_content},
        ]

        result = await self._llm.chat_json(messages, temperature=0.5)
        raw_chapters: list[dict[str, Any]] = result.get("chapters", [])
        chapters = [
            ChapterSpec(
                number=ch.get("number", i + 1),
                title=ch.get("title", ""),
                scene_ids=list(ch.get("scene_ids", [])),
                summary=ch.get("summary", ""),
            )
            for i, ch in enumerate(raw_chapters)
        ]
        return ChapterPlan(chapters=chapters)


# ---------------------------------------------------------------------------
# PostProcessor
# ---------------------------------------------------------------------------


class PostProcessor:
    """Normalises prose text per language conventions.

    ZH: Chinese quotes, ellipsis, em-dash, paragraph spacing.
    EN: Standard English punctuation and spacing.
    """

    @staticmethod
    def process(text: str) -> str:
        """Apply language-appropriate normalisation to the given text."""
        if get_lang() == Lang.ZH:
            return PostProcessor._process_zh(text)
        return PostProcessor._process_en(text)

    @staticmethod
    def _process_zh(text: str) -> str:
        text = re.sub(r"\.{3,}", "……", text)
        text = re.sub(r"。{3,}", "……", text)
        text = re.sub(r"-{3,}", "——", text)
        text = re.sub(r"—{1,2}", "——", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _process_en(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()

    # ------------------------------------------------------------------
    # Screenplay-specific normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_screenplay_content(text: str) -> str:
        """Remove leaked formatting markers that the LLM should not have produced.

        Strips:
        - Lines starting with # (leaked markdown headings)
        - Standalone --- lines
        - Scene-end markers like （第一幕·场景一完）or "(End of Act 1, Scene 1)"
        - **bold** markers around character names (ZH mode only)
        """
        lines = text.split("\n")
        cleaned: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Remove standalone markdown headings (lines starting with #),
            # but KEEP the very first line if it starts with "# " — that's the title added by code
            if stripped.startswith("#") and len(cleaned) > 0:
                continue

            # Remove standalone separator lines
            if re.match(r"^---+\s*$", stripped):
                continue

            # Remove scene-end markers like （第X幕·场景X完）or similar
            if re.search(
                r"[（(]\s*(第\d+幕|第\d+章|Act\s+\d+|Scene\s+\d+)[^）)]*[完终止][）)]\s*$",
                stripped,
            ):
                continue
            if re.search(
                r"[（(]\s*(End|结束|完)\s+of\s+", stripped, re.IGNORECASE
            ):
                continue

            # Remove **bold** markers around character names (ZH mode)
            if get_lang() == Lang.ZH:
                stripped = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)

            cleaned.append(stripped)

        return "\n".join(cleaned)

    @staticmethod
    def normalize_screenplay(text: str, characters: list[CharacterProfile]) -> str:
        """Apply screenplay-specific normalisations (headings, character names)."""
        text = PostProcessor._sanitize_screenplay_content(text)
        if get_lang() == Lang.ZH:
            text = PostProcessor._normalize_scene_headings_zh(text)
            text = PostProcessor._normalize_character_names(text, characters)
        else:
            text = PostProcessor._normalize_scene_headings_en(text)
        return text

    @staticmethod
    def _normalize_scene_headings_zh(text: str) -> str:
        """Normalise Chinese scene headings to [内景]/[外景] format."""
        text = re.sub(r'\[INT\.\]', '[内景]', text)
        text = re.sub(r'\[EXT\.\]', '[外景]', text)
        text = re.sub(r'\[INT/EXT\.\]', '[内景/外景]', text)
        text = re.sub(r'\[EXT/INT\.\]', '[外景/内景]', text)
        text = re.sub(r'(?<!\w)INT/EXT\.', '[内景/外景]', text)
        text = re.sub(r'(?<!\w)EXT/INT\.', '[外景/内景]', text)
        text = re.sub(r'(?<!\w)INT\.', '[内景]', text)
        text = re.sub(r'(?<!\w)EXT\.', '[外景]', text)
        text = re.sub(r'内景\.', '[内景]', text)
        text = re.sub(r'外景\.', '[外景]', text)
        text = re.sub(r'^(外景|内景)\s', r'[\1] ', text, flags=re.MULTILINE)
        return text

    @staticmethod
    def _normalize_scene_headings_en(text: str) -> str:
        """Normalise English scene headings to [INT.]/[EXT.] format."""
        for prefix in ('INT/EXT.', 'EXT/INT.', 'INT.', 'EXT.'):
            text = re.sub(
                rf'(?<!\w){re.escape(prefix)}(?!\])',
                f'[{prefix}]',
                text,
            )
        text = re.sub(r'\[\[(.*?)\]\]', r'[\1]', text)
        return text

    @staticmethod
    def _normalize_character_names(text: str, characters: list[CharacterProfile]) -> str:
        """Revert ALL CAPS English names to original form (ZH mode only)."""
        if get_lang() != Lang.ZH:
            return text
        for char in characters:
            if not char.name:
                continue
            upper_name = char.name.upper()
            if upper_name == char.name:
                continue
            text = re.sub(
                rf'(?<!\w){re.escape(upper_name)}(?!\w)',
                char.name,
                text,
            )
        return text


# ---------------------------------------------------------------------------
# Novel writer
# ---------------------------------------------------------------------------


class NovelWriter:
    """Writes novel-format prose chapter by chapter via LLM.

    Each chapter call receives its scene logs, chapter plan metadata, and
    adjacent chapter summaries for transition context.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def write_chapters(
        self,
        chapter_plan: ChapterPlan,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        scene_specs: dict[str, SceneSpec] | None = None,
    ) -> list[str]:
        """Write each chapter as prose.  Returns one string per chapter."""
        char_by_id = {c.id: c for c in characters}
        archive_by_id = {a.scene_id: a for a in scene_archives}
        chapters: list[str] = []

        for i, spec in enumerate(chapter_plan.chapters):
            scene_logs = self._build_chapter_scene_logs(
                spec, archive_by_id, char_by_id, scene_specs
            )

            prev_summary = chapter_plan.chapters[i - 1].summary if i > 0 else ""
            next_summary = (
                chapter_plan.chapters[i + 1].summary
                if i < len(chapter_plan.chapters) - 1
                else ""
            )

            word_count_target = (
                _get_chapter_write_short_target()
                if chapter_plan.is_short_story
                else _get_chapter_write_target()
            )

            chapter_prose = await self._generate_chapter(
                spec=spec,
                scene_logs=scene_logs,
                prev_summary=prev_summary,
                next_summary=next_summary,
                word_count_target=word_count_target,
                options=options,
            )

            if options.enhance:
                chapter_prose = await self._enhance_prose(chapter_prose)

            chapters.append(chapter_prose)

        return chapters

    # ------------------------------------------------------------------
    # Internal: chapter LLM call
    # ------------------------------------------------------------------

    async def _generate_chapter(
        self,
        spec: ChapterSpec,
        scene_logs: str,
        prev_summary: str,
        next_summary: str,
        word_count_target: str,
        options: WritingOptions,
    ) -> str:
        """Send a chapter prompt to the LLM and return the prose."""
        voice_label = options.narrative_voice.replace("_", " ")
        system_prompt = _get_chapter_write_system_prompt().format(voice=voice_label)

        lang = get_lang()
        if lang == Lang.ZH:
            user_prompt = (
                f"## 章节信息\n\n"
                f"标题：第{spec.number}章 {spec.title}\n"
                f"概述：{spec.summary}\n"
                f"目标字数：{word_count_target}\n\n"
                f"上一章概述：{prev_summary if prev_summary else '（无）'}\n"
                f"下一章概述：{next_summary if next_summary else '（无）'}\n\n"
                f"## 场景日志\n\n{scene_logs}\n\n"
                f"请写出完整的章节正文。"
            )
        else:
            user_prompt = (
                f"## Chapter Info\n\n"
                f"Title: Chapter {spec.number}: {spec.title}\n"
                f"Summary: {spec.summary}\n"
                f"Target word count: {word_count_target}\n\n"
                f"Previous chapter summary: {prev_summary if prev_summary else '(none)'}\n"
                f"Next chapter summary: {next_summary if next_summary else '(none)'}\n\n"
                f"## Scene Logs\n\n{scene_logs}\n\n"
                f"Write the complete chapter."
            )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw = await self._llm.chat(messages)
        return _extract_chapter_story(raw)

    async def _enhance_prose(self, prose: str) -> str:
        """Second-pass LLM call for pacing, sensory depth, and dialogue polish."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_novel_enhance_prompt()},
            {"role": "user", "content": prose},
        ]
        return await self._llm.chat(messages)

    # ------------------------------------------------------------------
    # Internal: scene log formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _build_chapter_scene_logs(
        spec: ChapterSpec,
        archive_by_id: dict[str, SceneArchive],
        char_by_id: dict[str, CharacterProfile],
        scene_specs: dict[str, SceneSpec] | None,
    ) -> str:
        """Build combined scene logs for a chapter."""
        all_lines: list[str] = []

        for scene_id in spec.scene_ids:
            archive = archive_by_id.get(scene_id)
            if archive is None:
                all_lines.append(f"## Scene: {scene_id} [no archive data]")
                all_lines.append("")
                continue

            sspec = scene_specs.get(scene_id) if scene_specs else None
            if sspec:
                all_lines.append(f"## Scene: {scene_id} - {sspec.title}")
                all_lines.append(f"Location: {sspec.location}")
            else:
                all_lines.append(f"## Scene: {scene_id}")
            all_lines.append(f"Atmosphere: {archive.final_environment.atmosphere}")
            if archive.final_environment.background_activity:
                all_lines.append(
                    f"Background: {archive.final_environment.background_activity}"
                )
            all_lines.append("")

            for entry in archive.rounds:
                all_lines.append(f"--- Round {entry.round_num} ---")
                all_lines.append(f"Actor: {entry.actor_name}")
                if entry.dialogue:
                    all_lines.append(f'Dialogue: "{entry.dialogue}"')
                if entry.action:
                    all_lines.append(f"Action: {entry.action}")
                if entry.inner_thought:
                    all_lines.append(f"Inner thought: {entry.inner_thought}")
                if entry.emotion:
                    all_lines.append(f"Emotion: {entry.emotion}")
                for reaction in entry.reactions:
                    all_lines.append(
                        f"  {reaction.reactor_name} reacts: {reaction.visible_reaction}"
                    )
                    if reaction.inner_thought:
                        all_lines.append(
                            f"    ({reaction.reactor_name} thinks: {reaction.inner_thought})"
                        )
                all_lines.append("")

        return "\n".join(all_lines)


# ---------------------------------------------------------------------------
# Screenplay writer
# ---------------------------------------------------------------------------


class ScreenplayWriter:
    """Converts scene logs to standard screenplay format with act structure.

    ZH scene headings use [内景]/[外景]; EN uses [INT.]/[EXT.].
    Acts and scene numbers are applied during assembly (not by the LLM).
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def convert(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        act_plan: ChapterPlan,
        title: str,
        title_candidates: list[str],
        scene_specs: dict[str, SceneSpec] | None = None,
    ) -> WrittenOutput:
        """Convert scene archives to screenplay-format text with act structure."""
        char_by_id = {c.id: c for c in characters}
        char_names = "、".join(c.name for c in characters if c.name)
        scene_pages: dict[str, str] = {}

        for archive in scene_archives:
            location = ""
            if scene_specs and archive.scene_id in scene_specs:
                location = scene_specs[archive.scene_id].location
            scene_log = self._format_scene_log(archive, char_by_id, location)
            formatted = await self._generate_screenplay(scene_log, char_names)
            formatted = self._strip_thinking_tags(formatted)
            if options.enhance:
                formatted = await self._enhance_screenplay(formatted)
            scene_pages[archive.scene_id] = formatted

        content = self._assemble_screenplay(
            title=title,
            scene_pages=scene_pages,
            act_plan=act_plan,
        )

        return WrittenOutput(
            content=content,
            format="screenplay",
            word_count=len(content.split()),
            scene_count=len(scene_archives),
            title=title,
            title_candidates=title_candidates,
            export_formats=["txt", "fountain"],
        )

    # ------------------------------------------------------------------
    # Internal: LLM calls
    # ------------------------------------------------------------------

    async def _generate_screenplay(
        self, scene_log: str, character_names: str = ""
    ) -> str:
        """Send a scene log to the LLM and return screenplay-format text."""
        from app.core.i18n import Lang, get_lang
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_screenplay_system_prompt()},
        ]
        if get_lang() == Lang.ZH:
            name_rule = (
                f"场景中的角色名称为：{character_names}。"
                "你必须使用这些中文名称，绝对不能写成拼音或英文大写。"
            ) if character_names else "你必须使用简体中文角色名，绝对不能写成拼音或英文大写。"
            messages.append({"role": "user", "content": name_rule})
        messages.append({"role": "user", "content": scene_log})
        return await self._llm.chat(messages)

    async def _enhance_screenplay(self, text: str) -> str:
        """Second-pass LLM call for formatting consistency."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_screenplay_enhance_prompt()},
            {"role": "user", "content": text},
        ]
        return await self._llm.chat(messages)

    @staticmethod
    def _strip_thinking_tags(text: str) -> str:
        """Remove <构思> / <thinking> tags from LLM screenplay output."""
        cleaned = re.sub(r'<构思>.*?</构思>', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=re.DOTALL)
        return cleaned.strip()

    # ------------------------------------------------------------------
    # Internal: formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_scene_log(
        archive: SceneArchive,
        char_by_id: dict[str, CharacterProfile],
        location: str = "",
    ) -> str:
        """Format scene rounds into a readable log for screenplay conversion."""
        lines: list[str] = []
        lines.append(f"Scene: {archive.scene_id}")
        if location:
            lines.append(f"Location: {location}")
        lines.append(f"Atmosphere: {archive.final_environment.atmosphere}")
        if archive.final_environment.background_activity:
            lines.append(
                f"Background: {archive.final_environment.background_activity}"
            )
        lines.append("")

        for entry in archive.rounds:
            lines.append(f"Character: {entry.actor_name}")
            if entry.dialogue:
                lines.append(f'Says: "{entry.dialogue}"')
            if entry.action:
                lines.append(f"Does: {entry.action}")
            if entry.inner_thought:
                lines.append(f"[内心] {entry.actor_name}心想：{entry.inner_thought}")
            if entry.emotion:
                lines.append(f"Emotion: {entry.emotion}")
            for reaction in entry.reactions:
                lines.append(
                    f"  {reaction.reactor_name} reacts: {reaction.visible_reaction}"
                )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _assemble_screenplay(
        title: str,
        scene_pages: dict[str, str],
        act_plan: ChapterPlan,
    ) -> str:
        """Combine formatted scenes into full screenplay with markdown structure.

        Uses the same markdown hierarchy as the novel output:
        # Title → ## Act → ### Scene
        """
        lang = get_lang()
        parts: list[str] = [f"# {title}", ""]

        global_scene_num = 1

        for act_spec in act_plan.chapters:
            # Skip acts where none of their scene_ids have content
            act_scenes = [sid for sid in act_spec.scene_ids if sid in scene_pages]
            if not act_scenes:
                continue

            if lang == Lang.ZH:
                parts.append(f"## 第{act_spec.number}幕 {act_spec.title}")
            else:
                parts.append(f"## Act {act_spec.number}: {act_spec.title}")
            parts.append("")

            for scene_id in act_scenes:
                scene_text = scene_pages.get(scene_id)
                if scene_text is None:
                    continue

                if lang == Lang.ZH:
                    parts.append(f"### 第{global_scene_num}场")
                else:
                    parts.append(f"### Scene {global_scene_num}")
                parts.append("")
                parts.append(scene_text)
                parts.append("")
                global_scene_num += 1

        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------


class NarrativeWriter:
    """Facade that orchestrates the full narrative pipeline.

    For novels:
      TitleGenerator -> ChapterPlanner -> NovelWriter (chapter-by-chapter)
      -> PostProcessor -> assembly with i18n
    For screenplays:
      ScreenplayWriter (per-scene) -> assembly with i18n

    Also handles export to file and format metadata queries.
    """

    def __init__(self, llm: LLMClient, memory: MemoryManager) -> None:
        self._llm = llm
        self._memory = memory
        self._title_gen = TitleGenerator(llm)
        self._planner = ChapterPlanner(llm)
        self._novel_writer = NovelWriter(llm)
        self._screenplay_writer = ScreenplayWriter(llm)
        self._post_processor = PostProcessor()

    async def convert(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        plot_outline: PlotOutline | None = None,
        world_summary: str = "",
        selected_title_index: int = 0,
    ) -> WrittenOutput:
        """Convert scene archives to the requested format.

        plot_outline: required for novel chapter planning; optional otherwise.
        world_summary: used for title generation; can be empty string.
        selected_title_index: which title candidate to use (default: first).
        """
        if not scene_archives:
            raise ValueError("At least one scene archive is required")
        if not characters:
            raise ValueError("At least one character profile is required")
        if options.format not in ("novel", "screenplay"):
            raise ValueError(
                f"Unsupported format '{options.format}'. "
                "Use 'novel' or 'screenplay'."
            )

        # --- Step 1: Generate title candidates ---
        title_candidates = await self._title_gen.generate_titles(
            world_summary, characters, plot_outline
        )
        selected_title = (
            title_candidates[selected_title_index]
            if title_candidates and selected_title_index < len(title_candidates)
            else t("writer.default_title")
        )

        if options.format == "novel":
            result = await self._convert_novel(
                scene_archives=scene_archives,
                characters=characters,
                options=options,
                plot_outline=plot_outline,
                selected_title=selected_title,
                title_candidates=title_candidates,
            )
        else:
            result = await self._convert_screenplay(
                scene_archives=scene_archives,
                characters=characters,
                options=options,
                plot_outline=plot_outline,
                selected_title=selected_title,
                title_candidates=title_candidates,
            )

        return result

    async def _convert_novel(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        plot_outline: PlotOutline | None,
        selected_title: str,
        title_candidates: list[str],
    ) -> WrittenOutput:
        """Full novel pipeline: plan chapters, write chapter by chapter, assemble."""
        scene_specs: dict[str, SceneSpec] = {}
        if plot_outline is not None:
            scene_specs = _flatten_scenes(plot_outline)

        # --- Step 2: Plan chapters ---
        if plot_outline is not None:
            chapter_plan = await self._planner.plan_chapters(plot_outline, characters)
        else:
            chapter_plan = self._fallback_chapter_plan(scene_archives)

        # --- Step 3: Write chapters ---
        chapters = await self._novel_writer.write_chapters(
            chapter_plan=chapter_plan,
            scene_archives=scene_archives,
            characters=characters,
            options=options,
            scene_specs=scene_specs if scene_specs else None,
        )

        # --- Step 4: Post-process each chapter ---
        chapters = [self._post_processor.process(ch) for ch in chapters]

        # --- Step 5: Assemble ---
        content = self._assemble_novel(selected_title, chapter_plan, chapters)

        return WrittenOutput(
            content=content,
            format="novel",
            word_count=len(content.split()),
            scene_count=len(scene_archives),
            title=selected_title,
            title_candidates=title_candidates,
            export_formats=["md", "txt"],
        )

    async def _convert_screenplay(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        plot_outline: PlotOutline | None,
        selected_title: str,
        title_candidates: list[str],
    ) -> WrittenOutput:
        """Screenplay pipeline: act planning, per-scene conversion, post-processing, assembly."""
        scene_specs: dict[str, SceneSpec] = {}
        if plot_outline is not None:
            scene_specs = _flatten_scenes(plot_outline)

        # Plan acts (reuse ChapterPlanner — chapters become acts in screenplay context)
        if plot_outline is not None:
            act_plan = await self._planner.plan_chapters(plot_outline, characters)
        else:
            act_plan = self._fallback_chapter_plan(scene_archives)

        output = await self._screenplay_writer.convert(
            scene_archives=scene_archives,
            characters=characters,
            options=options,
            act_plan=act_plan,
            title=selected_title,
            title_candidates=title_candidates,
            scene_specs=scene_specs if scene_specs else None,
        )

        # Post-process with screenplay-specific rules
        output.content = PostProcessor.normalize_screenplay(output.content, characters)
        output.word_count = len(output.content.split())

        return output

    # ------------------------------------------------------------------
    # Fallback: no plot outline
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_chapter_plan(
        scene_archives: list[SceneArchive],
    ) -> ChapterPlan:
        """Build a minimal chapter plan from archives when no plot outline exists.

        Groups every 3 scenes into one numbered chapter.
        """
        specs: list[ChapterSpec] = []
        chunk_size = 3
        lang = get_lang()

        for i in range(0, len(scene_archives), chunk_size):
            batch = scene_archives[i : i + chunk_size]
            chapter_num = i // chunk_size + 1
            scene_ids = [a.scene_id for a in batch]

            if lang == Lang.ZH:
                title = f"第{chapter_num}章"
            else:
                title = f"Chapter {chapter_num}"

            specs.append(
                ChapterSpec(
                    number=chapter_num,
                    title=title,
                    scene_ids=scene_ids,
                    summary="",
                )
            )

        if not specs:
            specs.append(
                ChapterSpec(
                    number=1,
                    title=t("writer.default_title"),
                    scene_ids=[],
                    summary="",
                )
            )

        return ChapterPlan(chapters=specs)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _assemble_novel(
        title: str,
        chapter_plan: ChapterPlan,
        chapter_prose: list[str],
    ) -> str:
        """Combine chapter prose into a single markdown document.

        Title and chapter headings come from TitleGenerator and ChapterPlanner.
        All static text uses i18n t().
        """
        lang = get_lang()
        parts: list[str] = [f"# {title}\n"]

        for spec, prose in zip(chapter_plan.chapters, chapter_prose):
            if lang == Lang.ZH:
                heading = f"## 第{spec.number}章 {spec.title}"
            else:
                heading = f"## Chapter {spec.number}: {spec.title}"
            parts.append(f"\n{heading}\n\n{prose}")

        return "".join(parts)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(
        self, output: WrittenOutput, fmt: str, filepath: str | Path
    ) -> None:
        """Write a WrittenOutput to disk in the requested export format.

        Supported format conversions:
          novel      -> md (Markdown, as-is)
          novel      -> txt (Plain text, stripped Markdown)
          screenplay -> txt (Plain text)
          screenplay -> fountain (Fountain format)
        """
        content = output.content
        ext = fmt.lower()

        if ext == "txt":
            if output.format == "novel":
                content = self._strip_markdown(content)
        elif ext == "fountain":
            if output.format != "screenplay":
                raise ValueError(
                    "Fountain export is only supported for screenplay format"
                )
            content = self._to_fountain(content)
        elif ext == "md":
            if output.format != "novel":
                raise ValueError(
                    "Markdown export is only supported for novel format"
                )
        else:
            raise ValueError(
                f"Unsupported export format '{fmt}'. "
                f"Supported: {', '.join(self._export_formats(output.format))}"
            )

        Path(filepath).write_text(content, encoding="utf-8")

    def export_to_temp(
        self, output: WrittenOutput, fmt: str
    ) -> str:
        """Export to a temporary file and return the file path."""
        suffix = f".{fmt}"
        with tempfile.NamedTemporaryFile(
            suffix=suffix, mode="w", encoding="utf-8", delete=False
        ) as f:
            self.export(output, fmt, f.name)
            return f.name

    @staticmethod
    def _export_formats(writing_format: str) -> list[str]:
        """Return list of export formats valid for the given writing format."""
        if writing_format == "novel":
            return ["md", "txt"]
        if writing_format == "screenplay":
            return ["txt", "fountain"]
        return []

    @staticmethod
    def supported_export_formats() -> dict[str, list[str]]:
        """Return mapping of writing format -> available export formats."""
        return {
            "novel": ["md", "txt"],
            "screenplay": ["txt", "fountain"],
        }

    # ------------------------------------------------------------------
    # Internal: format helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove Markdown formatting for plain-text export."""
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
        return text.strip()

    @staticmethod
    def _to_fountain(screenplay_text: str) -> str:
        """Convert basic screenplay text to Fountain format.

        Fountain is a plain-text markup language for screenplays.
        Since the screenplay output already uses standard conventions,
        this is primarily a normalization pass.
        """
        lines = screenplay_text.split("\n")
        fountain_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            if stripped.upper().startswith(("INT.", "EXT.", "INT/EXT.")):
                fountain_lines.append(stripped.upper())
                continue

            if stripped.isupper() and len(stripped) > 1 and stripped.strip("() ").isupper():
                fountain_lines.append(stripped)
                continue

            if stripped.startswith("(") and stripped.endswith(")"):
                fountain_lines.append(stripped)
                continue

            if not stripped:
                fountain_lines.append("")
                continue

            fountain_lines.append(stripped)

        return "\n".join(fountain_lines)
