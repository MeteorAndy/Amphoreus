## 1. Backend Scaffold

- [ ] 1.1 Create `backend/` with `uv init`, configure `pyproject.toml` with all deps (fastapi, uvicorn, openai, openviking, kuzu, pydantic, pydantic-settings)
- [ ] 1.2 Create `app/` package structure: `core/`, `models/`, `services/`, `api/`, `utils/`
- [ ] 1.3 Implement `core/config.py` — Settings with pydantic-settings, read from `~/.the-world/config.json`, two API keys (DeepSeek + Volcengine), local data dir
- [ ] 1.4 Implement `core/llm_client.py` — LLMClient wrapping openai SDK for deepseek-v4-flash, async, with retry/timeout
- [ ] 1.5 Implement `core/api_keys.py` — KeyManager encrypting API keys at rest, first-launch setup flow
- [ ] 1.6 Implement `app/main.py` — FastAPI app factory, CORS, lifespan events for OpenViking/Kuzu init

## 2. Memory System Foundation

- [ ] 2.1 Implement `memory/openviking_store.py` — OpenVikingStore class: init with world/chars/story schema, CRUD for files, L0/L1/L2 tier helpers
- [ ] 2.2 Implement `memory/kuzu_store.py` — KuzuStore class: init DB schema (Character/Location/Faction/Event nodes + relationship edges), CRUD, multi-hop query helper
- [ ] 2.3 Implement `memory/__init__.py` — unified MemoryManager facade combining both stores
- [ ] 2.4 Write `tests/test_memory.py` — integration tests for OpenViking write/read/tier + Kuzu CRUD/multi-hop

## 3. World Building

- [ ] 3.1 Implement `services/world_builder.py` — conversational LLM dialogue loop, progressive questioning, structured extraction → OpenViking
- [ ] 3.2 Implement `services/document_parser.py` — PDF/Markdown/TXT parsing, LLM extract → structured world data
- [ ] 3.3 Implement `api/world.py` — CRUD routes for rules/locations/factions/timeline
- [ ] 3.4 Write `tests/test_world.py` — integration tests: conversation flow, doc parse, CRUD

## 4. Character Management

- [ ] 4.1 Implement `models/character.py` — CharacterProfile pydantic model (identity, personality, core_desire, deep_fear, voice, secrets, knowledge_scope)
- [ ] 4.2 Implement `services/character_manager.py` — LLM character generation from world data, profile storage (OpenViking L0/L1/L2 + Kuzu node)
- [ ] 4.3 Implement `services/relationship_builder.py` — LLM inferred relationships → Kuzu edges with properties
- [ ] 4.4 Implement `api/characters.py` — CRUD routes
- [ ] 4.5 Write `tests/test_characters.py` — integration tests: generation, storage, relationship queries

## 5. Plot Architecture

