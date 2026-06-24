"""Novel writer — converts scene logs to literary prose chapter by chapter."""

from __future__ import annotations

import re

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.plot_architect import SceneSpec
from app.services.scene_engine.resolution import SceneArchive

from .prompts import (
    _get_chapter_write_system_prompt,
    _get_chapter_write_target,
    _get_chapter_write_short_target,
    _get_novel_enhance_prompt,
)
from .canon_verifier import verify
from .cliche_scanner import scan
from .foreshadowing import render_foreshadowing_block, visible_profile
from .fact_checker import FactChecker
from .logic_reviewer import LogicReviewer
from .post_processor import PostProcessor
from .reviser import build_revise_directive
from .scene_archive_io import flatten_scenes, load_scene_archive, parse_archive_json
from .tension_scorer import phase_for_chapter
from .token_budget import (
    ChapterBudget,
    allocate_chapter_sections,
    measure_chapter_sections,
)
from .types import ChapterPlan, ChapterSpec, WritingOptions


# ---------------------------------------------------------------------------
# Archive parsing helpers (moved to scene_archive_io; re-exported for callers)
# ---------------------------------------------------------------------------

_parse_archive_json = parse_archive_json
_load_scene_archive = load_scene_archive
_flatten_scenes = flatten_scenes

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
    # The model also echoes the chapter title as a BOLD line rather than a
    # markdown header: "**第1章 …**" / "**Chapter N: …**". Same duplicate-title
    # bug, different shape — strip a leading bold chapter-title line too.
    deanalyzed = re.sub(
        r"\A\s*\*+\s*(?:第\s*\d+\s*章|Chapter\s+\d+)[^\n]*\*+\s*\n+",
        "", deanalyzed, count=1,
    )

    result = deanalyzed.strip()
    # Safety: extraction must never blank out a non-empty response.
    if not result:
        result = re.sub(
            r"</?(story|思考|thinking)>", "", body, flags=re.IGNORECASE
        ).strip() or raw.strip()
    return result


def _replace_once(prompt: str, old: str, new: str) -> str:
    if not old or old == new:
        return prompt
    replacement = new if new else "[context trimmed]"
    return prompt.replace(old, replacement, 1)


