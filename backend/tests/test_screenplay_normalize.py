"""Regression tests for screenplay dialogue/voice-over normalisation (ZH).

Covers review findings: mixed inline vs block dialogue, and 5-6 incompatible
OS/旁白 markup variants. The normaliser must unify them WITHOUT splitting
action lines that merely contain a colon.
"""
from __future__ import annotations

import pytest

from app.core.i18n import set_lang, Lang
from app.models.character import CharacterProfile
from app.services.narrative.post_processor import PostProcessor


@pytest.fixture(autouse=True)
def _zh():
    set_lang(Lang.ZH)
    yield


CHARS = [
    CharacterProfile(id="1", name="林辰"),
    CharacterProfile(id="2", name="叶重霄"),
    CharacterProfile(id="3", name="苏婉清"),
]


def n(text: str) -> str:
    return PostProcessor._normalize_dialogue_zh(text, CHARS)


def test_inline_dialogue_split_to_block():
    assert n("林辰：苏小姐，你好。") == "林辰\n苏小姐，你好。"


@pytest.mark.parametrize("raw", [
    "叶重霄（OS）：伤疤传来词汇。",   # name (OS): content
    "（OS）叶重霄：伤疤传来词汇。",   # (OS) name: content
    "叶重霄：（OS）伤疤传来词汇。",   # name: (OS) content
    "（叶重霄OS）伤疤传来词汇。",     # (name OS) content
])
def test_os_variants_unified(raw):
    assert n(raw) == "叶重霄（OS）\n伤疤传来词汇。"


def test_narration_unified_to_vo():
    assert n("（旁白）：月光如刃。") == "旁白（VO）\n月光如刃。"


def test_action_line_with_colon_not_split():
    # Prefix is not a character name -> must stay intact.
    line = "桌上散落着三样东西：地图、玉坠、笔记。"
    assert n(line) == line


def test_bare_name_line_untouched():
    assert n("林辰") == "林辰"


def test_action_line_untouched():
    line = "月光如刃切开凝滞的空气。"
    assert n(line) == line


def test_idempotent():
    src = "林辰：苏小姐。\n叶重霄（OS）：伤疤。\n（旁白）：夜深了。"
    once = n(src)
    assert n(once) == once
