## Why

当前 Amphoreus 只能通过交互式 CLI 或 Web 前端使用，每一步都需要人类输入。用户希望：
1. AI Agent（如 OpenClaw）能 7×24 全自动调用，一次性生成完整小说/剧本
2. 任何 MCP 兼容的智能体都能发现并使用故事引擎的能力

## What Changes

### Part A: Headless Pipeline API

新增 `POST /api/pipeline/run` 端点：
- 接收完整配置 JSON（idea、语言、角色数量、叙事结构、输出格式等）
- 全自动执行完整管线：世界构建 → 角色生成 → 关系推断 → 剧情架构 → 场景执行 → 叙事写作
- SSE (Server-Sent Events) 流式返回每阶段进度和中间结果
- 最终返回完整小说/剧本文本 + 元数据
- 支持断点续传（传入 session_id 恢复）

### Part B: MCP Server

将故事引擎封装为 MCP (Model Context Protocol) 工具集：
- `amphoreus_generate_story` — 一键生成完整故事（调用 Pipeline API）
- `amphoreus_build_world` — 单独构建世界观
- `amphoreus_generate_characters` — 单独生成角色
- `amphoreus_create_plot` — 单独生成剧情大纲
- `amphoreus_run_scene` — 单独执行场景
- `amphoreus_write_narrative` — 单独转换为小说/剧本

MCP Server 作为独立入口点，可通过 `uv run mcp_server.py` 启动。
