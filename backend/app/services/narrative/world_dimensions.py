"""Deterministic 5-dimension worldbuilding view (T2-③).

A pure, zero-LLM classifier that buckets the EXISTING extracted world items
(rules / locations / factions / timeline) into five named dimensions — physical,
social, economic, cultural, metaphysical — modeled on PlotPilot. It is an
ADDITIVE, curated SUBSET view: nothing is removed from the flat WorldState lists,
no consumer of those lists changes, and the LLM extraction conversation is
untouched. The result is stored on ``WorldState.dimensions`` and rendered as an
opt-in section by ``world_contract``.

Assignment is first-match-wins over a fixed walk order (most-specific dimension
first, so e.g. a "magic system" rule is not swept into "physical" by a generic
"law" hit). An item matching nothing is omitted from dimensions (it remains in
its flat list). Factions default to "social" unless a more-specific dimension
matches — factions are social entities by definition.
"""

from __future__ import annotations

from typing import Any

from app.services.world_builder import WorldState

# Walk order: most-specific dimension first so a magic rule is not swept into a
# generic physical/social bucket by a loose keyword.
_DIMENSIONS = ("metaphysical", "economic", "cultural", "social", "physical")

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "metaphysical": (
        "magic", "metaphysical", "cosmolog", "divine", "deity", "supernatural",
        "soul", "afterlife", "fate", "creation", "myth", "genesis",
        "魔法", "灵力", "神祇", "神明", "神圣", "创世", "命运", "超自然",
    ),
    "economic": (
        "econom", "trade", "currency", "resource", "commerc", "market",
        "merchant", "guild", "port", "mine", "farm",
        "经济", "商会", "贸易", "货币", "市场", "港口", "矿", "农场",
    ),
    "cultural": (
        "religion", "culture", "belief", "language", "art", "custom",
        "tradition", "temple", "shrine", "academy", "theater", "monument",
        "tribe", "clan", "sect",
        "文化", "信仰", "宗教", "神殿", "庙", "部落", "宗族", "教派", "学院", "剧场",
    ),
    "social": (
        "politic", "government", "social", "hierarchy", "power", "authorit",
        "council", "kingdom", "empire", "military", "senate", "court",
        "政治", "议会", "王", "帝国", "军", "朝廷",
    ),
    "physical": (
        "physic", "natural law", "nature", "biolog", "technolog", "geograph",
        "climate", "terrain", "city", "town", "village", "region", "landform",
        "sea", "mountain", "forest", "building", "structure", "ruin", "lab",
        "station",
        "物理", "地理", "气候", "地形", "城", "镇", "村", "山", "海", "森林", "建筑", "遗迹",
    ),
}

DIMENSION_LABELS_ZH = {
    "metaphysical": "形而上学", "economic": "经济", "cultural": "文化",
    "social": "社会", "physical": "物理",
}
DIMENSION_LABELS_EN = {
    "metaphysical": "Metaphysical", "economic": "Economic", "cultural": "Cultural",
    "social": "Social", "physical": "Physical",
}


def _item_text(item: dict[str, Any], source: str) -> str:
    """Lowercased classification signal: name + description + the typed field
    the LLM emits per source (category for rules, type for locations/factions,
    era for timeline)."""
    parts = [str(item.get("name", "")), str(item.get("description", ""))]
    if source == "rules":
        parts.append(str(item.get("category", "")))
    elif source in ("locations", "factions"):
        parts.append(str(item.get("type", "")))
    elif source == "timeline":
        parts.append(str(item.get("era", "")))
    return " ".join(parts).lower()


def classify_item(item: dict[str, Any], source: str) -> str | None:
    """Return the dimension for one item, or None if it matches none.

    Factions default to 'social' (they are social entities by definition) unless
    a more-specific dimension matches first."""
    text = _item_text(item, source)
    for dim in _DIMENSIONS:
        if any(kw in text for kw in _KEYWORDS[dim]):
            return dim
    return "social" if source == "factions" else None


def derive_dimensions(world: WorldState) -> dict[str, list[dict[str, Any]]]:
    """Bucket every extracted item into at most one dimension.

    Returns only non-empty buckets. Items are shallow-copied and tagged with
    ``_source`` / ``_src_name`` for traceability; the flat lists on ``world`` are
    never mutated. Pure and idempotent."""
    buckets: dict[str, list[dict[str, Any]]] = {dim: [] for dim in _DIMENSIONS}
    sources = (
        ("rules", world.rules),
        ("locations", world.locations),
        ("factions", world.factions),
        ("timeline", world.timeline),
    )
    for source, items in sources:
        for item in items:
            if not isinstance(item, dict):
                continue
            dim = classify_item(item, source)
            if dim is None:
                continue
            tagged = dict(item)
            tagged["_source"] = source
            tagged["_src_name"] = str(item.get("name", ""))
            buckets[dim].append(tagged)
    return {dim: items for dim, items in buckets.items() if items}
