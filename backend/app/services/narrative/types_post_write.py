"""Data types for the post-write fact-extraction channel (PR3).

An InferredTriple is a subject-predicate-object fact the LLM read back out of
finished prose. These are tagged source_type='chapter_inferred' to distinguish
them from pre-write adjudicated CanonicalFacts, and carry chapter provenance so
a chapter rewrite can invalidate exactly its own inferred facts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

# Node labels and edge schema that KuzuStore accepts (mirrors kuzu_store, kept
# local so this module never imports the store's privates). An edge is only
# written when (subject_type, object_type) matches the predicate's schema row.
_VALID_NODE_TYPES = ("Character", "Location", "Faction", "Event")
_EDGE_SCHEMA = {
    "RELATES_TO": ("Character", "Character"),
    "BELONGS_TO": ("Character", "Faction"),
    "LOCATED_AT": ("Character", "Location"),
    "CAUSED_BY": ("Event", "Event"),
}


@dataclass
class InferredTriple:
    """One fact extracted from prose, ready to persist to the knowledge graph."""

    subject: str
    predicate: str
    object_: str
    subject_type: str = "Event"
    object_type: str = "Event"
    source_type: str = "chapter_inferred"
    chapter_id: str = ""
    confidence: float = 0.9

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "InferredTriple":
        return cls(
            subject=data["subject"],
            predicate=data.get("predicate", ""),
            object_=data.get("object_", data.get("object", "")),
            subject_type=data.get("subject_type", "Event"),
            object_type=data.get("object_type", "Event"),
            source_type=data.get("source_type", "chapter_inferred"),
            chapter_id=data.get("chapter_id", ""),
            confidence=data.get("confidence", 0.9),
        )

    def edge_is_valid(self) -> bool:
        """True iff this triple's predicate + endpoint types form a legal edge."""
        return _EDGE_SCHEMA.get(self.predicate) == (self.subject_type, self.object_type)
