export interface Location {
  name: string
  description: string
}

export interface Faction {
  name: string
  description: string
  members: string[]
}

export interface TimelineEntry {
  date: string
  event: string
  description: string
}

export interface WorldState {
  world_id: string
  name: string
  description: string
  rules: string[]
  locations: Location[]
  factions: Faction[]
  timeline: TimelineEntry[]
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatRequest {
  message: string
  world_id?: string
}

export interface ChatResponse {
  reply: string
  world_state?: WorldState
}

export interface Relationship {
  character_id: string
  character_name: string
  relationship_type: string
  strength: number
}

export interface CharacterProfile {
  id: string
  name: string
  age?: number
  role: string
  traits: string[]
  background: string
  goals: string[]
  appearance?: string
  relationships: Relationship[]
}

export interface CreateCharacterRequest {
  name: string
  age?: number
  role: string
  traits: string[]
  background: string
  goals: string[]
  appearance?: string
}

export interface UpdateCharacterRequest {
  name?: string
  age?: number
  role?: string
  traits?: string[]
  background?: string
  goals?: string[]
  appearance?: string
}

export interface RelationshipRequest {
  source_id: string
  target_id: string
  relationship_type: string
  strength: number
}

export interface Act {
  id: string
  number: number
  title: string
  summary: string
  scenes: SceneSpec[]
}

export interface PlotOutline {
  id: string
  title: string
  description: string
  structure: string
  acts: Act[]
}

export interface CreateOutlineRequest {
  title: string
  description: string
  structure: string
}

export interface SceneSpec {
  id: string
  title: string
  description: string
  setting: string
  characters: string[]
  act_id: string
  order: number
}

export interface CreateSceneRequest {
  title: string
  description: string
  setting: string
  characters: string[]
  act_id: string
  order: number
}

export interface SceneRound {
  round_number: number
  content: string
  character: string
  narration: string
  dialogue: string
  actions: string[]
}

export type SceneStatusType = 'idle' | 'running' | 'completed' | 'error'

export interface SceneStatus {
  scene_id?: string
  status: SceneStatusType
  current_round: number
  total_rounds: number
}

export interface SceneStreamMessage {
  type: 'setup' | 'environment' | 'round' | 'resolution' | 'complete' | 'error'
  data: SceneRound | SceneSetup | SceneEnvironment | SceneComplete | string
}

export interface SceneSetup {
  scene_id: string
  characters: string[]
  setting: string
}

export interface SceneEnvironment {
  description: string
  atmosphere: string
}

export interface SceneComplete {
  summary: string
  total_rounds: number
}

export interface SceneRunRequest {
  scene_spec_id: string
  plot_id: string
  character_ids: string[]
  max_rounds: number
}

export interface InterventionRequest {
  scene_id?: string
  intervention: string
}

export type NarrativeFormat = 'novel' | 'screenplay'

export interface Chapter {
  number: number
  title: string
  content: string
}

export interface WriterOutput {
  id: string
  title: string
  content: string
  format: NarrativeFormat
  chapters: Chapter[]
}

export interface TitleCandidate {
  title: string
  score: number
  reason: string
}

export interface GenerateRequest {
  plot_id: string
  format: NarrativeFormat
}

export interface GuardianValidationRequest {
  content: string
  context: string
}

export interface GuardianValidationResult {
  passed: boolean
  issues: GuardianIssue[]
}

export interface GuardianIssue {
  severity: 'error' | 'warning' | 'info'
  message: string
  rule: string
}

export interface ApiErrorResponse {
  detail: string
}

// World Builder conversational API types
export type WorldBuildStage = 'rules' | 'locations' | 'factions' | 'timeline' | 'done'

export interface WorldExtractedData {
  name?: string
  description?: string
  rules?: string[]
  locations?: Location[]
  factions?: Faction[]
  timeline?: TimelineEntry[]
}

export interface WorldBuildResponse {
  session_id: string
  stage: WorldBuildStage
  next_question: string
  extracted_data?: WorldExtractedData
  completeness: number
}
