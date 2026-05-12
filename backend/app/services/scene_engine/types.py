from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Reaction:
    """A single character's visible and private reaction to an action or line."""

    reactor_id: str
    reactor_name: str
    visible_reaction: str  # what others can observe
    inner_thought: str  # private thought


@dataclass
class RoundEntry:
    """One round of scene execution — what one character says, does, and feels."""

    round_num: int
    actor_id: str
    actor_name: str
    dialogue: str
    action: str  # physical action description
    inner_thought: str  # what character is thinking (not visible to others)
    emotion: str
    reactions: list[Reaction] = field(default_factory=list)


@dataclass
class SceneSetup:
    """Complete scene setup produced by the Director before any rounds begin."""

    scene_id: str
    location: str
    location_description: str
    cast: list[str]  # character IDs present
    character_goals: dict[str, str]  # char_id -> their private goal for this scene
    hidden_info: dict[str, list[str]]  # char_id -> list of secrets only they know
    conflict_seed: str  # the initial tension
    end_conditions: list[str]  # conditions that trigger scene end


@dataclass
class Adjudication:
    """Director's ruling after evaluating one round of scene play."""

    should_continue: bool
    reason: str
    next_speaker: str | None  # who should act next
    inject_event: str | None  # external event to inject (optional)
    pacing_note: str
    ooc_warnings: list[str]


@dataclass
class EnvironmentUpdate:
    """Sensory and atmospheric state for a given moment in the scene."""

    atmosphere: str  # current mood/sensory description
    changes: list[str]  # what changed since last round
    background_activity: str  # NPCs, weather, sounds
