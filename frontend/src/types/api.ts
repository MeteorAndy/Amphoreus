export interface WorldRule {
  path: string
  l0: string
  score: number
}

export interface WorldLocation {
  'n.name': string
  'n.properties': Record<string, unknown>
}

export interface WorldFaction {
  'n.name': string
  'n.properties': Record<string, unknown>
}

export interface WorldTimelineEvent {
  'n.name': string
  'n.properties': Record<string, unknown>
}

export interface Location {
  name: string
  description: string
  properties?: Record<string, unknown>
}

export interface Faction {
  name: string
  description: string
  members?: string[]
  properties?: Record<string, unknown>
}

export interface TimelineEntry {
  date: string
  event: string
  description: string
  properties?: Record<string, unknown>
}

export interface WorldState {
  rules: string[] | WorldRule[]
  locations: Location[]
  factions: Faction[]
  timeline: TimelineEntry[]
  completeness: number
  name?: string
  description?: string
  world_id?: string
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

export interface WorldBuildStage {
  rules: string
  locations: string
  factions: string
  timeline: string
  done: string
}

export type WorldBuildStageType = 'rules' | 'locations' | 'factions' | 'timeline' | 'done'

export interface WorldExtractedData {
  name?: string
  description?: string
  rules?: string[] | WorldRule[]
  locations?: Location[]
  factions?: Faction[]
  timeline?: TimelineEntry[]
}

export interface WorldBuildResponse {
  session_id: string
  stage: WorldBuildStageType
  next_question: string
  rules: string[] | Record<string, unknown>[]
  locations: Location[] | Record<string, unknown>[]
  factions: Faction[] | Record<string, unknown>[]
  timeline: TimelineEntry[] | Record<string, unknown>[]
  completeness: number
}

export interface DocumentParseResponse {
  raw_text: string
  extracted_world: WorldState
  entities: Record<string, unknown>[]
  name?: string
  description?: string
  rules?: string[] | WorldRule[]
  locations?: Location[]
  factions?: Faction[]
  timeline?: TimelineEntry[]
}

export interface FormatsResponse {
  formats: string[] | Record<string, string[]>
}

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
  id?: string
  source_id?: string
  target_id?: string
  from_id: string
  to_id: string
  rel_type: string
  relationship_type?: string
  strength: number
  description: string
  established_event?: string
}

export interface BuildRelationshipsRequest {
  character_ids: string[]
}

export interface PathStep {
  from_id?: string
  to_id?: string
  character_id?: string
  rel_type?: string
  relationship_type?: string
  description?: string
  path: string[]
  relationship_types?: string[]
}

export interface NetworkData {
  nodes: Record<string, unknown>[]
  edges: Record<string, unknown>[]
}

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

export interface PlotOutline {
  id: string
  title: string
  description: string
  structure: string
  acts: Act[]
  character_arcs?: Record<string, string[]>
}

export interface Act {
  id: string
  number: number
  title: string
  summary: string
  description?: string
  name?: string
  scenes: SceneSpec[]
}

export interface SceneSpec {
  id: string
  title: string
  description: string
  setting: string
  location?: string
  characters: string[]
  cast?: string[]
  conflict?: string
  goal?: string
  expected_outcome?: string
  causal_chain?: string[]
  act_id: string
  order: number
}

export interface AddSceneRequest {
  title: string
  location: string
  cast: string[]
  conflict: string
  goal: string
  expected_outcome: string
  causal_chain?: string[]
}

export interface CreateSceneRequest {
  title: string
  description: string
  setting: string
  characters: string[]
  act_id: string
  order: number
}

export type SceneRound = RoundEntry

export interface PlotConsistencyCheck {
  scene_id: string
  consistent: boolean
  issues: string[]
  suggested_fixes: string[]
}

export interface PlotTemplates {
  templates: Record<string, string>
}

export interface Reaction {
  reactor_id: string
  reactor_name: string
  visible_reaction: string
  inner_thought: string
}

export interface RoundEntry {
  round_num?: number
  round_number: number
  actor_id: string
  actor_name?: string
  character?: string
  dialogue?: string
  action?: string
  actions?: string[]
  narration?: string
  inner_thought?: string
  emotion?: string
  reactions?: Reaction[]
  environment?: EnvironmentUpdate
}

export interface EnvironmentUpdate {
  atmosphere: string
  changes: string[]
  background_activity: string
}

export interface SceneArchive {
  scene_id: string
  rounds: RoundEntry[]
  final_environment: EnvironmentUpdate
  character_changes: Record<string, unknown>
}

export type SceneStatusType = 'idle' | 'running' | 'completed' | 'error'

export interface SceneStatus {
  scene_id?: string
  status: SceneStatusType
  current_round?: number
  total_rounds?: number
}

