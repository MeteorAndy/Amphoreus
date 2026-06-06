"""Canon adjudicator — mints authoritative facts before writing begins.

A novel run and a screenplay run happen separately and each fabricate their own
answers wherever the source material is silent (verified: page numbers, parentage,
fates appear 0 times in archives/outline). This stage runs one low-temperature LLM
adjudication over the same source material the writers see, locking those
load-bearing facts into a CanonicalFacts object that both runs then obey.
"""

from __future__ import annotations

from typing import Any

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient, LLMError
from app.models.character import CharacterProfile
from app.services.plot_architect import PlotOutline
from app.services.scene_engine.resolution import SceneArchive

from .prompts import _get_canon_adjudicator_prompt
from .types import CanonicalFact, CanonicalFacts, OpenConflict

_LEGAL_SCOPES = ("all", "novel", "screenplay")


class CanonAdjudicator:
    """Generates a CanonicalFacts lock from the pre-writing source material."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def adjudicate(
        self,
        archives: list[SceneArchive],
        outline: PlotOutline | None,
        characters: list[CharacterProfile],
        world_summary: str = "",
        session_id: str = "",
    ) -> CanonicalFacts:
        """Run one adjudication pass. Degrades to empty facts on LLM/parse failure
        so a single bad response never crashes the pipeline — writers then run
        unconstrained (their prior behaviour)."""
        material = self._build_material(archives, outline, characters, world_summary)
        system = _get_canon_adjudicator_prompt(list(_LEGAL_SCOPES))
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": material},
        ]
        try:
            data = await self._llm.chat_json(messages, temperature=0.2)
        except LLMError:
            return CanonicalFacts(session_id=session_id, lang=get_lang().value)
        return self._parse(data, session_id)

    @staticmethod
    def _build_material(
        archives: list[SceneArchive],
        outline: PlotOutline | None,
        characters: list[CharacterProfile],
        world_summary: str,
    ) -> str:
        """Render the same source the writers see, condensed for adjudication."""
        is_zh = get_lang() == Lang.ZH
        parts: list[str] = []

        if world_summary.strip():
            parts.append(("## 世界观\n" if is_zh else "## World\n") + world_summary.strip())

        if characters:
            parts.append("## 角色" if is_zh else "## Characters")
            for c in characters:
                desc = getattr(c, "description", "") or getattr(c, "backstory", "")
                parts.append(f"- {c.name}: {desc}".rstrip(": "))

        if outline is not None:
            arcs = getattr(outline, "character_arcs", {}) or {}
            if arcs:
                parts.append("## 角色弧线" if is_zh else "## Character arcs")
                for cid, beats in arcs.items():
                    joined = " / ".join(beats) if isinstance(beats, list) else str(beats)
                    parts.append(f"- {cid}: {joined}")

        parts.append("## 场景日志" if is_zh else "## Scene logs")
        for a in archives:
            parts.append(f"### {a.scene_id}")
            env = getattr(a, "final_environment", None)
            if env is not None and getattr(env, "atmosphere", ""):
                parts.append((f"氛围：{env.atmosphere}" if is_zh else f"Atmosphere: {env.atmosphere}"))
            for entry in getattr(a, "rounds", []):
                bits: list[str] = [entry.actor_name]
                if entry.dialogue:
                    bits.append(f'"{entry.dialogue}"')
                if entry.action:
                    bits.append(f"[{entry.action}]")
                if entry.inner_thought:
                    bits.append(f"({entry.inner_thought})")
                parts.append(" ".join(bits))

        return "\n".join(parts)

    @staticmethod
    def _parse(data: dict[str, Any], session_id: str) -> CanonicalFacts:
        """Validate the LLM JSON into CanonicalFacts.

        Defensive: bad rows are dropped, illegal scope coerced to "all", and
        facts with an empty canonical answer demoted to unresolved rather than
        injected as an empty (and therefore useless) constraint.
        """
        facts: list[CanonicalFact] = []
        unresolved: list[OpenConflict] = []

        raw_facts = data.get("facts") if isinstance(data, dict) else None
        for i, row in enumerate(raw_facts or []):
            if not isinstance(row, dict):
                continue
            topic = str(row.get("topic", "")).strip()
            zh = str(row.get("canonical_answer_zh", "")).strip()
            en = str(row.get("canonical_answer_en", "")).strip()
            question = str(row.get("question", "")).strip()
            if not topic:
                continue
            if not zh and not en:
                # No usable ruling — surface as unresolved instead of dropping.
                unresolved.append(OpenConflict(topic=topic, question=question))
                continue
            scope = str(row.get("scope", "all")).strip().lower()
            if scope not in _LEGAL_SCOPES:
                scope = "all"
            rejected = row.get("rejected_answers") or []
            if not isinstance(rejected, list):
                rejected = [str(rejected)]
            facts.append(CanonicalFact(
                id=f"{topic}-{i + 1}",
                topic=topic,
                question=question,
                canonical_answer_zh=zh or en,
                canonical_answer_en=en or zh,
                rejected_answers=[str(r).strip() for r in rejected if str(r).strip()],
                scope=scope,
                rationale=str(row.get("rationale", "")).strip(),
            ))

        raw_unres = data.get("unresolved") if isinstance(data, dict) else None
        for row in raw_unres or []:
            if not isinstance(row, dict):
                continue
            topic = str(row.get("topic", "")).strip()
            if not topic:
                continue
            cands = row.get("candidates") or []
            if not isinstance(cands, list):
                cands = [str(cands)]
            unresolved.append(OpenConflict(
                topic=topic,
                question=str(row.get("question", "")).strip(),
                candidates=[str(c).strip() for c in cands if str(c).strip()],
            ))

        return CanonicalFacts(
            facts=facts,
            unresolved=unresolved,
            session_id=session_id,
            lang=get_lang().value,
        )
