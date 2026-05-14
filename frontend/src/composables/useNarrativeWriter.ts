import { ref } from 'vue'
import type { ConvertResponse, TitleCandidate, NarrativeFormat, WriterOutput } from '../types/api'
import {
  generateNarrative as apiGenerate,
  getTitleCandidates,
  exportOutput as apiExport,
} from '../api/client'

export function useNarrativeWriter() {
  const output = ref<WriterOutput | null>(null)
  const titleCandidates = ref<TitleCandidate[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const format = ref<NarrativeFormat>('novel')

  async function generate(
    sceneIds: string[],
    characterIds: string[],
    fmt: NarrativeFormat,
    narrativeVoice: string = 'third_person_limited',
  ): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const resp: ConvertResponse = await apiGenerate({
        scene_ids: sceneIds,
        character_ids: characterIds,
        format: fmt,
        narrative_voice: narrativeVoice,
        enhance: false,
        chapter_title: null,
      })
      // Map ConvertResponse to WriterOutput for display
      output.value = {
        id: `output-${Date.now()}`,
        title: '',
        content: resp.content,
        format: fmt,
        chapters: [],
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate narrative'
    } finally {
      loading.value = false
    }
  }

  async function fetchTitles(plotId: string): Promise<void> {
    error.value = null
    try {
      titleCandidates.value = await getTitleCandidates(plotId)
    } catch {
      titleCandidates.value = []
    }
  }

  async function exportOutput(fmt: NarrativeFormat): Promise<void> {
    error.value = null
    if (!output.value) return
    try {
      const blob = await apiExport(output.value.content, fmt)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${output.value.id || 'narrative'}.${fmt === 'novel' ? 'md' : 'fountain'}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to export'
    }
  }

  function setFormat(fmt: NarrativeFormat): void {
    format.value = fmt
  }

  return {
    output,
    titleCandidates,
    loading,
    error,
    format,
    generate,
    fetchTitles,
    exportOutput,
    setFormat,
  }
}