export type SceneStreamType = 'setup' | 'environment' | 'round' | 'resolution' | 'complete' | 'error' | 'connected'

export interface SceneStreamMessage {
  type: SceneStreamType
  data: RoundEntry | EnvironmentUpdate | SceneArchive | Record<string, unknown> | string
  session_id?: string
  round?: number
}

export interface SceneRunRequest {
  scene_spec_id: string
  plot_id: string
  character_ids: string[]
  max_rounds: number
}

export interface InterventionRequest {
  scene_id: string
  intervention: string
}

export interface InterventionResponse {
  scene_id: string
  intervention: string
  status: string
}

export type NarrativeFormat = 'novel' | 'screenplay'
export type NarrativeVoice = 'first_person' | 'third_person_limited' | 'third_person_omniscient'

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
  word_count?: number
  scene_count?: number
  created_at?: string
  scene_ids?: string[]
}

export interface ConvertRequest {
  scene_ids: string[]
  character_ids: string[]
  format: string
  narrative_voice: string
  enhance: boolean
  chapter_title: string | null
  pov_character_id?: string | null
}

export interface ConvertResponse {
  content: string
  format: string
  word_count: number
  scene_count: number
  export_formats: string[]
  cliche_report?: Record<string, unknown>
  canon_report?: Record<string, unknown>
  tension_report?: Record<string, unknown>
  prop_lifecycle_report?: Record<string, unknown>
  reader_sim_report?: Record<string, unknown>
  budget_report?: Record<string, unknown>
  relationship_trend_report?: Record<string, unknown>
  entity_event_report?: Record<string, unknown>
  graph_inference_report?: Record<string, unknown>
  adaptive_pattern_report?: Record<string, unknown>
}

export interface NarrativeOutput {
  output_id?: string
  title?: string
  content: string
  chapters?: Chapter[]
  word_count?: number
  scene_count?: number
  created_at?: string
}

export interface TitleCandidate {
  title: string
  subtitle?: string
  description?: string
}

export type GuardianCheckType = 'pacing' | 'character_consistency' | 'plot_logic' | 'full'

export interface GuardianCheckResult {
  score?: number
  issues?: GuardianIssue[]
  warnings?: GuardianIssue[]
  suggestions?: string[]
}

export interface GuardianReportResponse {
  overall_score?: number
  pacing?: GuardianCheckResult
  character_consistency?: GuardianCheckResult
  plot_logic?: GuardianCheckResult
  issues: GuardianIssue[]
  suggestions: string[]
}

export interface ExportRequest {
  content: string
  format: string
  export_format: string
}

export type GuardianSeverity = 'critical' | 'warning' | 'info'
export type GuardianVerdict = 'approve' | 'revise' | 'reject'

export interface GuardianIssue {
  severity: string
  dimension: string
  description: string
  suggestion: string
}

export interface GuardianResult {
  verdict: string
  issues: GuardianIssue[]
  can_override: boolean
}

export interface GuardianEvaluateRequest {
  proposed_plot: string
  affected_characters: string[]
  world_id?: string | null
}

export interface GuardianSceneInterventionRequest {
  scene_id: string
  intervention: string
  characters?: string[]
  current_round?: number
}

export interface PipelineConfig {
  seed_idea: string
  lang: string
  character_count: number
  narrative_structure: string
  output_format: string
  max_rounds_per_scene: number
  auto_refine: boolean
  adjudicate?: boolean
  stash_enabled?: boolean
  session_id?: string | null
}

export interface PipelineEvent {
  stage: string
  type: string
  data: Record<string, unknown>
  progress: number
  session_id: string
}

export interface Project {
  id: string
  name: string
  created_at: string
  updated_at: string
  last_stage: string
  seed_idea?: string
}

export interface ProjectState {
  id: string
  name: string
  seed_idea: string
  created_at: string
  updated_at: string
  last_stage: string
  world_state: WorldState | null
  world_session_id?: string | null
  characters: CharacterProfile[] | null
  relationships: Relationship[] | null
  plot_outline: PlotOutlineResponse | PlotOutline | null
  scene_archives: Record<string, SceneArchive> | null
  written_output: string | WriterOutput | null
}

export interface CreateProjectRequest {
  name: string
  seed_idea: string
}

export type SandboxEventType = 'connected' | 'injected' | 'action' | 'environment' | 'thought' | 'round_end' | 'stopped' | 'error'

export interface SandboxEvent {
  type: SandboxEventType
  character?: string
  content?: string
  event?: string
  round?: number
  rounds?: number
  session_id?: string
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

export interface ApiErrorResponse {
  detail: string
}

declare global {
  interface String {
    character_id?: undefined
  }
}
