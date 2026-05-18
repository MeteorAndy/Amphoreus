# Amphoreus — AI-Powered Story Engine

[中文](README.zh-CN.md) | **English**

> An AI-powered story engine for collaborative creation — from worldbuilding to scene generation.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12+ / FastAPI / Kuzu (Graph DB) / OpenAI / OpenViking |
| **Frontend** | Vue 3 / TypeScript / Vite / Tailwind CSS 4 |
| **Package Mgmt** | uv (Python) / pnpm (Node.js) |

## Features

- **World Building** — Define world rules, geography, history, and cultural background
- **Character Management** — Create character profiles and manage relationship networks (graph DB powered)
- **Plot Architecture** — Design main plotlines, subplots, and key turning points
- **Streaming Scene Generation** — Real-time context-aware narrative scenes with resume support
- **AI-Assisted Writing** — Guardian review + Writer generation, balancing quality and creativity
- **Document Parsing** — Upload PDFs/documents as worldbuilding reference material

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pnpm](https://pnpm.io/) (Node.js package manager)

### Backend

```bash
cd backend
uv sync
uv run python -m app.main
```

The server runs at `http://localhost:8000`. Check `/health` to verify.

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

The dev server runs at `http://localhost:5173`.

## Project Structure

```
Amphoreus/
├── backend/                # Python FastAPI backend
│   ├── app/
│   │   ├── api/            # REST API routes (world, character, plot, scene, writer, guardian)
│   │   ├── core/           # Configuration
│   │   ├── models/         # Data models
│   │   └── services/       # Business logic layer
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/               # Vue 3 frontend
│   ├── src/
│   │   ├── api/            # API client
│   │   ├── components/     # UI components
│   │   ├── composables/    # Composables
│   │   ├── router/         # Route config
│   │   ├── types/          # TypeScript types
│   │   └── views/          # Page views
│   ├── package.json
│   └── vite.config.ts
└── openspec/               # Specs & change management
```

## API Overview

| Endpoint | Description |
|----------|-------------|
| `/health` | Health check |
| `/api/world` | World building |
| `/api/characters` | Character management |
| `/api/plot` | Plot architecture |
| `/api/scene` | Scene generation |
| `/api/writer` | AI writing |
| `/api/guardian` | Story quality guardian |
