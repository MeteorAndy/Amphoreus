# Amphoreus Story Engine — Project Rules

## Code Style

- Single file max 500 lines. If a file exceeds this, split into modules.
- No comments explaining what code does — use clear naming instead.
- Type everything (Python: type hints, TypeScript: strict mode).
- Follow TDD: write tests first, then implement.

## Architecture

- Backend: Python 3.12 + FastAPI + OpenViking + Kuzu
- Frontend: Vue 3 + TypeScript + Tailwind CSS v4 + Vite
- LLM: DeepSeek via openai SDK
- i18n: bilingual ZH/EN throughout (backend `app/core/i18n.py`, frontend `src/i18n.ts`)

## Testing

- Backend: pytest + pytest-asyncio in `backend/tests/`
- Frontend: vitest (when configured)
- Run `uv run pytest tests/ -v` before committing backend changes
- Run `pnpm build` before committing frontend changes

## Git

- Commit messages: conventional commits (feat/fix/docs/refactor)
- Co-author line required for AI-assisted commits
