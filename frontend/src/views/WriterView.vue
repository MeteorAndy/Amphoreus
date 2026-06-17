<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import WritingPreview from '../components/WritingPreview.vue'
import { useNarrativeWriter } from '../composables/useNarrativeWriter'
import { usePlotArchitect } from '../composables/usePlotArchitect'
import { useCharacters } from '../composables/useCharacters'
import { useI18n } from '../i18n'
import type { NarrativeFormat } from '../types/api'

const { t } = useI18n()
const {
  output,
  titleCandidates,
  loading,
  error,
  format,
  generate,
  fetchTitles,
  exportOutput,
  setFormat,
} = useNarrativeWriter()

const { fetchOutlines, outlines, selectOutline, selectedOutline } = usePlotArchitect()
const { fetchCharacters, characters } = useCharacters()

const selectedPlotId = ref('')

onMounted(() => {
  fetchOutlines()
  fetchCharacters()
})

watch(selectedPlotId, async (newId) => {
  if (newId) {
    fetchTitles(newId)
    await selectOutline(newId)
  }
})

function getSceneIds(): string[] {
  if (!selectedOutline.value) return []
  const ids: string[] = []
  for (const act of selectedOutline.value.acts) {
    for (const scene of act.scenes) {
      ids.push(scene.id)
    }
  }
  return ids
}

function getCharacterIds(): string[] {
  return characters.value.map((c) => c.id)
}

function handleGenerate(): void {
  if (!selectedPlotId.value) return
  const sceneIds = getSceneIds()
  const characterIds = getCharacterIds()
  generate(sceneIds, characterIds, format.value)
}

function handleToggleFormat(fmt: NarrativeFormat): void {
  setFormat(fmt)
  if (output.value) {
    const sceneIds = getSceneIds()
    const characterIds = getCharacterIds()
    generate(sceneIds, characterIds, fmt)
  }
}

function handleExport(): void {
  exportOutput(format.value)
}

function handleSelectTitle(title: string): void {
  if (output.value) {
    output.value.title = title
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-parchment">{{ t('writer.title') }}</h1>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
      {{ error }}
    </div>

    <!-- Selection + Generate bar -->
    <div class="bg-ink-panel rounded-lg border border-ink-edge p-4">
      <div class="flex items-end gap-4">
        <div class="flex-1">
          <label class="block text-xs text-muted mb-1">{{ t('writer.plot_outline') }}</label>
          <select
            v-model="selectedPlotId"
            class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
          >
            <option value="" disabled>{{ t('writer.select_outline') }}</option>
            <option
              v-for="outline in outlines"
              :key="outline.id"
              :value="outline.id"
            >
              {{ outline.title }}
            </option>
          </select>
        </div>
        <button
          @click="handleGenerate"
          :disabled="!selectedPlotId || loading"
          class="px-6 py-2 bg-chop text-white rounded-lg text-sm font-medium hover:bg-chop disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ loading ? t('writer.generating') : t('writer.convert') }}
        </button>
      </div>
    </div>

    <!-- Title candidates -->
    <div v-if="titleCandidates.length > 0" class="bg-ink-panel rounded-lg border border-ink-edge p-4">
      <h3 class="text-sm font-semibold text-parchment mb-3">{{ t('writer.title_candidates') }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        <button
          v-for="candidate in titleCandidates"
          :key="candidate.title"
          @click="handleSelectTitle(candidate.title)"
          class="text-left bg-ink-elevated rounded-lg p-3 hover:border-chop border border-ink-edge transition-colors"
          :class="output?.title === candidate.title ? 'border-chop' : ''"
        >
          <p class="text-sm font-medium text-parchment">{{ candidate.title }}</p>
          <div class="flex items-center gap-2 mt-1">
            <span class="text-xs text-chop">{{ t('writer.score') }}: {{ candidate.score }}</span>
          </div>
          <p class="text-xs text-muted mt-1 line-clamp-2">{{ candidate.reason }}</p>
        </button>
      </div>
    </div>

    <!-- Preview -->
    <WritingPreview
      :output="output"
      :format="format"
      :loading="loading"
      @toggle-format="handleToggleFormat"
      @export="handleExport"
      @select-title="handleSelectTitle"
    />
  </div>
</template>
