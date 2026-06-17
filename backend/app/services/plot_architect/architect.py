from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.world_builder import WorldState
from app.services.plot_architect.prompts import (
    _STRUCTURE_TEMPLATES_EN,
    _STRUCTURE_TEMPLATES_ZH,
    _get_check_prompt,
    _get_plot_prompt,
    _get_refine_prompt,
)
from app.services.plot_architect.structure_planner import plan, format_structure_directive
from app.services.plot_architect.types import (
    Act,
    NarrativeStructure,
    PlanningStatus,
    PlotOutline,
    SceneSpec,
    _coerce_source,
    _coerce_status,
)


class PlotArchitect:
    """Generates narrative structure from world + characters.

    Public interface:
      - async generate_plot(
          world: WorldState,
          characters: list[CharacterProfile],
          structure: NarrativeStructure = THREE_ACT
        ) -> PlotOutline
      - async refine_plot(outline: PlotOutline, feedback: str) -> PlotOutline
      - async generate_scene_specs(outline: PlotOutline) -> list[SceneSpec]
      - get_structure_templates() -> dict[str, str]
    """

    def __init__(self, llm_client: LLMClient, memory_manager: MemoryManager) -> None:
        self._llm = llm_client
        self._ov = memory_manager.openviking

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_plot(
        self,
        world: WorldState,
        characters: list[CharacterProfile],
        structure: NarrativeStructure = NarrativeStructure.THREE_ACT,
        target_chapters: int = 0,
    ) -> PlotOutline:
        """Generate a complete plot outline from world state and characters.

        When *target_chapters* > 3, a deterministic structure constraint is
        injected into the prompt so the LLM produces an outline at that scale.
        """
        prompt = self._build_generation_prompt(world, characters, structure,
                                               target_chapters)
        result = await self._llm.chat_json(prompt)
        return self._parse_outline(result, structure)

    async def refine_plot(
        self, outline: PlotOutline, feedback: str
    ) -> PlotOutline:
        """Revise an existing outline using LLM with user feedback.

        Nodes the user marked USER_EDITED are preserved verbatim (T3-①): the LLM
        may rewrite the rest, but a hand-edited scene/act is copied back from the
        pre-refine outline so user changes survive re-refinement."""
        prompt = self._build_refinement_prompt(outline, feedback)
        result = await self._llm.chat_json(prompt)
        refined = self._parse_outline(result, outline.structure)
        return self._merge_user_edited(outline, refined)

    @staticmethod
    def _merge_user_edited(
        before: PlotOutline, after: PlotOutline
    ) -> PlotOutline:
        """Copy USER_EDITED acts/scenes from `before` over `after` (by name/id).

        Pure: builds a fresh outline so neither input is mutated. Nodes not
        marked USER_EDITED pass through unchanged (current behavior)."""
        edited_scenes = {
            s.id: s
            for a in before.acts
            for s in a.scenes
            if s.planning_status == PlanningStatus.USER_EDITED
        }
        edited_acts = {
            a.name: a
            for a in before.acts
            if a.planning_status == PlanningStatus.USER_EDITED
        }

        new_acts: list[Act] = []
        for act in after.acts:
            if act.name in edited_acts:
                new_acts.append(edited_acts[act.name])
                continue
            scenes = [
                edited_scenes.get(s.id, s) if s.id in edited_scenes else s
                for s in act.scenes
            ]
            # preserve scene order; replace edited ones in place
            scenes = [edited_scenes.get(s.id, s) for s in act.scenes]
            new_acts.append(Act(
                name=act.name, description=act.description, scenes=scenes,
                planning_status=act.planning_status, source=act.source,
            ))
        return PlotOutline(
            structure=after.structure, acts=new_acts,
            character_arcs=after.character_arcs,
        )

    async def generate_scene_specs(
        self, outline: PlotOutline
    ) -> list[SceneSpec]:
        """Flatten all scenes from the outline into a single list."""
        scenes: list[SceneSpec] = []
        for act in outline.acts:
            scenes.extend(act.scenes)
        return scenes

    def get_structure_templates(self) -> dict[str, str]:
        """Return descriptions of each available narrative template."""
        templates = _STRUCTURE_TEMPLATES_ZH if get_lang() == Lang.ZH else _STRUCTURE_TEMPLATES_EN
        return {k.value: v for k, v in templates.items()}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _plot_path(self, plot_id: str) -> str:
        return f"story/plots/{plot_id}/outline"

    def _write_plot(self, plot_id: str, outline: PlotOutline) -> None:
        data = self._outline_to_dict(outline)
        content = json.dumps(data, ensure_ascii=False)
        self._ov.write_entry(
            self._plot_path(plot_id),
            content,
            l0="story",
            l1=f"plot-{plot_id}",
        )

    def save_plot(self, outline: PlotOutline) -> str:
        """Persist a new outline and return its plot ID."""
        plot_id = str(uuid.uuid4())
        self._write_plot(plot_id, outline)
        return plot_id

    def save_plot_with_id(self, plot_id: str, outline: PlotOutline) -> None:
        """Persist the outline under a specific plot ID (for updates)."""
        self._write_plot(plot_id, outline)

    def load_plot(self, plot_id: str) -> PlotOutline | None:
        """Load a plot outline by its ID."""
        try:
            entry = self._ov.read_entry(self._plot_path(plot_id))
        except Exception:
            return None
        try:
            data = json.loads(entry.l2)
        except (json.JSONDecodeError, TypeError):
            return None
        return self._dict_to_outline(data)

    def delete_plot(self, plot_id: str) -> None:
        """Remove a stored plot outline."""
        self._ov.delete_entry(self._plot_path(plot_id))

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_generation_prompt(
        self,
        world: WorldState,
        characters: list[CharacterProfile],
        structure: NarrativeStructure,
        target_chapters: int = 0,
    ) -> list[dict[str, str]]:
        world_desc = json.dumps(
            {
                "rules": world.rules,
                "locations": world.locations,
                "factions": world.factions,
                "timeline": world.timeline,
            },
            indent=2,
            ensure_ascii=False,
        )
        char_descs = [
            {
                "id": c.id,
                "name": c.name,
                "role": c.role,
                "core_desire": c.core_desire,
                "deep_fear": c.deep_fear,
                "arc_stage": c.arc_stage,
                "personality_traits": c.personality.core_traits,
            }
            for c in characters
        ]
        char_json = json.dumps(char_descs, indent=2, ensure_ascii=False)

        template_desc = _STRUCTURE_TEMPLATES_EN.get(structure, "")

        # Build the content string so we can optionally prepend a structure
        # constraint (zero-LLM, deterministic — T1-③).
        parts = [
            f"Narrative structure: {structure.value}\n",
            f"Template description:\n{template_desc}\n",
        ]
        if target_chapters > 3:
            params = plan(target_chapters, structure)
            zh = get_lang() == Lang.ZH
            parts.append(f"{format_structure_directive(params, zh)}\n")
        parts.extend([
            f"World state:\n{world_desc}\n",
            f"Characters:\n{char_json}\n",
            f"Generate a complete plot outline using the {structure.value} structure.",
        ])

        return [
            {"role": "system", "content": _get_plot_prompt()},
            {"role": "user", "content": "".join(parts)},
        ]

    def _build_refinement_prompt(
        self, outline: PlotOutline, feedback: str
    ) -> list[dict[str, str]]:
        outline_json = json.dumps(
            self._outline_to_dict(outline), indent=2, ensure_ascii=False
        )
        return [
            {"role": "system", "content": _get_refine_prompt()},
            {
                "role": "user",
                "content": (
                    f"Current outline:\n{outline_json}\n\n"
                    f"Feedback:\n{feedback}\n\n"
                    "Return the revised plot outline."
                ),
            },
        ]

    def _build_check_prompt(
        self, outline: PlotOutline, scene_id: str
    ) -> list[dict[str, str]]:
        outline_json = json.dumps(
            self._outline_to_dict(outline), indent=2, ensure_ascii=False
        )
        return [
            {"role": "system", "content": _get_check_prompt()},
            {
                "role": "user",
                "content": (
                    f"Plot outline:\n{outline_json}\n\n"
                    f"Scene to check: {scene_id}\n\n"
                    "Analyze scene consistency with all character arcs."
                ),
            },
        ]

    # ------------------------------------------------------------------
    # Parsing / serialization
    # ------------------------------------------------------------------

    def _parse_outline(
        self, data: dict[str, Any], structure: NarrativeStructure
    ) -> PlotOutline:
        raw_acts: list[dict[str, Any]] = data.get("acts", [])
        acts: list[Act] = []
        for raw in raw_acts:
            raw_scenes: list[dict[str, Any]] = raw.get("scenes", [])
            scenes = [SceneSpec(**s) for s in raw_scenes]
            acts.append(
                Act(
                    name=raw.get("name", ""),
                    description=raw.get("description", ""),
                    scenes=scenes,
                    planning_status=_coerce_status(raw.get("planning_status")),
                    source=_coerce_source(raw.get("source")),
                )
            )

        char_arcs: dict[str, list[str]] = {
            k: list(v) for k, v in data.get("character_arcs", {}).items()
        }

        return PlotOutline(
            structure=structure,
            acts=acts,
            character_arcs=char_arcs,
        )

    @staticmethod
    def _outline_to_dict(outline: PlotOutline) -> dict[str, Any]:
        return {
            "structure": outline.structure.value,
            "acts": [
                {
                    "name": a.name,
                    "description": a.description,
                    "planning_status": a.planning_status.value,
                    "source": a.source.value,
                    "scenes": [
                        {
                            "id": s.id,
                            "title": s.title,
                            "location": s.location,
                            "cast": s.cast,
                            "conflict": s.conflict,
                            "goal": s.goal,
                            "expected_outcome": s.expected_outcome,
                            "causal_chain": s.causal_chain,
                            "planning_status": s.planning_status.value,
                            "source": s.source.value,
                        }
                        for s in a.scenes
                    ],
                }
                for a in outline.acts
            ],
            "character_arcs": outline.character_arcs,
        }

    @staticmethod
    def _dict_to_outline(data: dict[str, Any]) -> PlotOutline:
        structure = NarrativeStructure(data.get("structure", "three_act"))
        raw_acts: list[dict[str, Any]] = data.get("acts", [])
        acts = [
            Act(
                name=a.get("name", ""),
                description=a.get("description", ""),
                scenes=[SceneSpec(**s) for s in a.get("scenes", [])],
                planning_status=_coerce_status(a.get("planning_status")),
                source=_coerce_source(a.get("source")),
            )
            for a in raw_acts
        ]
        char_arcs: dict[str, list[str]] = {
            k: list(v) for k, v in data.get("character_arcs", {}).items()
        }
        return PlotOutline(
            structure=structure,
            acts=acts,
            character_arcs=char_arcs,
        )
