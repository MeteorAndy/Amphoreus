import { ref } from 'vue'
import type { PlotOutline, Act, ActResponse, SceneSpecResponse, PlotOutlineResponse } from '../types/api'
import {
  getPlotTemplates,
  createOutline as apiCreateOutline,
  getPlot,
  updatePlot as apiUpdatePlot,
  deletePlot as apiDeletePlot,
  refinePlot as apiRefinePlot,
  addScene as apiAddScene,
  deleteScene as apiDeleteScene,
  checkPlotConsistency as apiCheckConsistency,
} from '../api/client'

function mapResponseToDisplay(resp: PlotOutlineResponse): PlotOutline {
  const numberWords = ['I', 'II', 'III', 'IV', 'V']
  return {
    id: resp.plot_id,
    title: resp.structure.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
    description: '',
    structure: resp.structure,
    acts: resp.acts.map((act: ActResponse, i: number) => ({
      id: `act-${i}`,
      number: i + 1,
      title: act.name || `Act ${numberWords[i] || i + 1}`,
      summary: act.description,
      scenes: act.scenes.map((scene: SceneSpecResponse, j: number) => ({
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

export function usePlotArchitect() {
  const outlines = ref<PlotOutline[]>([])
  const selectedOutline = ref<PlotOutline | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Track plot IDs in a separate list for later retrieval
  const plotIds = ref<string[]>([])

  async function fetchOutlines(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      // fetch templates to validate structure options, then load any known outlines
      await getPlotTemplates()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch templates'
    } finally {
      loading.value = false
    }
  }

  async function createOutline(worldId: string, structure: string, characterIds: string[]): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const resp = await apiCreateOutline({
        world_id: worldId,
        structure,
        character_ids: characterIds,
      })
      const display = mapResponseToDisplay(resp)
      outlines.value.push(display)
      plotIds.value.push(resp.plot_id)
      selectedOutline.value = display
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create outline'
    } finally {
      loading.value = false
    }
  }

  async function selectOutline(id: string): Promise<void> {
    // Check if it's already loaded in our outlines list
    const existing = outlines.value.find((o) => o.id === id)
    if (existing) {
      selectedOutline.value = existing
      return
    }

    // Try fetching from backend
    loading.value = true
    error.value = null
    try {
      const resp = await getPlot(id)
      const display = mapResponseToDisplay(resp)
      outlines.value.push(display)
      plotIds.value.push(id)
      selectedOutline.value = display
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load outline'
    } finally {
      loading.value = false
    }
  }

  async function updateOutline(id: string, data: { acts?: Act[] }): Promise<void> {
    error.value = null
    try {
      // Convert display acts back to API format
      const apiActs = data.acts
        ? data.acts.map((act) => ({
            name: act.title,
            description: act.summary,
            scenes: act.scenes.map((s) => ({
              id: s.id,
              title: s.title,
              location: s.setting,
              cast: s.characters,
              conflict: s.description,
              goal: '',
              expected_outcome: '',
              causal_chain: [] as string[],
            })),
          }))
        : undefined

      const resp = await apiUpdatePlot(id, { acts: apiActs as Record<string, unknown>[] | undefined })
      const updated = mapResponseToDisplay(resp)
      const idx = outlines.value.findIndex((o) => o.id === id)
      if (idx !== -1) outlines.value[idx] = updated
      if (selectedOutline.value?.id === id) selectedOutline.value = updated
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update outline'
    }
  }

  async function removeOutline(id: string): Promise<void> {
    error.value = null
    try {
      await apiDeletePlot(id)
      outlines.value = outlines.value.filter((o) => o.id !== id)
      const pIdx = plotIds.value.indexOf(id)
      if (pIdx !== -1) plotIds.value.splice(pIdx, 1)
      if (selectedOutline.value?.id === id) selectedOutline.value = null
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete outline'
    }
  }

  async function createScene(
    outlineId: string,
    data: { title: string; setting: string; characters: string[]; description: string; act_id: string },
  ): Promise<void> {
    error.value = null
    try {
      const resp = await apiAddScene(outlineId, {
        title: data.title,
        location: data.setting,
        cast: data.characters,
        conflict: data.description,
        goal: '',
        expected_outcome: '',
      })
      // Reload the outline from the response
      const updated = mapResponseToDisplay(resp)
      const idx = outlines.value.findIndex((o) => o.id === outlineId)
      if (idx !== -1) outlines.value[idx] = updated
      if (selectedOutline.value?.id === outlineId) selectedOutline.value = updated
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create scene'
    }
  }

  async function updateSceneById(id: string, data: { title: string; setting: string; description: string }): Promise<void> {
    error.value = null
    // Scene update is done through plot update (PUT /api/plot/{id}) with full acts list
    // Since we don't have a dedicated scene update endpoint, we skip server-side update
    // and just update locally
    if (selectedOutline.value) {
      for (const act of selectedOutline.value.acts) {
        const idx = act.scenes.findIndex((s) => s.id === id)
        if (idx !== -1) {
          act.scenes[idx] = { ...act.scenes[idx], ...data }
          break
        }
      }
    }
  }

  async function removeScene(id: string): Promise<void> {
    error.value = null
    if (!selectedOutline.value) return
    try {
      const resp = await apiDeleteScene(selectedOutline.value.id, id)
      const updated = mapResponseToDisplay(resp)
      const idx = outlines.value.findIndex((o) => o.id === selectedOutline.value!.id)
      if (idx !== -1) outlines.value[idx] = updated
      selectedOutline.value = updated
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete scene'
    }
  }

  async function refineOutline(plotId: string, feedback: string): Promise<void> {
    error.value = null
    try {
      const resp = await apiRefinePlot(plotId, feedback)
      const updated = mapResponseToDisplay(resp)
      const idx = outlines.value.findIndex((o) => o.id === plotId)
      if (idx !== -1) outlines.value[idx] = updated
      if (selectedOutline.value?.id === plotId) selectedOutline.value = updated
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to refine outline'
    }
  }

  async function checkConsistency(plotId: string, sceneId: string): Promise<{
    scene_id: string
    consistent: boolean
    issues: string[]
    suggested_fixes: string[]
  } | null> {
    error.value = null
    try {
      return await apiCheckConsistency(plotId, sceneId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to check consistency'
      return null
    }
  }

  return {
    outlines,
    selectedOutline,
    loading,
    error,
    plotIds,
    fetchOutlines,
    createOutline,
    selectOutline,
    updateOutline,
    removeOutline,
    createScene,
    updateSceneById,
    removeScene,
    refineOutline,
    checkConsistency,
  }
}
