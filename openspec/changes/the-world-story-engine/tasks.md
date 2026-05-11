## 1. Project Scaffold

- [ ] 1.1 Initialize backend project structure (FastAPI app, directory layout, config module)
- [ ] 1.2 Add core Python dependencies (openai, openviking, kuzu, pydantic, uvicorn)
- [ ] 1.3 Configure DeepSeek-V4-Flash LLM client with OpenAI-compatible SDK
- [ ] 1.4 Implement local API Key management (input on first launch, encrypt store, multi-provider support)
- [ ] 1.5 Set up environment config (settings model with validation, user data dir ~/.the-world/)

## 2. Memory System Foundation

- [ ] 2.1 Initialize OpenViking storage with world/chars/story directory schema
- [ ] 2.2 Implement OpenViking store wrapper (read/write/update with L0/L1/L2 tiering)
- [ ] 2.3 Initialize Kuzu database with schema (Character, Location, Faction, Event nodes + relations)
- [ ] 2.4 Implement Kuzu store wrapper (CRUD nodes, create/update/delete edges, multi-hop queries)
- [ ] 2.5 Implement memory tiering helper (generate L0 summary + L1 overview on write)
- [ ] 2.6 Write integration tests for OpenViking + Kuzu basic operations

## 3. World Building

- [ ] 3.1 Implement conversational world building service (LLM progressive questioning)
- [ ] 3.2 Implement world data extraction from conversation (structured parsing → OpenViking)
- [ ] 3.3 Implement document upload API (PDF/Markdown/TXT parsing)
- [ ] 3.4 Implement document-to-world-data extraction (LLM parsing → editable result)
- [ ] 3.5 Implement world data CRUD API (rules, locations, factions, timeline)

## 4. Character Management

- [ ] 4.1 Implement character generation service (LLM suggests characters from world data)
- [ ] 4.2 Implement character profile data model (identity, personality, desire, fear, voice)
- [ ] 4.3 Implement character storage pipeline (OpenViking L0/L1/L2 + Kuzu node creation)
- [ ] 4.4 Implement relationship graph builder (LLM infers relationships + writes to Kuzu)
- [ ] 4.5 Implement character CRUD API

## 5. Plot Architecture

