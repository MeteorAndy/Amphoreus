"""Tests for the POV firewall chokepoint (PART B)."""

from __future__ import annotations

import pytest

from app.models.character import CharacterProfile
from app.services.character_manager import CharacterManager
from app.services.narrative.foreshadowing import visible_profile
from app.services.narrative.novel_writer import NovelWriter
from app.services.narrative.token_budget import TokenBudgetConfig
from app.services.narrative.types import ChapterPlan, ChapterSpec, WritingOptions


def _char(**kw) -> CharacterProfile:
    base = {"id": "c1", "name": "Aglaea"}
    base.update(kw)
    return CharacterProfile(**base)


def test_hidden_omitted_before_reveal_chapter():
    c = _char(public_profile="public", hidden_profile="SECRET", reveal_chapter=5)
    out = visible_profile(c, current_chapter=3)
    assert "SECRET" not in out
    assert "public" in out


def test_hidden_shown_at_reveal_chapter():
    c = _char(public_profile="public", hidden_profile="SECRET", reveal_chapter=5)
    out = visible_profile(c, current_chapter=5)
    assert "SECRET" in out


def test_hidden_shown_after_reveal_chapter():
    c = _char(public_profile="public", hidden_profile="SECRET", reveal_chapter=5)
    assert "SECRET" in visible_profile(c, current_chapter=8)


def test_reveal_none_always_shows_hidden():
    c = _char(public_profile="public", hidden_profile="SECRET", reveal_chapter=None)
    assert "SECRET" in visible_profile(c, current_chapter=None)
    assert "SECRET" in visible_profile(c, current_chapter=1)


def test_current_chapter_none_hides_when_reveal_set():
    c = _char(public_profile="public", hidden_profile="SECRET", reveal_chapter=5)
    assert "SECRET" not in visible_profile(c, current_chapter=None)


def test_empty_public_falls_back_to_appearance():
    c = _char(public_profile="", appearance="tall and pale", reveal_chapter=99)
    assert visible_profile(c, current_chapter=1) == "tall and pale"


def test_empty_everything_returns_empty_or_name_safe():
    c = _char(public_profile="", appearance="", hidden_profile="", reveal_chapter=None)
    out = visible_profile(c, current_chapter=1)
    assert isinstance(out, str)
    assert out == ""


def test_character_does_not_self_filter():
    c = _char(public_profile="public", hidden_profile="SECRET", reveal_chapter=5)
    assert c.hidden_profile == "SECRET"
    assert "SECRET" not in visible_profile(c, current_chapter=1)


def test_character_manager_parses_pov_firewall_fields():
    manager = object.__new__(CharacterManager)
    profile = manager._parse_character(
        {
            "id": "c1",
            "name": "Aglaea",
            "public_profile": "court musician",
            "hidden_profile": "exiled heir",
            "reveal_chapter": 4,
        },
        "now",
    )

    assert profile.public_profile == "court musician"
    assert profile.hidden_profile == "exiled heir"
    assert profile.reveal_chapter == 4


class _SpyLLM:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages, **kwargs):
        self.calls.append(messages)
        return "chapter prose"


def _single_chapter(number: int) -> ChapterPlan:
    return ChapterPlan(
        chapters=[
            ChapterSpec(
                number=number,
                title="Open",
                scene_ids=[],
                summary="summary",
            )
        ]
    )


@pytest.mark.asyncio
async def test_novel_prompt_uses_visible_profile_before_reveal():
    llm = _SpyLLM()
    writer = NovelWriter(llm)
    char = _char(
        name="Aglaea",
        public_profile="court musician",
        hidden_profile="exiled heir",
        reveal_chapter=4,
    )

    await writer.write_chapters(
        _single_chapter(2),
        [],
        [char],
        WritingOptions(format="novel"),
    )

    user_prompt = llm.calls[0][-1]["content"]
    assert "court musician" in user_prompt
    assert "exiled heir" not in user_prompt


@pytest.mark.asyncio
async def test_novel_prompt_reveals_hidden_profile_at_reveal_chapter():
    llm = _SpyLLM()
    writer = NovelWriter(llm)
    char = _char(
        name="Aglaea",
        public_profile="court musician",
        hidden_profile="exiled heir",
        reveal_chapter=4,
    )

    await writer.write_chapters(
        _single_chapter(4),
        [],
        [char],
        WritingOptions(format="novel"),
    )

    user_prompt = llm.calls[0][-1]["content"]
    assert "court musician" in user_prompt
    assert "exiled heir" in user_prompt


@pytest.mark.asyncio
async def test_token_budget_accounts_visible_character_context():
    llm = _SpyLLM()
    writer = NovelWriter(llm)
    acc = []
    char = _char(name="Aglaea", public_profile="court musician")

    await writer.write_chapters(
        _single_chapter(1),
        [],
        [char],
        WritingOptions(
            format="novel",
            token_budget=TokenBudgetConfig(enabled=True, budget_tokens=8000),
        ),
        budget_acc=acc,
    )

    assert any(section.name == "character_context" for section in acc[0].sections)
