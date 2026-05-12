from __future__ import annotations


class KnowledgeMatrix:
    """Tracks who knows what in a scene.

    NOT an LLM agent — pure data structure. Maintains a truth table of
    character x fact booleans. Updated in-memory during scene execution
    when information is shared.
    """

    def __init__(self) -> None:
        # char_id -> set of fact_ids the character knows
        self._facts: dict[str, set[str]] = {}
        # fact_id -> set of char_ids who know it (derived, kept in sync)
        self._holders: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_scene_secrets(self, hidden_info: dict[str, list[str]]) -> None:
        """Seed the matrix with initial per-character hidden information.

        Each entry maps a character ID to a list of fact IDs that only
        that character initially knows.
        """
        self._facts.clear()
        self._holders.clear()

        for char_id, fact_ids in hidden_info.items():
            char_set = set(fact_ids)
            self._facts[char_id] = char_set
            for fid in char_set:
                if fid not in self._holders:
                    self._holders[fid] = set()
                self._holders[fid].add(char_id)

    def character_knows(self, char_id: str, fact_id: str) -> bool:
        """Return True if the character knows the given fact."""
        return char_id in self._facts and fact_id in self._facts[char_id]

    def reveal_fact(self, char_id: str, fact_id: str) -> None:
        """Record that a character has just learned a fact."""
        if char_id not in self._facts:
            self._facts[char_id] = set()
        self._facts[char_id].add(fact_id)

        if fact_id not in self._holders:
            self._holders[fact_id] = set()
        self._holders[fact_id].add(char_id)

    def get_known_facts(self, char_id: str) -> set[str]:
        """Return the set of all fact IDs the character currently knows."""
        return set(self._facts.get(char_id, set()))

    def get_unknowing_characters(self, fact_id: str) -> list[str]:
        """Return all characters who do NOT know the given fact."""
        knowers = self._holders.get(fact_id, set())
        return [cid for cid in self._facts if cid not in knowers]

    def known_by_all(self, fact_id: str) -> bool:
        """Return True if every tracked character knows the fact."""
        if not self._facts:
            return False
        knowers = self._holders.get(fact_id, set())
        return len(knowers) == len(self._facts)
