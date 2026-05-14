<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import WritingPreview from '../components/WritingPreview.vue'
import { useNarrativeWriter } from '../composables/useNarrativeWriter'
import { usePlotArchitect } from '../composables/usePlotArchitect'
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

const { fetchOutlines, outlines } = usePlotArchitect()

const selectedPlotId = ref('')

onMounted(() => {
  fetchOutlines()
})

watch(selectedPlotId, (newId) => {
  if (newId) {
    fetchTitles(newId)
  }
})

function handleGenerate(): void {
  if (!selectedPlotId.value) return
  generate(selectedPlotId.value, format.value)
}

function handleToggleFormat(fmt: NarrativeFormat): void {
  setFormat(fmt)
  if (output.value) {
    generate(selectedPlotId.value, fmt)
  }
}

function handleExport(): void {
  if (output.value) {
    exportOutput(output.value.id, format.value)
  }
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
      <h1 class="text-xl font-bold text-gray-100">{{ t('writer.title') }}</h1>
    </div>
    <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
      {{ error }}
    </div>
    <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
      <div class="flex items-end gap-4">
        <div class="flex-1">
          <label class="block text-xs text-gray-500 mb-1">{{ t('writer.plot_outline') }}</label>
          <select
            v-model="selectedPlotId"
            class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
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
          class="px-6 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ loading ? t('writer.generating') : t('writer.convert') }}
        </button>
      </div>
    </div>
    <div v-if="titleCandidates.length > 0" class="bg-gray-900 rounded-lg border border-gray-800 p-4">
      <h3 class="text-sm font-semibold text-gray-200 mb-3">{{ t('writer.title_candidates') }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        <button
          v-for="candidate in titleCandidates"
          :key="candidate.title"
          @click="handleSelectTitle(candidate.title)"
          class="text-left bg-gray-800 rounded-lg p-3 hover:border-indigo-500 border border-gray-700 transition-colors"
          :class="output?.title === candidate.title ? 'border-indigo-500' : ''"
        >
          <p class="text-sm font-medium text-gray-200">{{ candidate.title }}</p>
          <div class="flex items-center gap-2 mt-1">
            <span class="text-xs text-indigo-400">{{ t('writer.score') }}: {{ candidate.score }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-1 line-clamp-2">{{ candidate.reason }}</p>
        </button>
      </div>
    </div>
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
