"""Data types for narrative writing — shared across all writers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WritingOptions:
    """Configuration for the narrative conversion process."""

    format: str  # "novel" or "screenplay"
    narrative_voice: str = "third_person_limited"
    enhance: bool = False
    chapter_title: str | None = None


@dataclass
class WrittenOutput:
    """Result of a narrative conversion."""

    content: str
    format: str
    word_count: int
    scene_count: int
    title: str = ""
    title_candidates: list[str] = field(default_factory=list)
    export_formats: list[str] = field(default_factory=list)


@dataclass
class ChapterSpec:
    """One chapter in a chapter plan."""

    number: int
    title: str
    scene_ids: list[str]
    summary: str


@dataclass
class ChapterPlan:
    """Complete chapter plan — groups scenes into chapters."""

    chapters: list[ChapterSpec] = field(default_factory=list)

    @property
    def is_short_story(self) -> bool:
        total = sum(len(c.scene_ids) for c in self.chapters)
        return total < 3
