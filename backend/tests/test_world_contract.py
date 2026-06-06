"""Tests for T1-⑥: unified world-constraint formatter."""

from __future__ import annotations

from app.core.i18n import set_lang, Lang
from app.services.narrative.world_contract import build_contract_block
from app.services.world_builder import WorldState


def _world(**kw):
    return WorldState(
        rules=kw.get("rules", []),
        locations=kw.get("locations", []),
        factions=kw.get("factions", []),
        timeline=kw.get("timeline", []),
    )


def test_empty_world_returns_empty_string():
    assert build_contract_block(WorldState()) == ""


def test_rules_rendered_zh():
    set_lang(Lang.ZH)
    w = _world(rules=[{"name": "记忆代价", "description": "改写现实需以记忆为代价"}])
    block = build_contract_block(w)
    assert "记忆代价" in block and "改写现实" in block


def test_locations_rendered_en():
    set_lang(Lang.EN)
    w = _world(locations=[{"name": "Cloud Library", "type": "Floating", "description": "Holds forbidden books"}])
    block = build_contract_block(w)
    assert "Cloud Library" in block and "Key Locations" in block


def test_tone_hints_when_rule_dense():
    set_lang(Lang.ZH)
    w = _world(rules=[{"name": f"r{i}"} for i in range(6)], factions=[{"name": "A"}, {"name": "B"}, {"name": "C"}])
    block = build_contract_block(w)
    assert "氛围基调" in block or "Tone" in block


def test_empty_sections_omitted():
    set_lang(Lang.ZH)
    w = _world(rules=[{"name": "x"}])
    block = build_contract_block(w)
    assert "势力" not in block and "地点" not in block
