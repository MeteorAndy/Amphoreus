## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Amphoreus Story Engine                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Web Frontend │  │  MCP Server  │  │  Pipeline API    │  │
│  │  (Vue 3)     │  │  (stdio/sse) │  │  (SSE stream)    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                  │                    │            │
│         ▼                  ▼                    ▼            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              PipelineOrchestrator                      │   │
│  │  (Headless, async, yields progress events)            │   │
│  └──────────────────────────────────────────────────────┘   │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Existing Services (WorldBuilder, CharacterManager,   │   │
│  │  PlotArchitect, SceneEngine, NarrativeWriter, etc.)   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. PipelineOrchestrator (核心)

新建 `app/services/pipeline_orchestrator.py`：
- 接收 `PipelineConfig` dataclass（所有参数一次性传入）
- 异步生成器，yield `PipelineEvent` 事件流
- 每个阶段自动决策（不需要人类输入）
- 内置错误恢复 + 断点续传

```python
@dataclass
class PipelineConfig:
    seed_idea: str
    lang: str = "zh"
    character_count: int = 5
    narrative_structure: str = "three_act"
    output_format: str = "novel"  # novel | screenplay
    max_rounds_per_scene: int = 15
    auto_refine: bool = True
    session_id: str | None = None  # for resume

@dataclass
class PipelineEvent:
    stage: str  # world | characters | relationships | plot | scenes | writing
    type: str   # started | progress | completed | error
    data: dict[str, Any]
    progress: float  # 0.0 - 1.0 overall
```

### 2. Pipeline API Endpoint

`POST /api/pipeline/run` → SSE stream
- Request body: PipelineConfig JSON
- Response: `text/event-stream` with PipelineEvent JSON per line
- Final event contains full output text + metadata

`GET /api/pipeline/{session_id}/status` → current state
`POST /api/pipeline/{session_id}/cancel` → graceful stop

### 3. MCP Server

独立文件 `backend/mcp_server.py`，使用 `mcp` Python SDK：
- Transport: stdio (for agent integration) + SSE (for network)
- 6 个 tools + 1 个 resource

Tools:
- `generate_story(config)` — 完整管线
- `build_world(seed_idea, lang)` — 世界构建
- `generate_characters(world_id, count)` — 角色生成
- `create_plot(world_id, character_ids, structure)` — 剧情
- `run_scenes(plot_id, character_ids)` — 场景执行
- `write_narrative(scene_ids, character_ids, format)` — 写作

Resources:
- `amphoreus://session/{id}` — 会话状态

### 4. Auto-Decision Logic

Pipeline 中每个需要"人类决策"的点改为自动：
- 世界构建：LLM 自动回答自己的问题（self-play），直到 completeness > 0.8
- 角色编辑：跳过（auto_refine=true 时自动 refine 一轮）
- 结构选择：使用 config 中指定的 structure
- 场景选择：全部执行
- 标题选择：自动选第一个候选
