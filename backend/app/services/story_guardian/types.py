from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.models.character import CharacterProfile
from app.services.relationship_builder import Relationship


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"


class Verdict(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    WARNING = "warning"


@dataclass
class GuardianIssue:
    severity: Severity
    dimension: str
    description: str
    suggestion: str
    # T3-⑤ OOC-vs-Breakout tag (report-only; verdict never changes). Defaults to
    # UNCLASSIFIED so existing behavior is unchanged unless classification runs.
    deviation_kind: str = "UNCLASSIFIED"


@dataclass
class GuardianResult:
    verdict: Verdict
    issues: list[GuardianIssue]
    can_override: bool


@dataclass
class EvaluationContext:
    proposed_plot: str
    characters: list[CharacterProfile] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    world_rules: list[dict[str, Any]] = field(default_factory=list)
    recent_scenes: list[str] = field(default_factory=list)
    character_arcs: dict[str, list[str]] = field(default_factory=dict)
