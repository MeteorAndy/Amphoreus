import { ref, watch } from 'vue'
import type { PlotOutline, Act, CreateSceneRequest } from '../types/api'
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
import { useProjectStore } from './useProjectStore'

export function usePlotArchitect() {
  const projectStore = useProjectStore()

  const outlines = ref<PlotOutline[]>([])
  const selectedOutline = ref<PlotOutline | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const templates = ref<string[]>([])

  function mapResponseToDisplay(resp: {
    plot_id: string
    structure: string
    acts: {
      name: string
      description: string
      scenes: {
        id: string
        title: string
        location: string
        cast: string[]
        conflict: string
        goal: string
        expected_outcome: string
        causal_chain: string[]
      }[]
    }[]
  }): PlotOutline {
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

  async function fetchTemplates(): Promise<void> {
    try {
      templates.value = await getPlotTemplates()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch templates'
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
      selectedOutline.value = display
      await projectStore.setPlotOutline(display, resp.plot_id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create outline'
    } finally {
      loading.value = false
    }
  }

  async function selectOutline(id: string): Promise<void> {
    const existing = outlines.value.find((o) => o.id === id)
    if (existing) {
      selectedOutline.value = existing
      return
    }

    loading.value = true
    error.value = null
    try {
      const resp = await getPlot(id)
      const display = mapResponseToDisplay(resp)
      outlines.value.push(display)
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
      await projectStore.setPlotOutline(updated, id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update outline'
    }
  }

  async function removeOutline(id: string): Promise<void> {
    error.value = null
    try {
      await apiDeletePlot(id)
      outlines.value = outlines.value.filter((o) => o.id !== id)
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
      const updated = mapResponseToDisplay(resp)
      const idx = outlines.value.findIndex((o) => o.id === outlineId)
      if (idx !== -1) outlines.value[idx] = updated
      if (selectedOutline.value?.id === outlineId) selectedOutline.value = updated
      await projectStore.setPlotOutline(updated, outlineId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create scene'
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
      await projectStore.setPlotOutline(updated, selectedOutline.value.id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete scene'
    }
  }

  async function updateSceneById(sceneId: string, data: CreateSceneRequest): Promise<void> {
    error.value = null
    if (!selectedOutline.value) return
    try {
      const outline = { ...selectedOutline.value }
      for (const act of outline.acts) {
        const sceneIdx = act.scenes.findIndex((s) => s.id === sceneId)
        if (sceneIdx !== -1) {
          act.scenes[sceneIdx] = {
            ...act.scenes[sceneIdx],
            title: data.title,
            description: data.description,
            setting: data.setting,
            characters: data.characters,
            order: data.order,
          }
          break
        }
      }
      await updateOutline(outline.id, { acts: outline.acts })
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update scene'
    }
  }

  function fetchOutlines(): void {
    initFromProject()
  }

  async function refineOutline(plotId: string, feedback: string): Promise<void> {
    error.value = null
    try {
      const resp = await apiRefinePlot(plotId, feedback)
      const updated = mapResponseToDisplay(resp)
      const idx = outlines.value.findIndex((o) => o.id === plotId)
      if (idx !== -1) outlines.value[idx] = updated
      if (selectedOutline.value?.id === plotId) selectedOutline.value = updated
      await projectStore.setPlotOutline(updated, plotId)
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

  function initFromProject(): void {
    if (projectStore.currentPlotOutline.value && projectStore.currentPlotId.value) {
      const outline = projectStore.currentPlotOutline.value
      outlines.value = [outline]
      selectedOutline.value = outline
    }
  }

  watch(
    () => projectStore.currentPlotOutline.value,
    (outline) => {
      if (outline) {
        const existing = outlines.value.findIndex((o) => o.id === outline.id)
        if (existing === -1) {
          outlines.value.push(outline)
        } else {
          outlines.value[existing] = outline
        }
        if (!selectedOutline.value || selectedOutline.value.id === outline.id) {
          selectedOutline.value = outline
        }
      }
    },
    { immediate: true },
  )

  return {
    outlines,
    selectedOutline,
    loading,
    error,
    templates,
    fetchTemplates,
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
    initFromProject,
  }
}
