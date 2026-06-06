import { ref } from 'vue'
import type { WorldState, CharacterProfile, PlotOutline, SceneRound } from '../types/api'
import {
  generateCharacters as apiGenerateCharacters,
  createOutline as apiCreateOutline,
  generateNarrative as apiGenerateNarrative,
  exportOutput as apiExportOutput,
} from '../api/client'
import type { ActResponse, SceneSpecResponse } from '../types/api'

export type InteractiveStep = 1 | 2 | 3 | 4 | 5

export function useInteractive() {
  const currentStep = ref<InteractiveStep>(1)
  const worldState = ref<WorldState | null>(null)
  const characters = ref<CharacterProfile[]>([])
  const plotOutline = ref<PlotOutline | null>(null)
  const sceneArchives = ref<SceneRound[]>([])
  const writtenOutput = ref('')
  const generating = ref(false)
  const error = ref<string | null>(null)

  function goToStep(step: number): void {
    if (step >= 1 && step <= 5) {
      currentStep.value = step as InteractiveStep
    }
  }

  function nextStep(): void {
    goToStep(currentStep.value + 1)
  }

  function prevStep(): void {
    goToStep(currentStep.value - 1)
  }

  async function generateCharacters(worldId: string, count = 5): Promise<void> {
    generating.value = true
    error.value = null
    try {
      const generated = await apiGenerateCharacters(worldId, count)
      characters.value = generated
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate characters'
    } finally {
      generating.value = false
    }
  }

  async function generatePlot(worldId: string, structure: string): Promise<void> {
    generating.value = true
    error.value = null
    try {
      const charIds = characters.value.map((c) => c.id)
      const resp = await apiCreateOutline({ world_id: worldId, structure, character_ids: charIds })
      const numberWords = ['I', 'II', 'III', 'IV', 'V']
      plotOutline.value = {
        id: resp.plot_id,
        title: resp.structure.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()),
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
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate plot'
    } finally {
      generating.value = false
    }
  }

  function addSceneArchive(rounds: SceneRound[]): void {
    sceneArchives.value.push(...rounds)
  }

  async function writeNarrative(format: 'novel' | 'screenplay'): Promise<void> {
    generating.value = true
    error.value = null
    try {
      const sceneIds = plotOutline.value?.acts.flatMap((a) => a.scenes.map((s) => s.id)) ?? []
      const charIds = characters.value.map((c) => c.id)
      const resp = await apiGenerateNarrative({
        scene_ids: sceneIds,
        character_ids: charIds,
        format,
        narrative_voice: 'third_person_limited',
        enhance: false,
        chapter_title: null,
      })
      writtenOutput.value = resp.content
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to write narrative'
    } finally {
      generating.value = false
    }
  }

  async function exportNarrative(format: 'novel' | 'screenplay'): Promise<void> {
    if (!writtenOutput.value) return
    try {
      const blob = await apiExportOutput(writtenOutput.value, format)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `narrative.${format === 'novel' ? 'md' : 'fountain'}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to export'
    }
  }

  return {
    currentStep,
    worldState,
    characters,
    plotOutline,
    sceneArchives,
    writtenOutput,
    generating,
    error,
    goToStep,
    nextStep,
    prevStep,
    generateCharacters,
    generatePlot,
    addSceneArchive,
    writeNarrative,
    exportNarrative,
  }
}
