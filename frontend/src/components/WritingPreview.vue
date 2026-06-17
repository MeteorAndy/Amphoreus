<script setup lang="ts">
import { computed } from 'vue'
import type { WriterOutput, NarrativeFormat } from '../types/api'
import { useI18n } from '../i18n'

const { t } = useI18n()

const props = defineProps<{
  output: WriterOutput | null
  format: NarrativeFormat
  loading: boolean
}>()

const emit = defineEmits<{
  toggleFormat: [format: NarrativeFormat]
  export: []
  selectTitle: [title: string]
}>()

const displayContent = computed(() => {
  if (!props.output) return ''
  if (props.format === 'novel') {
    return props.output.chapters
      ? props.output.chapters.map((ch) => `## Chapter ${ch.number}: ${ch.title}\n\n${ch.content}`).join('\n\n')
      : props.output.content
  }
  return props.output.content
})
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="flex items-center justify-between mb-4">
      <div class="flex bg-ink-panel rounded-lg border border-ink-edge overflow-hidden">
        <button
          @click="emit('toggleFormat', 'novel')"
          class="px-4 py-2 text-sm font-medium transition-colors"
          :class="format === 'novel' ? 'bg-chop text-white' : 'text-parchment-dim hover:text-parchment'"
        >
          {{ t('writer.format_novel') }}
        </button>
        <button
          @click="emit('toggleFormat', 'screenplay')"
          class="px-4 py-2 text-sm font-medium transition-colors"
          :class="format === 'screenplay' ? 'bg-chop text-white' : 'text-parchment-dim hover:text-parchment'"
        >
          {{ t('writer.format_screenplay') }}
        </button>
      </div>
      <button
        @click="emit('export')"
        :disabled="!output || loading"
        class="px-4 py-2 bg-chop text-white rounded-lg text-sm font-medium hover:bg-chop disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {{ t('writer.export') }}
      </button>
    </div>
    <div v-if="loading" class="flex items-center justify-center h-64">
      <div class="flex gap-2">
        <span class="w-3 h-3 bg-chop rounded-full animate-bounce" style="animation-delay: 0s" />
        <span class="w-3 h-3 bg-chop rounded-full animate-bounce" style="animation-delay: 0.15s" />
        <span class="w-3 h-3 bg-chop rounded-full animate-bounce" style="animation-delay: 0.3s" />
      </div>
    </div>
    <div
      v-else-if="output"
      class="flex-1 bg-ink-panel rounded-lg border border-ink-edge p-6 overflow-y-auto"
    >
      <div class="max-w-none">
        <h1 class="text-2xl font-bold text-parchment mb-6">{{ output.title }}</h1>
        <div class="prose prose-invert prose-sm max-w-none text-parchment-dim leading-relaxed whitespace-pre-wrap">
          {{ displayContent }}
        </div>
      </div>
    </div>
    <div v-else class="flex items-center justify-center h-64 text-muted text-sm">
      {{ t('writer.preview_hint') }}
    </div>
  </div>
</template>
