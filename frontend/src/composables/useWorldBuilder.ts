import { ref, computed } from 'vue'
import type { ChatMessage, WorldBuildStage, WorldExtractedData, WorldState } from '../types/api'
import { startWorldBuild, continueWorldBuild, finalizeWorldBuild } from '../api/client'

export function useWorldBuilder() {
  const messages = ref<ChatMessage[]>([])
  const sessionId = ref<string | null>(null)
  const stage = ref<WorldBuildStage>('rules')
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
      mergeExtractedData(res.extracted_data)
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
      mergeExtractedData(res.extracted_data)
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
      if (state.world_id) {
        localStorage.setItem('amphoreus-world-id', state.world_id)
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to finalize world'
    } finally {
      loading.value = false
    }
  }

  function mergeExtractedData(data?: WorldExtractedData): void {
    if (!data) return
    if (data.name) extractedData.value.name = data.name
    if (data.description) extractedData.value.description = data.description
    if (data.rules) {
      const existing = new Set(extractedData.value.rules || [])
      for (const rule of data.rules) {
        if (!existing.has(rule)) {
          extractedData.value.rules = [...(extractedData.value.rules || []), rule]
          existing.add(rule)
        }
      }
    }
    if (data.locations) {
      const existing = new Map((extractedData.value.locations || []).map((l) => [l.name, l]))
      for (const loc of data.locations) {
        if (!existing.has(loc.name)) {
          extractedData.value.locations = [...(extractedData.value.locations || []), loc]
          existing.set(loc.name, loc)
        }
      }
    }
    if (data.factions) {
      const existing = new Map((extractedData.value.factions || []).map((f) => [f.name, f]))
      for (const fac of data.factions) {
        if (!existing.has(fac.name)) {
          extractedData.value.factions = [...(extractedData.value.factions || []), fac]
          existing.set(fac.name, fac)
        }
      }
    }
    if (data.timeline) {
      const existing = new Set((extractedData.value.timeline || []).map((t) => `${t.date}|${t.event}`))
      for (const entry of data.timeline) {
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
    localStorage.removeItem('amphoreus-world-id')
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
  }
}
