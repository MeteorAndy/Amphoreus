"""Backward compatibility shim — delegates to narrative/ package."""
from app.services.narrative import (
    WritingOptions, WrittenOutput, ChapterSpec, ChapterPlan,
    TitleGenerator, ChapterPlanner, PostProcessor,
    NovelWriter, ScreenplayWriter, NarrativeWriter,
    scan, ClicheReport, ClicheHit, verify, CanonReport,
)

__all__ = [
    "WritingOptions", "WrittenOutput", "ChapterSpec", "ChapterPlan",
    "TitleGenerator", "ChapterPlanner", "PostProcessor",
    "NovelWriter", "ScreenplayWriter", "NarrativeWriter",
    "scan", "ClicheReport", "ClicheHit", "verify", "CanonReport",
]
