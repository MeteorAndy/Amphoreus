## Part A: Headless Pipeline

- [ ] 1.1 Create `PipelineConfig` and `PipelineEvent` dataclasses in `app/services/pipeline_orchestrator.py`
- [ ] 1.2 Implement `PipelineOrchestrator.run()` async generator — world building with self-play
- [ ] 1.3 Implement character generation + auto-refine stage
- [ ] 1.4 Implement relationship inference + plot generation stage
- [ ] 1.5 Implement scene execution stage (all scenes, streaming)
- [ ] 1.6 Implement narrative writing stage (title + chapters + export)
- [ ] 1.7 Add session persistence + resume logic in orchestrator
- [ ] 1.8 Create `app/api/pipeline.py` router with SSE endpoint
- [ ] 1.9 Register pipeline router in main.py

## Part B: MCP Server

- [ ] 2.1 Add `mcp` dependency to pyproject.toml
- [ ] 2.2 Create `backend/mcp_server.py` with MCP server setup (stdio transport)
- [ ] 2.3 Implement `generate_story` tool (calls PipelineOrchestrator)
- [ ] 2.4 Implement individual tools: build_world, generate_characters, create_plot, run_scenes, write_narrative
- [ ] 2.5 Implement `amphoreus://session/{id}` resource
- [ ] 2.6 Add SSE transport option for network access

## Part C: Integration

- [ ] 3.1 Update frontend to add "Auto Generate" button that calls pipeline API
- [ ] 3.2 Add pipeline progress view in frontend (SSE consumer)
- [ ] 3.3 Verify: `uv run mcp_server.py` starts and responds to tool calls
