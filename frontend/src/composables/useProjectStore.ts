import { ref, computed, watch } from 'vue'
import type {
  Project,
  ProjectState,
  WorldState,
  CharacterProfile,
  Relationship,
  PlotOutline,
  PlotOutlineResponse,
  SceneArchive,
  WriterOutput,
  CreateProjectRequest,
} from '../types/api'
import {
  listProjects as apiListProjects,
  createProject as apiCreateProject,
  getProject as apiGetProject,
  updateProject as apiUpdateProject,
  deleteProject as apiDeleteProject,
} from '../api/client'

const STORAGE_KEY = 'amphoreus-current-project'

function mapPlotResponseToOutline(resp: PlotOutlineResponse): PlotOutline {
  const numberWords = ['I', 'II', 'III', 'IV', 'V']
  return {
    id: resp.plot_id,
    title: resp.structure.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
    description: '',
    structure: resp.structure,
    acts: resp.acts.map((act, i) => ({
      id: `act-${i}`,
      number: i + 1,
      title: act.name || `Act ${numberWords[i] || i + 1}`,
      summary: act.description,
      scenes: act.scenes.map((scene, j) => ({
        id: scene.id,
        title: scene.title,
        description: scene.conflict,
        setting: scene.location,
        characters: scene.cast,
        act_id: `act-${i}`,
        order: j + 1,
      })),
    })),
  }
}

const projects = ref<Project[]>([])
const currentProjectId = ref<string | null>(null)
const currentProject = ref<ProjectState | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const currentWorldId = computed(() => currentProject.value?.world_session_id ?? null)
const currentWorldState = computed(() => currentProject.value?.world_state ?? null)
const currentCharacters = computed(() => currentProject.value?.characters ?? [])
const currentRelationships = computed(() => currentProject.value?.relationships ?? [])
const currentPlotOutline = computed<PlotOutline | null>(() => {
  const raw = currentProject.value?.plot_outline
  if (!raw) return null
  if ('plot_id' in raw) {
    return mapPlotResponseToOutline(raw as PlotOutlineResponse)
  }
  return raw as PlotOutline
})
const currentPlotId = computed<string | null>(() => {
  const outline = currentPlotOutline.value
  return outline?.id ?? null
})
const currentSceneArchives = computed(() => currentProject.value?.scene_archives ?? {})
const currentWrittenOutput = computed<WriterOutput | null>(() => {
  const raw = currentProject.value?.written_output
  if (!raw) return null
  if (typeof raw === 'string') {
    return {
      id: `output-${Date.now()}`,
      title: 'Untitled',
      content: raw,
      format: 'novel',
      chapters: [],
    }
  }
  return raw as WriterOutput
})
const lastStage = computed(() => currentProject.value?.last_stage ?? 'idle')

async function fetchProjects(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const res = await apiListProjects()
    projects.value = res.projects
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load projects'
  } finally {
    loading.value = false
  }
}

async function createProject(name: string, seedIdea: string): Promise<string> {
  loading.value = true
  error.value = null
  try {
    const req: CreateProjectRequest = { name, seed_idea: seedIdea }
    const res = await apiCreateProject(req)
    await fetchProjects()
    await selectProject(res.id)
    return res.id
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to create project'
    throw e
  } finally {
    loading.value = false
  }
}

async function selectProject(projectId: string): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const state = await apiGetProject(projectId)
    currentProjectId.value = projectId
    currentProject.value = state
    localStorage.setItem(STORAGE_KEY, projectId)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load project'
    throw e
  } finally {
    loading.value = false
  }
}

async function refreshProject(): Promise<void> {
  if (!currentProjectId.value) return
  await selectProject(currentProjectId.value)
}

async function updateProjectState(updates: Partial<ProjectState>): Promise<void> {
  if (!currentProjectId.value || !currentProject.value) return
  error.value = null
  try {
    const updated = await apiUpdateProject(currentProjectId.value, updates)
    currentProject.value = updated
    await fetchProjects()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to update project'
    throw e
  }
}

async function setWorldState(worldState: WorldState, sessionId?: string): Promise<void> {
  await updateProjectState({
    world_state: worldState,
    world_session_id: sessionId,
    last_stage: 'world',
  })
}

async function setCharacters(characters: CharacterProfile[]): Promise<void> {
  await updateProjectState({
    characters,
    last_stage: 'characters',
  })
}

async function setRelationships(relationships: Relationship[]): Promise<void> {
  await updateProjectState({ relationships })
}

async function setPlotOutline(plotOutline: PlotOutline | PlotOutlineResponse, plotId?: string): Promise<void> {
  let outlineToStore: PlotOutline
  if ('plot_id' in plotOutline) {
    outlineToStore = mapPlotResponseToOutline(plotOutline)
  } else {
    outlineToStore = plotOutline
  }
  if (plotId) {
    outlineToStore = { ...outlineToStore, id: plotId }
  }
  await updateProjectState({
    plot_outline: outlineToStore,
    last_stage: 'plot',
  })
}

async function addSceneArchive(archive: unknown | SceneArchive, sceneId?: string): Promise<void> {
  const archives = { ...(currentProject.value?.scene_archives ?? {}) }
  if (sceneId && archive) {
    archives[sceneId] = archive as SceneArchive
  } else if (archive && typeof archive === 'object' && 'scene_id' in (archive as Record<string, unknown>)) {
    const a = archive as { scene_id: string } & SceneArchive
    archives[a.scene_id] = archive as SceneArchive
  }
  await updateProjectState({
    scene_archives: archives,
    last_stage: 'scenes',
  })
}

async function setWrittenOutput(output: WriterOutput | string, outputId?: string): Promise<void> {
  let outputToStore: WriterOutput
  if (typeof output === 'string') {
    outputToStore = {
      id: outputId || `output-${Date.now()}`,
      title: 'Untitled',
      content: output,
      format: 'novel',
      chapters: [],
    }
  } else {
    outputToStore = output
  }
  await updateProjectState({
    written_output: outputToStore,
    last_stage: 'writing',
  })
}

async function removeProject(projectId: string): Promise<void> {
  error.value = null
  try {
    await apiDeleteProject(projectId)
    if (currentProjectId.value === projectId) {
      currentProjectId.value = null
      currentProject.value = null
      localStorage.removeItem(STORAGE_KEY)
    }
    await fetchProjects()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to delete project'
    throw e
  }
}

function clearCurrentProject(): void {
  currentProjectId.value = null
  currentProject.value = null
  localStorage.removeItem(STORAGE_KEY)
}

async function restoreSavedProject(): Promise<void> {
  const savedId = localStorage.getItem(STORAGE_KEY)
  if (savedId) {
    try {
      await selectProject(savedId)
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
  }
}

watch(currentProjectId, (newId) => {
  if (newId) {
    localStorage.setItem(STORAGE_KEY, newId)
  }
})

export function useProjectStore() {
  return {
    projects,
    currentProjectId,
    currentProject,
    loading,
    error,
    currentWorldId,
    currentWorldState,
    currentCharacters,
    currentRelationships,
    currentPlotOutline,
    currentPlotId,
    currentSceneArchives,
    currentWrittenOutput,
    lastStage,
    fetchProjects,
    createProject,
    selectProject,
    refreshProject,
    updateProjectState,
    setWorldState,
    setCharacters,
    setRelationships,
    setPlotOutline,
    addSceneArchive,
    setWrittenOutput,
    removeProject,
    clearCurrentProject,
    restoreSavedProject,
  }
}
