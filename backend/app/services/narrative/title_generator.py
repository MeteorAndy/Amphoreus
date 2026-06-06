"""Title generator — produces 3-5 novel/screenplay title candidates via LLM."""

from __future__ import annotations

import json

from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.plot_architect import PlotOutline

from .prompts import _get_title_prompt


class TitleGenerator:
    """Generates 3-5 novel/screenplay title candidates via LLM.

    ZH mode: Chinese titles (金庸/古龙/网络文学风格).
    EN mode: English titles (literary/suspense/direct).
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def generate_titles(
        self,
        world_summary: str,
        characters: list[CharacterProfile],
        plot_outline: PlotOutline | None = None,
    ) -> list[str]:
        """Call LLM and return 3-5 title candidates.

        If plot_outline is None, title generation uses only world and character info.
        """
        char_json = json.dumps(
            [
                {"name": c.name, "role": c.role, "core_desire": c.core_desire, "deep_fear": c.deep_fear}
                for c in characters
            ],
            indent=2,
            ensure_ascii=False,
        )

        outline_text = ""
        if plot_outline:
            parts: list[str] = []
            for act in plot_outline.acts:
                parts.append(f"{act.name}: {act.description}")
                for scene in act.scenes:
                    parts.append(f"  - {scene.title}: {scene.conflict}")
            outline_text = "\n".join(parts)

        user_content = (
            f"World summary:\n{world_summary}\n\n"
            f"Characters:\n{char_json}\n\n"
            f"Plot outline:\n{outline_text if outline_text else '(not provided)'}\n\n"
            "Generate 3-5 title candidates."
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_title_prompt()},
            {"role": "user", "content": user_content},
        ]

        result = await self._llm.chat_json(messages, temperature=0.8)
        if isinstance(result, list):
            return [str(item) for item in result]
        for val in result.values():
            if isinstance(val, list):
                return [str(item) for item in val]
        return [str(result)]
