"""Tests for the POV firewall chokepoint (PART B)."""

from __future__ import annotations

from app.models.character import CharacterProfile
from app.services.narrative.foreshadowing import visible_profile


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