def _render_character_context(
    characters: list[CharacterProfile],
    current_chapter: int,
    is_zh: bool,
) -> str:
    lines: list[str] = []
    for char in characters:
        profile = visible_profile(char, current_chapter).strip()
        if not profile:
            continue
        role = f" ({char.role})" if char.role else ""
        lines.append(f"- {char.name}{role}: {profile}")
    if not lines:
        return ""
    header = "## 可见角色档案" if is_zh else "## Visible Character Context"
    return f"{header}\n\n" + "\n".join(lines)


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

    def __init__(self, llm: LLMClient, fact_checker: FactChecker | None = None) -> None:
        self._llm = llm
        self._logic_reviewer = LogicReviewer(llm)
        # Optional: injected by the pipeline when a Tavily key is configured.
        # None => fact-checking is skipped (no-op) in the revise loop.
        self._fact_checker = fact_checker

    async def write_chapters(
        self,
        chapter_plan: ChapterPlan,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        scene_specs: dict[str, SceneSpec] | None = None,
        budget_acc: list[ChapterBudget] | None = None,
        world_summary: str = "",
    ) -> list[str]:
        """Write each chapter as prose.  Returns one string per chapter.

        `budget_acc`, when given and options.token_budget is enabled, collects one
        advisory ChapterBudget per chapter (measure-only T2-④; never alters prose).
        """
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
                character_context=_render_character_context(
                    characters, spec.number, get_lang() == Lang.ZH
                ),
                foreshadowing_block=render_foreshadowing_block(
                    options.foreshadowing_registry, spec.number, get_lang() == Lang.ZH
                ),
                phase_block=_render_phase_directive(
                    spec.number, len(chapter_plan.chapters), get_lang() == Lang.ZH
                ),
                budget_acc=budget_acc,
            )

            if options.enhance:
                chapter_prose = await self._enhance_prose(chapter_prose, canon_block)

            if options.revise is not None and options.revise.enabled:
                chapter_prose = await self._revise_chapter(
                    chapter_prose, options, world_summary, characters
                )

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
        character_context: str = "",
        foreshadowing_block: str = "",
        phase_block: str = "",
        budget_acc: list[ChapterBudget] | None = None,
    ) -> str:
        """Send a chapter prompt to the LLM and return the prose."""
        voice_label = options.narrative_voice.replace("_", " ")
        system_prompt = _get_chapter_write_system_prompt().format(voice=voice_label)

        lang = get_lang()
        character_section = f"{character_context}\n\n" if character_context else ""
        if lang == Lang.ZH:
            user_prompt = (
                f"## 章节信息\n\n"
                f"标题：第{spec.number}章 {spec.title}\n"
                f"概述：{spec.summary}\n"
                f"目标字数：{word_count_target}\n\n"
                f"上一章概述：{prev_summary if prev_summary else '（无）'}\n"
                f"下一章概述：{next_summary if next_summary else '（无）'}\n\n"
                f"{character_section}"
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
                f"{character_section}"
                f"## Scene Logs\n\n{scene_logs}\n\n"
                f"Write the complete chapter."
            )

        canon = ""
        if options.canonical_facts is not None:
            canon = options.canonical_facts.render_block("novel", lang == Lang.ZH)

        cfg = options.token_budget
        if cfg is not None and cfg.enabled:
            parts = {
                "system": system_prompt, "canon": canon,
                "foreshadowing": foreshadowing_block, "phase": phase_block,
                "character_context": character_context,
                "prev_summary": prev_summary, "next_summary": next_summary,
                "scene_logs": scene_logs,
            }
            if cfg.apply_trimming:
                allocated, budget = allocate_chapter_sections(
                    spec.number, is_zh=lang == Lang.ZH,
                    budget_tokens=cfg.budget_tokens, parts=parts,
                )
                user_prompt = _replace_once(
                    user_prompt, prev_summary, allocated["prev_summary"]
                )
                user_prompt = _replace_once(
                    user_prompt, next_summary, allocated["next_summary"]
                )
                user_prompt = _replace_once(
                    user_prompt, scene_logs, allocated["scene_logs"]
                )
                canon = allocated["canon"]
                foreshadowing_block = allocated["foreshadowing"]
                phase_block = allocated["phase"]
            else:
                budget = measure_chapter_sections(
                    spec.number, is_zh=lang == Lang.ZH,
                    budget_tokens=cfg.budget_tokens, parts=parts,
                )
            if budget_acc is not None:
                budget_acc.append(budget)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]
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

    async def _revise_chapter(
        self,
        prose: str,
        options: WritingOptions,
        world_summary: str = "",
        characters: list[CharacterProfile] | None = None,
    ) -> str:
        """Bounded quality-loop rewrite (T1-①), reusing the second-pass channel.

        Each round runs the diagnostics — cliche scan, canon verify, verbatim-
        repeat detection, and (when logic_enabled) an LLM logic-plausibility
        review — and asks `reviser` for a directive. An empty directive means
        nothing crossed threshold, so we stop without spending an LLM call.
        Otherwise we rewrite the chapter against the directive, then re-check;
        we stop early once clean or after max_rounds. Rewrites that come back
        empty are discarded (keep the better draft).
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
            logic = None
            if config.logic_enabled:
                logic = await self._logic_reviewer.review(
                    chapter_text=prose,
                    world_summary=world_summary,
                    characters=characters or [],
                    max_issues=config.logic_max_issues,
                )
            fact_report = None
            if config.fact_check_enabled and self._fact_checker is not None:
                fact_report = await self._fact_checker.check(
                    chapter_text=prose,
                    world_summary=world_summary,
                    characters=characters or [],
                    max_queries=config.fact_check_max_queries,
                )
            directive = build_revise_directive(
                cliche, canon, repeats, config, is_zh, logic=logic, facts=fact_report
            )
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