- [ ] 5.1 Implement narrative structure templates (three-act, hero's journey, save-the-cat, qi-cheng-zhuan-he)
- [ ] 5.2 Implement plot generation service (LLM generates outline from world + characters + structure)
- [ ] 5.3 Implement scene outline generator (breakdown plot into scene list with metadata)
- [ ] 5.4 Implement scene CRUD API with reorder support
- [ ] 5.5 Implement plot-scene consistency check (scene goals vs character arcs)

## 6. Story Guardian

- [ ] 6.1 Implement Guardian evaluation pipeline (load profiles + relationships + rules + recent history)
- [ ] 6.2 Implement character consistency validator
- [ ] 6.3 Implement relationship logic validator (Kuzu query + LLM analysis)
- [ ] 6.4 Implement world rules compliance validator
- [ ] 6.5 Implement pacing evaluator
- [ ] 6.6 Implement character arc integrity checker
- [ ] 6.7 Implement tiered response system (CRITICAL reject / WARNING allow-override / SUGGESTION inform)
- [ ] 6.8 Implement Guardian API endpoint
- [ ] 6.9 Write tests for each Guardian evaluation dimension

## 7. Scene Engine (核心)

- [ ] 7.1 Implement Director agent (scene setup: location, cast, goals, hidden info, conflict seed, end conditions)
- [ ] 7.2 Implement Environment Agent (atmosphere updates, background activity, sensory details)
- [ ] 7.3 Implement character context assembler (L0+L1+scene layer, respecting knowledge boundaries)
- [ ] 7.4 Implement action generation (single character LLM call with structured JSON output)
- [ ] 7.5 Implement parallel reaction generation (asyncio.gather for multiple character responses)
- [ ] 7.6 Implement Director adjudication (per-round: conflict check, OOC check, pacing check, end check)
- [ ] 7.7 Implement information asymmetry matrix (who-knows-what tracking)
- [ ] 7.8 Implement scene resolution pipeline (memory update + world state update + log archive)
- [ ] 7.9 Implement Scene Engine API (setup, step, inject, end, status)
- [ ] 7.10 Implement WebSocket endpoint for real-time scene streaming
- [ ] 7.11 Write integration tests for full scene lifecycle (3-character scene, 10+ rounds)

## 8. Narrative Writer

- [ ] 8.1 Implement scene log loader (read archived JSON logs)
- [ ] 8.2 Implement novel format converter (logs → literary prose with narrative voice)
- [ ] 8.3 Implement screenplay format converter (logs → standard screenplay format)
- [ ] 8.4 Implement quality enhancement mode (pacing, sensory detail, dialogue polish)
- [ ] 8.5 Implement export functionality (MD/TXT for novel, TXT/Fountain for screenplay)
- [ ] 8.6 Implement Writer API endpoint

## 9. Phase 0: Self-Dogfooding — CLI/MVP 验证

- [ ] 9.1 Build CLI entry point: 输入 idea → 对话式世界构建 → 角色生成 → 选一个场景 → 执行 → 输出小说
- [ ] 9.2 Run end-to-end pipeline with a real story idea, produce a ~5000字 short story
- [ ] 9.3 Validate: character interaction quality, Director pacing, Guardian effectiveness
- [ ] 9.4 Iterate on prompts and engine parameters based on self-use feedback
- [ ] 9.5 Once engine quality is validated, proceed to frontend and desktop packaging

## 10. Frontend — Minimal Viable UI

- [ ] 10.1 Initialize Vue 3 + Vite + Tailwind CSS frontend project
- [ ] 10.2 Build WorldBuilderView (chat panel + document upload)
- [ ] 10.3 Build CharacterView (character cards + relationship graph visualization)
- [ ] 10.4 Build PlotView (timeline/card view + structure selector)
- [ ] 10.5 Build SceneView (real-time interaction feed + Director panel + intervention controls)
- [ ] 10.6 Build WriterView (novel/screenplay preview toggle + export buttons)
- [ ] 10.7 Implement project management (create, load, save, list projects)
- [ ] 10.8 Build main navigation and mode selector UI

## 11. User Experience — 三模式

- [ ] 11.1 Implement one-click generation mode (full pipeline orchestration with progress display)
- [ ] 11.2 Implement interactive creation mode (stage-by-stage with pause/edit points)
- [ ] 11.3 Implement sandbox observation mode (free character wandering + world event injection)
- [ ] 11.4 Implement mode switching logic (preserve state across mode transitions)
- [ ] 11.5 Implement progress persistence (auto-save + resume from last step)

## 12. Desktop Packaging — Tauri

- [ ] 12.1 Initialize Tauri project (Rust shell, config, window management)
- [ ] 12.2 Configure Python FastAPI as Sidecar (PyInstaller打包 + Tauri spawn/kill)
- [ ] 12.3 Configure WebView to point to localhost:5001
- [ ] 12.4 Implement auto-update mechanism (Tauri updater)
- [ ] 12.5 Build installers for Windows (.msi) and macOS (.dmg)
- [ ] 12.6 Test full desktop workflow: install → launch → input API Key → create story → export

## 13. Integration & Polish

- [ ] 13.1 End-to-end test: idea → world → characters → full pipeline → novel output
- [ ] 13.2 End-to-end test: document upload → parse → edit → characters → scene → screenplay output
- [ ] 13.3 End-to-end test: interactive mode user intervention + Guardian rejection + override flow
- [ ] 13.4 Performance optimization (parallel LLM calls, context caching, token budgeting)
- [ ] 13.5 Error handling and recovery (LLM failures, timeout retries, partial progress preservation)
- [ ] 13.6 UI design quality review (anti-AI-slob aesthetic, thematic consistency)
- [ ] 13.7 README and user documentation

## 14. Future: OpenClaw Integration (Stretch)

- [ ] 14.1 Design OpenClaw Agent plugin interface for TheWorld engine
- [ ] 14.2 Implement "Cyber Writer" agent: autonomous chapter scheduling, character state monitoring
- [ ] 14.3 Implement cross-platform publishing adapters (web novel platforms, social media)
- [ ] 14.4 Implement reader feedback ingestion → story adaptation loop