- [ ] 5.1 Implement `services/plot_architect.py` — narrative templates (three-act, hero's journey, save-the-cat, qi-cheng-zhuan-he), LLM outline generation
- [ ] 5.2 Implement scene outline generator — breakdown plot into scene list with location/cast/conflict/goal/causal-chain metadata
- [ ] 5.3 Implement `api/plot.py` — CRUD routes with reorder support
- [ ] 5.4 Write `tests/test_plot.py` — integration tests: outline generation, scene breakdown

## 6. Story Guardian

- [ ] 6.1 Implement `services/story_guardian.py` — Guardian class: evaluation pipeline (load profiles + relationships + rules + recent history)
- [ ] 6.2 Implement five validators: character consistency, relationship logic, world rules compliance, pacing, arc integrity
- [ ] 6.3 Implement tiered response: CRITICAL (reject) / WARNING (allow-override) / SUGGESTION (inform)
- [ ] 6.4 Implement `api/guardian.py` — evaluate endpoint
- [ ] 6.5 Write `tests/test_guardian.py` — unit tests per validator + integration test for full evaluation

## 7. Scene Engine (核心)

- [ ] 7.1 Implement `services/scene_engine/director.py` — Director: scene setup (location, cast, goals, hidden info, conflict seed, end conditions), per-round adjudication
- [ ] 7.2 Implement `services/scene_engine/environment.py` — EnvironmentAgent: atmosphere updates, sensory details
- [ ] 7.3 Implement `services/scene_engine/interactor.py` — CharacterInteractor: context assembly (L0+L1+scene), action generation (structured JSON), parallel reaction generation (asyncio.gather)
- [ ] 7.4 Implement `services/scene_engine/knowledge_matrix.py` — KnowledgeMatrix: who-knows-what tracking, truth table
- [ ] 7.5 Implement `services/scene_engine/resolution.py` — SceneResolution: memory update pipeline, world state update, log archive
- [ ] 7.6 Implement `services/scene_engine/__init__.py` — SceneEngine facade orchestrating all submodules
- [ ] 7.7 Implement `api/scene.py` — REST endpoints (setup, step, inject, end, status) + WebSocket for real-time streaming
- [ ] 7.8 Write `tests/test_scene_engine.py` — full lifecycle integration test (3-character, 10+ rounds)

## 8. Narrative Writer

- [ ] 8.1 Implement `services/narrative_writer.py` — NovelWriter and ScreenplayWriter: load scene logs, LLM literary conversion
- [ ] 8.2 Implement quality enhancement — pacing, sensory detail, dialogue polish pass
- [ ] 8.3 Implement export — MD/TXT for novel, TXT/Fountain for screenplay
- [ ] 8.4 Implement `api/writer.py` — convert and export endpoints
- [ ] 8.5 Write `tests/test_writer.py` — integration tests: scene log → novel, scene log → screenplay, export

## 9. Phase 0 — CLI Self-Dogfooding

- [ ] 9.1 Build CLI entry point (`backend/cli.py`) — interactive menu: build world → create characters → plan plot → run scene → write output
- [ ] 9.2 Run end-to-end: idea → full pipeline → ~5000字 short story
- [ ] 9.3 Quality validation: character interaction naturalness, Director pacing, Guardian effectiveness, literary output quality
- [ ] 9.4 Iterate prompts and engine parameters based on self-use feedback

## 10. Frontend — Minimal Viable UI

- [ ] 10.1 Initialize `frontend/` with `pnpm create vue` + Tailwind CSS + Vite
- [ ] 10.2 Build WorldBuilderView — chat panel + document upload
- [ ] 10.3 Build CharacterView — cards + relationship graph (vis-network)
- [ ] 10.4 Build PlotView — timeline/card with drag-and-drop
- [ ] 10.5 Build SceneView — real-time feed + Director panel + intervention controls
- [ ] 10.6 Build WriterView — novel/screenplay preview toggle + export
- [ ] 10.7 Implement project management — create/load/save/list, auto-save, resume

## 11. User Experience — Three Modes

- [ ] 11.1 One-click generation mode — full pipeline orchestration with progress
- [ ] 11.2 Interactive creation mode — stage-by-stage with pause/edit
- [ ] 11.3 Sandbox observation mode — free character wandering + world event injection
- [ ] 11.4 Mode switching — preserve state across transitions

## 12. Desktop Packaging — Tauri

- [ ] 12.1 Initialize Tauri project, configure sidecar spawn/kill for Python backend
- [ ] 12.2 PyInstaller packaging for Python sidecar
- [ ] 12.3 Build installers for Windows (.msi) and macOS (.dmg)

## 13. Integration & Polish

- [ ] 13.1 E2E test: idea → world → characters → full pipeline → novel output
- [ ] 13.2 E2E test: document upload → parse → edit → scene → screenplay output
- [ ] 13.3 E2E test: interactive intervention + Guardian rejection + override flow
- [ ] 13.4 Performance: parallel LLM calls, context caching, token budgeting
- [ ] 13.5 Error handling: LLM failures, timeout retries, partial progress preservation
- [ ] 13.6 README and user documentation
