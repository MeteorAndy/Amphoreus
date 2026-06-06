"""Narrative writing package — converts scene logs to novel or screenplay format.

Public API:
  - WritingOptions, WrittenOutput, ChapterSpec, ChapterPlan
  - TitleGenerator, ChapterPlanner, PostProcessor
  - NovelWriter, ScreenplayWriter, NarrativeWriter
"""

from .types import WritingOptions, WrittenOutput, ChapterSpec, ChapterPlan
from .types import CanonicalFacts, CanonicalFact, OpenConflict
from .title_generator import TitleGenerator
from .chapter_planner import ChapterPlanner
from .post_processor import PostProcessor
from .novel_writer import NovelWriter
from .screenplay_writer import ScreenplayWriter
from .writer import NarrativeWriter
from .canon_adjudicator import CanonAdjudicator
from .cliche_scanner import scan, ClicheReport, ClicheHit
from .canon_verifier import verify, CanonReport, Violation

__all__ = [
    "WritingOptions", "WrittenOutput", "ChapterSpec", "ChapterPlan",
    "CanonicalFacts", "CanonicalFact", "OpenConflict",
    "TitleGenerator", "ChapterPlanner", "PostProcessor",
    "NovelWriter", "ScreenplayWriter", "NarrativeWriter",
    "CanonAdjudicator",
    "scan", "ClicheReport", "ClicheHit",
    "verify", "CanonReport", "Violation",
]
