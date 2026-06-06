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

// ---------------------------------------------------------------------------
// Character types (matches backend app.models.character)
// ---------------------------------------------------------------------------

export interface Big5 {
  openness: number
  conscientiousness: number
  extraversion: number
  agreeableness: number
  neuroticism: number
}

export interface Personality {
  big5: Big5
  mbti: string
  core_traits: string[]
  emotional_pattern: string
}

export interface CharacterProfile {
  id: string
  name: string
  role: string
  appearance: string
  personality: Personality
  core_desire: string
  deep_fear: string
  voice_sample: string
  secrets: string[]
  knowledge_scope: string[]
  arc_stage: string
  created_at: string
  updated_at: string
}

export interface Relationship {
  from_id: string
  to_id: string
  rel_type: string
  strength: number
  description: string
  established_event: string
}

export interface PathStep {
  from_id: string
  to_id: string
  rel_type: string
  description: string
}

export interface RelationshipRequest {
  source_id: string
  target_id: string
  relationship_type: string
  strength: number
}

export interface NetworkData {
  nodes: Record<string, unknown>[]
  edges: Record<string, unknown>[]
}

// ---------------------------------------------------------------------------
// Plot types (matches backend PlotOutlineResponse / PlotOutline)
// ---------------------------------------------------------------------------

export interface PlotOutlineResponse {
  plot_id: string
  structure: string
  acts: ActResponse[]
  character_arcs: Record<string, string[]>
}

export interface ActResponse {
  name: string
  description: string
  scenes: SceneSpecResponse[]
}

export interface SceneSpecResponse {
  id: string
  title: string
  location: string
  cast: string[]
  conflict: string
  goal: string
  expected_outcome: string
  causal_chain: string[]
}

// Display types (view-layer, mapped from API responses)
export interface PlotOutline {
  id: string
  title: string
  description: string
  structure: string
  acts: Act[]
}

export interface Act {
  id: string
  number: number
  title: string
  summary: string
  scenes: SceneSpec[]
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

export interface CreateOutlineRequest {
  title: string
  description: string
  structure: string
}

export interface CreateSceneRequest {
  title: string
  description: string
  setting: string
  characters: string[]
  act_id: string
  order: number
}

// ---------------------------------------------------------------------------
// Scene / Round types (matches backend scene_engine.types)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Writer types (matches backend narrative_writer)
// ---------------------------------------------------------------------------

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

export interface ConvertRequest {
  scene_ids: string[]
  character_ids: string[]
  format: string
  narrative_voice: string
  enhance: boolean
  chapter_title: string | null
}

export interface ConvertResponse {
  content: string
  format: string
  word_count: number
  scene_count: number
  export_formats: string[]
}

// ---------------------------------------------------------------------------
// Guardian types
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// World Builder conversational API types
// ---------------------------------------------------------------------------

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

export interface TemplatesResponse {
  templates: Record<string, string>
}

// ---------------------------------------------------------------------------
// Sandbox types
// ---------------------------------------------------------------------------

export interface SandboxEvent {
  type: 'connected' | 'injected' | 'action' | 'environment' | 'thought' | 'round_end' | 'stopped'
  character?: string
  content?: string
  event?: string
  round?: number
  rounds?: number
}

export interface SandboxStartRequest {
  world_id: string
  character_ids: string[]
  location?: string
}

export interface SandboxStartResponse {
  session_id: string
  status: string
}
