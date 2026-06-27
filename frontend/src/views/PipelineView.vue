<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from '../i18n'
import { usePipeline, type PipelineConfig } from '../composables/usePipeline'
import { Workflow, FileText, Film, Users, BookOpen, Sparkles, Square, RotateCcw, Check, Globe, Drama, PenTool } from 'lucide-vue-next'

const { t, currentLang } = useI18n()
const pipeline = usePipeline()

const seedIdea = ref('')
const outputFormat = ref<'novel' | 'screenplay'>('novel')
const structure = ref('three_act')
const characterCount = ref(5)

const structures = computed(() => [
  { value: 'three_act', label: t('structure.three_act') },
  { value: 'hero_journey', label: t('structure.hero_journey') },
  { value: 'save_the_cat', label: t('structure.save_the_cat') },
  { value: 'qi_cheng_zhuan_he', label: t('structure.qi_cheng_zhuan_he') },
])

function handleStart() {
  if (!seedIdea.value.trim()) return
  const config: PipelineConfig = {
    seed_idea: seedIdea.value.trim(),
    lang: currentLang.value,
    character_count: characterCount.value,
    narrative_structure: structure.value,
    output_format: outputFormat.value,
    max_rounds_per_scene: 15,
    auto_refine: true,
  }
  pipeline.start(config)
}

const stages = ['world', 'characters', 'relationships', 'plot', 'scenes', 'writing']
const stageIcons: Record<string, typeof Workflow> = {
  world: Globe,
  characters: Users,
  relationships: Users,
  plot: BookOpen,
  scenes: Drama,
  writing: PenTool,
}

function stageStatus(idx: number): 'done' | 'current' | 'upcoming' {
  const currentIdx = stages.indexOf(pipeline.currentStage.value)
  if (currentIdx < 0) return 'upcoming'
  if (idx < currentIdx) return 'done'
  if (idx === currentIdx) return 'current'
  return 'upcoming'
}
</script>

<template>
  <div class="flex-1 min-h-0 overflow-y-auto max-w-3xl mx-auto fade-in-up pr-1">
    <div class="page-header text-center pb-6 mb-6">
      <div class="flex flex-col items-center gap-3 w-full">
        <div class="w-14 h-14 rounded-seal flex items-center justify-center seal-glow" style="background: var(--gradient-chop-seal);">
          <Workflow :size="26" class="text-white" />
        </div>
        <div>
          <h1 class="font-display text-2xl mb-1">{{ t('pipeline.title') }}</h1>
          <p class="text-sm text-muted italic">{{ t('pipeline.subtitle') }}</p>
        </div>
      </div>
    </div>
    <div class="rule-ornament rule-ornament-diamond text-xs mb-8">
      <span class="font-display small-caps tracking-widest opacity-70">PIPELINE</span>
    </div>

    <div v-if="pipeline.status.value === 'idle'" class="card p-6 space-y-5">
      <div>
        <label class="field-label">{{ t('pipeline.idea') }}</label>
        <textarea v-model="seedIdea" :placeholder="t('pipeline.idea_placeholder')" rows="4" class="input" />
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="field-label">{{ t('pipeline.format') }}</label>
          <div class="flex gap-2">
            <button
              @click="outputFormat = 'novel'"
              class="chip flex-1 justify-center"
              :class="outputFormat === 'novel' ? 'chip-active' : ''"
            >
              <FileText :size="13" />
              {{ t('pipeline.novel') }}
            </button>
            <button
              @click="outputFormat = 'screenplay'"
              class="chip flex-1 justify-center"
              :class="outputFormat === 'screenplay' ? 'chip-active' : ''"
            >
              <Film :size="13" />
              {{ t('pipeline.screenplay') }}
            </button>
          </div>
        </div>
        <div>
          <label class="field-label">{{ t('pipeline.structure') }}</label>
          <select v-model="structure" class="input">
            <option v-for="s in structures" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div>
          <label class="field-label">{{ t('pipeline.characters_count') }}</label>
          <input v-model.number="characterCount" type="number" min="1" max="20" class="input" />
        </div>
      </div>

      <button
        @click="handleStart"
        :disabled="!seedIdea.trim()"
        class="btn btn-primary btn-lg w-full"
      >
        <Sparkles :size="16" />
        {{ t('pipeline.start') }}
      </button>
    </div>

    <div v-if="pipeline.status.value !== 'idle'" class="space-y-5">
      <div class="card p-6">
        <div class="flex justify-between items-center mb-3">
          <span class="text-sm font-medium text-parchment-dim">{{ t('pipeline.progress') }}</span>
          <span class="text-sm font-semibold text-chop">{{ Math.round(pipeline.progress.value * 100) }}%</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${pipeline.progress.value * 100}%` }" />
        </div>

        <div class="mt-6 grid grid-cols-6 gap-2">
          <div v-for="(stage, idx) in stages" :key="stage" class="flex flex-col items-center gap-1.5">
            <div
              class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold transition-all"
              :class="{
                'bg-chop text-white shadow-lg shadow-chop/30': stageStatus(idx) === 'current',
                'bg-editor text-white': stageStatus(idx) === 'done',
                'bg-ink-elevated text-muted border border-ink-edge': stageStatus(idx) === 'upcoming',
              }"
            >
              <Check v-if="stageStatus(idx) === 'done'" :size="14" />
              <component v-else :is="stageIcons[stage]" :size="14" />
            </div>
            <span
              class="text-[0.65rem] text-center leading-tight"
              :class="{
                'text-chop font-medium': stageStatus(idx) === 'current',
                'text-parchment-dim': stageStatus(idx) === 'done',
                'text-muted': stageStatus(idx) === 'upcoming',
              }"
            >
              {{ t(`pipeline.stage.${stage}`) }}
            </span>
          </div>
        </div>
      </div>

      <div v-if="pipeline.status.value === 'running'" class="text-center text-chop font-medium animate-pulse text-sm">
        {{ t('pipeline.running') }}
      </div>
      <div v-if="pipeline.status.value === 'completed'" class="text-center text-editor font-medium text-sm flex items-center justify-center gap-1.5">
        <Check :size="16" />
        {{ t('pipeline.completed') }}
      </div>
      <div v-if="pipeline.status.value === 'error'" class="error-banner justify-center">
        {{ t('pipeline.error') }}: {{ pipeline.error.value }}
      </div>

      <button
        v-if="pipeline.isRunning.value"
        @click="pipeline.stop()"
        class="btn btn-danger w-full"
      >
        <Square :size="14" />
        {{ t('pipeline.stop') }}
      </button>

      <div v-if="pipeline.outputText.value" class="card p-6">
        <pre class="whitespace-pre-wrap text-sm text-parchment-dim max-h-96 overflow-y-auto font-sans leading-relaxed">{{ pipeline.outputText.value }}</pre>
      </div>

      <button
        v-if="!pipeline.isRunning.value"
        @click="pipeline.reset()"
        class="btn btn-secondary w-full"
      >
        <RotateCcw :size="14" />
        {{ t('pipeline.start') }}
      </button>
    </div>
  </div>
</template>
