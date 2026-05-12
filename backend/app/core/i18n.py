"""Amphoreus i18n — Chinese/English bilingual support."""

from __future__ import annotations

from enum import Enum
from typing import Callable


class Lang(str, Enum):
    ZH = "zh"
    EN = "en"


_current: Lang = Lang.ZH


def set_lang(lang: Lang) -> None:
    global _current
    _current = lang


def get_lang() -> Lang:
    return _current


# ── Translation table ──────────────────────────────────────────────

_T: dict[str, dict[Lang, str]] = {
    # Banner
    "banner.title": {
        Lang.ZH: "Amphoreus 故事引擎",
        Lang.EN: "Amphoreus Story Engine",
    },
    "banner.subtitle": {
        Lang.ZH: "AI 驱动的小说与剧本生成器",
        Lang.EN: "AI-Powered Novel & Screenplay Generator",
    },
    # Mode selection
    "mode.title": {
        Lang.ZH: "选择模式",
        Lang.EN: "Select Mode",
    },
    "mode.1": {
        Lang.ZH: "从 idea 构建新世界",
        Lang.EN: "Build a new world from an idea",
    },
    "mode.2": {
        Lang.ZH: "上传已有世界观文档",
        Lang.EN: "Upload existing world document",
    },
    "mode.3": {
        Lang.ZH: "继续已有项目",
        Lang.EN: "Continue existing project",
    },
    "mode.q": {
        Lang.ZH: "退出",
        Lang.EN: "Quit",
    },
    # Language
    "lang.select": {
        Lang.ZH: "选择语言 / Select Language",
        Lang.EN: "Select Language / 选择语言",
    },
    "lang.zh": {
        Lang.ZH: "简体中文",
        Lang.EN: "Simplified Chinese",
    },
    "lang.en": {
        Lang.ZH: "English",
        Lang.EN: "English",
    },
    # API Key
    "apikey.missing_deepseek": {
        Lang.ZH: "未配置 DeepSeek API Key。请在 https://platform.deepseek.com/api_keys 获取。",
        Lang.EN: "DeepSeek API Key not configured. Get one at https://platform.deepseek.com/api_keys",
    },
    "apikey.missing_volcengine": {
        Lang.ZH: "未配置火山引擎 API Key。请在 https://console.volcengine.com/ark 获取。",
        Lang.EN: "Volcengine API Key not configured. Get one at https://console.volcengine.com/ark",
    },
    "apikey.enter": {
        Lang.ZH: "请输入你的 API Key",
        Lang.EN: "Enter your API Key",
    },
    "apikey.configured": {
        Lang.ZH: "API Key 已配置",
        Lang.EN: "API Keys configured",
    },
    # World building
    "world.start": {
        Lang.ZH: "🌍 世界构建",
        Lang.EN: "🌍 World Building",
    },
    "world.enter_idea": {
        Lang.ZH: "请输入你的故事 idea（一句话）",
        Lang.EN: "Enter your story idea (one sentence)",
    },
    "world.stage": {
        Lang.ZH: "阶段",
        Lang.EN: "Stage",
    },
    "world.completeness": {
        Lang.ZH: "完成度",
        Lang.EN: "Completeness",
    },
    "world.finalized": {
        Lang.ZH: "世界构建完成！",
        Lang.EN: "World building complete!",
    },
    # Characters
    "chars.title": {
        Lang.ZH: "👥 角色生成",
        Lang.EN: "👥 Character Generation",
    },
    "chars.generating": {
        Lang.ZH: "正在从你的世界中生成角色...",
        Lang.EN: "Generating characters from your world...",
    },
    "chars.count": {
        Lang.ZH: "已生成 {count} 个角色",
        Lang.EN: "Generated {count} characters",
    },
    "chars.edit_prompt": {
        Lang.ZH: "输入编号编辑角色，回车继续",
        Lang.EN: "Enter number to edit, Enter to continue",
    },
    # Plot
    "plot.title": {
        Lang.ZH: "📖 剧情架构",
        Lang.EN: "📖 Plot Architecture",
    },
    "plot.select_structure": {
        Lang.ZH: "选择叙事结构",
        Lang.EN: "Select narrative structure",
    },
    "plot.generating": {
        Lang.ZH: "正在生成剧情大纲...",
        Lang.EN: "Generating plot outline...",
    },
    "plot.scenes": {
        Lang.ZH: "场次",
        Lang.EN: "Scenes",
    },
    # Scene
    "scene.title": {
        Lang.ZH: "🎬 场景执行",
        Lang.EN: "🎬 Scene Execution",
    },
    "scene.select": {
        Lang.ZH: "选择要执行的场景 (编号, 'all', 或回车执行第一场)",
        Lang.EN: "Select scene to run (number, 'all', or Enter for first)",
    },
    "scene.round": {
        Lang.ZH: "第 {n} 轮",
        Lang.EN: "Round {n}",
    },
    "scene.complete": {
        Lang.ZH: "场景完成！共 {n} 轮",
        Lang.EN: "Scene complete! {n} rounds",
    },
    "scene.location": {
        Lang.ZH: "地点",
        Lang.EN: "Location",
    },
    # Writing
    "writer.title": {
        Lang.ZH: "📝 叙事写作",
        Lang.EN: "📝 Narrative Writing",
    },
    "writer.converting": {
        Lang.ZH: "转换为 {format} 格式...",
        Lang.EN: "Converting to {format} format...",
    },
    "writer.enhancing": {
        Lang.ZH: "质量增强中...",
        Lang.EN: "Quality enhancement...",
    },
    "writer.saved": {
        Lang.ZH: "已保存到 {path}",
        Lang.EN: "Saved to {path}",
    },
    "writer.view": {
        Lang.ZH: "查看输出？",
        Lang.EN: "View output?",
    },
    # General
    "general.yes": {
        Lang.ZH: "是",
        Lang.EN: "yes",
    },
    "general.no": {
        Lang.ZH: "否",
        Lang.EN: "no",
    },
    "general.back": {
        Lang.ZH: "返回",
        Lang.EN: "back",
    },
    "general.continue": {
        Lang.ZH: "继续",
        Lang.EN: "continue",
    },
    "general.loading": {
        Lang.ZH: "加载中...",
        Lang.EN: "Loading...",
    },
    "general.error": {
        Lang.ZH: "错误",
        Lang.EN: "Error",
    },
    "general.retry": {
        Lang.ZH: "重试",
        Lang.EN: "Retry",
    },
    "general.cancelled": {
        Lang.ZH: "已取消",
        Lang.EN: "Cancelled",
    },
    "general.goodbye": {
        Lang.ZH: "感谢使用 Amphoreus！再会。",
        Lang.EN: "Thank you for using Amphoreus. Goodbye.",
    },
    "general.press_enter": {
        Lang.ZH: "按回车继续...",
        Lang.EN: "Press Enter to continue...",
    },
    "general.next_scene": {
        Lang.ZH: "继续下一场？",
        Lang.EN: "Continue to next scene?",
    },
    # Structures
    "structure.three_act": {
        Lang.ZH: "三幕结构",
        Lang.EN: "Three-Act Structure",
    },
    "structure.hero_journey": {
        Lang.ZH: "英雄之旅 (12步)",
        Lang.EN: "Hero's Journey (12 Steps)",
    },
    "structure.save_the_cat": {
        Lang.ZH: "Save the Cat (15拍)",
        Lang.EN: "Save the Cat (15 Beats)",
    },
    "structure.qi_cheng_zhuan_he": {
        Lang.ZH: "起承转合 (东方四段)",
        Lang.EN: "Qi Cheng Zhuan He (Eastern 4-Part)",
    },
    # Guardian
    "guardian.rejected": {
        Lang.ZH: "🔴 故事守护者拒绝了此修改",
        Lang.EN: "🔴 Story Guardian rejected this change",
    },
    "guardian.warning": {
        Lang.ZH: "🟡 故事守护者发出警告",
        Lang.EN: "🟡 Story Guardian issued a warning",
    },
    "guardian.suggestion": {
        Lang.ZH: "🔵 故事守护者建议",
        Lang.EN: "🔵 Story Guardian suggestion",
    },
    # Document
    "doc.upload": {
        Lang.ZH: "输入文档路径 (PDF/MD/TXT)",
        Lang.EN: "Enter document path (PDF/MD/TXT)",
    },
    "doc.parsing": {
        Lang.ZH: "正在解析文档...",
        Lang.EN: "Parsing document...",
    },
    "doc.parsed": {
        Lang.ZH: "解析完成，提取到以下世界数据",
        Lang.EN: "Parsing complete. Extracted world data",
    },
    # Session
    "session.saved": {
        Lang.ZH: "进度已保存",
        Lang.EN: "Progress saved",
    },
    "session.resume": {
        Lang.ZH: "选择要恢复的会话",
        Lang.EN: "Select session to resume",
    },
    "session.none": {
        Lang.ZH: "没有可恢复的会话",
        Lang.EN: "No sessions to resume",
    },
    # Character editing
    "chars.editing": {
        Lang.ZH: "编辑角色 {name}",
        Lang.EN: "Editing character {name}",
    },
    "chars.edit_field": {
        Lang.ZH: "要修改什么？(name/role/desire/fear/personality/done)",
        Lang.EN: "What to edit? (name/role/desire/fear/personality/done)",
    },
    "chars.enter_new_value": {
        Lang.ZH: "输入新值",
        Lang.EN: "Enter new value",
    },
    # Roles
    "role.protagonist": {
        Lang.ZH: "主角",
        Lang.EN: "Protagonist",
    },
    "role.antagonist": {
        Lang.ZH: "反派",
        Lang.EN: "Antagonist",
    },
    "role.supporting": {
        Lang.ZH: "配角",
        Lang.EN: "Supporting",
    },
    "role.deuteragonist": {
        Lang.ZH: "第二主角",
        Lang.EN: "Deuteragonist",
    },
}


def t(key: str, **kwargs: object) -> str:
    """Get translated string for current language. Supports {fmt} args."""
    entry = _T.get(key, {})
    text = entry.get(_current, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
