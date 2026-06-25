import type {
  CharacterProfile,
  NetworkData,
  PathStep,
  PlotOutlineResponse,
  Relationship,
  BuildRelationshipsRequest,
  SceneRunRequest,
  ConvertRequest,
  ConvertResponse,
  GuardianEvaluateRequest,
  GuardianSceneInterventionRequest,
  GuardianResult,
  InterventionRequest,
  InterventionResponse,
  WorldState,
  WorldBuildResponse,
  SandboxStartRequest,
  SandboxStartResponse,
  DocumentParseResponse,
  FormatsResponse,
  PlotConsistencyCheck,
  PlotTemplates,
  AddSceneRequest,
  SceneArchive,
  RoundEntry,
  Project,
  ProjectState,
  CreateProjectRequest,
  PipelineConfig,
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

const API_BASE = ''

// ---------------------------------------------------------------------------
// World Builder API
// ---------------------------------------------------------------------------

export async function startWorldBuild(seedIdea: string): Promise<WorldBuildResponse> {
  return request<WorldBuildResponse>(`${API_BASE}/api/world/build/start`, {
    method: 'POST',
    body: JSON.stringify({ seed_idea: seedIdea }),
  })
}

export async function continueWorldBuild(sessionId: string, userInput: string): Promise<WorldBuildResponse> {
  return request<WorldBuildResponse>(`${API_BASE}/api/world/build/continue`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, user_input: userInput }),
  })
}

export async function getWorldBuildSession(sessionId: string): Promise<WorldBuildResponse> {
  return request<WorldBuildResponse>(`${API_BASE}/api/world/build/${sessionId}`)
}

export async function finalizeWorldBuild(sessionId: string): Promise<WorldState> {
  return request<WorldState>(`${API_BASE}/api/world/build/finalize`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}

export async function uploadDocument(file: File): Promise<DocumentParseResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return request<DocumentParseResponse>(`${API_BASE}/api/world/parse`, {
    method: 'POST',
    body: formData,
  })
}

export async function getSupportedFormats(): Promise<FormatsResponse> {
  return request<FormatsResponse>(`${API_BASE}/api/world/formats`)
}

export async function getWorldRules(): Promise<Array<{ path: string; l0: string; score: number }>> {
  return request(`${API_BASE}/api/world/rules`)
}

export async function getWorldLocations(): Promise<Array<Record<string, unknown>>> {
  return request(`${API_BASE}/api/world/locations`)
}

export async function getWorldFactions(): Promise<Array<Record<string, unknown>>> {
  return request(`${API_BASE}/api/world/factions`)
}

export async function getWorldTimeline(): Promise<Array<Record<string, unknown>>> {
  return request(`${API_BASE}/api/world/timeline`)
}

// ---------------------------------------------------------------------------
// Characters API
// ---------------------------------------------------------------------------

export async function generateCharacters(worldId: string, count: number = 5): Promise<CharacterProfile[]> {
  return request<CharacterProfile[]>(`${API_BASE}/api/characters/generate`, {
    method: 'POST',
    body: JSON.stringify({ world_id: worldId, count }),
  })
}

export async function listCharacters(): Promise<CharacterProfile[]> {
  return request<CharacterProfile[]>(`${API_BASE}/api/characters`)
}

export async function getCharacter(id: string): Promise<CharacterProfile> {
  return request<CharacterProfile>(`${API_BASE}/api/characters/${id}`)
}

