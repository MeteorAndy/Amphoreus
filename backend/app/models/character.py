from __future__ import annotations

from pydantic import BaseModel, Field


class Big5(BaseModel):
    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)


class Personality(BaseModel):
    big5: Big5 = Field(default_factory=Big5)
    mbti: str = ""
    core_traits: list[str] = Field(default_factory=list)
    emotional_pattern: str = ""


class CharacterProfile(BaseModel):
    id: str
    name: str
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
    created_at: str = ""
    updated_at: str = ""
