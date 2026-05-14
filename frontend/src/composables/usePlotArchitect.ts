import { ref } from 'vue'
import type { PlotOutline, CreateOutlineRequest, CreateSceneRequest } from '../types/api'
import {
  listOutlines,
  createOutline as apiCreateOutline,
  getOutline,
  updateOutline as apiUpdateOutline,
  deleteOutline as apiDeleteOutline,
  createScene as apiCreateScene,
  updateScene as apiUpdateScene,
  deleteScene as apiDeleteScene,
  reorderScenes as apiReorderScenes,
} from '../api/client'

export function usePlotArchitect() {
  const outlines = ref<PlotOutline[]>([])
  const selectedOutline = ref<PlotOutline | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchOutlines(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      outlines.value = await listOutlines()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch outlines'
    } finally {
      loading.value = false
    }
  }

  async function createOutline(data: CreateOutlineRequest): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const created = await apiCreateOutline(data)
      outlines.value.push(created)
      selectedOutline.value = created
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create outline'
    } finally {
      loading.value = false
    }
  }

  async function selectOutline(id: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      selectedOutline.value = await getOutline(id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load outline'
    } finally {
      loading.value = false
    }
  }

  async function updateOutline(id: string, data: Partial<CreateOutlineRequest>): Promise<void> {
    error.value = null
    try {
      const updated = await apiUpdateOutline(id, data)
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
      await apiDeleteOutline(id)
      outlines.value = outlines.value.filter((o) => o.id !== id)
      if (selectedOutline.value?.id === id) selectedOutline.value = null
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete outline'
    }
  }

  async function createScene(outlineId: string, data: CreateSceneRequest): Promise<void> {
    error.value = null
    try {
      const scene = await apiCreateScene(outlineId, data)
      if (selectedOutline.value?.id === outlineId) {
        const act = selectedOutline.value.acts.find((a) => a.id === data.act_id)
        if (act) act.scenes.push(scene)
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create scene'
    }
  }

  async function updateSceneById(id: string, data: Partial<CreateSceneRequest>): Promise<void> {
    error.value = null
    try {
      const updated = await apiUpdateScene(id, data)
      if (selectedOutline.value) {
        for (const act of selectedOutline.value.acts) {
          const idx = act.scenes.findIndex((s) => s.id === id)
          if (idx !== -1) {
            act.scenes[idx] = updated
            break
          }
        }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update scene'
    }
  }

  async function removeScene(id: string): Promise<void> {
    error.value = null
    try {
      await apiDeleteScene(selectedOutline.value?.id || '', id)
      if (selectedOutline.value) {
        for (const act of selectedOutline.value.acts) {
          act.scenes = act.scenes.filter((s) => s.id !== id)
        }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete scene'
    }
  }

  async function reorderScenes(sceneIds: string[]): Promise<void> {
    error.value = null
    try {
      await apiReorderScenes(sceneIds)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to reorder scenes'
    }
  }

  return {
    outlines,
    selectedOutline,
    loading,
    error,
    fetchOutlines,
    createOutline,
    selectOutline,
    updateOutline,
    removeOutline,
    createScene,
    updateSceneById,
    removeScene,
    reorderScenes,
  }
}
