# Sandbox Observation Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "God mode" sandbox where characters wander freely and the user observes and injects world events via a live SSE feed.

**Architecture:** A new FastAPI router (`app/api/sandbox.py`) manages in-memory sandbox sessions with SSE streaming. The frontend composable (`useSandbox.ts`) wraps the four REST endpoints and an `EventSource` connection. `SandboxView.vue` renders the two-column layout with a live feed and event injection panel.

**Tech Stack:** FastAPI + asyncio queues (SSE), Vue 3 + TypeScript, Tailwind CSS v4, `useToast` for notifications, `useI18n` for bilingual strings.

---

### Key Patterns from Existing Code

- **Router pattern:** `router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])`, registered in `create_app()` in `app/main.py`.
- **In-memory store:** `scene.py` uses `_pending_interventions: dict[str, list[str]] = {}` at module level — same pattern here.
- **Test pattern:** `test_projects_api.py` uses `httpx.AsyncClient` + `ASGITransport(app=create_app())`, `asyncio_mode = "auto"` so no `@pytest.mark.asyncio` needed.
- **SSE:** FastAPI's `StreamingResponse` with `media_type="text/event-stream"` and an `asyncio.Queue` per session.
- **Frontend composable:** `useInteractive.ts` pattern — `ref()` state, async functions, returned as plain object.
- **i18n:** Add keys to the `translations` dict in `frontend/src/i18n.ts`.
- **Nav:** `AppLayout.vue` `navItems` array — add entry with `labelKey`, `path`, `icon`.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/api/sandbox.py` | Create | Router: start/inject/stop/feed endpoints, in-memory session store |
| `backend/app/main.py` | Modify | Register sandbox router |
| `backend/tests/test_sandbox_api.py` | Create | 6 pytest-asyncio tests covering all endpoints |
| `frontend/src/api/client.ts` | Modify | Add 3 sandbox API functions |
| `frontend/src/types/api.ts` | Modify | Add `SandboxEvent`, `SandboxSession` types |
| `frontend/src/composables/useSandbox.ts` | Create | Reactive state + start/inject/stop/connectFeed |
| `frontend/src/views/SandboxView.vue` | Create | Two-column layout: live feed + injection panel |
| `frontend/src/router/index.ts` | Modify | Add `/sandbox` route |
| `frontend/src/components/AppLayout.vue` | Modify | Add sandbox nav item after Interactive |
| `frontend/src/i18n.ts` | Modify | Add 14 sandbox i18n keys |

---

### Task 1: Backend — `app/api/sandbox.py`

**Files:**
- Create: `backend/app/api/sandbox.py`

The complete file must be written in chunks (≤50 lines each). Write it in three passes.

- [ ] **Step 1: Write the file header + models (lines 1–55)**

Create `backend/app/api/sandbox.py` with:

```python
"""Sandbox Observation Mode API.

Endpoints:
  POST /api/sandbox/start        — start a sandbox session
  POST /api/sandbox/inject       — inject a world event
  POST /api/sandbox/stop         — stop the sandbox
  GET  /api/sandbox/{id}/feed    — SSE stream of sandbox events
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

# In-memory session store.
# session_id -> {"world_id", "character_ids", "location", "rounds", "queue", "running"}
_sessions: dict[str, dict[str, Any]] = {}


class StartRequest(BaseModel):
    world_id: str
    character_ids: list[str]
    location: str | None = None


class StartResponse(BaseModel):
    session_id: str
    status: str


class InjectRequest(BaseModel):
    session_id: str
    event: str


class OkResponse(BaseModel):
    ok: bool


class StopRequest(BaseModel):
    session_id: str


class StopResponse(BaseModel):
    ok: bool
    rounds: int
```

- [ ] **Step 2: Append the REST endpoints (lines 56–100)**

```python

@router.post("/start", response_model=StartResponse)
async def start_sandbox(req: StartRequest) -> StartResponse:
    """Create a new sandbox session."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "world_id": req.world_id,
        "character_ids": req.character_ids,
        "location": req.location,
        "rounds": 0,
        "queue": asyncio.Queue(),
        "running": True,
    }
    return StartResponse(session_id=session_id, status="running")


@router.post("/inject", response_model=OkResponse)
async def inject_event(req: InjectRequest) -> OkResponse:
    """Inject a world event into a running sandbox session."""
    session = _sessions.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{req.session_id}' not found")
    event_data = json.dumps({"type": "injected", "event": req.event})
    await session["queue"].put(event_data)
    return OkResponse(ok=True)


