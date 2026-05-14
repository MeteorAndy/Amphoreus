from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI
from openviking.pyagfs import RAGFSBindingClient
from openviking.pyagfs.exceptions import AGFSMountPointExistsError

from app.core.config import Settings

_VOLCENGINE_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
_SCOPES = ("world", "chars", "story")
_OV_CONF_FILENAME = "ov.conf"


@dataclass
class VikingEntry:
    l0: str
    l1: str
    l2: str
    path: str
    updated_at: str = ""


@dataclass
class SearchResult:
    path: str
    l0: str
    score: float


class OpenVikingStore:
    """Manages world/chars/story data in OpenViking's file-system paradigm."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._root: Path = settings.data_dir / "openviking"
        self._storage_dir: Path = self._root / "agfs_data"
        self._conf_path: Path = self._root / _OV_CONF_FILENAME
        self._client: RAGFSBindingClient | None = None
        self._initialized: bool = False

    # ── Schema ─────────────────────────────────────────────────

    def ensure_schema(self) -> None:
        """Create the ov.conf, mount localfs, and create scope directories."""
        if self._initialized:
            return

        self._root.mkdir(parents=True, exist_ok=True)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._write_config()
        self._client = RAGFSBindingClient(config_path=str(self._conf_path))
        self._mount_localfs()
        for scope in _SCOPES:
            self._agfs_mkdir(f"/{scope}")
        self._initialized = True

    # ── CRUD ───────────────────────────────────────────────────

    def write_entry(self, path: str, content: str, *, l0: str, l1: str) -> None:
        """Create or overwrite an entry.

        The *path* is a relative path within the store (e.g. ``world/valley``).
        """
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "l0": l0,
            "l1": l1,
            "l2": content,
            "path": path,
            "updated_at": now,
        }
        self._agfs_write(self._agfs_path(path), json.dumps(entry, ensure_ascii=False).encode("utf-8"))

    def read_entry(self, path: str) -> VikingEntry:
        """Read a single entry by its store-relative path."""
        raw = self._agfs_read(self._agfs_path(path))
        data = json.loads(raw.decode("utf-8"))
        return VikingEntry(
            l0=data["l0"],
            l1=data["l1"],
            l2=data["l2"],
            path=data["path"],
            updated_at=data.get("updated_at", ""),
        )

    def update_entry(
        self, path: str, content: str, *, l0: str | None = None, l1: str | None = None
    ) -> None:
        """Update an existing entry, replacing l2 content and optionally l0/l1."""
        current = self.read_entry(path)
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "l0": current.l0 if l0 is None else l0,
            "l1": current.l1 if l1 is None else l1,
            "l2": content,
            "path": current.path,
            "updated_at": now,
        }
        self._agfs_write(self._agfs_path(path), json.dumps(entry, ensure_ascii=False).encode("utf-8"))

    def delete_entry(self, path: str) -> None:
        """Delete an entry by its store-relative path."""
        agfs_path = self._agfs_path(path)
        try:
            self._client.rm(agfs_path)  # type: ignore[union-attr]
        except Exception:
            pass  # idempotent

    # ── Search ─────────────────────────────────────────────────

    def search(self, query: str, *, scope: str = "all") -> list[SearchResult]:
        """Text-based search across entries.

        Supports ``scope``: ``"all"``, ``"world"``, ``"chars"``, ``"story"``.
        """
        directories = _SCOPES if scope == "all" else (scope,)
        results: list[SearchResult] = []
        q = query.lower()

        for directory in directories:
            entries = self._list_entries(f"/{directory}")
            for e in entries:
                data = e["data"]
                l0 = data.get("l0", "")
                l1 = data.get("l1", "")
                l2 = data.get("l2", "")

                score = self._match_score(q, l0, l1, l2)
                if score > 0.0:
                    results.append(
                        SearchResult(
                            path=e["rel_path"],
                            l0=l0,
                            score=score,
                        )
                    )

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    # ── Tier generation (LLM) ──────────────────────────────────

    def generate_tiers(self, content: str) -> tuple[str, str]:
        """Use Volcengine VLM to generate L0 (title) and L1 (overview) from L2 content."""
        client = OpenAI(
            api_key=self._settings.volcengine_api_key_effective,
            base_url=_VOLCENGINE_BASE_URL,
        )
        resp = client.chat.completions.create(
            model=self._settings.volcengine_vlm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a story analyst. Given the following story content, "
                        "generate:\n"
                        "- L0: a concise title or abstract (max 100 characters)\n"
                        "- L1: a one-paragraph overview (max 500 characters)\n"
                        "Respond ONLY with valid JSON: {\"l0\": \"...\", \"l1\": \"...\"}"
                    ),
                },
                {"role": "user", "content": content},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        text = resp.choices[0].message.content or '{"l0": "", "l1": ""}'
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return ("", text[:100])
        return (parsed.get("l0", ""), parsed.get("l1", ""))

    # ── Internal helpers ───────────────────────────────────────

    def _write_config(self) -> None:
        """Write a minimal AGFS config if one does not already exist."""
        if self._conf_path.exists():
            return
        config = {
            "storage": {
                "agfs": {"backend": "local", "path": str(self._root)},
                "vectordb": {"backend": "local", "path": str(self._root)},
            }
        }
        self._conf_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    def _mount_localfs(self) -> None:
        """Mount a local filesystem backend at the AGFS root."""
        existing = {m["path"] for m in self._client.mounts()}  # type: ignore[union-attr]
        if "/" in existing:
            return
        try:
            self._client.mount("localfs", "/", {"local_dir": str(self._storage_dir)})  # type: ignore[union-attr]
        except AGFSMountPointExistsError:
            pass

    def _agfs_mkdir(self, agfs_path: str) -> None:
        """Create a directory, ignoring AlreadyExists errors."""
        try:
            self._client.mkdir(agfs_path)  # type: ignore[union-attr]
        except Exception:
            pass

    def _agfs_path(self, rel_path: str) -> str:
        """Convert a store-relative path to an AGFS path, always suffixed with .json."""
        return f"/{rel_path}.json"

    def _agfs_write(self, agfs_path: str, data: bytes) -> None:
        """Write bytes to AGFS, auto-creating parent directories."""
        parts = agfs_path.strip("/").split("/")
        for i in range(1, len(parts)):
            parent = "/" + "/".join(parts[:i])
            self._agfs_mkdir(parent)
        self._client.write(agfs_path, data)  # type: ignore[union-attr]

    def _agfs_read(self, agfs_path: str) -> bytes:
        """Read bytes from AGFS."""
        raw = self._client.read(agfs_path)  # type: ignore[union-attr]
        if isinstance(raw, str):
            return raw.encode("utf-8")
        return raw

    def _list_entries(self, agfs_dir: str) -> list[dict[str, Any]]:
        """Return list of {rel_path, data} for each .json entry under *agfs_dir*."""
        entries: list[dict[str, Any]] = []
        try:
            items = self._client.ls(agfs_dir)  # type: ignore[union-attr]
        except Exception:
            return entries

        for item in items:
            name: str = item.get("name", "")
            if not name.endswith(".json"):
                continue
            if item.get("isDir", False):
                continue
            agfs_path = f"{agfs_dir}/{name}"
            try:
                raw = self._agfs_read(agfs_path)
            except Exception:
                continue
            try:
                data = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            entries.append({"rel_path": agfs_path.lstrip("/").removesuffix(".json"), "data": data})

        return entries

    @staticmethod
    def _match_score(q: str, l0: str, l1: str, l2: str) -> float:
        """Return a relevance score for *q* against the three tier texts."""
        if not q:
            return 0.0
        score = 0.0
        if q in l0.lower():
            score = 1.0
        elif q in l1.lower():
            score = 0.8
        elif q in l2.lower():
            score = 0.5
        # Boost score when the query appears in multiple tiers
        tier_count = sum(1 for t in (l0.lower(), l1.lower(), l2.lower()) if q in t)
        score += 0.15 * (tier_count - 1) if tier_count > 1 else 0.0
        return score
