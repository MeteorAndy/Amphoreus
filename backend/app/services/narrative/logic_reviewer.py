"""Logic reviewer — LLM-driven logical-plausibility audit (T1-⑧).

Closes the gap the existing revise loop left open: cliche_scanner, canon_verifier,
and repeat-detection are all string-level, zero-LLM diagnostics, so they cannot
catch *reasonableness* failures — a character identifying someone "by the name
carved into the heel of their army boot", a left-handed action right after the
hand was severed, allies suddenly cooperating with no explanation. This module
adds exactly that: one LLM call per chapter that reports logical implausibilities
as structured LogicIssues, which reviser.build_revise_directive then folds into
the existing rewrite loop.

Design mirrors reader_sim / prop extraction:
- ONE LLM call (temp 0.1, must be stable judgement), returns JSON.
- NEVER fatal: any LLM error or malformed payload yields an empty report, so the
  write path and the revise loop are never broken. Bad rows are dropped, not
  propagated.
- Bounded: issues are capped (highest severity first) so a noisy chapter cannot
  bloat the revise directive.
- Scope is deliberately narrow: ONLY logical plausibility. Canon consistency
  stays with canon_verifier; prose flavor stays with cliche_scanner. No overlap.

The few-shot negative examples are seeded from real dogfood findings (PRD 9.2
acceptance run, novel "灰烬活水") and should grow as more hard-cases are found.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from app.core.llm_client import LLMError

if TYPE_CHECKING:
    from app.core.llm_client import LLMClient
    from app.services.character_manager import Character

logger = logging.getLogger(__name__)

Severity = Literal["critical", "major", "minor"]
Category = Literal["常识错误", "逻辑矛盾", "动机不通", "因果断裂", "设定违和"]

_VALID_SEVERITIES = ("critical", "major", "minor")
_VALID_CATEGORIES = ("常识错误", "逻辑矛盾", "动机不通", "因果断裂", "设定违和")
_DEFAULT_MAX_ISSUES = 8


@dataclass
class LogicIssue:
    severity: Severity
    category: Category
    location: str   # quoted excerpt from the prose
    problem: str    # why it is implausible
    fix_hint: str   # concrete rewrite direction


@dataclass
class LogicReport:
    issues: list[LogicIssue] = field(default_factory=list)

    @property
    def needs_rewrite(self) -> bool:
        """True iff any critical/major issue is present (minor = note only)."""
        return any(i.severity in ("critical", "major") for i in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {"issues": [
            {"severity": i.severity, "category": i.category,
             "location": i.location, "problem": i.problem, "fix_hint": i.fix_hint}
            for i in self.issues
        ]}


class LogicReviewer:
    """LLM logic-plausibility auditor. One call per chapter, never fatal."""

    def __init__(self, llm: "LLMClient"):
        self._llm = llm

    async def review(
        self,
        *,
        chapter_text: str,
        world_summary: str,
        characters: list["Character | dict[str, str]"],
        max_issues: int = _DEFAULT_MAX_ISSUES,
    ) -> LogicReport:
        """Audit one chapter. Returns a report (possibly empty). Never raises."""
        if not chapter_text.strip():
            return LogicReport()
        try:
            payload = await self._llm.chat_json(
                self._build_messages(chapter_text, world_summary, characters),
                temperature=0.1,
            )
        except LLMError as exc:
            logger.warning("logic_reviewer LLM call failed: %s", exc)
            return LogicReport()
        except Exception as exc:  # never break the write path
            logger.warning("logic_reviewer unexpected error: %s", exc)
            return LogicReport()

        issues = _parse_payload(payload)
        issues = _bound(issues, max_issues)
        return LogicReport(issues=issues)

    # -- prompt ---------------------------------------------------------------

    def _build_messages(
        self,
        chapter_text: str,
        world_summary: str,
        characters: list["Character | dict[str, str]"],
    ) -> list[dict[str, str]]:
        char_block = _render_characters(characters)
        world_block = world_summary.strip() or "（无世界观摘要）"
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"# 世界观摘要\n{world_block}\n\n"
                f"# 主要角色\n{char_block}\n\n"
                f"# 待审查的章节正文\n{chapter_text}\n\n"
                "请审查并返回 JSON。"
            )},
        ]


# ---- parsing & bounding (pure, unit-tested) --------------------------------


def _parse_payload(payload: Any) -> list[LogicIssue]:
    """Coerce an LLM payload (dict | JSON string, possibly fence-wrapped) to issues.

    Drops malformed rows rather than raising. Robust to ```json fences and to
    the model wrapping the array under various keys.
    """
    data = payload
    if isinstance(data, str):
        data = _extract_json_object(data)
        if data is None:
            return []
    if not isinstance(data, dict):
        return []

    raw_issues = data.get("issues")
    if not isinstance(raw_issues, list):
        # tolerate models that return the array at top level or under "problems"
        alt = data.get("problems") or data.get("findings")
        if isinstance(alt, list):
            raw_issues = alt
        else:
            return []

    out: list[LogicIssue] = []
    for row in raw_issues:
        if not isinstance(row, dict):
            continue
        sev = str(row.get("severity", "")).strip().lower()
        if sev not in _VALID_SEVERITIES:
            continue
        cat = str(row.get("category", "")).strip()
        if cat not in _VALID_CATEGORIES:
            # don't drop the whole row for an odd category label — coerce to the
            # closest bucket rather than losing a real finding
            cat = "逻辑矛盾"
        location = str(row.get("location", "")).strip()
        problem = str(row.get("problem", "")).strip()
        fix_hint = str(row.get("fix_hint", "")).strip()
        if not location or not problem:
            continue  # a finding we can't locate or explain is unusable
        out.append(LogicIssue(sev, cat, location, problem, fix_hint))  # type: ignore[arg-type]
    return out


def _bound(issues: list[LogicIssue], max_issues: int) -> list[LogicIssue]:
    """Cap to max_issues, keeping highest severity first (critical > major > minor)."""
    if len(issues) <= max_issues:
        return issues
    rank = {"critical": 0, "major": 1, "minor": 2}
    ordered = sorted(issues, key=lambda i: rank.get(i.severity, 9))
    return ordered[:max_issues]


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Pull a JSON object out of a string that may have markdown fences or prose."""
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


def _render_characters(characters: list["Character | dict[str, str]"]) -> str:
    if not characters:
        return "（未提供角色信息）"
    lines = []
    for c in characters:
        if isinstance(c, dict):
            name = c.get("name", "?")
            role = c.get("role", "")
            desire = c.get("core_desire", "")
        else:
            name = getattr(c, "name", "?")
            role = getattr(c, "role", "")
            desire = getattr(c, "core_desire", "")
        head = f"- {name}" + (f"（{role}）" if role else "")
        lines.append(f"{head}：{desire}" if desire else head)
    return "\n".join(lines)


# ---- prompt ----------------------------------------------------------------

_SYSTEM_PROMPT = """你是一名资深小说编辑，专攻【逻辑合理性审查】。

你的任务：阅读一章小说正文，找出其中的【逻辑不合理】问题。这是你的唯一职责——
不要评价文笔、不要评价设定是否忠于原始设定（那些有专门环节负责）、不要评价套话。
你只关心：情节在现实/常识/逻辑上站不站得住脚。

审查范围（5 类，且仅限这 5 类）：
1. 常识错误：违背现实常识的设定或描写（如「用军靴后跟刻字作为个人身份识别」——
   军靴刻字是工厂标识，不构成个人身份；如「中世纪背景出现电子表」）。
2. 逻辑矛盾：前后文互相冲突（如「前文说角色断了左手，后文他用左手开门」）。
3. 动机不通：角色行为缺乏可信动机或过渡（如「A 痛恨 B，下一章突然毫无解释地合作」）。
4. 因果断裂：事件之间缺乏因果链（如「他死了」→下一段「他走进房间」）。
5. 设定违和：场景内的物/事与既有世界观氛围冲突（如废土稀缺背景下角色随手丢弃净水）。

判断标准（重要）：
- 只报【站不住脚】的问题，不要为「可以解释得通」的细节挑刺。
- severity 标准：critical = 明显且无法自圆其说（如身份识别物本身就不成立）；
  major = 影响可信度但有修补空间；minor = 细微，读者可能注意不到。
- 不要凑数。没有问题就返回空 issues 数组，这是完全可接受的正确答案。

返回纯 JSON，格式严格如下，不要包裹在代码块里，不要任何解释文字：
{
  "issues": [
    {
      "severity": "critical",
      "category": "常识错误",
      "location": "引用原文中出现问题的片段",
      "problem": "为什么这是逻辑问题（一句话）",
      "fix_hint": "给作者的具体修改方向"
    }
  ]
}

参考示例（仅用于校准你的判断尺度，不要照抄）：
- 正文：「你的名字刻在军靴后跟上。我翻遍你身上的破布才找到。」
  → critical / 常识错误：军靴后跟刻字是工厂批次标识，不是个人身份信息，
    也不能解释「翻遍破布才找到」。fix_hint：改为随身铭牌、旧证件或身体特征（胎记/疤痕）。
- 正文：（前文断左手）「他用左手缓缓推开木门。」
  → critical / 逻辑矛盾：与「断了左手」直接冲突。fix_hint：改为右手或义肢。
"""
