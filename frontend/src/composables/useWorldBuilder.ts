import { ref, computed } from 'vue'
import type { ChatMessage, WorldBuildStageType, WorldExtractedData, WorldState } from '../types/api'
import { startWorldBuild, continueWorldBuild, finalizeWorldBuild } from '../api/client'
import { useProjectStore } from './useProjectStore'

export function useWorldBuilder() {
  const projectStore = useProjectStore()

  const messages = ref<ChatMessage[]>([])
  const sessionId = ref<string | null>(null)
  const stage = ref<WorldBuildStageType>('rules')
  const extractedData = ref<WorldExtractedData>({})
  const completeness = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const worldState = ref<WorldState | null>(null)
  const finalized = ref(false)

  const isBuilding = computed(() => !!sessionId.value && !finalized.value)
  const isDone = computed(() => stage.value === 'done')

  async function startBuilding(seedIdea: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await withRetry(() => startWorldBuild(seedIdea))
      sessionId.value = res.session_id
      stage.value = res.stage
      completeness.value = res.completeness
      mergeExtractedDataFromResponse(res)
      messages.value.push({ role: 'user', content: seedIdea })
      messages.value.push({ role: 'assistant', content: res.next_question })
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to start world building'
    } finally {
      loading.value = false
    }
  }

  async function continueBuilding(userInput: string): Promise<void> {
    if (!sessionId.value) return
    loading.value = true
    error.value = null
    try {
      const res = await withRetry(() => continueWorldBuild(sessionId.value!, userInput))
      stage.value = res.stage
      completeness.value = res.completeness
      mergeExtractedDataFromResponse(res)
      messages.value.push({ role: 'user', content: userInput })
      messages.value.push({ role: 'assistant', content: res.next_question })
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to continue world building'
    } finally {
      loading.value = false
    }
  }

  async function finalizeWorld(): Promise<void> {
    if (!sessionId.value) return
    loading.value = true
    error.value = null
    try {
      const state = await withRetry(() => finalizeWorldBuild(sessionId.value!))
      worldState.value = state
      finalized.value = true
      await projectStore.setWorldState(state, sessionId.value)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to finalize world'
    } finally {
      loading.value = false
    }
  }

  function mergeExtractedDataFromResponse(res: {
    rules: unknown[]
    locations: unknown[]
    factions: unknown[]
    timeline: unknown[]
  }): void {
    if (res.rules?.length) {
      const rules = res.rules
        .filter((r): r is string => typeof r === 'string')
      const existingRules = Array.isArray(extractedData.value.rules)
        ? extractedData.value.rules.filter((r): r is string => typeof r === 'string')
        : []
      extractedData.value.rules = [...new Set([...existingRules, ...rules])]
    }

    if (res.locations?.length) {
      const locations = res.locations
        .filter((l): l is { name: string; description: string } =>
          typeof l === 'object' && l !== null && 'name' in l)
      const existing = new Map((extractedData.value.locations || []).map((l) => [l.name, l]))
      for (const loc of locations) {
        existing.set(loc.name, { ...existing.get(loc.name), ...loc })
      }
      extractedData.value.locations = Array.from(existing.values())
    }

    if (res.factions?.length) {
      const factions = res.factions
        .filter((f): f is { name: string; description: string } =>
          typeof f === 'object' && f !== null && 'name' in f)
      const existing = new Map((extractedData.value.factions || []).map((f) => [f.name, f]))
      for (const fac of factions) {
        existing.set(fac.name, { ...existing.get(fac.name), ...fac })
      }
      extractedData.value.factions = Array.from(existing.values())
    }

    if (res.timeline?.length) {
      const timeline = res.timeline
        .filter((t): t is { date: string; event: string; description: string } =>
          typeof t === 'object' && t !== null && 'event' in t)
      const existing = new Set(
        (extractedData.value.timeline || []).map((t) => `${t.date}|${t.event}`),
      )
      for (const entry of timeline) {
        const key = `${entry.date}|${entry.event}`
        if (!existing.has(key)) {
          extractedData.value.timeline = [...(extractedData.value.timeline || []), entry]
          existing.add(key)
        }
      }
    }
  }

  async function withRetry<T>(fn: () => Promise<T>, maxRetries = 1): Promise<T> {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await fn()
      } catch (e) {
        if (attempt < maxRetries) {
          await new Promise((r) => setTimeout(r, 1000))
        } else {
          throw e
        }
      }
    }
    throw new Error('Unreachable')
  }

  function resetWorld(): void {
    sessionId.value = null
    stage.value = 'rules'
    extractedData.value = {}
    completeness.value = 0
    messages.value = []
    error.value = null
    worldState.value = null
    finalized.value = false
  }

  function initFromProject(): void {
    if (projectStore.currentWorldState.value && projectStore.currentWorldId.value) {
      const ws = projectStore.currentWorldState.value
      worldState.value = ws
      sessionId.value = projectStore.currentWorldId.value
      finalized.value = true
      stage.value = 'done'
      extractedData.value = {
        rules: Array.isArray(ws.rules)
          ? ws.rules.filter((r): r is string => typeof r === 'string')
          : [],
        locations: ws.locations || [],
        factions: ws.factions || [],
        timeline: ws.timeline || [],
      }
    }
  }

  return {
    messages,
    sessionId,
    stage,
    extractedData,
    completeness,
    loading,
    error,
    worldState,
    finalized,
    isBuilding,
    isDone,
    startBuilding,
    continueBuilding,
    finalizeWorld,
    resetWorld,
    initFromProject,
  }
}
