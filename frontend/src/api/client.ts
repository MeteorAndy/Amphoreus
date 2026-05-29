import type {
  CharacterProfile,
  ChatRequest,
  ChatResponse,
  ConvertRequest,
  ConvertResponse,
  GuardianValidationRequest,
  GuardianValidationResult,
  InterventionRequest,
  NarrativeFormat,
  NetworkData,
  PathStep,
  PlotOutlineResponse,
  Relationship,
  RelationshipRequest,
  SceneRunRequest,
  SceneStatus,
  TemplatesResponse,
  TitleCandidate,
  WorldState,
  WorldBuildResponse,
  SandboxStartRequest,
  SandboxStartResponse,
} from '../types/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(url, { ...options, headers })
  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error')
    throw new ApiError(res.status, text)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

async function requestBlob(url: string, options: RequestInit = {}): Promise<Blob> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(url, { ...options, headers })
  if (!res.ok) throw new ApiError(res.status, await res.text().catch(() => 'Unknown error'))
  return res.blob()
}

// World Builder API
export async function worldChat(req: ChatRequest): Promise<ChatResponse> {
  const url = req.world_id ? '/api/world/build/continue' : '/api/world/build/start'
  const body = req.world_id
    ? JSON.stringify({ session_id: req.world_id, user_input: req.message })
    : JSON.stringify({ seed_idea: req.message })
  return request<ChatResponse>(url, { method: 'POST', body })
}

export async function uploadDocument(file: File): Promise<WorldState> {
  const formData = new FormData()
  formData.append('file', file)
  return request<WorldState>('/api/world/parse', {
    method: 'POST',
    body: formData,
  })
}

export async function getWorldState(sessionId?: string): Promise<WorldState> {
  if (!sessionId) return Promise.reject(new Error('No session ID'))
  return request<WorldState>(`/api/world/build/${sessionId}`)
}

export async function resetWorld(sessionId: string): Promise<void> {
  return request<void>('/api/world/build/finalize', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}

export async function startWorldBuild(seedIdea: string): Promise<WorldBuildResponse> {
  return request<WorldBuildResponse>('/api/world/build/start', {
    method: 'POST',
    body: JSON.stringify({ seed_idea: seedIdea }),
  })
}

export async function continueWorldBuild(sessionId: string, userInput: string): Promise<WorldBuildResponse> {
  return request<WorldBuildResponse>('/api/world/build/continue', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, user_input: userInput }),
  })
}