export async function updateCharacter(id: string, data: Partial<CharacterProfile>): Promise<CharacterProfile> {
  return request<CharacterProfile>(`${API_BASE}/api/characters/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCharacter(id: string): Promise<void> {
  return request<void>(`${API_BASE}/api/characters/${id}`, { method: 'DELETE' })
}

export async function refineCharacter(charId: string, feedback: string): Promise<CharacterProfile> {
  return request<CharacterProfile>(`${API_BASE}/api/characters/${charId}/refine`, {
    method: 'POST',
    body: JSON.stringify({ feedback }),
  })
}

export async function buildRelationships(characterIds: string[]): Promise<Relationship[]> {
  const req: BuildRelationshipsRequest = { character_ids: characterIds }
  const raw = await request<Relationship[]>(`${API_BASE}/api/characters/relationships/build`, {
    method: 'POST',
    body: JSON.stringify(req),
  })
  return raw.map(normalizeRelationship)
}

export async function getCharacterNetwork(charId: string, depth: number = 2): Promise<NetworkData> {
  return request<NetworkData>(`${API_BASE}/api/characters/relationships/${charId}?depth=${depth}`)
}

export async function listRelationships(): Promise<Relationship[]> {
  const raw = await request<Relationship[]>(`${API_BASE}/api/characters/relationships`)
  return raw.map(normalizeRelationship)
}

function normalizeRelationship(r: Relationship): Relationship {
  return {
    ...r,
    from_id: r.from_id || r.source_id || '',
    to_id: r.to_id || r.target_id || '',
    strength: r.strength ?? 1,
  }
}

export async function getRelationshipPath(fromId: string, toId: string): Promise<PathStep[]> {
  const raw = await request<{
    path: Array<string | { character_id: string; name?: string }>
    [key: string]: unknown
  }[]>(`${API_BASE}/api/characters/relationships/path?from_id=${encodeURIComponent(fromId)}&to_id=${encodeURIComponent(toId)}`)
  return raw.map((step) => ({
    ...step,
    path: step.path.map((node) => {
      if (typeof node === 'string') {
        return node
      }
      return node.character_id
    }),
  })) as PathStep[]
}

export const createOutline = generatePlot

// ---------------------------------------------------------------------------
// Plot API
// ---------------------------------------------------------------------------

export async function getPlotTemplates(): Promise<string[]> {
  try {
    const resp = await request<PlotTemplates | string[]>(`${API_BASE}/api/plot/templates`)
    if (Array.isArray(resp)) return resp
    return Object.keys(resp.templates || {})
  } catch {
    return ['three_act', 'heros_journey', 'save_the_cat', 'five_act']
  }
}

export async function generatePlot(data: {
  world_id: string
  structure: string
  character_ids: string[]
}): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>(`${API_BASE}/api/plot/generate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getPlot(plotId: string): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>(`${API_BASE}/api/plot/${plotId}`)
}

export async function updatePlot(plotId: string, data: {
  acts?: Record<string, unknown>[]
  character_arcs?: Record<string, string[]>
}): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>(`${API_BASE}/api/plot/${plotId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deletePlot(plotId: string): Promise<void> {
  return request<void>(`${API_BASE}/api/plot/${plotId}`, { method: 'DELETE' })
}

export async function refinePlot(plotId: string, feedback: string): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>(`${API_BASE}/api/plot/refine`, {
    method: 'POST',
    body: JSON.stringify({ plot_id: plotId, feedback }),
  })
}

export async function addScene(plotId: string, data: AddSceneRequest): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>(`${API_BASE}/api/plot/${plotId}/scenes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export const addSceneToPlot = addScene

export async function deleteScene(plotId: string, sceneId: string): Promise<PlotOutlineResponse> {
  return request<PlotOutlineResponse>(`${API_BASE}/api/plot/${plotId}/scenes/${sceneId}`, { method: 'DELETE' })
}

export const deleteSceneFromPlot = deleteScene

export async function checkPlotConsistency(plotId: string, sceneId: string): Promise<PlotConsistencyCheck> {
  return request<PlotConsistencyCheck>(`${API_BASE}/api/plot/check`, {
    method: 'POST',
    body: JSON.stringify({ plot_id: plotId, scene_id: sceneId }),
  })
}

// ---------------------------------------------------------------------------
// Scene Engine API
// ---------------------------------------------------------------------------

export async function runScene(req: SceneRunRequest): Promise<SceneArchive> {
  return request<SceneArchive>(`${API_BASE}/api/scene/run`, {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function getSceneArchive(sceneId: string): Promise<SceneArchive> {
  return request<SceneArchive>(`${API_BASE}/api/scene/${sceneId}/archive`)
}

export async function getSceneRounds(sceneId: string): Promise<RoundEntry[]> {
  return request<RoundEntry[]>(`${API_BASE}/api/scene/${sceneId}/rounds`)
}

export async function getSceneRound(sceneId: string, roundNum: number): Promise<RoundEntry> {
  return request<RoundEntry>(`${API_BASE}/api/scene/${sceneId}/rounds/${roundNum}`)
}

export async function interveneScene(req: InterventionRequest): Promise<InterventionResponse> {
  return request<InterventionResponse>(`${API_BASE}/api/scene/intervene`, {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function createSceneWebSocket(): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return new WebSocket(`${protocol}//${host}${API_BASE}/api/scene/ws/run`)
}

// ---------------------------------------------------------------------------
// Guardian API
// ---------------------------------------------------------------------------

export async function evaluatePlot(req: GuardianEvaluateRequest): Promise<GuardianResult> {
  return request<GuardianResult>(`${API_BASE}/api/guardian/evaluate`, {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function evaluateSceneIntervention(req: GuardianSceneInterventionRequest): Promise<GuardianResult> {
  return request<GuardianResult>(`${API_BASE}/api/guardian/evaluate/scene`, {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

// ---------------------------------------------------------------------------
// Narrative Writer API
// ---------------------------------------------------------------------------

export async function generateNarrative(req: ConvertRequest): Promise<ConvertResponse> {
  return request<ConvertResponse>(`${API_BASE}/api/writer/convert`, {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export const convertScenesToNarrative = generateNarrative

export async function getWriterFormats(): Promise<FormatsResponse> {
  return request<FormatsResponse>(`${API_BASE}/api/writer/formats`)
}

export async function getTitleCandidates(plotId: string): Promise<string[]> {
  const resp = await request<{ titles: { title: string; subtitle?: string; description?: string }[] }>(
    `${API_BASE}/api/writer/titles?plot_id=${encodeURIComponent(plotId)}`,
  )
  return resp.titles.map((t) => t.title)
}

export async function exportOutput(content: string, format: string): Promise<Blob> {
  return requestBlob(`${API_BASE}/api/writer/export`, {
    method: 'POST',
    body: JSON.stringify({ content, format, export_format: format }),
  })
}

export const exportNarrative = exportOutput

// ---------------------------------------------------------------------------
// Pipeline API
// ---------------------------------------------------------------------------

export function startPipeline(config: PipelineConfig): EventSource {
  const params = new URLSearchParams()
  Object.entries(config).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      params.set(key, String(value))
    }
  })
  return new EventSource(`${API_BASE}/api/pipeline/run?${params.toString()}`)
}

export async function startPipelinePost(config: PipelineConfig): Promise<Response> {
  return fetch(`${API_BASE}/api/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
}

// ---------------------------------------------------------------------------
// Projects API
// ---------------------------------------------------------------------------

export async function listProjects(): Promise<{ projects: Project[] }> {
  return request<{ projects: Project[] }>(`${API_BASE}/api/projects`)
}

export async function createProject(req: CreateProjectRequest): Promise<{ id: string; name: string; created_at: string }> {
  return request(`${API_BASE}/api/projects`, {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function getProject(projectId: string): Promise<ProjectState> {
  return request<ProjectState>(`${API_BASE}/api/projects/${projectId}`)
}

export async function updateProject(projectId: string, data: Partial<ProjectState>): Promise<ProjectState> {
  return request<ProjectState>(`${API_BASE}/api/projects/${projectId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteProject(projectId: string): Promise<void> {
  return request<void>(`${API_BASE}/api/projects/${projectId}`, { method: 'DELETE' })
}

// ---------------------------------------------------------------------------
// Sandbox API
// ---------------------------------------------------------------------------

export async function startSandbox(req: SandboxStartRequest): Promise<SandboxStartResponse> {
  return request<SandboxStartResponse>(`${API_BASE}/api/sandbox/start`, {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function injectSandboxEvent(sessionId: string, event: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`${API_BASE}/api/sandbox/inject`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, event }),
  })
}

export async function stopSandbox(sessionId: string): Promise<{ ok: boolean; rounds: number }> {
  return request<{ ok: boolean; rounds: number }>(`${API_BASE}/api/sandbox/stop`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}

export function createSandboxEventSource(sessionId: string): EventSource {
  return new EventSource(`${API_BASE}/api/sandbox/${sessionId}/feed`)
}
