import { ref } from 'vue'
import type { GuardianResult } from '../types/api'
import { evaluatePlot as apiEvaluatePlot, evaluateSceneIntervention as apiEvaluateScene } from '../api/client'

export function useGuardian() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastResult = ref<GuardianResult | null>(null)
  const lastSceneResult = ref<GuardianResult | null>(null)

  async function evaluatePlot(
    proposedPlot: string,
    affectedCharacters: string[],
    worldId?: string,
  ): Promise<GuardianResult | null> {
    loading.value = true
    error.value = null
    try {
      lastResult.value = await apiEvaluatePlot({
        proposed_plot: proposedPlot,
        affected_characters: affectedCharacters,
        world_id: worldId,
      })
      return lastResult.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to evaluate plot'
      return null
    } finally {
      loading.value = false
    }
  }

  async function evaluateScene(
    sceneId: string,
    intervention: string,
    characters: string[],
  ): Promise<GuardianResult | null> {
    loading.value = true
    error.value = null
    try {
      lastSceneResult.value = await apiEvaluateScene({
        scene_id: sceneId,
        intervention,
        characters,
      })
      return lastSceneResult.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to evaluate scene intervention'
      return null
    } finally {
      loading.value = false
    }
  }

  function reset(): void {
    lastResult.value = null
    lastSceneResult.value = null
    error.value = null
  }

  function getIssueCount(result: GuardianResult | null): number {
    return result?.issues?.length || 0
  }

  function getBlockingIssues(result: GuardianResult | null): number {
    if (!result?.issues) return 0
    return result.issues.filter((i) => i.severity === 'error').length
  }

  function canProceed(result: GuardianResult | null): boolean {
    if (!result) return true
    return result.verdict !== 'reject' || result.can_override
  }

  return {
    loading,
    error,
    lastResult,
    lastSceneResult,
    evaluatePlot,
    evaluateScene,
    reset,
    getIssueCount,
    getBlockingIssues,
    canProceed,
  }
}
