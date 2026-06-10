"""Persistent narrative-debt ledger.

The ledger normalizes post-write diagnostics into one durable list of open
story obligations: unresolved props, dangling reader questions, canon issues,
and planted foreshadowing threads.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from .foreshadowing import ForeshadowingRegistry
from .types import WrittenOutput

_VALID_STATUS = {"OPEN", "RESOLVED", "ABANDONED"}
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class NarrativeDebtItem:
    """One unresolved or previously resolved story obligation."""

    id: str
    kind: str
    description: str
    severity: str
    status: str
    source: str
    introduced_in_chapter: int | None = None
    evidence: str = ""

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATUS:
            raise ValueError(f"unknown narrative debt status: {self.status!r}")
        if self.severity not in _SEVERITY_RANK:
            raise ValueError(f"unknown narrative debt severity: {self.severity!r}")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "NarrativeDebtItem":
        return cls(
            id=data["id"],
            kind=data["kind"],
            description=data.get("description", ""),
            severity=data.get("severity", "medium"),
            status=data.get("status", "OPEN"),
            source=data.get("source", ""),
            introduced_in_chapter=data.get("introduced_in_chapter"),
            evidence=data.get("evidence", ""),
        )


@dataclass(frozen=True)
class NarrativeDebtLedger:
    """Durable collection of narrative debt items."""

    items: list[NarrativeDebtItem] = field(default_factory=list)
    schema_version: int = 1

    @property
    def open_items(self) -> list[NarrativeDebtItem]:
        return [item for item in self.items if item.status == "OPEN"]

    @property
    def open_count(self) -> int:
        return len(self.open_items)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "open_count": self.open_count,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NarrativeDebtLedger":
        return cls(
            items=[
                NarrativeDebtItem.from_dict(item)
                for item in data.get("items", [])
                if isinstance(item, dict)
            ],
            schema_version=int(data.get("schema_version", 1)),
        )


def build_narrative_debt_ledger(
    output: WrittenOutput,
    *,
    prior: NarrativeDebtLedger | None = None,
    foreshadowing_registry: ForeshadowingRegistry | None = None,
) -> NarrativeDebtLedger:
    """Build a ledger from available post-write reports.

    When a prior ledger is supplied, open debts from sources observed in the
    current output are marked RESOLVED if they no longer appear.
    """
    items_by_id = {item.id: item for item in prior.items} if prior else {}
    current = _items_from_output(output, foreshadowing_registry)
    current_ids = {item.id for item in current}
    seen_sources = _seen_sources(output, foreshadowing_registry)

    for item_id, item in list(items_by_id.items()):
        if (
            item.status == "OPEN"
            and item.source in seen_sources
            and item_id not in current_ids
        ):
            items_by_id[item_id] = dataclasses.replace(item, status="RESOLVED")

    for item in current:
        items_by_id[item.id] = item

    return NarrativeDebtLedger(items=sorted(items_by_id.values(), key=_sort_key))


def _items_from_output(
    output: WrittenOutput,
    foreshadowing_registry: ForeshadowingRegistry | None,
) -> list[NarrativeDebtItem]:
    items: list[NarrativeDebtItem] = []

    if output.prop_lifecycle_report is not None:
        for prop in output.prop_lifecycle_report.props:
            if prop.status != "UNRESOLVED":
                continue
            items.append(
                NarrativeDebtItem(
                    id=f"prop:{prop.object_name}",
                    kind="prop_unresolved",
                    description=f"Unresolved prop: {prop.object_name}",
                    severity="medium",
                    status="OPEN",
                    source="prop_lifecycle",
                    introduced_in_chapter=prop.introduced_in_chapter,
                )
            )

    if output.reader_sim_report is not None:
        for thread in output.reader_sim_report.dangling_threads:
            items.append(
                NarrativeDebtItem(
                    id=f"reader:{thread.introduced_chapter}:{thread.question}",
                    kind="reader_dangling",
                    description=f"Dangling reader question: {thread.question}",
                    severity=_severity(thread.severity),
                    status="OPEN",
                    source="reader_sim",
                    introduced_in_chapter=thread.introduced_chapter,
                )
            )

    if output.canon_report is not None:
        for violation in output.canon_report.violations:
            items.append(
                NarrativeDebtItem(
                    id=f"canon:{violation.fact_id}:{violation.kind}",
                    kind=f"canon_{violation.kind}",
                    description=f"Canon {violation.kind}: {violation.topic}",
                    severity=_severity(violation.severity),
                    status="OPEN",
                    source="canon_verifier",
                    evidence=violation.evidence,
                )
            )

    if foreshadowing_registry is not None:
        for thread in foreshadowing_registry.get_unresolved():
            items.append(
                NarrativeDebtItem(
                    id=f"foreshadowing:{thread.id}",
                    kind="foreshadowing_open",
                    description=thread.description,
                    severity=_importance_to_severity(thread.importance),
                    status="OPEN",
                    source="foreshadowing_registry",
                    introduced_in_chapter=thread.planted_in_chapter,
                )
            )

    return items


def _seen_sources(
    output: WrittenOutput,
    foreshadowing_registry: ForeshadowingRegistry | None,
) -> set[str]:
    sources: set[str] = set()
    if output.prop_lifecycle_report is not None:
        sources.add("prop_lifecycle")
    if output.reader_sim_report is not None:
        sources.add("reader_sim")
    if output.canon_report is not None:
        sources.add("canon_verifier")
    if foreshadowing_registry is not None:
        sources.add("foreshadowing_registry")
    return sources


def _severity(value: str) -> str:
    lowered = value.lower()
    return lowered if lowered in _SEVERITY_RANK else "medium"


def _importance_to_severity(importance: str) -> str:
    if importance in ("HIGH", "CRITICAL"):
        return "high"
    if importance == "LOW":
        return "low"
    return "medium"


def _sort_key(item: NarrativeDebtItem) -> tuple[int, str, int, str]:
    return (
        0 if item.status == "OPEN" else 1,
        item.source,
        -_SEVERITY_RANK[item.severity],
        item.id,
    )