@router.post("/stop", response_model=StopResponse)
async def stop_sandbox(req: StopRequest) -> StopResponse:
    """Stop a sandbox session and return the round count."""
    session = _sessions.pop(req.session_id, None)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{req.session_id}' not found")
    session["running"] = False
    await session["queue"].put(None)  # signal SSE generator to close
    return StopResponse(ok=True, rounds=session["rounds"])
```

- [ ] **Step 3: Append the SSE feed endpoint + mock generator (lines 101–160)**

```python

_MOCK_EVENTS: list[dict[str, Any]] = [
    {"type": "environment", "content": "The world stirs with quiet energy."},
    {"type": "action", "character": "Alice", "content": "walks toward the garden gate", "round": 1},
    {"type": "thought", "character": "Bob", "content": "I wonder what she's looking for.", "round": 1},
    {"type": "interaction", "from": "Alice", "to": "Bob", "content": "glances back with a smile", "round": 2},
    {"type": "action", "character": "Bob", "content": "follows at a cautious distance", "round": 2},
    {"type": "environment", "content": "A breeze rustles the leaves overhead."},
    {"type": "action", "character": "Alice", "content": "pauses to examine a strange flower", "round": 3},
    {"type": "thought", "character": "Alice", "content": "This wasn't here yesterday.", "round": 3},
]


