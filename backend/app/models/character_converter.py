"""Bidirectional converter: CharacterProfile <-> CharacterCard.

Classic Mode uses CharacterProfile (existing pipeline). Agent Mode uses
CharacterCard (new agent system). This converter bridges the two so a
character created in Classic Mode can enter Agent Mode without data loss,
and vice versa (decision #8: Classic -> Agent is the supported direction).

Design: CharacterProfile -> CharacterCard is lossless (all fields preserved
in .extensions.amphoreus). CharacterCard -> CharacterProfile is lossy
(psychology/goals/agent_config/scenario have no CharacterProfile equivalent).
"""

from __future__ import annotations

from app.models.character import CharacterProfile, Personality
from app.models.character_card import (
    AmphoreusExtension,
    CharacterCard,
    Goal,
    Psychology,
)


def profile_to_card(profile: CharacterProfile) -> CharacterCard:
    """Convert a Classic Mode CharacterProfile to an Agent Mode CharacterCard.

    Lossless: every CharacterProfile field is preserved in .extensions.
    Derives goals from core_desire/deep_fear and psychology from personality.
    """
    goals: list[Goal] = []
    if profile.core_desire:
        goals.append(Goal(description=profile.core_desire, priority=0.8))
    if profile.deep_fear:
        goals.append(Goal(
            description=f"避免：{profile.deep_fear}", priority=0.6,
        ))

    personality_text = "、".join(profile.personality.core_traits) if profile.personality.core_traits else ""
    if profile.personality.emotional_pattern:
        personality_text += f"（{profile.personality.emotional_pattern}）"

    return CharacterCard(
        id=profile.id,
        name=profile.name,
        description=profile.public_profile or profile.appearance,
        personality=personality_text,
        first_mes="",
        mes_example=profile.voice_sample,
        psychology=Psychology(
            core_belief=profile.core_desire,
            voice_profile=profile.voice_sample,
        ),
        goals=goals,
        extensions=AmphoreusExtension(
            role=profile.role,
            appearance=profile.appearance,
            personality=profile.personality,
            core_desire=profile.core_desire,
            deep_fear=profile.deep_fear,
            voice_sample=profile.voice_sample,
            secrets=profile.secrets,
            knowledge_scope=profile.knowledge_scope,
            arc_stage=profile.arc_stage,
            public_profile=profile.public_profile,
            hidden_profile=profile.hidden_profile,
            reveal_chapter=profile.reveal_chapter,
        ),
    )


def card_to_profile(card: CharacterCard) -> CharacterProfile:
    """Convert an Agent Mode CharacterCard back to a Classic Mode CharacterProfile.

    Lossy: psychology/goals/agent_config/scenario/mes_example have no
    CharacterProfile equivalent and are dropped. Extensions fields are
    preserved. Useful for feeding agent-created characters back into
    Classic Mode (decision #8: reverse direction is Phase 5+).
    """
    ext = card.extensions
    return CharacterProfile(
        id=card.id,
        name=card.name,
        role=ext.role,
        appearance=ext.appearance or card.description,
        personality=ext.personality,
        core_desire=ext.core_desire or card.psychology.core_belief,
        deep_fear=ext.deep_fear,
        voice_sample=ext.voice_sample or card.psychology.voice_profile,
        secrets=ext.secrets,
        knowledge_scope=ext.knowledge_scope,
        arc_stage=ext.arc_stage,
        public_profile=ext.public_profile,
        hidden_profile=ext.hidden_profile,
        reveal_chapter=ext.reveal_chapter,
    )
