<script setup lang="ts">
import { computed } from 'vue'
import { PenTool, Download, BookOpen, Film } from 'lucide-vue-next'
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

interface ChapterSection {
  number: number
  title: string
  content: string
}

const parsedChapters = computed<ChapterSection[]>(() => {
  if (!props.output || props.format !== 'novel' || !props.output.chapters) {
    return []
  }
  return props.output.chapters.map((ch) => ({
    number: ch.number,
    title: ch.title,
    content: ch.content,
  }))
})

const plainContent = computed(() => {
  if (!props.output) return ''
  if (props.format === 'novel' && !props.output.chapters) {
    return props.output.content
  }
  if (props.format === 'screenplay') {
    return props.output.content
  }
  return ''
})
</script>

<template>
  <div class="flex flex-col h-full fade-in-up">
    <div class="flex items-center justify-between mb-4">
      <div class="flex gap-1.5">
        <button
          @click="emit('toggleFormat', 'novel')"
          class="chip"
          :class="format === 'novel' ? 'chip-active' : ''"
        >
          <BookOpen :size="14" />
          {{ t('writer.format_novel') }}
        </button>
        <button
          @click="emit('toggleFormat', 'screenplay')"
          class="chip"
          :class="format === 'screenplay' ? 'chip-active' : ''"
        >
          <Film :size="14" />
          {{ t('writer.format_screenplay') }}
        </button>
      </div>
      <button
        @click="emit('export')"
        :disabled="!output || loading"
        class="btn btn-primary"
      >
        <Download :size="14" />
        {{ t('writer.export') }}
      </button>
    </div>

    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="flex flex-col items-center gap-4">
        <div class="flex gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-chop" style="animation: inkDrip 1.4s infinite var(--ease-editorial); animation-delay: 0s" />
          <span class="w-2.5 h-2.5 rounded-full bg-chop" style="animation: inkDrip 1.4s infinite var(--ease-editorial); animation-delay: 0.2s" />
          <span class="w-2.5 h-2.5 rounded-full bg-chop" style="animation: inkDrip 1.4s infinite var(--ease-editorial); animation-delay: 0.4s" />
        </div>
        <span class="text-sm text-muted font-display italic">{{ t('writer.generating') || '笔墨酝酿中...' }}</span>
      </div>
    </div>

    <div
      v-else-if="output"
      class="flex-1 card overflow-y-auto"
    >
      <div class="manuscript-rail px-8 py-10 md:px-12 lg:px-16 max-w-4xl mx-auto">
        <header class="text-center mb-12">
          <div class="inline-block">
            <h1 class="font-display text-3xl md:text-4xl lg:text-5xl font-bold text-parchment-bright tracking-tight mb-4">
              {{ output.title }}
            </h1>
            <div class="flex items-center justify-center gap-3">
              <span class="h-px w-12 bg-gradient-to-r from-transparent to-chop/60" />
              <span class="w-1.5 h-1.5 rounded-full bg-chop/60" />
              <span class="h-px w-12 bg-gradient-to-l from-transparent to-chop/60" />
            </div>
          </div>
        </header>

        <article class="manuscript-content">
          <template v-if="parsedChapters.length > 0">
            <section
              v-for="(chapter, idx) in parsedChapters"
              :key="idx"
              class="mb-12"
            >
              <div class="chapter-divider flex items-center justify-center gap-4 mb-8">
                <span class="h-px flex-1 bg-gradient-to-r from-transparent via-ink-edge to-transparent" />
                <span class="text-xs uppercase tracking-[0.2em] text-muted font-display">
                  {{ t('writer.chapter') || 'Chapter' }} {{ chapter.number }}
                </span>
                <span class="h-px flex-1 bg-gradient-to-l from-transparent via-ink-edge to-transparent" />
              </div>
              <h2 class="font-display text-xl md:text-2xl font-semibold text-parchment mb-6 text-center">
                {{ chapter.title }}
              </h2>
              <div class="drop-cap text-parchment-dim font-body leading-[2] tracking-wide text-[0.95rem] whitespace-pre-wrap">
                {{ chapter.content }}
              </div>
            </section>
          </template>
          <div v-else class="text-parchment-dim font-body leading-[2] tracking-wide text-[0.95rem] whitespace-pre-wrap">
            {{ plainContent }}
          </div>
        </article>
      </div>
    </div>

    <div v-else class="flex-1 flex items-center justify-center">
      <div class="empty-state">
        <div class="empty-state-icon">
          <PenTool :size="48" />
        </div>
        <p class="empty-state-text font-display italic">
          {{ t('writer.preview_hint') }}
        </p>
        <div class="rule-ornament w-32">
          <span class="text-xs text-muted/60">✦</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.manuscript-content {
  text-align: justify;
  hyphens: auto;
}

.chapter-divider span:first-child,
.chapter-divider span:last-child {
  max-width: 80px;
}

@media (max-width: 640px) {
  .manuscript-rail {
    padding-left: 1rem !important;
    padding-right: 1rem !important;
  }
}
</style>
