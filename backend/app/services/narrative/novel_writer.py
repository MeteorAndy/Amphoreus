"""Novel writer — converts scene logs to literary prose chapter by chapter."""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.plot_architect import PlotOutline, SceneSpec
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate, Reaction, RoundEntry

from .prompts import (
    _get_chapter_write_system_prompt,
    _get_chapter_write_target,
    _get_chapter_write_short_target,
    _get_novel_enhance_prompt,
)
from .canon_verifier import verify
from .cliche_scanner import scan
from .foreshadowing import render_foreshadowing_block
from .post_processor import PostProcessor
from .reviser import build_revise_directive
from .tension_scorer import phase_for_chapter
from .types import ChapterPlan, ChapterSpec, WritingOptions


# ---------------------------------------------------------------------------
# Archive parsing helpers
# ---------------------------------------------------------------------------


def _parse_archive_json(l2_content: str) -> SceneArchive:
    """Reconstruct a SceneArchive dataclass from stored JSON."""
    data: dict[str, Any] = json.loads(l2_content)

    rounds: list[RoundEntry] = [
        RoundEntry(
            round_num=r["round_num"],
            actor_id=r["actor_id"],
            actor_name=r["actor_name"],
            dialogue=r.get("dialogue", ""),
            action=r.get("action", ""),
            inner_thought=r.get("inner_thought", ""),
            emotion=r.get("emotion", ""),
            reactions=[
                Reaction(
                    reactor_id=rx["reactor_id"],
                    reactor_name=rx["reactor_name"],
                    visible_reaction=rx.get("visible_reaction", ""),
                    inner_thought=rx.get("inner_thought", ""),
                )
                for rx in r.get("reactions", [])
            ],
        )
        for r in data.get("rounds", [])
    ]

    fe_data = data.get("final_environment", {})
    final_environment = EnvironmentUpdate(
        atmosphere=fe_data.get("atmosphere", ""),
        changes=fe_data.get("changes", []),
        background_activity=fe_data.get("background_activity", ""),
    )

    return SceneArchive(
        scene_id=data["scene_id"],
        rounds=rounds,
        final_environment=final_environment,
        character_changes=data.get("character_changes", {}),
    )


def _load_scene_archive(memory: MemoryManager, scene_id: str) -> SceneArchive:
    """Load a single scene archive from OpenViking and return a SceneArchive."""
    entry = memory.openviking.read_entry(f"story/scenes/{scene_id}")
    return _parse_archive_json(entry.l2)


def _flatten_scenes(outline: PlotOutline) -> dict[str, SceneSpec]:
    """Flatten all SceneSpecs from a PlotOutline into a scene_id -> SceneSpec map."""
    result: dict[str, SceneSpec] = {}
    for act in outline.acts:
        for scene in act.scenes:
            result[scene.id] = scene
    return result


_ANALYSIS_HDR = (
    r"章节分析|分析|思考|写作策略|Chapter\s+Analysis|Analysis|Writing\s+Strategy"
)
_ANALYSIS_KW = re.compile(
    r"章节分析|逻辑漏洞|节奏问题|改进方向|写作策略|Chapter\s+Analysis|"
    r"Writing\s+Strategy|logical\s+gap|pacing\s+issue",
    re.IGNORECASE,
)


def _strip_leading_analysis(body: str) -> str:
    """Drop a leading analysis section when prose follows it with no body-header
    delimiter (the worst-case leak). Only engages when the first paragraph IS an
    analysis header, then skips analysis-shaped paragraphs (headers, bold labels,
    list items, analysis keywords) up to the first prose paragraph. Returns the
    original body if that would remove everything."""
    paras = re.split(r"\n\s*\n", body)
    first = next((p for p in paras if p.strip()), "")
    if not re.match(rf"^\s*#{{1,6}}\s*({_ANALYSIS_HDR})\s*$", first, re.IGNORECASE):
        return body
    kept: list[str] = []
    started = False
    for p in paras:
        s = p.strip()
        if not started:
            if not s:
                continue
            analysis_like = (
                s.startswith(("#", "**", "-", "*"))
                or re.match(r"^\d+[.、)]", s)
                or _ANALYSIS_KW.search(s)
            )
            if analysis_like:
                continue
            started = True
        kept.append(p)
    return "\n\n".join(kept).strip() or body


