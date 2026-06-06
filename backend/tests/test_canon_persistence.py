"""Round-trip tests for canon_persistence serializers."""
from __future__ import annotations

from app.models.character import CharacterProfile
from app.services.narrative import canon_persistence as cp
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate, Reaction, RoundEntry
from app.services.world_builder import WorldState


def test_archive_roundtrip_preserves_inner_thought_and_reactions():
    archive = SceneArchive(
        scene_id="s1",
        rounds=[RoundEntry(
            round_num=1, actor_id="c1", actor_name="林辰",
            dialogue="你好", action="转身", inner_thought="不能暴露", emotion="警惕",
            reactions=[Reaction(reactor_id="c2", reactor_name="苏婉清",
                                visible_reaction="皱眉", inner_thought="他在撒谎")],
        )],
        final_environment=EnvironmentUpdate(
            atmosphere="紧张", changes=["灯灭"], background_activity="远处钟声"),
        character_changes={"c1": {"trust": -1}},
    )
    restored = cp.archive_from_dict(cp.archive_to_dict(archive))
    assert restored == archive  # dataclass eq — full fidelity incl. inner_thought/reactions


def test_world_state_roundtrip():
    w = WorldState(rules=[{"name": "r"}], locations=[{"name": "l"}],
                   factions=[], timeline=[{"t": 1}], completeness=0.8)
    assert cp.world_state_from_dict(cp.world_state_to_dict(w)) == w


def test_character_roundtrip():
    c = CharacterProfile(id="c1", name="林辰")
    restored = cp.character_from_dict(cp.character_to_dict(c))
    assert restored.id == c.id and restored.name == c.name
    assert cp.character_to_dict(restored) == cp.character_to_dict(c)