export async function finalizeWorldBuild(sessionId: string): Promise<WorldState> {
  return request<WorldState>('/api/world/build/finalize', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}

// ---------------------------------------------------------------------------
// Characters API
// ---------------------------------------------------------------------------

export async function generateCharacters(worldId: string, count: number = 5): Promise<CharacterProfile[]> {
  return request<CharacterProfile[]>('/api/characters/generate', {
    method: 'POST',
    body: JSON.stringify({ world_id: worldId, count }),
  })
}

export async function listCharacters(): Promise<CharacterProfile[]> {
  return request<CharacterProfile[]>('/api/characters')
}

export async function getCharacter(id: string): Promise<CharacterProfile> {
  return request<CharacterProfile>(`/api/characters/${id}`)
}

export async function updateCharacter(id: string, data: Partial<CharacterProfile>): Promise<CharacterProfile> {
  return request<CharacterProfile>(`/api/characters/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCharacter(id: string): Promise<void> {
  return request<void>(`/api/characters/${id}`, { method: 'DELETE' })
}

export async function refineCharacter(charId: string, feedback: string): Promise<CharacterProfile> {
  return request<CharacterProfile>(`/api/characters/${charId}/refine`, {
    method: 'POST',
    body: JSON.stringify({ feedback }),
  })
}

export async function listRelationships(): Promise<Relationship[]> {
  return request<Relationship[]>('/api/characters/relationships')
}

export async function getCharacterNetwork(charId: string): Promise<NetworkData> {
  return request<NetworkData>(`/api/characters/relationships/${charId}`)
}

export async function getRelationshipPath(fromId: string, toId: string): Promise<PathStep[]> {
  return request<PathStep[]>(`/api/characters/relationships/path?from_id=${encodeURIComponent(fromId)}&to_id=${encodeURIComponent(toId)}`)
}

export async function createRelationship(data: RelationshipRequest): Promise<Relationship> {
  return request<Relationship>('/api/characters/relationships/build', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ---------------------------------------------------------------------------
// Plot API
// ---------------------------------------------------------------------------

export async function getPlotTemplates(): Promise<TemplatesResponse> {
  return request<TemplatesResponse>('/api/plot/templates')
}

export async function createOutline(data: {
  world_id: string
  structure: string
  character_ids: string[]
}): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>('/api/plot/generate', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getPlot(plotId: string): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>(`/api/plot/${plotId}`)
}

export async function updatePlot(plotId: string, data: { acts?: Record<string, unknown>[]; character_arcs?: Record<string, string[]> }): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>(`/api/plot/${plotId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deletePlot(plotId: string): Promise<void> {
  return request<void>(`/api/plot/${plotId}`, { method: 'DELETE' })
}

export async function refinePlot(plotId: string, feedback: string): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>('/api/plot/refine', {
    method: 'POST',
    body: JSON.stringify({ plot_id: plotId, feedback }),
  })
}

export async function addScene(plotId: string, data: {
  title: string
  location: string
  cast: string[]
  conflict: string
  goal: string
  expected_outcome: string
  causal_chain?: string[]
}): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>(`/api/plot/${plotId}/scenes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteScene(plotId: string, sceneId: string): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>(`/api/plot/${plotId}/scenes/${sceneId}`, { method: 'DELETE' })
}

export async function checkPlotConsistency(plotId: string, sceneId: string): Promise<{
  scene_id: string
  consistent: boolean
  issues: string[]
  suggested_fixes: string[]
}> {
  return request('/api/plot/check', {
    method: 'POST',
    body: JSON.stringify({ plot_id: plotId, scene_id: sceneId }),
  })
}

// ---------------------------------------------------------------------------
// Scene Engine API
// ---------------------------------------------------------------------------

export async function getSceneStatus(): Promise<SceneStatus> {
  return request<SceneStatus>('/api/scene/status')
}

export async function startScene(req: SceneRunRequest): Promise<SceneStatus> {
  return request<SceneStatus>('/api/scene/run', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function interveneScene(req: InterventionRequest): Promise<unknown> {
  return request<unknown>('/api/scene/intervene', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function endScene(): Promise<void> {
  return request<void>('/api/scene/end', { method: 'POST' })
}

// ---------------------------------------------------------------------------
// Guardian API
// ---------------------------------------------------------------------------

export async function validateContent(req: GuardianValidationRequest): Promise<GuardianValidationResult> {
  return request<GuardianValidationResult>('/api/guardian/evaluate', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

// ---------------------------------------------------------------------------
// Narrative Writer API
// ---------------------------------------------------------------------------

export async function generateNarrative(req: ConvertRequest): Promise<ConvertResponse> {
  return request<ConvertResponse>('/api/writer/convert', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function getTitleCandidates(plotId: string): Promise<TitleCandidate[]> {
  return request<TitleCandidate[]>(`/api/writer/titles?plot_id=${plotId}`)
}

export async function exportOutput(content: string, format: NarrativeFormat): Promise<Blob> {
  return requestBlob('/api/writer/export', {
    method: 'POST',
    body: JSON.stringify({ content, format, export_format: format }),
  })
}

// ---------------------------------------------------------------------------
// WebSocket for scene execution
// ---------------------------------------------------------------------------

export function createSceneWebSocket(): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return new WebSocket(`${protocol}//${window.location.host}/api/scene/ws/run`)
}

// ---------------------------------------------------------------------------
// Sandbox API
// ---------------------------------------------------------------------------

export async function startSandbox(req: SandboxStartRequest): Promise<SandboxStartResponse> {
  return request<SandboxStartResponse>('/api/sandbox/start', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function injectSandboxEvent(sessionId: string, event: string): Promise<void> {
  return request<void>('/api/sandbox/inject', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, event }),
  })
}

export async function stopSandbox(sessionId: string): Promise<{ ok: boolean; rounds: number }> {
  return request<{ ok: boolean; rounds: number }>('/api/sandbox/stop', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}
