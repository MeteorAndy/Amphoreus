"""Unified world-constraint formatter (T1-⑥).

Single source of truth that turns a `WorldState` into a compact, bilingual
constraint block for injection into writing prompts. Empty sections are
omitted so the prompt never carries dead weight. Separates hard rules
(taboos / physical laws) from soft atmosphere hints so a future token-budget
allocator can route them into different tiers.

Pure function — zero LLM, stateless.
"""

from __future__ import annotations

from app.core.i18n import get_lang, Lang
from app.services.world_builder import WorldState


def build_contract_block(world: WorldState, target: str = "all") -> str:
    """Render the world contract as a compact bilingual prompt-constraint block.

    ``target``: "all" (novel + screenplay), "novel", or "screenplay".

    Returns "" when the world is empty (no rules, no locations, no factions,
    no timeline) — callers inject nothing extra.
    """
    if not _has_content(world):
        return ""
    is_zh = get_lang() == Lang.ZH
    sections: list[str] = []

    _append_rules(sections, world, is_zh)
    _append_locations(sections, world, is_zh)
    _append_factions(sections, world, is_zh)
    _append_timeline(sections, world, is_zh)
    _append_tone(sections, world, is_zh)

    if not sections:
        return ""
    if is_zh:
        header = "## 世界观约束\n以下是故事世界的核心设定，写作时不得违背："
    else:
        header = "## World Constraints\nThe following are the story's core world rules — do not contradict them:"
    return header + "\n" + "".join(sections)


def _has_content(w: WorldState) -> bool:
    return bool(w.rules or w.locations or w.factions or w.timeline)


def _append_rules(lines: list[str], w: WorldState, is_zh: bool) -> None:
    if not w.rules:
        return
    if is_zh:
        lines.append("\n### 世界法则\n")
    else:
        lines.append("\n### World Rules\n")
    for r in w.rules:
        name = r.get("name", "")
        desc = r.get("description", "") or r.get("l1", "")
        if name:
            lines.append(f"- {name}：{desc}" if is_zh else f"- {name}: {desc}")


def _append_locations(lines: list[str], w: WorldState, is_zh: bool) -> None:
    items = [l for l in w.locations if l.get("name")]
    if not items:
        return
    if is_zh:
        lines.append("\n### 关键地点\n")
    else:
        lines.append("\n### Key Locations\n")
    for l in items[:8]:
        name = l.get("name", "")
        loc_type = l.get("type", "")
        desc = l.get("description", "") or loc_type
        if is_zh:
            lines.append(f"- {name}（{loc_type}）：{desc}" if loc_type else f"- {name}：{desc}")
        else:
            lines.append(f"- {name} ({loc_type}): {desc}" if loc_type else f"- {name}: {desc}")


def _append_factions(lines: list[str], w: WorldState, is_zh: bool) -> None:
    items = [f for f in w.factions if f.get("name")]
    if not items:
        return
    if is_zh:
        lines.append("\n### 势力\n")
    else:
        lines.append("\n### Factions\n")
    for f in items[:5]:
        name = f.get("name", "")
        desc = f.get("description", "")
        if is_zh:
            lines.append(f"- {name}：{desc}" if desc else f"- {name}")
        else:
            lines.append(f"- {name}: {desc}" if desc else f"- {name}")


def _append_timeline(lines: list[str], w: WorldState, is_zh: bool) -> None:
    items = [t for t in w.timeline if t.get("name") or t.get("event")]
    if not items:
        return
    if is_zh:
        lines.append("\n### 时间线\n")
    else:
        lines.append("\n### Timeline\n")
    for t in items[:5]:
        name = t.get("name") or t.get("event", "")
        era = t.get("era", "")
        if is_zh:
            lines.append(f"- {era}：{name}" if era else f"- {name}")
        else:
            lines.append(f"- {era}: {name}" if era else f"- {name}")


def _append_tone(lines: list[str], w: WorldState, is_zh: bool) -> None:
    """Derive lightweight tone hints from the overall world state.

    Not a hard constraint — a soft atmosphere guide for the writers."""
    if not _has_content(w):
        return
    hints: list[str] = []
    faction_count = len(w.factions)
    timeline_count = len(w.timeline)
    rule_count = len(w.rules)
    if faction_count >= 3:
        hints.append("政治/派系" if is_zh else "politically layered")
    if timeline_count >= 2:
        hints.append("历史跨度" if is_zh else "deep history")
    if rule_count >= 5:
        hints.append("法则密集" if is_zh else "rule-dense")

    if not hints:
        return
    if is_zh:
        lines.append("\n### 氛围基调\n" + "、".join(hints) + "的世界。\n")
    else:
        lines.append("\n### Tone\nA " + ", ".join(hints) + " world.\n")
