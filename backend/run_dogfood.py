"""Headless dogfood driver — run the full PRD pipeline end-to-end.

Produces a finished short story from a seed idea, so the actual generated
prose can be read and judged (PRD task 9.2 acceptance).

Dumps all stage artifacts to ./dogfood_out/ so the content is reviewable
even if a later stage misbehaves.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))
sys.stdout.reconfigure(line_buffering=True)

from app.core.config import get_settings
from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.pipeline_types import PipelineConfig

SEED_IDEA = (
    "末世废土上，一个失忆的拾荒者陈漠在锈铁镇醒来，"
    "发现镇上的水源被武装帮派'铁颅团'垄断。"
    "他必须与神秘女医生苏静合作，揭开自己失忆前与水源有关的秘密。"
)

OUT_DIR = BACKEND / "dogfood_out"
OUT_DIR.mkdir(exist_ok=True)
STATE_PICKLE = OUT_DIR / "pre_writing_state.pkl"

# Two-phase mode: the full run cannot finish inside one 10-min tool timeout
# (WORLD alone is 4-9 LLM rounds). So we split:
#   phase 1 (default): run WORLD→SCENES, then pickle the in-memory state.
#   phase 2 (--write): load the pickle, run only WRITING, write the novel.
# This guarantees each phase finishes well within the timeout.
PHASE = sys.argv[1] if len(sys.argv) > 1 else "1"

# Keep the run inside a reasonable time budget: WORLD varies 4-9 LLM rounds,
# each scene is 4 rounds * multiple characters. Two scenes + lean writing
# fits comfortably when the 8 diagnostic channels are off (now the default).
MAX_SCENES = 2


async def main() -> int:
    settings = get_settings()
    memory = MemoryManager(settings)
    await memory.initialize()

    config = PipelineConfig(
        seed_idea=SEED_IDEA,
        lang="zh",
        character_count=3,
        narrative_structure="three_act",
        output_format="novel",
        max_rounds_per_scene=4,
        auto_refine=False,
        adjudicate=False,
    )

    orchestrator = PipelineOrchestrator(llm=LLMClient(), memory=memory)

    # Cap the scene count so the whole run finishes inside the timeout.
    original_stage_plot = orchestrator._stage_plot

    async def _truncated_stage_plot(cfg, sid, state):
        async for event in original_stage_plot(cfg, sid, state):
            yield event
        outline = state.get("outline")
        if outline is not None and outline.acts:
            kept = 0
            for act in outline.acts:
                if kept >= MAX_SCENES:
                    act.scenes = []
                    continue
                room = MAX_SCENES - kept
                act.scenes = act.scenes[:room]
                kept += len(act.scenes)
            print(f"\n  [dogfood] 场景截断为前 {kept} 个\n", flush=True)

    orchestrator._stage_plot = _truncated_stage_plot

    # Capture the internal state so we can dump artifacts even on timeout.
    orchestrator._captured_state = None
    _orig_drive = orchestrator._drive_stage

    async def _capturing_drive(stage, cfg, sid, state):
        orchestrator._captured_state = state
        async for ev in _orig_drive(stage, cfg, sid, state):
            yield ev

    orchestrator._drive_stage = _capturing_drive

    print("=" * 70, flush=True)
    print("PRD 任务 9.2 验收：端到端生成", flush=True)
    print(f"种子创意：{SEED_IDEA}", flush=True)
    print(f"配置：3角色 / {MAX_SCENES}场景 / 每场景4轮 / 诊断关闭", flush=True)
    print("=" * 70, flush=True)

    # Wrap narrative_writer.convert to time it and surface any failure
    # (the orchestrator swallows exceptions with bare `except: pass`, so we
    # need to observe at this boundary).
    _nw = orchestrator._narrative_writer
    _orig_convert = _nw.convert

    async def _timed_convert(*args, **kwargs):
        t0 = time.time()
        print(f"\n  [WRITING] narrative_writer.convert 开始...", flush=True)
        try:
            result = await _orig_convert(*args, **kwargs)
            print(f"  [WRITING] convert 完成，耗时 {time.time()-t0:.1f}s", flush=True)
            return result
        except Exception as e:
            import traceback
            print(f"  [WRITING] convert 失败 ({time.time()-t0:.1f}s): {e}", flush=True)
            traceback.print_exc()
            raise

    _nw.convert = _timed_convert

    # Also wrap the aftermath graph-inference step that runs after convert.
    if hasattr(orchestrator, '_aftermath') and orchestrator._aftermath is not None:
        _am = orchestrator._aftermath
        if hasattr(_am, 'persist_inferred_facts'):
            _orig_pf = _am.persist_inferred_facts
            async def _timed_pf(*a, **kw):
                t0 = time.time()
                print(f"\n  [WRITING] persist_inferred_facts (图推理) 开始...", flush=True)
                try:
                    r = await _orig_pf(*a, **kw)
                    print(f"  [WRITING] 图推理完成，耗时 {time.time()-t0:.1f}s", flush=True)
                    return r
                except Exception as e:
                    print(f"  [WRITING] 图推理失败 ({time.time()-t0:.1f}s): {e}", flush=True)
                    raise
            _am.persist_inferred_facts = _timed_pf

    start = time.time()

    if PHASE == "1":
        # Phase 1: run WORLD → SCENES, then pickle the in-memory state so
        # phase 2 can resume with only WRITING (which fits the timeout).
        print(f"\n>>> PHASE 1: 生成世界/角色/剧情/场景，之后序列化状态", flush=True)
        scenes_done = False
        try:
            async for event in orchestrator.run(config):
                stage = str(event.stage).split(".")[-1]
                etype = event.type
                data = event.data
                if etype == "started":
                    print(f"\n>>> [{stage}] 开始", flush=True)
                elif etype == "completed" and stage == "SCENES":
                    print(f"<<< [{stage}] 完成", flush=True)
                    _dump_state(orchestrator)
                    scenes_done = True
                    # Pickle state immediately and exit phase 1.
                    import pickle
                    with open(STATE_PICKLE, "wb") as f:
                        pickle.dump(orchestrator._captured_state, f)
                    print(f"\n状态已序列化: {STATE_PICKLE}", flush=True)
                    print(f"现在运行 phase 2:  uv run python run_dogfood.py 2", flush=True)
                    break
                elif etype == "progress":
                    title = data.get("title", "")
                    if title:
                        idx = data.get("index", 0)
                        total = data.get("total", 0)
                        print(f"  [{stage}] 场景{idx+1}/{total} 「{title}」", flush=True)
        except Exception as exc:
            import traceback
            print(f"\n!!!! PHASE 1 异常: {exc}", flush=True)
            traceback.print_exc()

        _dump_state(orchestrator)
        print(f"\nPhase 1 耗时 {time.time()-start:.1f}s (scenes_done={scenes_done})", flush=True)
        await memory.close()
        return 0 if scenes_done else 1

    # Phase 2: load pickled state, run only _stage_writing, write the novel.
    import pickle
    if not STATE_PICKLE.exists():
        print(f"!! 找不到状态文件 {STATE_PICKLE}，请先运行 phase 1", flush=True)
        await memory.close()
        return 1
    with open(STATE_PICKLE, "rb") as f:
        state = pickle.load(f)
    orchestrator._captured_state = state
    print(f"\n>>> PHASE 2: 加载状态，仅运行 WRITING", flush=True)
    _dump_state(orchestrator)

    session_id = "dogfood-resume"
    final_text = None
    final_title = ""
    try:
        async for event in orchestrator._stage_writing(config, session_id, state):
            stage = str(event.stage).split(".")[-1]
            etype = event.type
            data = event.data
            if etype == "started":
                print(f"\n>>> [{stage}] 开始", flush=True)
            elif etype == "chunk":
                txt = data.get("text", "")
                if txt:
                    print(txt, end="", flush=True)
            elif etype == "completed":
                content = data.get("content")
                if content:
                    final_text = content
                    final_title = data.get("title", "")
                    wc = data.get("word_count", "")
                    print(f"\n=== 成文完成: 「{final_title}」 {wc}字 ===", flush=True)
    except Exception as exc:
        import traceback
        print(f"\n!!!! PHASE 2 异常: {exc}", flush=True)
        traceback.print_exc()

    # Fallback: pull from state["output"] if the event didn't carry content.
    if final_text is None:
        out = state.get("output")
        if out is not None:
            final_text = getattr(out, "content", None)
            final_title = getattr(out, "title", "") or final_title

    if final_text:
        # `content` already carries the title (assembled by _assemble_novel as
        # "# {title}\n"), so do NOT prepend another header — that doubled the
        # title in earlier runs.
        (OUT_DIR / "novel.md").write_text(final_text, encoding="utf-8")
        print(f"\n小说已保存：{OUT_DIR / 'novel.md'}", flush=True)

    print(f"\nPhase 2 耗时 {time.time()-start:.1f}s", flush=True)
    await memory.close()
    return 0 if final_text else 1


def _dump_state(orchestrator) -> None:
    state = getattr(orchestrator, "_captured_state", None)
    if state is None:
        return
    snap: dict = {}

    ws = state.get("world_state")
    if ws is not None:
        snap["world"] = {
            "rules": getattr(ws, "rules", None),
            "locations": getattr(ws, "locations", None),
            "factions": getattr(ws, "factions", None),
            "timeline": getattr(ws, "timeline", None),
        }

    chars = state.get("characters")
    if chars:
        snap["characters"] = [
            {"name": getattr(c, "name", ""),
             "personality": getattr(c, "personality", ""),
             "core_desire": getattr(c, "core_desire", ""),
             "deep_fear": getattr(c, "deep_fear", ""),
             "background": getattr(c, "background", "")}
            for c in chars
        ]

    outline = state.get("outline")
    if outline is not None:
        snap["plot"] = {
            "acts": [
                {"name": a.name, "description": a.description,
                 "scenes": [{"id": s.id, "title": s.title,
                             "summary": getattr(s, "summary", ""),
                             "cast": list(getattr(s, "cast", []))}
                            for s in getattr(a, "scenes", [])]}
                for a in getattr(outline, "acts", [])
            ]
        }

    archives = state.get("archives")
    if archives:
        snap["scenes"] = [_archive_dict(a) for a in archives]

    (OUT_DIR / "state_snapshot.json").write_text(
        json.dumps(snap, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def _archive_dict(a) -> dict:
    # SceneArchive.rounds is a flat list[RoundEntry]; each RoundEntry is one
    # character's turn (actor + dialogue + action + thought + reactions).
    rounds = []
    for r in getattr(a, "rounds", []):
        reactions = []
        for rx in getattr(r, "reactions", []) or []:
            reactions.append({
                "reactor": getattr(rx, "reactor_name", ""),
                "visible": getattr(rx, "visible_reaction", ""),
                "thought": getattr(rx, "inner_thought", ""),
            })
        rounds.append({
            "round": getattr(r, "round_num", ""),
            "actor": getattr(r, "actor_name", ""),
            "dialogue": getattr(r, "dialogue", ""),
            "action": getattr(r, "action", ""),
            "thought": getattr(r, "inner_thought", ""),
            "emotion": getattr(r, "emotion", ""),
            "reactions": reactions,
        })
    setup = getattr(a, "setup", None) or getattr(a, "scene_setup", None)
    return {
        "scene_id": getattr(a, "scene_id", ""),
        "setup": {
            "location": getattr(setup, "location", "") if setup else "",
            "location_desc": getattr(setup, "location_description", "") if setup else "",
            "cast": list(getattr(setup, "cast", [])) if setup else [],
            "conflict_seed": getattr(setup, "conflict_seed", "") if setup else "",
            "character_goals": dict(getattr(setup, "character_goals", {})) if setup else {},
        } if setup else {},
        "rounds": rounds,
        "final_environment": getattr(a, "final_environment", None),
        "character_changes": getattr(a, "character_changes", None),
    }


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
