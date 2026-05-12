from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager


@dataclass
class WorldState:
    rules: list[dict[str, Any]] = field(default_factory=list)
    locations: list[dict[str, Any]] = field(default_factory=list)
    factions: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    completeness: float = 0.0


@dataclass
class WorldBuilderSession:
    session_id: str
    stage: str  # rules | locations | factions | timeline | done
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    extracted_data: WorldState = field(default_factory=WorldState)
    next_question: str = ""


_SYSTEM_PROMPT = """\
You are a creative world-building assistant for a story engine. \
Your goal is to help the user build a rich, detailed world through a guided conversation.

Progress through these stages in order:
1. RULES — The fundamental rules, physics, magic systems, or constraints of the world
2. LOCATIONS — Key places in the world
3. FACTIONS — Groups, organizations, cultures, or political entities
4. TIMELINE — Historical events and eras

Rules for the conversation:
- Ask ONE focused question at a time.
- Move to the next stage only when you have enough information (minimum 2–3 items per stage).
- Extract structured data from each user response.

Respond in the following JSON format only:
{
  "stage": "rules" | "locations" | "factions" | "timeline" | "done",
  "next_question": "your single focused question to the user",
  "extracted": {
    "rules": [{"name": "...", "category": "...", "description": "...", "l0": "...", "l1": "..."}],
    "locations": [{"name": "...", "type": "...", "description": "...", "l0": "...", "l1": "..."}],
    "factions": [{"name": "...", "type": "...", "description": "...", "l0": "...", "l1": "..."}],
    "timeline": [{"name": "...", "era": "...", "description": "...", "l0": "...", "l1": "..."}]
  },
  "completeness": 0.0–1.0
}
"""


class WorldBuilder:
    """Conversational world building through LLM-guided dialogue.

    Walks the user through structured world creation stages:
    rules -> locations -> factions -> timeline -> done.

    Session state persists in OpenViking under ``world/sessions/{session_id}/``.
    """

    def __init__(self, llm_client: LLMClient, memory_manager: MemoryManager) -> None:
        self._llm = llm_client
        self._ov = memory_manager.openviking

    async def start_new_world(self, seed_idea: str) -> WorldBuilderSession:
        """Begin a new world-building conversation from a seed idea."""
        session_id = str(uuid.uuid4())
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Seed idea: {seed_idea}\n\n"
                    "Start by asking me a focused question to begin building the world. "
                    "Begin with the RULES stage."
                ),
            },
        ]

        result = await self._llm.chat_json(messages)
        stage = result.get("stage", "rules")
        next_question = result.get("next_question", "")
        extracted_data = _parse_extracted(result.get("extracted", {}))
        extracted_data.completeness = result.get("completeness", 0.0)

        session = WorldBuilderSession(
            session_id=session_id,
            stage=stage,
            conversation_history=messages + [{"role": "assistant", "content": next_question}],
            extracted_data=extracted_data,
            next_question=next_question,
        )
        self._save_session(session)
        return session

    async def continue_session(
        self, session_id: str, user_input: str
    ) -> WorldBuilderSession:
        """Continue an existing session with the user's latest response."""
        session = self._load_session(session_id)
        session.conversation_history.append({"role": "user", "content": user_input})

        result = await self._llm.chat_json(session.conversation_history)
        stage = result.get("stage", session.stage)
        next_question = result.get("next_question", "")

        extracted = result.get("extracted", {})
        merged = _merge_extracted(session.extracted_data, extracted)
        merged.completeness = result.get("completeness", session.extracted_data.completeness)

        session.stage = stage
        session.next_question = next_question
        session.extracted_data = merged
        session.conversation_history.append({"role": "assistant", "content": next_question})

        self._save_session(session)
        return session

    async def get_session(self, session_id: str) -> WorldBuilderSession:
        """Load a session without calling the LLM (read-only)."""
        return self._load_session(session_id)

    async def finalize_world(self, session_id: str) -> WorldState:
        """Return the accumulated WorldState for a completed session."""
        session = self._load_session(session_id)
        return session.extracted_data

    # ---- persistence helpers ----

    def _session_path(self, session_id: str) -> str:
        return f"world/sessions/{session_id}/state"

    def _save_session(self, session: WorldBuilderSession) -> None:
        data = {
            "session_id": session.session_id,
            "stage": session.stage,
            "conversation_history": session.conversation_history,
            "extracted_data": {
                "rules": session.extracted_data.rules,
                "locations": session.extracted_data.locations,
                "factions": session.extracted_data.factions,
                "timeline": session.extracted_data.timeline,
                "completeness": session.extracted_data.completeness,
            },
            "next_question": session.next_question,
        }
        self._ov.write_entry(
            self._session_path(session.session_id),
            json.dumps(data, ensure_ascii=False),
            l0="world",
            l1=f"session-{session.session_id}",
        )

    def _load_session(self, session_id: str) -> WorldBuilderSession:
        entry = self._ov.read_entry(self._session_path(session_id))
        data = json.loads(entry.l2)
        extracted = data.get("extracted_data", {})
        return WorldBuilderSession(
            session_id=data["session_id"],
            stage=data["stage"],
            conversation_history=data.get("conversation_history", []),
            extracted_data=WorldState(
                rules=extracted.get("rules", []),
                locations=extracted.get("locations", []),
                factions=extracted.get("factions", []),
                timeline=extracted.get("timeline", []),
                completeness=extracted.get("completeness", 0.0),
            ),
            next_question=data.get("next_question", ""),
        )


# ---- module-level helpers (to keep the class focused on orchestration) ----


def _parse_extracted(extracted: dict[str, Any]) -> WorldState:
    return WorldState(
        rules=extracted.get("rules", []),
        locations=extracted.get("locations", []),
        factions=extracted.get("factions", []),
        timeline=extracted.get("timeline", []),
    )


def _merge_extracted(current: WorldState, new_data: dict[str, Any]) -> WorldState:
    for key in ("rules", "locations", "factions", "timeline"):
        existing = getattr(current, key)
        seen_names = {e.get("name") for e in existing if e.get("name")}
        for item in new_data.get(key, []):
            if item.get("name") and item["name"] not in seen_names:
                existing.append(item)
                seen_names.add(item["name"])
    return current
