"""Tests for T2-③: deterministic 5-dimension worldbuilding view.

Pure, zero-LLM classifier that buckets the EXISTING extracted world items
(rules/locations/factions/timeline) into 5 named dimensions (physical / social /
economic / cultural / metaphysical). Additive — dimensions is a curated SUBSET
view; nothing is removed from the flat lists, no consumer changes.

Run as a targeted file (full suite hangs on integration tests):
    uv run pytest tests/test_world_dimensions.py -v
"""

from __future__ import annotations

import copy

from app.services.narrative.world_contract import build_contract_block
from app.services.narrative.world_dimensions import derive_dimensions
from app.services.world_builder import WorldState
from app.services.narrative import canon_persistence as cp


def _rule(name, category, desc=""):
    return {"name": name, "category": category, "description": desc}


def _loc(name, type_, desc=""):
    return {"name": name, "type": type_, "description": desc}


def _fac(name, type_, desc=""):
    return {"name": name, "type": type_, "description": desc}


def _tl(name, era, desc=""):
    return {"name": name, "era": era, "description": desc}


# --- classifier core ------------------------------------------------------

def test_empty_world_returns_empty_dict():
    assert derive_dimensions(WorldState()) == {}


def test_magic_rule_goes_to_metaphysical_not_physical():
    w = WorldState(rules=[_rule("灵脉", "magic system")])
    d = derive_dimensions(w)
    assert "metaphysical" in d and "physical" not in d


def test_physics_rule_goes_to_physical():
    w = WorldState(rules=[_rule("重力法则", "physics")])
    d = derive_dimensions(w)
    assert d.get("physical") and not d.get("metaphysical")


def test_all_factions_go_to_social_by_default():
    w = WorldState(factions=[_fac("骑士团", "order"), _fac("议会", "council")])
    d = derive_dimensions(w)
    social = {x["name"] for x in d.get("social", [])}
    assert social == {"骑士团", "议会"}


def test_economic_faction_beats_social_first_match():
    w = WorldState(factions=[_fac("商会", "merchant guild")])
    d = derive_dimensions(w)
    assert d.get("economic") and not d.get("social")


def test_market_location_goes_to_economic():
    w = WorldState(locations=[_loc("大港", "port")])
    d = derive_dimensions(w)
    assert d.get("economic")


def test_temple_location_goes_to_cultural():
    w = WorldState(locations=[_loc("神殿", "temple")])
    d = derive_dimensions(w)
    assert d.get("cultural")


def test_mythic_timeline_era_goes_to_metaphysical():
    w = WorldState(timeline=[_tl("创世", "Creation Era")])
    d = derive_dimensions(w)
    assert d.get("metaphysical")


def test_pure_history_timeline_is_omitted():
    tl = _tl("贞观之治", "Tang Dynasty")
    w = WorldState(timeline=[tl])
    d = derive_dimensions(w)
    # no dimension bucket contains it, but the flat list is untouched
    assert all(tl not in bucket for bucket in d.values())
    assert w.timeline == [tl]


def test_does_not_mutate_flat_lists():
    rules = [_rule("魔法", "magic")]
    w = WorldState(rules=rules)
    snapshot = copy.deepcopy(rules)
    derive_dimensions(w)
    assert w.rules == snapshot           # identity + contents unchanged
    assert w.rules is rules               # not replaced


def test_item_appears_in_at_most_one_bucket():
    # a rule matching several keyword sets lands in exactly one bucket
    w = WorldState(rules=[_rule("神圣魔法经济", "magic economy religion")])
    d = derive_dimensions(w)
    counts = sum(1 for bucket in d.values() for item in bucket if item["name"] == "神圣魔法经济")
    assert counts == 1


def test_bucket_items_tagged_with_source():
    w = WorldState(factions=[_fac("议会", "council")])
    d = derive_dimensions(w)
    item = d["social"][0]
    assert item["_source"] == "factions"
    assert item["_src_name"] == "议会"


# --- WorldState additive field --------------------------------------------

def test_world_state_default_dimensions_is_empty_dict():
    assert WorldState().dimensions == {}


# --- persistence round-trip ------------------------------------------------

def test_to_dict_from_dict_round_trips_dimensions():
    w = WorldState(rules=[_rule("魔法", "magic")])
    w.dimensions = derive_dimensions(w)
    restored = cp.world_state_from_dict(cp.world_state_to_dict(w))
    assert restored.dimensions == w.dimensions


def test_old_artifact_missing_dimensions_loads_empty():
    old = {"rules": [], "locations": [], "factions": [], "timeline": [], "completeness": 0.5}
    assert cp.world_state_from_dict(old).dimensions == {}


# --- world_contract consumption -------------------------------------------

def test_contract_emits_dimensions_section_when_populated():
    w = WorldState(rules=[_rule("魔法体系", "magic")], factions=[_fac("议会", "council")])
    w.dimensions = derive_dimensions(w)
    block = build_contract_block(w)
    assert "世界维度" in block or "World Dimensions" in block


def test_contract_omits_dimensions_section_when_empty():
    w = WorldState(rules=[_rule("法则", "physics")])  # dimensions NOT derived -> {}
    block = build_contract_block(w)
    assert "世界维度" not in block and "World Dimensions" not in block