async def _mock_event_generator(session_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted events until the session is stopped."""
    session = _sessions.get(session_id)
    if session is None:
        return

    mock_idx = 0
    while session.get("running", False):
        # Drain injected events first (non-blocking)
        try:
            item = session["queue"].get_nowait()
            if item is None:
                break
            yield f"data: {item}\n\n"
            continue
        except asyncio.QueueEmpty:
            pass

        # Emit next mock event
        evt = _MOCK_EVENTS[mock_idx % len(_MOCK_EVENTS)]
        session["rounds"] = evt.get("round", session["rounds"])
        yield f"data: {json.dumps(evt)}\n\n"
        mock_idx += 1
        await asyncio.sleep(2)


@router.get("/{session_id}/feed")
async def sandbox_feed(session_id: str) -> StreamingResponse:
    """SSE stream of sandbox events for a running session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return StreamingResponse(
        _mock_event_generator(session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 4: Verify the file is under 500 lines**

```bash
wc -l backend/app/api/sandbox.py
```

Expected: under 160 lines.

---

### Task 2: Backend Tests — `tests/test_sandbox_api.py`

**Files:**
- Create: `backend/tests/test_sandbox_api.py`

Write this file BEFORE implementing Task 1 (TDD red phase). The tests use the same pattern as `test_projects_api.py`.

- [ ] **Step 1: Write the test file**

```python
"""TDD tests for Sandbox Observation Mode API.

Written BEFORE implementation (RED phase).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_start_sandbox_returns_session_id(client):
    """POST /api/sandbox/start returns session_id and status=running."""
    resp = await client.post(
        "/api/sandbox/start",
        json={"world_id": "world-1", "character_ids": ["char-1", "char-2"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["status"] == "running"


async def test_start_sandbox_without_world_id_returns_422(client):
    """POST /api/sandbox/start without world_id returns 422."""
    resp = await client.post(
        "/api/sandbox/start",
        json={"character_ids": ["char-1"]},
    )
    assert resp.status_code == 422


async def test_inject_event_with_valid_session_returns_ok(client):
    """POST /api/sandbox/inject with valid session returns ok=true."""
    start = await client.post(
        "/api/sandbox/start",
        json={"world_id": "world-1", "character_ids": ["char-1"]},
    )
    session_id = start.json()["session_id"]

    resp = await client.post(
        "/api/sandbox/inject",
        json={"session_id": session_id, "event": "A storm rolls in from the north."},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


async def test_inject_event_with_invalid_session_returns_404(client):
    """POST /api/sandbox/inject with unknown session_id returns 404."""
    resp = await client.post(
        "/api/sandbox/inject",
        json={"session_id": "nonexistent-id", "event": "Something happens."},
    )
    assert resp.status_code == 404


async def test_stop_sandbox_returns_ok_and_rounds(client):
    """POST /api/sandbox/stop returns ok=true and rounds count."""
    start = await client.post(
        "/api/sandbox/start",
        json={"world_id": "world-1", "character_ids": ["char-1"]},
    )
    session_id = start.json()["session_id"]

    resp = await client.post(
        "/api/sandbox/stop",
        json={"session_id": session_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "rounds" in data
    assert isinstance(data["rounds"], int)


async def test_feed_returns_sse_content_type(client):
    """GET /api/sandbox/{id}/feed returns text/event-stream content type."""
    start = await client.post(
        "/api/sandbox/start",
        json={"world_id": "world-1", "character_ids": ["char-1"]},
    )
    session_id = start.json()["session_id"]

    # Use stream=True to avoid consuming the full SSE stream
    async with client.stream("GET", f"/api/sandbox/{session_id}/feed") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
```

- [ ] **Step 2: Run tests to confirm RED (all fail — sandbox.py doesn't exist yet)**

```bash
cd Z:/TheWorld/backend && uv run pytest tests/test_sandbox_api.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — that's the RED phase.

- [ ] **Step 3: Implement Task 1 (sandbox.py + register router)**

After Task 1 is done, come back here.

- [ ] **Step 4: Run tests to confirm GREEN**

```bash
cd Z:/TheWorld/backend && uv run pytest tests/test_sandbox_api.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
cd Z:/TheWorld/backend && uv run pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/sandbox.py backend/app/main.py backend/tests/test_sandbox_api.py
git commit -m "feat: sandbox observation mode — backend API + tests"
```

---

### Task 3: Register Router in `app/main.py`

**Files:**
- Modify: `backend/app/main.py`

This is a one-liner change. Do it as part of Task 1 (before running tests).

- [ ] **Step 1: Add the import and `include_router` call**

In `backend/app/main.py`, add after the existing router imports:

```python
from app.api.sandbox import router as sandbox_router
```

And inside `create_app()`, after `app.include_router(projects_router)`:

```python
app.include_router(sandbox_router)
```

- [ ] **Step 2: Verify the app starts without errors**

```bash
cd Z:/TheWorld/backend && uv run python -c "from app.main import create_app; app = create_app(); print('OK')"
```

Expected: `OK`

---

### Task 4: Frontend Types — `src/types/api.ts`

**Files:**
- Modify: `frontend/src/types/api.ts`

- [ ] **Step 1: Append sandbox types to the end of the file**

```typescript
// ---------------------------------------------------------------------------
// Sandbox types
// ---------------------------------------------------------------------------

export type SandboxEventType = 'action' | 'environment' | 'thought' | 'interaction' | 'injected'

export interface SandboxEvent {
  type: SandboxEventType
  character?: string
  from?: string
  to?: string
  content?: string
  event?: string
  round?: number
}

export interface SandboxSession {
  session_id: string
  status: 'running' | 'stopped'
}

export interface SandboxStartRequest {
  world_id: string
  character_ids: string[]
  location?: string
}

export interface SandboxInjectRequest {
  session_id: string
  event: string
}

export interface SandboxStopRequest {
  session_id: string
}

export interface SandboxStopResponse {
  ok: boolean
  rounds: number
}
```

---

### Task 5: Frontend API Client — `src/api/client.ts`

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Append sandbox API functions to the end of the file**

```typescript
// ---------------------------------------------------------------------------
// Sandbox API
// ---------------------------------------------------------------------------

import type {
  SandboxStartRequest,
  SandboxSession,
  SandboxInjectRequest,
  SandboxStopRequest,
  SandboxStopResponse,
} from '../types/api'

export async function startSandbox(req: SandboxStartRequest): Promise<SandboxSession> {
  return request<SandboxSession>('/api/sandbox/start', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function injectSandboxEvent(req: SandboxInjectRequest): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>('/api/sandbox/inject', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function stopSandbox(req: SandboxStopRequest): Promise<SandboxStopResponse> {
  return request<SandboxStopResponse>('/api/sandbox/stop', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}
```

Note: The SSE feed uses `EventSource` directly in the composable — no wrapper needed in `client.ts`.

Note on imports: `client.ts` already has all its imports at the top. The `import type` block above should be moved to the top of the file alongside the existing imports, not left at the bottom. When appending, add only the three `export async function` blocks at the bottom, and add the type names to the existing `import type` block at the top.

---

### Task 6: Frontend Composable — `src/composables/useSandbox.ts`

**Files:**
- Create: `frontend/src/composables/useSandbox.ts`

- [ ] **Step 1: Write the composable (first 50 lines)**

```typescript
import { ref } from 'vue'
import type { SandboxEvent, SandboxStopResponse } from '../types/api'
import { startSandbox, injectSandboxEvent, stopSandbox } from '../api/client'

export function useSandbox() {
  const sessionId = ref('')
  const events = ref<SandboxEvent[]>([])
  const isRunning = ref(false)
  const rounds = ref(0)
  const error = ref<string | null>(null)

  let _eventSource: EventSource | null = null

  async function start(
    worldId: string,
    characterIds: string[],
    location?: string,
  ): Promise<void> {
    error.value = null
    try {
      const resp = await startSandbox({ world_id: worldId, character_ids: characterIds, location })
      sessionId.value = resp.session_id
      isRunning.value = true
      events.value = []
      rounds.value = 0
      connectFeed()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to start sandbox'
    }
  }

  async function inject(event: string): Promise<void> {
    if (!sessionId.value) return
    try {
      await injectSandboxEvent({ session_id: sessionId.value, event })
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to inject event'
    }
  }

  async function stop(): Promise<SandboxStopResponse | null> {
    if (!sessionId.value) return null
    _eventSource?.close()
    _eventSource = null
    try {
      const resp = await stopSandbox({ session_id: sessionId.value })
      rounds.value = resp.rounds
      isRunning.value = false
      sessionId.value = ''
      return resp
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to stop sandbox'
      return null
    }
  }
```

- [ ] **Step 2: Append the connectFeed function and return statement**

```typescript
  function connectFeed(): void {
    if (!sessionId.value) return
    _eventSource?.close()
    _eventSource = new EventSource(`/api/sandbox/${sessionId.value}/feed`)

    _eventSource.onmessage = (e: MessageEvent) => {
      try {
        const evt = JSON.parse(e.data) as SandboxEvent
        events.value.push(evt)
      } catch {
        // ignore malformed events
      }
    }

    _eventSource.onerror = () => {
      if (!isRunning.value) return
      // Reconnect after 3 seconds on error
      setTimeout(() => {
        if (isRunning.value) connectFeed()
      }, 3000)
    }
  }

  return {
    sessionId,
    events,
    isRunning,
    rounds,
    error,
    start,
    inject,
    stop,
    connectFeed,
  }
}
```

---

### Task 7: i18n Keys — `src/i18n.ts`

**Files:**
- Modify: `frontend/src/i18n.ts`

- [ ] **Step 1: Add sandbox keys to the translations object**

In `frontend/src/i18n.ts`, append these entries inside the `translations` object (before the closing `}`):

```typescript
  // Sandbox
  'nav.sandbox': { zh: '沙盒观察', en: 'Sandbox' },
  'sandbox.title': { zh: '沙盒观察', en: 'Sandbox Observation' },
  'sandbox.subtitle': { zh: '观察角色自由行动，注入世界事件', en: 'Watch characters roam freely, inject world events' },
  'sandbox.start': { zh: '开始观察', en: 'Start Observing' },
  'sandbox.stop': { zh: '停止', en: 'Stop' },
  'sandbox.inject': { zh: '注入事件', en: 'Inject Event' },
  'sandbox.inject_placeholder': { zh: '描述世界事件...', en: 'Describe a world event...' },
  'sandbox.quick_storm': { zh: '暴风雨来袭', en: 'Storm arrives' },
  'sandbox.quick_npc': { zh: '陌生人出现', en: 'Stranger appears' },
  'sandbox.quick_quake': { zh: '地震', en: 'Earthquake' },
  'sandbox.quick_news': { zh: '传来消息', en: 'News arrives' },
  'sandbox.feed_empty': { zh: '等待角色行动...', en: 'Waiting for characters...' },
  'sandbox.stopped': { zh: '沙盒已停止', en: 'Sandbox stopped' },
  'sandbox.select_chars': { zh: '选择角色', en: 'Select Characters' },
  'sandbox.location': { zh: '地点（可选）', en: 'Location (optional)' },
```

---

### Task 8: Router + Nav

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/AppLayout.vue`

- [ ] **Step 1: Add the `/sandbox` route**

In `frontend/src/router/index.ts`, add the import:

```typescript
import SandboxView from '../views/SandboxView.vue'
```

Add the route after the Interactive route:

```typescript
{ path: '/sandbox', name: 'Sandbox', component: SandboxView },
```

- [ ] **Step 2: Add the sandbox nav item**

In `frontend/src/components/AppLayout.vue`, add after the Interactive nav item in `navItems`:

```typescript
{ labelKey: 'nav.sandbox', path: '/sandbox', icon: '🔭' },
```

---

### Task 9: SandboxView — `src/views/SandboxView.vue`

**Files:**
- Create: `frontend/src/views/SandboxView.vue`

Write in three chunks.

- [ ] **Step 1: Write the script setup block**

```vue
<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useI18n } from '../i18n'
import { useSandbox } from '../composables/useSandbox'
import { useToast } from '../composables/useToast'
import { listCharacters } from '../api/client'
import type { CharacterProfile, SandboxEvent } from '../types/api'

const { t } = useI18n()
const sandbox = useSandbox()
const { success: toastSuccess } = useToast()

const availableChars = ref<CharacterProfile[]>([])
const selectedCharIds = ref<string[]>([])
const locationInput = ref('')
const loadingChars = ref(false)
const feedEl = ref<HTMLElement | null>(null)
const injectText = ref('')

async function loadChars(): Promise<void> {
  loadingChars.value = true
  try { availableChars.value = await listCharacters() } catch { /* ignore */ }
  finally { loadingChars.value = false }
}
loadChars()

watch(() => sandbox.events.value.length, async () => {
  await nextTick()
  if (feedEl.value) feedEl.value.scrollTop = feedEl.value.scrollHeight
})

async function handleStart(): Promise<void> {
  if (selectedCharIds.value.length === 0) return
  await sandbox.start('default-world', selectedCharIds.value, locationInput.value || undefined)
}

async function handleStop(): Promise<void> {
  const result = await sandbox.stop()
  if (result) toastSuccess(t('sandbox.stopped'))
}

async function handleInject(): Promise<void> {
  if (!injectText.value.trim()) return
  await sandbox.inject(injectText.value.trim())
  injectText.value = ''
}

async function handleQuickEvent(key: string): Promise<void> {
  await sandbox.inject(t(key))
}

function toggleChar(id: string): void {
  const idx = selectedCharIds.value.indexOf(id)
  if (idx === -1) selectedCharIds.value.push(id)
  else selectedCharIds.value.splice(idx, 1)
}

function getEventIcon(evt: SandboxEvent): string {
  switch (evt.type) {
    case 'action': return '🧑'
    case 'environment': return '🌍'
    case 'thought': return '💭'
    case 'interaction': return '💬'
    case 'injected': return '⚡'
    default: return '•'
  }
}
</script>
```

- [ ] **Step 2: Write the template — header + start form**

```vue
<template>
  <div class="space-y-4 max-w-6xl mx-auto">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-gray-100">{{ t('sandbox.title') }}</h1>
        <p class="text-sm text-gray-500 mt-1">{{ t('sandbox.subtitle') }}</p>
      </div>
      <button v-if="sandbox.isRunning.value" @click="handleStop"
        class="px-4 py-2 bg-red-700 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors">
        {{ t('sandbox.stop') }}
      </button>
    </div>

    <div v-if="sandbox.error.value" class="bg-red-900/20 border border-red-800 rounded-lg p-3">
      <span class="text-sm text-red-400">{{ sandbox.error.value }}</span>
    </div>

    <div v-if="!sandbox.isRunning.value" class="bg-gray-900 rounded-lg border border-gray-800 p-4 space-y-4">
      <h2 class="text-base font-semibold text-gray-100">{{ t('sandbox.select_chars') }}</h2>
      <div v-if="loadingChars" class="text-sm text-gray-500 animate-pulse">{{ t('general.loading') }}</div>
      <div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <button v-for="char in availableChars" :key="char.id" @click="toggleChar(char.id)"
          class="flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors text-left"
          :class="selectedCharIds.includes(char.id)
            ? 'border-indigo-500 bg-indigo-900/30 text-indigo-300'
            : 'border-gray-700 bg-gray-800 text-gray-400 hover:text-gray-200'">
          <span class="text-base">🧑</span>
          <span class="truncate">{{ char.name }}</span>
        </button>
      </div>
      <div>
        <label class="block text-xs text-gray-400 mb-1">{{ t('sandbox.location') }}</label>
        <input v-model="locationInput" type="text"
          class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
          :placeholder="t('sandbox.location')" />
      </div>
      <button @click="handleStart" :disabled="selectedCharIds.length === 0"
        class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors">
        {{ t('sandbox.start') }}
      </button>
    </div>
```

- [ ] **Step 3: Write the template — two-column live layout + closing tags**

```vue
    <div v-if="sandbox.isRunning.value" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 bg-gray-900 rounded-lg border border-gray-800 flex flex-col" style="height: 520px;">
        <div class="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
          <span class="text-sm font-semibold text-gray-200">Live Feed</span>
          <span class="text-xs text-gray-500">Round {{ sandbox.rounds.value }}</span>
        </div>
        <div ref="feedEl" class="flex-1 overflow-y-auto p-4 space-y-2">
          <p v-if="sandbox.events.value.length === 0" class="text-sm text-gray-500 italic">
            {{ t('sandbox.feed_empty') }}
          </p>
          <div v-for="(evt, idx) in sandbox.events.value" :key="idx" class="flex items-start gap-2 text-sm">
            <span class="flex-shrink-0 text-base leading-5">{{ getEventIcon(evt) }}</span>
            <span class="text-gray-300">
              <span v-if="evt.character" class="font-medium text-indigo-300">{{ evt.character }}: </span>
              <span v-if="evt.from && evt.to" class="font-medium text-indigo-300">{{ evt.from }} → {{ evt.to }}: </span>
              <span v-if="evt.type === 'injected'" class="text-yellow-400 italic">{{ evt.event }}</span>
              <span v-else>{{ evt.content }}</span>
            </span>
          </div>
        </div>
      </div>

      <div class="bg-gray-900 rounded-lg border border-gray-800 p-4 space-y-4">
        <h2 class="text-sm font-semibold text-gray-200">{{ t('sandbox.inject') }}</h2>
        <div class="space-y-2">
          <textarea v-model="injectText" rows="4" :placeholder="t('sandbox.inject_placeholder')"
            class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none" />
          <button @click="handleInject" :disabled="!injectText.trim()"
            class="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors">
            {{ t('sandbox.inject') }}
          </button>
        </div>
        <div class="border-t border-gray-800 pt-3 space-y-2">
          <p class="text-xs text-gray-500">Quick Events</p>
          <div class="grid grid-cols-2 gap-2">
            <button v-for="key in ['sandbox.quick_storm','sandbox.quick_npc','sandbox.quick_quake','sandbox.quick_news']"
              :key="key" @click="handleQuickEvent(key)"
              class="px-2 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 rounded text-xs transition-colors">
              {{ t(key) }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
```

---

### Task 10: Verify Frontend Build

- [ ] **Step 1: Run the TypeScript build**

```bash
cd Z:/TheWorld/frontend && pnpm build
```

Expected: zero type errors, build succeeds.

- [ ] **Step 2: Fix any type errors**

Common issues:
- `useToast` — the composable exports `{ show, success, error, warning, dismiss }`. Use `const { success: toastSuccess } = useToast()` and call `toastSuccess(message)` — not `showToast`.
- `SandboxEvent` import — ensure it's in the `import type` line at the top of `SandboxView.vue`.
- `client.ts` imports — the `import type` block at the top of `client.ts` must include the new sandbox types.

- [ ] **Step 3: Commit frontend changes**

```bash
git add frontend/src/api/client.ts frontend/src/types/api.ts frontend/src/composables/useSandbox.ts frontend/src/views/SandboxView.vue frontend/src/router/index.ts frontend/src/components/AppLayout.vue frontend/src/i18n.ts
git commit -m "feat: sandbox observation mode — frontend view, composable, nav"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|---|---|
| POST /api/sandbox/start | Task 1 |
| POST /api/sandbox/inject | Task 1 |
| POST /api/sandbox/stop | Task 1 |
| GET /api/sandbox/{id}/feed SSE | Task 1 |
| Register router in main.py | Task 3 |
| 6 backend tests | Task 2 |
| SandboxEvent + session types | Task 4 |
| API client functions | Task 5 |
| useSandbox composable | Task 6 |
| 14 i18n keys | Task 7 |
| /sandbox route | Task 8 |
| nav.sandbox nav item | Task 8 |
| Two-column layout | Task 9 |
| Start form + character checkboxes | Task 9 |
| Live feed auto-scroll | Task 9 |
| Quick event buttons | Task 9 |
| Stop button | Task 9 |
| pnpm build zero errors | Task 10 |

All spec requirements covered. No placeholders. Types consistent across tasks.