def _extract_chapter_story(raw: str) -> str:
    """Extract just the chapter prose from an LLM chapter response.

    The model is asked to wrap prose in <story>...</story> after a
    <思考>/<thinking> analysis block, but it does not always comply. This
    strips every observed scaffolding variant so analysis/planning text never
    leaks into the final novel:
      1. Prefer the <story>...</story> block (closed or unclosed).
      2. Else drop <思考>/<thinking> blocks.
      3. Else cut everything up to a "章节正文 / Chapter Body" header.
      4. Always remove any leftover analysis-header section and stray tags.
    """
    # 1. Preferred: explicit <story> tag (tolerate a missing close tag).
    m = re.search(r"<story>(.*?)</story>", raw, re.DOTALL | re.IGNORECASE)
    if m:
        body = m.group(1)
    elif re.search(r"<story>", raw, re.IGNORECASE):
        body = raw[re.search(r"<story>", raw, re.IGNORECASE).end():]
    else:
        body = raw

    # 2. Remove thinking/analysis tag blocks.
    body = re.sub(r"<(思考|thinking)>.*?</\1>", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"</?(story|思考|thinking)>", "", body, flags=re.IGNORECASE)

    # 3. If a "chapter body" header is present, keep only what follows the LAST one.
    body_hdr = list(re.finditer(
        r"^#{1,6}\s*(章节正文|正文|Chapter\s+Body|Story)\s*$",
        body, flags=re.MULTILINE | re.IGNORECASE,
    ))
    if body_hdr:
        body = body[body_hdr[-1].end():]

    # 4. Drop a leading analysis section. First try the bounded form (analysis
    #    header followed by another header), then the unbounded form (analysis
    #    header followed directly by prose) via paragraph-walking. Neither will
    #    delete everything — _strip_leading_analysis returns the original body if
    #    it would, so a non-empty response is never blanked out.
    deanalyzed = re.sub(
        rf"^#{{1,6}}\s*({_ANALYSIS_HDR})\s*$.*?(?=\n#{{1,6}}\s)",
        "", body, count=1, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    deanalyzed = _strip_leading_analysis(deanalyzed)

    # 5. Strip a leading chapter heading the model emitted itself (e.g.
    #    "# 第1章 …" / "## Chapter 1: …"). The assembler always prepends the
    #    canonical heading, so prose beginning with its own heading produces a
    #    duplicate (often with a mismatched subtitle). Only the leading run is
    #    removed; headings deeper in the prose are left untouched.
    deanalyzed = re.sub(
        r"\A(?:\s*#{1,6}[^\n]*\n+)+", "", deanalyzed,
    )

    result = deanalyzed.strip()
    # Safety: extraction must never blank out a non-empty response.
    if not result:
        result = re.sub(
            r"</?(story|思考|thinking)>", "", body, flags=re.IGNORECASE
        ).strip() or raw.strip()
    return result


def _render_phase_directive(
    chapter_num: int, total: int, is_zh: bool
) -> str:
    """Return a compact phase-awareness directive, or '' if too few chapters."""
    if total < 3:
        return ""
    phase = phase_for_chapter(chapter_num, total)

    if is_zh:
        table = {
            "opening": (
                "【叙事阶段：开篇】你在故事的起势阶段。展开世界观，引出主角动机"
                "与核心冲突，为后续埋下伏笔。可以铺设线索，不必急于收束。"
            ),
            "development": (
                "【叙事阶段：发展】你在故事的主体推进阶段。冲突升级、人物成长"
                "加速，早期伏笔应在本阶段开始回收，新线索可继续铺设但需节制。"
            ),
            "convergence": (
                "【叙事阶段：收束】故事进入高强度收束期。禁止开设新的伏笔或子"
                "情节，全力填坑——逾期的伏笔必须在本章或下一章了结。保持张力，"
                "为终局冲刺。"
            ),
            "finale": (
                "【叙事阶段：终局】只剩最后几章。切断日常描写，专注核心对决与"
                "人物结局。所有未收线索必须在本章内闭合。给读者一个有力的收束。"
            ),
        }
    else:
        table = {
            "opening": (
                "[STORY PHASE: OPENING] You are at the start. Introduce the world, "
                "the protagonist's motivation, and the core conflict. Plant threads "
                "freely — no pressure to resolve yet."
            ),
            "development": (
                "[STORY PHASE: DEVELOPMENT] The bulk of the story. Escalate "
                "conflicts, deepen characters, and begin paying off early threads. "
                "New threads are still welcome but be judicious."
            ),
            "convergence": (
                "[STORY PHASE: CONVERGENCE] High-pressure closing stretch. NO new "
                "subplots. Resolve every loose end. Keep tension high."
            ),
            "finale": (
                "[STORY PHASE: FINALE] Final chapters. Cut all daily-life padding; "
                "focus on the climactic confrontation. Every thread must close."
            ),
        }
    return table[phase]


# ---------------------------------------------------------------------------
# Novel writer
# ---------------------------------------------------------------------------


class NovelWriter:
    """Writes novel-format prose chapter by chapter via LLM.

    Each chapter call receives its scene logs, chapter plan metadata, and
    adjacent chapter summaries for transition context.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def write_chapters(
        self,
        chapter_plan: ChapterPlan,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        scene_specs: dict[str, SceneSpec] | None = None,
    ) -> list[str]:
        """Write each chapter as prose.  Returns one string per chapter."""
        char_by_id = {c.id: c for c in characters}
        archive_by_id = {a.scene_id: a for a in scene_archives}
        chapters: list[str] = []
        canon_block = ""
        if options.canonical_facts is not None:
            canon_block = options.canonical_facts.render_block("novel", get_lang() == Lang.ZH)

        for i, spec in enumerate(chapter_plan.chapters):
            scene_logs = self._build_chapter_scene_logs(
                spec, archive_by_id, char_by_id, scene_specs
            )

            prev_summary = chapter_plan.chapters[i - 1].summary if i > 0 else ""
            next_summary = (
                chapter_plan.chapters[i + 1].summary
                if i < len(chapter_plan.chapters) - 1
                else ""
            )

            word_count_target = (
                _get_chapter_write_short_target()
                if chapter_plan.is_short_story
                else _get_chapter_write_target()
            )

            chapter_prose = await self._generate_chapter(
                spec=spec,
                scene_logs=scene_logs,
                prev_summary=prev_summary,
                next_summary=next_summary,
                word_count_target=word_count_target,
                options=options,
                foreshadowing_block=render_foreshadowing_block(
                    options.foreshadowing_registry, spec.number, get_lang() == Lang.ZH
                ),
                phase_block=_render_phase_directive(
                    spec.number, len(chapter_plan.chapters), get_lang() == Lang.ZH
                ),
            )

            if options.enhance:
                chapter_prose = await self._enhance_prose(chapter_prose, canon_block)

            if options.revise is not None and options.revise.enabled:
                chapter_prose = await self._revise_chapter(chapter_prose, options)

            chapters.append(chapter_prose)

        return chapters

    # ------------------------------------------------------------------
    # Internal: chapter LLM call
    # ------------------------------------------------------------------

    async def _generate_chapter(
        self,
        spec: ChapterSpec,
        scene_logs: str,
        prev_summary: str,
        next_summary: str,
        word_count_target: str,
        options: WritingOptions,
        foreshadowing_block: str = "",
        phase_block: str = "",
    ) -> str:
        """Send a chapter prompt to the LLM and return the prose."""
        voice_label = options.narrative_voice.replace("_", " ")
        system_prompt = _get_chapter_write_system_prompt().format(voice=voice_label)

        lang = get_lang()
        if lang == Lang.ZH:
            user_prompt = (
                f"## 章节信息\n\n"
                f"标题：第{spec.number}章 {spec.title}\n"
                f"概述：{spec.summary}\n"
                f"目标字数：{word_count_target}\n\n"
                f"上一章概述：{prev_summary if prev_summary else '（无）'}\n"
                f"下一章概述：{next_summary if next_summary else '（无）'}\n\n"
                f"## 场景日志\n\n{scene_logs}\n\n"
                f"请写出完整的章节正文。"
            )
        else:
            user_prompt = (
                f"## Chapter Info\n\n"
                f"Title: Chapter {spec.number}: {spec.title}\n"
                f"Summary: {spec.summary}\n"
                f"Target word count: {word_count_target}\n\n"
                f"Previous chapter summary: {prev_summary if prev_summary else '(none)'}\n"
                f"Next chapter summary: {next_summary if next_summary else '(none)'}\n\n"
                f"## Scene Logs\n\n{scene_logs}\n\n"
                f"Write the complete chapter."
            )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]
        if options.canonical_facts is not None:
            canon = options.canonical_facts.render_block("novel", lang == Lang.ZH)
            if canon:
                messages.append({"role": "system", "content": canon})
        if foreshadowing_block:
            messages.append({"role": "system", "content": foreshadowing_block})
        if phase_block:
            messages.append({"role": "system", "content": phase_block})
        messages.append({"role": "user", "content": user_prompt})

        raw = await self._llm.chat(messages)
        return _extract_chapter_story(raw)

    async def _enhance_prose(self, prose: str, canon_block: str = "") -> str:
        """Second-pass LLM call for pacing, sensory depth, and dialogue polish."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_novel_enhance_prompt()},
        ]
        if canon_block:
            messages.append({"role": "system", "content": canon_block})
        messages.append({"role": "user", "content": prose})
        return await self._llm.chat(messages)

    async def _revise_chapter(self, prose: str, options: WritingOptions) -> str:
        """Bounded quality-loop rewrite (T1-①), reusing the second-pass channel.

        Each round runs the existing zero-LLM diagnostics — cliche scan, canon
        verify, verbatim-repeat detection — and asks `reviser` for a directive.
        An empty directive means nothing crossed threshold, so we stop without
        spending an LLM call. Otherwise we rewrite the chapter against the
        directive, then re-check; we stop early once clean or after max_rounds.
        Rewrites that come back empty are discarded (keep the better draft).
        """
        config = options.revise
        if config is None:
            return prose
        is_zh = get_lang() == Lang.ZH
        facts = options.canonical_facts
        # Inject the authoritative facts into the rewrite (their correct answers
        # + rejected list), mirroring _generate_chapter — a canon directive that
        # only says "this contradicts canon" without the correct value lets the
        # model rewrite into a different-but-still-wrong phrasing that verify()
        # (literal rejected_answers match) would not catch.
        canon_block = facts.render_block("novel", is_zh) if facts is not None else ""

        for _ in range(max(1, config.max_rounds)):
            cliche = scan(prose)
            canon = verify(prose, facts, "novel") if facts is not None else None
            repeats = PostProcessor.find_repeated_fragments(prose, config.repeat_min_len)
            directive = build_revise_directive(cliche, canon, repeats, config, is_zh)
            if not directive:
                break
            messages: list[dict[str, str]] = [
                {"role": "system", "content": directive},
            ]
            if canon_block:
                messages.append({"role": "system", "content": canon_block})
            messages.append({"role": "user", "content": prose})
            raw = await self._llm.chat(messages)
            revised = _extract_chapter_story(raw)
            if revised.strip():
                prose = revised
        return prose

    # ------------------------------------------------------------------
    # Internal: scene log formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _build_chapter_scene_logs(
        spec: ChapterSpec,
        archive_by_id: dict[str, SceneArchive],
        char_by_id: dict[str, CharacterProfile],
        scene_specs: dict[str, SceneSpec] | None,
    ) -> str:
        """Build combined scene logs for a chapter."""
        all_lines: list[str] = []

        for scene_id in spec.scene_ids:
            archive = archive_by_id.get(scene_id)
            if archive is None:
                all_lines.append(f"## Scene: {scene_id} [no archive data]")
                all_lines.append("")
                continue

            sspec = scene_specs.get(scene_id) if scene_specs else None
            if sspec:
                all_lines.append(f"## Scene: {scene_id} - {sspec.title}")
                all_lines.append(f"Location: {sspec.location}")
            else:
                all_lines.append(f"## Scene: {scene_id}")
            all_lines.append(f"Atmosphere: {archive.final_environment.atmosphere}")
            if archive.final_environment.background_activity:
                all_lines.append(
                    f"Background: {archive.final_environment.background_activity}"
                )
            all_lines.append("")

            for entry in archive.rounds:
                all_lines.append(f"--- Round {entry.round_num} ---")
                all_lines.append(f"Actor: {entry.actor_name}")
                if entry.dialogue:
                    all_lines.append(f'Dialogue: "{entry.dialogue}"')
                if entry.action:
                    all_lines.append(f"Action: {entry.action}")
                if entry.inner_thought:
                    all_lines.append(f"Inner thought: {entry.inner_thought}")
                if entry.emotion:
                    all_lines.append(f"Emotion: {entry.emotion}")
                for reaction in entry.reactions:
                    all_lines.append(
                        f"  {reaction.reactor_name} reacts: {reaction.visible_reaction}"
                    )
                    if reaction.inner_thought:
                        all_lines.append(
                            f"    ({reaction.reactor_name} thinks: {reaction.inner_thought})"
                        )
                all_lines.append("")

        return "\n".join(all_lines)
