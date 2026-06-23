"""Fact checker — Tavily-backed real-world fact verification (T1-⑨).

The logic reviewer catches *reasonableness* failures; this module catches
*real-world factual* failures: a 1943 scene featuring an AK-47 (designed 1947,
fielded 1949), pre-1928 clinical use of penicillin, the wrong capital for a
country, anachronistic technology. These are not logic bugs (the prose is
internally coherent) and not canon bugs (the world is fictional) — they are
errors against the real world, which only web search can reliably catch.

Two-phase design, mirroring the project's cost discipline:

  Phase A (one LLM call): pre-filter. Reads the chapter and extracts ONLY
    checkable real-world factual claims — years, weapon/hardware models,
    historical figures, geography, medical/technical procedures — explicitly
    skipping pure fiction and world-specific lore. This bounds Tavily spend:
    a fully fictional chapter yields zero candidates and zero search calls.

  Phase B (N Tavily calls + one LLM call): verify. Runs one Tavily search per
    candidate, then asks the LLM once to classify each candidate as
    confirmed / contradiction / unverifiable against the pooled evidence.

Never fatal: no Tavily key => silent no-op (returns empty report, no LLM call);
any LLM/Tavily error degrades to an empty report or drops just the failing
check. Contradictions drive the revise loop; confirmed/unverifiable are notes.

Cost ceiling: `max_queries` caps Tavily calls per chapter (default 5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from app.core.llm_client import LLMError

if TYPE_CHECKING:
    from app.core.llm_client import LLMClient

logger = logging.getLogger(__name__)

Verdict = Literal["confirmed", "contradiction", "unverifiable"]
_DEFAULT_MAX_QUERIES = 5
_TAVILY_URL = "https://api.tavily.com/search"


@dataclass
class FactCandidate:
    """A single checkable real-world claim extracted from the prose."""
    claim: str       # the assertion as stated in the chapter
    location: str    # quoted excerpt anchoring it in the prose
    category: str    # 武器年代 / 医疗史 / 历史 / 地理 / 技术 ...
    query: str       # the Tavily search query


@dataclass
class FactCheck:
    """The verdict for one candidate after consulting Tavily."""
    claim: str
    query: str
    verdict: Verdict
    evidence: str    # the Tavily snippet that supports the verdict


@dataclass
class FactReport:
    candidates: list[FactCandidate] = field(default_factory=list)
    checks: list[FactCheck] = field(default_factory=list)

    @property
    def needs_rewrite(self) -> bool:
        """Only a confirmed contradiction blocks; unverifiable is a note."""
        return any(c.verdict == "contradiction" for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates": [
                {"claim": c.claim, "location": c.location,
                 "category": c.category, "query": c.query}
                for c in self.candidates
            ],
            "checks": [
                {"claim": c.claim, "query": c.query,
                 "verdict": c.verdict, "evidence": c.evidence}
                for c in self.checks
            ],
        }


class TavilyClient:
    """Minimal async Tavily search client (httpx, no SDK dependency).

    Returns the `answer` field (Tavily's LLM-synthesized answer) when present,
    else a concatenation of the top result snippets — whichever the verdict
    LLM can reason over. Raises on auth/network errors so the caller can drop
    just this check rather than abort the chapter.
    """

    def __init__(self, api_key: str, timeout: float = 20.0):
        self._key = api_key
        self._timeout = timeout

    async def search(self, query: str) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                _TAVILY_URL,
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 3,
                    "include_answer": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        answer = (data.get("answer") or "").strip()
        if answer:
            return answer
        results = data.get("results") or []
        return " ".join((r.get("content") or "").strip() for r in results[:3]).strip()


class FactChecker:
    """Two-phase real-world fact auditor. Never fatal."""

    def __init__(
        self,
        llm: "LLMClient",
        tavily: TavilyClient | None,
        *,
        has_key: bool = False,
    ):
        self._llm = llm
        self._tavily = tavily
        self._has_key = has_key

    async def check(
        self,
        *,
        chapter_text: str,
        world_summary: str,
        characters: list[Any],
        max_queries: int = _DEFAULT_MAX_QUERIES,
    ) -> FactReport:
        """Audit one chapter's real-world facts. Returns a report. Never raises."""
        # No key => silent no-op. Crucially do NOT call the LLM either: a user
        # who hasn't opted into web checking pays nothing.
        if not self._has_key or self._tavily is None:
            return FactReport()
        if not chapter_text.strip():
            return FactReport()

        # Phase A: extract checkable candidates.
        try:
            payload = await self._llm.chat_json(
                self._build_extract_messages(chapter_text, world_summary),
                temperature=0.1,
            )
        except LLMError as exc:
            logger.warning("fact_checker extraction LLM failed: %s", exc)
            return FactReport()
        except Exception as exc:
            logger.warning("fact_checker extraction error: %s", exc)
            return FactReport()

        candidates = _parse_candidates_payload(payload)[:max_queries]
        if not candidates:
            return FactReport(candidates=[])

        # Phase B: Tavily search per candidate, then one LLM verdict pass.
        evidence_map: dict[int, str] = {}  # candidate index -> raw evidence
        for i, cand in enumerate(candidates):
            try:
                evidence_map[i] = await self._tavily.search(cand.query)
            except Exception as exc:
                # Drop just this check; a single network failure must not abort
                # the chapter or poison other checks with a false contradiction.
                logger.warning("fact_checker tavily query failed (%s): %s", cand.query, exc)

        checks = await self._verdicts(candidates, evidence_map)
        return FactReport(candidates=candidates, checks=checks)

    # -- verdict synthesis (one LLM call over all evidence) ------------------

    async def _verdicts(
        self, candidates: list[FactCandidate], evidence_map: dict[int, str]
    ) -> list[FactCheck]:
        if not candidates:
            return []
        try:
            payload = await self._llm.chat_json(
                self._build_verdict_messages(candidates, evidence_map),
                temperature=0.1,
            )
        except Exception as exc:
            logger.warning("fact_checker verdict LLM failed: %s", exc)
            return []
        return _parse_verdicts_payload(payload, candidates, evidence_map)

    # -- prompts --------------------------------------------------------------

    def _build_extract_messages(self, chapter_text: str, world_summary: str) -> list[dict[str, str]]:
        world_block = world_summary.strip() or "（无世界观摘要）"
        return [
            {"role": "system", "content": _EXTRACT_PROMPT},
            {"role": "user", "content": (
                f"# 世界观（仅用于排除虚构设定，不要核查它）\n{world_block}\n\n"
                f"# 章节正文\n{chapter_text}\n\n"
                "请抽取可核查的现实世界事实断言，返回 JSON。"
            )},
        ]

    def _build_verdict_messages(
        self, candidates: list[FactCandidate], evidence_map: dict[int, str]
    ) -> list[dict[str, str]]:
        rows = []
        for i, c in enumerate(candidates):
            ev = evidence_map.get(i, "（无搜索结果）")
            rows.append(
                f"## 断言{i + 1}\n"
                f"原文声称：{c.claim}\n"
                f"分类：{c.category}\n"
                f"搜索证据：{ev}"
            )
        return [
            {"role": "system", "content": _VERDICT_PROMPT},
            {"role": "user", "content": "\n\n".join(rows) + "\n\n请返回 JSON。"},
        ]


# ---- parsing (pure, unit-tested) ------------------------------------------


def _parse_candidates_payload(payload: Any) -> list[FactCandidate]:
    """Coerce LLM payload (dict/JSON string) to candidates. Drops bad rows."""
    import json

    data = payload
    if isinstance(data, str):
        data = _extract_json_object(data)
        if data is None:
            return []
    if not isinstance(data, dict):
        return []
    raw = data.get("candidates")
    if not isinstance(raw, list):
        return []
    out: list[FactCandidate] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        claim = str(row.get("claim", "")).strip()
        location = str(row.get("location", "")).strip()
        category = str(row.get("category", "")).strip() or "事实"
        query = str(row.get("query", "")).strip()
        if not claim or not query:
            continue
        out.append(FactCandidate(claim=claim, location=location, category=category, query=query))
    return out


def _parse_verdicts_payload(
    payload: Any,
    candidates: list[FactCandidate],
    evidence_map: dict[int, str],
) -> list[FactCheck]:
    """Coerce verdict LLM payload to FactCheck list. Drops malformed rows."""
    data = payload
    if isinstance(data, str):
        data = _extract_json_object(data)
        if data is None:
            return []
    if not isinstance(data, dict):
        return []
    raw = data.get("verdicts")
    if not isinstance(raw, list):
        return []
    out: list[FactCheck] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        verdict = str(row.get("verdict", "")).strip().lower()
        if verdict not in ("confirmed", "contradiction", "unverifiable"):
            continue
        # Match back to a candidate by claim text (the LLM echoes it).
        claim = str(row.get("claim", "")).strip()
        cand = next((c for c in candidates if c.claim == claim), None)
        if cand is None:
            continue
        idx = candidates.index(cand)
        out.append(FactCheck(
            claim=claim,
            query=cand.query,
            verdict=verdict,  # type: ignore[arg-type]
            evidence=evidence_map.get(idx, ""),
        ))
    return out


def _extract_json_object(text: str) -> dict[str, Any] | None:
    import json
    import re

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace.group(0) if brace else None
    if not candidate:
        return None
    try:
        obj = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


# ---- prompts ---------------------------------------------------------------

_EXTRACT_PROMPT = """你是一名事实核查编辑。任务：从小说章节中抽取【可核查的现实世界事实断言】。

只抽取以下类型的断言（这些能用网络搜索验证）：
1. 武器/装备型号与其出现年代（如「AK-47」「F-16」出现的时期是否合理）
2. 医疗/科技程序的历史（如青霉素、麻醉、电力的使用年代）
3. 历史人物、事件、年代（如某年某战役、某人生卒）
4. 地理常识（国家首都、山河走向、气候带）
5. 物理/化学/生物常识（物质的性质、反应条件）

明确【不要】抽取的：
- 纯虚构的设定（世界观、势力、地名、角色）—— 这些用世界观摘要排除
- 逻辑合理性问题（动机、因果）—— 那是逻辑审查的职责
- 文学性/文笔问题

如果章节里没有可核查的现实世界事实断言，返回空 candidates 数组——这是正确答案，不要凑数。

返回纯 JSON（不要代码块包裹）：
{
  "candidates": [
    {
      "claim": "章节中的事实断言（完整陈述）",
      "location": "原文中对应的片段",
      "category": "武器年代/医疗史/历史/地理/技术/物理化学",
      "query": "适合网络搜索的查询词（中性、简洁，如「AK-47 量产年份」）"
    }
  ]
}"""

_VERDICT_PROMPT = """你是一名事实核查编辑。下面给出若干断言及其网络搜索证据。
请对每个断言判定 verdict：

- confirmed：证据支持断言成立（与原文一致）
- contradiction：证据表明断言错误（如武器型号在所述年代尚未存在）
- unverifiable：证据不足或无法判断

判定标准：只有当证据【明确】与断言矛盾时才判 contradiction；模棱两可的归 unverifiable，不要臆断。

返回纯 JSON（不要代码块包裹）：
{
  "verdicts": [
    {"claim": "断言原文（必须与输入完全一致）", "verdict": "contradiction"}
  ]
}"""
