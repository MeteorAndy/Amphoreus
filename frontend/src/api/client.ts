import type {
  CharacterProfile,
  ChatRequest,
  ChatResponse,
  CreateCharacterRequest,
  CreateOutlineRequest,
  CreateSceneRequest,
  GenerateRequest,
  GuardianValidationRequest,
  GuardianValidationResult,
  InterventionRequest,
  NarrativeFormat,
  PlotOutline,
  Relationship,
  RelationshipRequest,
  SceneRunRequest,
  SceneSpec,
  SceneStatus,
  TitleCandidate,
  UpdateCharacterRequest,
  WorldState,
  WriterOutput,
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

async function requestBlob(url: string): Promise<Blob> {
  const res = await fetch(url)
  if (!res.ok) throw new ApiError(res.status, await res.text().catch(() => 'Unknown error'))
  return res.blob()
}

// World Builder API
export async function worldChat(req: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>('/api/world/chat', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function uploadDocument(file: File): Promise<WorldState> {
  const formData = new FormData()
  formData.append('file', file)
  return request<WorldState>('/api/world/document', {
    method: 'POST',
    body: formData,
  })
}

export async function getWorldState(): Promise<WorldState> {
  return request<WorldState>('/api/world/state')
}

export async function resetWorld(): Promise<void> {
  return request<void>('/api/world/state', { method: 'DELETE' })
}

// Characters API
export async function listCharacters(): Promise<CharacterProfile[]> {
  return request<CharacterProfile[]>('/api/characters')
}

export async function createCharacter(data: CreateCharacterRequest): Promise<CharacterProfile> {
  return request<CharacterProfile>('/api/characters', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getCharacter(id: string): Promise<CharacterProfile> {
  return request<CharacterProfile>(`/api/characters/${id}`)
}

export async function updateCharacter(id: string, data: UpdateCharacterRequest): Promise<CharacterProfile> {
  return request<CharacterProfile>(`/api/characters/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCharacter(id: string): Promise<void> {
  return request<void>(`/api/characters/${id}`, { method: 'DELETE' })
}

export async function listRelationships(): Promise<Relationship[]> {
  return request<Relationship[]>('/api/characters/relationships')
}

export async function createRelationship(data: RelationshipRequest): Promise<Relationship> {
  return request<Relationship>('/api/characters/relationships', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// Plot API
export async function listOutlines(): Promise<PlotOutline[]> {
  return request<PlotOutline[]>('/api/plot/outlines')
}

export async function createOutline(data: CreateOutlineRequest): Promise<PlotOutline> {
  return request<PlotOutline>('/api/plot/outlines', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getOutline(id: string): Promise<PlotOutline> {
  return request<PlotOutline>(`/api/plot/outlines/${id}`)
}

export async function updateOutline(id: string, data: Partial<CreateOutlineRequest>): Promise<PlotOutline> {
  return request<PlotOutline>(`/api/plot/outlines/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteOutline(id: string): Promise<void> {
  return request<void>(`/api/plot/outlines/${id}`, { method: 'DELETE' })
}

export async function createScene(outlineId: string, data: CreateSceneRequest): Promise<SceneSpec> {
  return request<SceneSpec>(`/api/plot/outlines/${outlineId}/scenes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateScene(id: string, data: Partial<CreateSceneRequest>): Promise<SceneSpec> {
  return request<SceneSpec>(`/api/plot/scenes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteScene(id: string): Promise<void> {
  return request<void>(`/api/plot/scenes/${id}`, { method: 'DELETE' })
}

export async function reorderScenes(sceneIds: string[]): Promise<void> {
  return request<void>('/api/plot/scenes/reorder', {
    method: 'POST',
    body: JSON.stringify({ scene_ids: sceneIds }),
  })
}

// Scene Engine API
export async function getSceneStatus(): Promise<SceneStatus> {
  return request<SceneStatus>('/api/scene/status')
}

export async function startScene(req: SceneRunRequest): Promise<SceneStatus> {
  return request<SceneStatus>('/api/scene/start', {
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

// Guardian API
export async function validateContent(req: GuardianValidationRequest): Promise<GuardianValidationResult> {
  return request<GuardianValidationResult>('/api/guardian/validate', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

// Narrative Writer API
export async function generateNarrative(req: GenerateRequest): Promise<WriterOutput> {
  return request<WriterOutput>('/api/writer/generate', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function getWriterOutput(id: string): Promise<WriterOutput> {
  return request<WriterOutput>(`/api/writer/output/${id}`)
}

export async function getTitleCandidates(plotId: string): Promise<TitleCandidate[]> {
  return request<TitleCandidate[]>(`/api/writer/titles?plot_id=${plotId}`)
}

export async function exportOutput(outputId: string, format: NarrativeFormat): Promise<Blob> {
  return requestBlob(`/api/writer/export/${outputId}?format=${format}`)
}

// WebSocket for scene execution
export function createSceneWebSocket(): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return new WebSocket(`${protocol}//${window.location.host}/api/scene/ws/run`)
}
