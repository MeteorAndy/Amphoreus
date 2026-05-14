import { ref } from 'vue'
import type { WriterOutput, TitleCandidate, NarrativeFormat } from '../types/api'
import {
  generateNarrative as apiGenerate,
  getWriterOutput,
  getTitleCandidates,
  exportOutput as apiExport,
} from '../api/client'

export function useNarrativeWriter() {
  const output = ref<WriterOutput | null>(null)
  const titleCandidates = ref<TitleCandidate[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const format = ref<NarrativeFormat>('novel')

  async function generate(plotId: string, fmt: NarrativeFormat): Promise<void> {
    loading.value = true
    error.value = null
    try {
      output.value = await apiGenerate({ plot_id: plotId, format: fmt })
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate narrative'
    } finally {
      loading.value = false
    }
  }

  async function fetchOutput(id: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      output.value = await getWriterOutput(id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch output'
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

  async function exportOutput(_outputId: string, fmt: NarrativeFormat): Promise<void> {
    error.value = null
    if (!output.value) return
    try {
      const blob = await apiExport(output.value.content, fmt)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${output.value.id}.${fmt === 'novel' ? 'md' : 'fountain'}`
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
    fetchOutput,
    fetchTitles,
    exportOutput,
    setFormat,
  }
}
