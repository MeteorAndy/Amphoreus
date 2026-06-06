"""Chapter planner — maps scenes to chapters using LLM."""

from __future__ import annotations

import json
from typing import Any

from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.plot_architect import PlotOutline

from .prompts import _get_chapter_plan_prompt
from .types import ChapterSpec, ChapterPlan


class ChapterPlanner:
    """Plans scene-to-chapter mapping using LLM.

    Output: ChapterPlan with ChapterSpec entries describing grouping, titles,
    and summaries. Word count targeting per the spec.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def plan_chapters(
        self,
        plot_outline: PlotOutline,
        characters: list[CharacterProfile],
    ) -> ChapterPlan:
        """Build a chapter plan from the plot outline and character profiles."""
        scenes_json = json.dumps(
            [
                {
                    "id": s.id,
                    "title": s.title,
                    "location": s.location,
                    "conflict": s.conflict,
                    "goal": s.goal,
                    "cast": s.cast,
                }
                for act in plot_outline.acts
                for s in act.scenes
            ],
            indent=2,
            ensure_ascii=False,
        )

        char_json = json.dumps(
            [{"name": c.name, "role": c.role, "core_desire": c.core_desire} for c in characters],
            indent=2,
            ensure_ascii=False,
        )

        user_content = (
            f"Scene list:\n{scenes_json}\n\n"
            f"Characters:\n{char_json}\n\n"
            "Plan the chapter structure."
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_chapter_plan_prompt()},
            {"role": "user", "content": user_content},
        ]

        result = await self._llm.chat_json(messages, temperature=0.5)
        raw_chapters: list[dict[str, Any]] = result.get("chapters", [])
        chapters = [
            ChapterSpec(
                number=ch.get("number", i + 1),
                title=ch.get("title", ""),
                scene_ids=list(ch.get("scene_ids", [])),
                summary=ch.get("summary", ""),
            )
            for i, ch in enumerate(raw_chapters)
        ]
        return ChapterPlan(chapters=chapters)
