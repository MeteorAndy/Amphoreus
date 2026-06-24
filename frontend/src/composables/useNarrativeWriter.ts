import { ref, watch } from 'vue'
import type { TitleCandidate, NarrativeFormat, WriterOutput, ConvertResponse } from '../types/api'
import {
  generateNarrative as apiGenerate,
  getTitleCandidates,
  exportOutput as apiExport,
} from '../api/client'
import { useProjectStore } from './useProjectStore'

export function useNarrativeWriter() {
  const projectStore = useProjectStore()

  const output = ref<WriterOutput | null>(null)
  const titleCandidates = ref<TitleCandidate[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const format = ref<NarrativeFormat>('novel')
  const enhanceEnabled = ref(true)
  const narrativeVoice = ref<'first_person' | 'third_person_limited' | 'third_person_omniscient'>('third_person_limited')

  async function generate(
    sceneIds: string[],
    characterIds: string[],
    fmt: NarrativeFormat = format.value,
    voice: 'first_person' | 'third_person_limited' | 'third_person_omniscient' = narrativeVoice.value,
    chapterTitle?: string,
    povCharacterId?: string,
  ): Promise<WriterOutput | null> {
    loading.value = true
    error.value = null
    try {
      const resp: ConvertResponse = await apiGenerate({
        scene_ids: sceneIds,
        character_ids: characterIds,
        format: fmt,
        narrative_voice: voice,
        enhance: enhanceEnabled.value,
        chapter_title: chapterTitle || null,
        pov_character_id: povCharacterId || null,
      })
      const writerOutput: WriterOutput = {
        id: `output-${Date.now()}`,
        title: chapterTitle || 'Untitled',
        content: resp.content,
        format: fmt,
        chapters: [],
        created_at: new Date().toISOString(),
        scene_ids: sceneIds,
        word_count: resp.word_count,
        scene_count: resp.scene_count,
      }
      output.value = writerOutput
      await projectStore.setWrittenOutput(writerOutput, writerOutput.id)
      return writerOutput
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate narrative'
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchTitles(plotId: string): Promise<void> {
    error.value = null
    try {
      const titles = await getTitleCandidates(plotId)
      titleCandidates.value = titles.map((title) => ({ title }))
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
      a.download = `${output.value.title || 'narrative'}.${fmt === 'novel' ? 'md' : 'fountain'}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to export'
    }
  }

  function setFormat(fmt: NarrativeFormat): void {
    format.value = fmt
  }

  function setVoice(voice: 'first_person' | 'third_person_limited' | 'third_person_omniscient'): void {
    narrativeVoice.value = voice
  }

  function toggleEnhance(enabled: boolean): void {
    enhanceEnabled.value = enabled
  }

  watch(
    () => projectStore.currentWrittenOutput.value,
    (written) => {
      if (written) {
        output.value = written
      }
    },
    { immediate: true },
  )

  return {
    output,
    titleCandidates,
    loading,
    error,
    format,
    narrativeVoice,
    enhanceEnabled,
    generate,
    fetchTitles,
    exportOutput,
    setFormat,
    setVoice,
    toggleEnhance,
  }
}
