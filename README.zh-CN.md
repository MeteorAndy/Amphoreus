# Amphoreus — AI 驱动的故事引擎

[English](README.md) | **中文**

> AI 驱动的故事引擎，从世界观构建到场景生成，全流程协作创作。

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python 3.12+ / FastAPI / Kuzu (图数据库) / OpenAI / OpenViking |
| **前端** | Vue 3 / TypeScript / Vite / Tailwind CSS 4 |
| **包管理** | uv (Python) / pnpm (Node.js) |

## 核心功能

- **世界观构建** — 定义世界的规则、地理、历史和文化背景
- **角色管理** — 创建角色档案，管理角色关系网络（图数据库驱动）
- **剧情架构** — 设计故事主线、支线和关键转折点
- **场景流式生成** — 基于上下文实时生成叙事场景，支持断点续传
- **AI 协作写作** — Guardian 审查 + Writer 生成，质量与创意兼顾
- **文档解析** — 支持上传 PDF/文档作为世界观参考素材

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python 包管理)
- [pnpm](https://pnpm.io/) (Node.js 包管理)

### 后端启动

```bash
cd backend
uv sync
uv run python -m app.main
```

服务默认运行在 `http://localhost:8000`。访问 `/health` 确认服务正常。

### 前端启动

```bash
cd frontend
pnpm install
pnpm dev
```

开发服务器默认运行在 `http://localhost:5173`。

## 项目结构

```
Amphoreus/
├── backend/                # Python FastAPI 后端
│   ├── app/
│   │   ├── api/            # REST API 路由 (world, character, plot, scene, writer, guardian)
│   │   ├── core/           # 配置管理
│   │   ├── models/         # 数据模型
│   │   └── services/       # 业务逻辑层
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── api/            # API 客户端
│   │   ├── components/     # UI 组件
│   │   ├── composables/    # 组合式函数
│   │   ├── router/         # 路由配置
│   │   ├── types/          # TypeScript 类型
│   │   └── views/          # 页面视图
│   ├── package.json
│   └── vite.config.ts
└── openspec/               # 项目规范与变更管理
```

## API 概览

| Endpoint | 说明 |
|----------|------|
| `/health` | 健康检查 |
| `/api/world` | 世界观管理 |
| `/api/characters` | 角色管理 |
| `/api/plot` | 剧情架构 |
| `/api/scene` | 场景生成 |
| `/api/writer` | AI 写作 |
| `/api/guardian` | 质量审查 |
