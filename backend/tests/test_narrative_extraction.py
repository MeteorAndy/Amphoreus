"""Regression tests for chapter-prose extraction and word counting.

Covers the critical scaffolding-leak bug: planning/analysis text and stray
tags leaking into the final novel content (see review finding #1).
"""
from __future__ import annotations

from app.services.narrative.novel_writer import _extract_chapter_story


def _clean(result: str, *leaked: str) -> bool:
    return not any(t in result for t in leaked)


def test_extract_real_leak_analysis_then_body_header():
    raw = ("# 章节分析\n\n审阅后：\n**逻辑漏洞**：场景过渡需强化\n\n"
           "# 章节正文\n\n暮色沉入深蓝，林辰靠在石墙上。")
    out = _extract_chapter_story(raw)
    assert _clean(out, "章节分析", "逻辑漏洞", "章节正文")
    assert "暮色沉入深蓝" in out


def test_extract_proper_story_tags():
    raw = "<思考>分析逻辑漏洞和节奏</思考>\n<story>\n夜色降临，林辰握紧笔记。\n</story>"
    out = _extract_chapter_story(raw)
    assert _clean(out, "分析", "思考") and "夜色降临" in out


def test_extract_unclosed_story_tag():
    raw = "<思考>分析内容</思考>\n<story>\n风停了，书页静止。林辰皱眉。"
    out = _extract_chapter_story(raw)
    assert _clean(out, "分析", "思考") and "风停了" in out


def test_extract_bare_analysis_header_then_prose_no_body_header():
    # The worst case: analysis header followed directly by prose, no <story>,
    # no body header. Must drop analysis but KEEP the prose.
    raw = "# 章节分析\n\n节奏问题：开头太慢。\n\n夜风穿过回响之井，林辰俯身向前。"
    out = _extract_chapter_story(raw)
    assert _clean(out, "章节分析", "节奏问题")
    assert "夜风穿过回响之井" in out


def test_extract_multi_section_analysis_then_prose():
    raw = ("# 章节分析\n\n**逻辑漏洞**：\n1. 过渡突兀\n\n**节奏问题**：\n1. 对话冗长\n\n"
           "**改进方向**：\n1. 增加环境渲染\n\n月光漫过书脊，林辰停下脚步。")
    out = _extract_chapter_story(raw)
    assert _clean(out, "章节分析", "逻辑漏洞", "节奏问题", "改进方向")
    assert "月光漫过书脊" in out


def test_extract_english_story_tags():
    raw = ("<thinking>analysis of pacing</thinking>\n"
           "<story>\nThe night fell. Lin Chen gripped his notebook.\n</story>")
    out = _extract_chapter_story(raw)
    assert _clean(out, "analysis", "pacing") and "The night fell" in out


def test_extract_clean_prose_passthrough():
    raw = "晨光照进图书馆，苏婉清翻开书页。"
    assert _extract_chapter_story(raw) == raw


def test_extract_never_blanks_nonempty():
    # Even pathological input must not yield empty output.
    assert _extract_chapter_story("# 章节分析\n\n仅有分析没有正文").strip()


def test_extract_strips_leading_chapter_heading():
    # The assembler prepends the canonical "## 第N章 …"; if the model also emits
    # its own heading atop the prose, they double up (the duplicate-title bug).
    raw = "<story>\n# 第1章 残页与飘零\n\n暮色沉入深蓝，林辰靠在石墙上。\n</story>"
    out = _extract_chapter_story(raw)
    assert not out.lstrip().startswith("#")
    assert "暮色沉入深蓝" in out


def test_extract_strips_stacked_leading_headings():
    raw = "## 第2章 遗忘阶梯\n# 第2章 遗忘阶梯的试炼\n\n月光漫过书脊，林辰停下脚步。"
    out = _extract_chapter_story(raw)
    assert not out.lstrip().startswith("#")
    assert "月光漫过书脊" in out


def test_extract_strips_leading_bold_chapter_heading():
    # The model sometimes emits the chapter title as a bold line rather than a
    # markdown header: "**第1章 灰烬中的觉醒**". The assembler still prepends
    # its canonical "## 第N章 …", so the bold echo must be stripped too —
    # otherwise the finished novel shows both (the duplicate-title bug seen in
    # the dogfood run).
    raw = "<story>\n**第1章 灰烬中的觉醒**\n\n油灯的光芒被瓶中液体染成幽蓝。\n</story>"
    out = _extract_chapter_story(raw)
    assert "灰烬中的觉醒" not in out
    assert not out.lstrip().startswith("**")
    assert "油灯的光芒" in out


def test_extract_strips_leading_bold_english_chapter_heading():
    raw = "**Chapter 3: The Forgetting Stair**\n\nThe night fell."
    out = _extract_chapter_story(raw)
    assert "Forgetting Stair" not in out
    assert "The night fell" in out


def test_extract_preserves_inner_heading():
    # Only a LEADING heading run is stripped; headings within prose stay.
    raw = "夜色降临。\n\n# 章节内的小节标题\n\n他继续前行。"
    out = _extract_chapter_story(raw)
    assert out.startswith("夜色降临")
    assert "# 章节内的小节标题" in out
