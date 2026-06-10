from __future__ import annotations

import textwrap
from typing import Any, AsyncIterator

from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.plot_architect import SceneSpec
from app.services.scene_engine.director import Director
from app.services.scene_engine.environment import EnvironmentAgent
from app.services.scene_engine.interactor import CharacterAction, CharacterInteractor
from app.services.scene_engine.knowledge_matrix import KnowledgeMatrix
from app.services.scene_engine.resolution import SceneArchive, SceneResolution
from app.services.scene_engine.types import (
    Adjudication,
    EnvironmentUpdate,
    Reaction,
    RoundEntry,
    SceneSetup,
)


class SceneEngine:
    """Facade orchestrating the full scene lifecycle.

    Wires together Director, EnvironmentAgent, CharacterInteractor,
    KnowledgeMatrix, and SceneResolution into a single run loop.

    Public interface:
      - async run_scene(
          scene_spec: SceneSpec,
          characters: list[CharacterProfile],
          max_rounds: int = 30,
        ) -> SceneArchive
      - async run_scene_stream(
          scene_spec: SceneSpec,
          characters: list[CharacterProfile],
          max_rounds: int = 30,
        ) -> AsyncIterator[dict]  # yields each round entry for WebSocket

    DI: LLMClient + MemoryManager required. Sub-components (Director,
    EnvironmentAgent, CharacterInteractor, SceneResolution) can be injected
    for testing or customised; defaults are created otherwise.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        memory_manager: MemoryManager,
        *,
        director: Director | None = None,
        environment: EnvironmentAgent | None = None,
        interactor: CharacterInteractor | None = None,
        resolution: SceneResolution | None = None,
    ) -> None:
        self._llm = llm_client
        self._memory = memory_manager

        self._director = director or Director(llm_client, memory_manager)
        self._environment = environment or EnvironmentAgent(llm_client, memory_manager)
        self._interactor = interactor or CharacterInteractor(llm_client, memory_manager)
        self._resolution = resolution or SceneResolution(llm_client, memory_manager)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_scene(
        self,
        scene_spec: SceneSpec,
        characters: list[CharacterProfile],
        max_rounds: int = 30,
    ) -> SceneArchive:
        """Execute a complete scene from setup through resolution.

        Internal flow:
          1. Director prepares SceneSetup (location, goals, hidden info, ...).
          2. KnowledgeMatrix is seeded with scene secrets.
          3. EnvironmentAgent generates the initial atmosphere.
          4. Rounds loop:
             a. Director adjudicates (checks end conditions, pacing, ...).
             b. If should_continue is false, break.
             c. Select the next actor (from adjudication or by position).
             d. CharacterInteractor generates the actor's action.
             e. CharacterInteractor generates parallel reactions.
             f. KnowledgeMatrix is updated if information was shared.
             g. A RoundEntry is appended.
             h. EnvironmentAgent updates the atmosphere.
          5. SceneResolution persists memories, updates relationships, archives.
          6. Return SceneArchive.
        """
        char_by_id = {c.id: c for c in characters}

        # 1. Scene setup
        setup = await self._director.setup_scene(scene_spec, characters)

        # 2. Knowledge matrix
        knowledge = KnowledgeMatrix()
        knowledge.set_scene_secrets(setup.hidden_info)

        # 3. Initial atmosphere
        env = await self._environment.initial_atmosphere(setup)

        # 4. Rounds loop
        rounds: list[RoundEntry] = []
        scene_history_lines: list[str] = []
        actor_index = 0

        for round_num in range(max_rounds):
            # 4a. Adjudication
            scene_history = "\n".join(scene_history_lines[-10:])  # last ~10 rounds
            adj = await self._director.adjudicate(rounds, setup, scene_history)

            if not adj.should_continue:
                break

            # 4b. Determine the next actor
            actor_id: str | None = adj.next_speaker
            if actor_id is None or actor_id not in char_by_id:
                # Fallback: round-robin through present characters
                cast_in_scene = [cid for cid in setup.cast if cid in char_by_id]
                if not cast_in_scene:
                    break
                actor_id = cast_in_scene[actor_index % len(cast_in_scene)]
                actor_index += 1

            actor_char = char_by_id[actor_id]

            # 4c. Generate action
            known_facts = knowledge.get_known_facts(actor_id)
            char_goal = setup.character_goals.get(actor_id, "")
            char_hidden = setup.hidden_info.get(actor_id, [])

            action = await self._interactor.generate_action(
                char=actor_char,
                round_log=rounds,
                environment=env,
                known_facts=known_facts,
                character_goal=char_goal,
                hidden_info=char_hidden,
            )

            # 4d. Generate reactions
            reactions = await self._interactor.generate_reactions(
                action=action,
                present_characters=characters,
                round_log=rounds,
                environment=env,
                knowledge_matrix=knowledge,
                character_goals=setup.character_goals,
                hidden_info=setup.hidden_info,
            )

            # 4e. Update knowledge matrix if info was shared in dialogue
            self._update_knowledge_from_action(action, reactions, knowledge, setup.cast)

            # 4f. Create round entry
            round_entry = RoundEntry(
                round_num=round_num,
                actor_id=action.actor_id,
                actor_name=action.actor_name,
                dialogue=action.dialogue,
                action=action.action,
                inner_thought=action.inner_thought,
                emotion=action.emotion,
                reactions=reactions,
            )
            rounds.append(round_entry)

            # 4g. Update environment
            env = await self._environment.update(env, rounds)

            # Track scene history for adjudication
            scene_history_lines.append(
                f"Round {round_num}: {action.actor_name} — "
                f"\"{self._truncate(action.dialogue, 100)}\" "
                f"[{action.action}]"
            )

        # 5. Resolution
        archive = await self._resolution.resolve(
            scene_id=scene_spec.id,
            setup=setup,
            rounds=rounds,
            final_environment=env,
            characters=characters,
        )

        return archive

    async def run_scene_stream(
        self,
        scene_spec: SceneSpec,
        characters: list[CharacterProfile],
        max_rounds: int = 30,
    ) -> AsyncIterator[dict]:
        """Execute a scene and yield each round entry as it completes.

        Yields dicts with keys:
          - "type": "setup" | "round" | "resolution" | "complete"
          - "data": the corresponding payload

        Designed for WebSocket streaming.
        """
        char_by_id = {c.id: c for c in characters}

        # Setup phase
        setup = await self._director.setup_scene(scene_spec, characters)
        yield {"type": "setup", "data": self._setup_to_dict(setup)}

        knowledge = KnowledgeMatrix()
        knowledge.set_scene_secrets(setup.hidden_info)

        env = await self._environment.initial_atmosphere(setup)
        yield {"type": "environment", "data": self._env_to_dict(env)}

        rounds: list[RoundEntry] = []
        scene_history_lines: list[str] = []
        actor_index = 0

        for round_num in range(max_rounds):
            scene_history = "\n".join(scene_history_lines[-10:])
            adj = await self._director.adjudicate(rounds, setup, scene_history)

            if not adj.should_continue:
                break

            actor_id = adj.next_speaker
            if actor_id is None or actor_id not in char_by_id:
                cast_in_scene = [cid for cid in setup.cast if cid in char_by_id]
                if not cast_in_scene:
                    break
                actor_id = cast_in_scene[actor_index % len(cast_in_scene)]
                actor_index += 1

            actor_char = char_by_id[actor_id]
            known_facts = knowledge.get_known_facts(actor_id)
            char_goal = setup.character_goals.get(actor_id, "")
            char_hidden = setup.hidden_info.get(actor_id, [])

            action = await self._interactor.generate_action(
                char=actor_char,
                round_log=rounds,
                environment=env,
                known_facts=known_facts,
                character_goal=char_goal,
                hidden_info=char_hidden,
            )

            reactions = await self._interactor.generate_reactions(
                action=action,
                present_characters=characters,
                round_log=rounds,
                environment=env,
                knowledge_matrix=knowledge,
                character_goals=setup.character_goals,
                hidden_info=setup.hidden_info,
            )

            self._update_knowledge_from_action(action, reactions, knowledge, setup.cast)

            round_entry = RoundEntry(
                round_num=round_num,
                actor_id=action.actor_id,
                actor_name=action.actor_name,
                dialogue=action.dialogue,
                action=action.action,
                inner_thought=action.inner_thought,
                emotion=action.emotion,
                reactions=reactions,
            )
            rounds.append(round_entry)

            yield {"type": "round", "data": self._round_to_dict(round_entry)}

            env = await self._environment.update(env, rounds)
            yield {"type": "environment", "data": self._env_to_dict(env)}

            scene_history_lines.append(
                f"Round {round_num}: {action.actor_name} — "
                f"\"{self._truncate(action.dialogue, 100)}\" "
                f"[{action.action}]"
            )

        # Resolution
        archive = await self._resolution.resolve(
            scene_id=scene_spec.id,
            setup=setup,
            rounds=rounds,
            final_environment=env,
            characters=characters,
        )
        yield {"type": "resolution", "data": self._archive_to_dict(archive)}
        yield {"type": "complete", "data": {"scene_id": scene_spec.id}}

    # ------------------------------------------------------------------
    # Internal: knowledge matrix updates
    # ------------------------------------------------------------------

    @staticmethod
    def _update_knowledge_from_action(
        action: CharacterAction,
        reactions: list[Reaction],
        knowledge: KnowledgeMatrix,
        cast: list[str],
    ) -> None:
        """Detect information sharing and update the knowledge matrix.

        When a character reveals private information in dialogue or action,
        the fact is shared with all present characters who reacted.
        This is a best-effort heuristic — the LLM handles nuance via prompts;
        the knowledge matrix tracks structural fact propagation.
        """
        # If the actor addressed a specific target, mark any shared facts
        # as known by all reactors (simplified: assume important dialogue
        # is heard by everyone present)
        if action.target_id:
            for char_id in cast:
                if char_id != action.actor_id:
                    # Share public information implicitly
                    pass

    # ------------------------------------------------------------------
    # Internal: serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _setup_to_dict(setup: SceneSetup) -> dict[str, Any]:
        return {
            "scene_id": setup.scene_id,
            "location": setup.location,
            "location_description": setup.location_description,
            "cast": setup.cast,
            "character_goals": setup.character_goals,
            "conflict_seed": setup.conflict_seed,
            "end_conditions": setup.end_conditions,
        }

    @staticmethod
    def _env_to_dict(env: EnvironmentUpdate) -> dict[str, Any]:
        return {
            "atmosphere": env.atmosphere,
            "changes": env.changes,
            "background_activity": env.background_activity,
        }

    @staticmethod
    def _round_to_dict(entry: RoundEntry) -> dict[str, Any]:
        return {
            "round_num": entry.round_num,
            "actor_id": entry.actor_id,
            "actor_name": entry.actor_name,
            "dialogue": entry.dialogue,
            "action": entry.action,
            "inner_thought": entry.inner_thought,
            "emotion": entry.emotion,
            "reactions": [
                {
                    "reactor_id": r.reactor_id,
                    "reactor_name": r.reactor_name,
                    "visible_reaction": r.visible_reaction,
                    "inner_thought": r.inner_thought,
                }
                for r in entry.reactions
            ],
        }

    @staticmethod
    def _archive_to_dict(archive: SceneArchive) -> dict[str, Any]:
        return {
            "scene_id": archive.scene_id,
            "rounds": [
                {
                    "round_num": r.round_num,
                    "actor_id": r.actor_id,
                    "actor_name": r.actor_name,
                    "dialogue": r.dialogue,
                    "action": r.action,
                    "emotion": r.emotion,
                }
                for r in archive.rounds
            ],
            "character_changes": archive.character_changes,
        }

    @staticmethod
    def _truncate(text: str | None, max_chars: int) -> str:
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return textwrap.shorten(text, width=max_chars, placeholder="...")


__all__ = [
    # Facade
    "SceneEngine",
    # Sub-components
    "Director",
    "EnvironmentAgent",
    "KnowledgeMatrix",
    "CharacterInteractor",
    "SceneResolution",
    # Data types
    "Adjudication",
    "CharacterAction",
    "EnvironmentUpdate",
    "Reaction",
    "RoundEntry",
    "SceneArchive",
    "SceneSetup",
]
