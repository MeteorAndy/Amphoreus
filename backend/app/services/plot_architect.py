from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.world_builder import WorldState


class NarrativeStructure(str, Enum):
    THREE_ACT = "three_act"
    HERO_JOURNEY = "hero_journey"
    SAVE_THE_CAT = "save_the_cat"
    QI_CHENG_ZHUAN_HE = "qi_cheng_zhuan_he"


@dataclass
class SceneSpec:
    id: str
    title: str
    location: str
    cast: list[str]
    conflict: str
    goal: str
    expected_outcome: str
    causal_chain: list[str] = field(default_factory=list)


@dataclass
class Act:
    name: str
    description: str
    scenes: list[SceneSpec] = field(default_factory=list)


@dataclass
class PlotOutline:
    structure: NarrativeStructure
    acts: list[Act] = field(default_factory=list)
    character_arcs: dict[str, list[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Narrative structure templates
# ---------------------------------------------------------------------------

_STRUCTURE_TEMPLATES: dict[NarrativeStructure, str] = {
    NarrativeStructure.THREE_ACT: (
        "Three-Act Structure: Setup (25%) — Establish the world, characters, and "
        "central conflict. Confrontation (50%) — Rising stakes, obstacles, and midpoint "
        "reversal. Resolution (25%) — Climax and aftermath."
    ),
    NarrativeStructure.HERO_JOURNEY: (
        "Hero's Journey (12 steps): Ordinary World → Call to Adventure → Refusal of "
        "the Call → Meeting the Mentor → Crossing the Threshold → Tests, Allies, Enemies "
        "→ Approach to the Inmost Cave → Ordeal → Reward → The Road Back → Resurrection "
        "→ Return with the Elixir."
    ),
    NarrativeStructure.SAVE_THE_CAT: (
        "Save the Cat (15 beats): Opening Image → Theme Stated → Set-Up → Catalyst → "
        "Debate → Break into Two → B Story → Fun and Games → Midpoint → Bad Guys Close "
        "In → All Is Lost → Dark Night of the Soul → Break into Three → Finale → "
        "Final Image."
    ),
    NarrativeStructure.QI_CHENG_ZHUAN_HE: (
        "Qi Cheng Zhuan He (4 parts): 起 (Qi/Introduction) — Establish characters and "
        "setting. 承 (Cheng/Development) — Build the conflict and develop relationships. "
        "转 (Zhuan/Twist) — Unexpected turn or reversal that raises stakes. "
        "合 (He/Resolution) — Convergence and resolution of all threads."
    ),
}

_PLOT_SYSTEM_PROMPT = """\
You are a master plot architect for a story engine. Given a world state, character \
profiles, and a narrative structure template, generate a complete plot outline.

Rules:
1. Fill the template with concrete scenes based on character conflicts and world elements.
2. Each scene MUST have a clear dramatic purpose — no filler scenes.
3. Every scene must include a specific conflict, a goal, and an expected outcome.
4. Character arcs MUST show progression through the scenes — each character should \
change or be challenged across the arc.
5. Scenes should have causal chains — each scene builds on or reacts to prior scenes.
6. Assign locations from the world state where possible.
7. Cast only characters that have a meaningful role in each scene.

The story should feel organic, driven by character desires and world constraints, not \
just a mechanical filling of plot beats.

You MUST respond ONLY with valid JSON in this format:
{
  "acts": [
    {
      "name": "Act 1: ...",
      "description": "Overview of this act's purpose",
      "scenes": [
        {
          "id": "scene_1",
          "title": "Scene title",
          "location": "Where it happens",
          "cast": ["character_id_1", "character_id_2"],
          "conflict": "The dramatic conflict",
          "goal": "What this scene accomplishes",
          "expected_outcome": "How the scene resolves",
          "causal_chain": []
        }
      ]
    }
  ],
  "character_arcs": {
    "character_id": ["arc milestone 1", "arc milestone 2"]
  }
}"""

_REFINE_SYSTEM_PROMPT = """\
You are a plot editor. Given an existing plot outline and user feedback, revise the \
outline to address the feedback while preserving the core narrative. You may reorder \
scenes, rewrite scene details, adjust character arcs, or change act descriptions.

Preserve all scene IDs so existing references remain valid.

You MUST respond ONLY with valid JSON in the same format as the original outline:
{
  "acts": [...],
  "character_arcs": {...}
}"""

_CHECK_SYSTEM_PROMPT = """\
You are a plot consistency checker. Given a plot outline and a specific scene, analyze \
whether the scene is consistent with all character arcs across the outline.

Consider:
1. Does each character's arc progression logically lead into and out of this scene?
2. Does this scene contradict any established character trait, desire, or fear?
3. Does the scene's causal chain connect properly to prerequisite scenes?
4. Does the emotional/logical outcome match character trajectories?

You MUST respond ONLY with valid JSON in this format:
{
  "consistent": true or false,
  "issues": ["Description of issue 1", "Description of issue 2"],
  "suggested_fixes": ["Fix for issue 1", "Fix for issue 2"]
}"""


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
    ) -> PlotOutline:
        """Generate a complete plot outline from world state and characters."""
        prompt = self._build_generation_prompt(world, characters, structure)
        result = await self._llm.chat_json(prompt)
        return self._parse_outline(result, structure)

    async def refine_plot(
        self, outline: PlotOutline, feedback: str
    ) -> PlotOutline:
        """Revise an existing outline using LLM with user feedback."""
        prompt = self._build_refinement_prompt(outline, feedback)
        result = await self._llm.chat_json(prompt)
        return self._parse_outline(result, outline.structure)

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
        return {k.value: v for k, v in _STRUCTURE_TEMPLATES.items()}

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

        template_desc = _STRUCTURE_TEMPLATES.get(structure, "")

        return [
            {"role": "system", "content": _PLOT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Narrative structure: {structure.value}\n\n"
                    f"Template description:\n{template_desc}\n\n"
                    f"World state:\n{world_desc}\n\n"
                    f"Characters:\n{char_json}\n\n"
                    f"Generate a complete plot outline using the {structure.value} structure."
                ),
            },
        ]

    def _build_refinement_prompt(
        self, outline: PlotOutline, feedback: str
    ) -> list[dict[str, str]]:
        outline_json = json.dumps(
            self._outline_to_dict(outline), indent=2, ensure_ascii=False
        )
        return [
            {"role": "system", "content": _REFINE_SYSTEM_PROMPT},
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
            {"role": "system", "content": _CHECK_SYSTEM_PROMPT},
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
