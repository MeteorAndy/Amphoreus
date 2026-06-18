"""CharacterCard — the authoritative identity definition for a character agent.

Extends SillyTavern V2 concepts + PlotPilot 4-dimension psychology +
Amphoreus's existing CharacterProfile fields. This replaces CharacterProfile
as the identity source for the Agent Mode. Classic Mode continues to use
CharacterProfile; a bidirectional converter bridges the two.

Design decisions (see memory/architecture-decisions.md):
- content_rating field for self-constraint (decision #5)
- goals[] drives emergent behavior (decision #2: soft outline)
- psychology 4-dim from PlotPilot
- agent_config controls memory/activation per-agent
- All existing CharacterProfile fields accessible via .extensions.amphoreus
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.character import Big5, Personality


class Psychology(BaseModel):
    """4-dimension character psychology (borrowed from PlotPilot).

    core_belief: the fundamental worldview the character operates from.
    moral_taboos: lines they will not cross (drives refusal/defection).
    voice_profile: speech patterns, vocabulary register, verbal tics.
    active_wounds: unresolved traumas that color perception and reaction.
    """

    core_belief: str = ""
    moral_taboos: list[str] = Field(default_factory=list)
    voice_profile: str = ""
    active_wounds: list[str] = Field(default_factory=list)


class Goal(BaseModel):
    """A persistent goal that drives character behavior.

    description: what the character wants.
    priority: higher = more urgent (drives activation_score in TurnManager).
    status: active / suspended / achieved / abandoned.
    """

    description: str
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    status: str = "active"


class AgentConfig(BaseModel):
    """Per-agent runtime configuration."""

    memory_budget_tokens: int = 2000
    activation_strategy: str = "round_robin"
    self_response_enabled: bool = True
    bias_strings: list[str] = Field(default_factory=list)


class AmphoreusExtension(BaseModel):
    """Backward-compatible bridge to the existing CharacterProfile fields.

    Populated by the CharacterProfile -> CharacterCard converter so Classic
    Mode data isn't lost when a character enters Agent Mode.
    """

    role: str = "supporting"
    appearance: str = ""
    personality: Personality = Field(default_factory=Personality)
    core_desire: str = ""
    deep_fear: str = ""
    voice_sample: str = ""
    secrets: list[str] = Field(default_factory=list)
    knowledge_scope: list[str] = Field(default_factory=list)
    arc_stage: str = "introduction"
    public_profile: str = ""
    hidden_profile: str = ""
    reveal_chapter: int | None = None


class CharacterCard(BaseModel):
    """The authoritative identity for a character agent.

    Merges SillyTavern V2 (description, personality, scenario, first_mes,
    mes_example) + PlotPilot psychology (core_belief, moral_taboos,
    voice_profile, active_wounds) + Amphoreus goals/agent_config.

    content_rating (decision #5): G / PG / R — injected into the agent's
    system prompt for self-constraint.
    """

    id: str
    name: str
    description: str = ""
    personality: str = ""

    scenario: str = ""
    first_mes: str = ""
    mes_example: str = ""

    psychology: Psychology = Field(default_factory=Psychology)
    goals: list[Goal] = Field(default_factory=list)

    content_rating: str = "PG"

    agent_config: AgentConfig = Field(default_factory=AgentConfig)

    extensions: AmphoreusExtension = Field(default_factory=AmphoreusExtension)

    creator_notes: str = ""
