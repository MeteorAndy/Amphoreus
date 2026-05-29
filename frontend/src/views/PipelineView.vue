<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from '../i18n'
import { usePipeline, type PipelineConfig } from '../composables/usePipeline'

const { t } = useI18n()
const pipeline = usePipeline()

const seedIdea = ref('')
const outputFormat = ref<'novel' | 'screenplay'>('novel')
const structure = ref('three_act')
const characterCount = ref(5)

const structures = [
  { value: 'three_act', label: { zh: '三幕结构', en: 'Three-Act' } },
  { value: 'hero_journey', label: { zh: '英雄之旅', en: "Hero's Journey" } },
  { value: 'save_the_cat', label: { zh: 'Save the Cat', en: 'Save the Cat' } },
  { value: 'qi_cheng_zhuan_he', label: { zh: '起承转合', en: 'Qi Cheng Zhuan He' } },
]

function handleStart() {
  if (!seedIdea.value.trim()) return
  const config: PipelineConfig = {
    seed_idea: seedIdea.value.trim(),
    lang: localStorage.getItem('amphoreus-lang') || 'zh',
    character_count: characterCount.value,
    narrative_structure: structure.value,
    output_format: outputFormat.value,
    max_rounds_per_scene: 15,
    auto_refine: true,
  }
  pipeline.start(config)
}

const stages = ['world', 'characters', 'relationships', 'plot', 'scenes', 'writing']
</script>

<template>
  <div class="max-w-4xl mx-auto p-6 space-y-6">
    <!-- Header -->
    <div class="text-center">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
        {{ t('pipeline.title') }}
      </h1>
      <p class="mt-2 text-gray-500 dark:text-gray-400">
        {{ t('pipeline.subtitle') }}
      </p>
    </div>

    <!-- Config Form (shown when idle) -->
    <div v-if="pipeline.status.value === 'idle'" class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('pipeline.idea') }}</label>
        <textarea v-model="seedIdea" :placeholder="t('pipeline.idea_placeholder')" rows="3" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('pipeline.format') }}</label>
          <select v-model="outputFormat" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-gray-900 dark:text-white">
            <option value="novel">{{ t('pipeline.novel') }}</option>
            <option value="screenplay">{{ t('pipeline.screenplay') }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('pipeline.structure') }}</label>
          <select v-model="structure" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-gray-900 dark:text-white">
            <option v-for="s in structures" :key="s.value" :value="s.value">{{ s.label.zh }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('pipeline.characters_count') }}</label>
          <input v-model.number="characterCount" type="number" min="1" max="20" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-gray-900 dark:text-white" />
        </div>
      </div>
      <button @click="handleStart" :disabled="!seedIdea.trim()" class="w-full py-3 px-6 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium transition-colors">
        {{ t('pipeline.start') }}
      </button>
    </div>

    <!-- Progress (shown when running/completed) -->
    <div v-if="pipeline.status.value !== 'idle'" class="space-y-4">
      <!-- Progress Bar -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div class="flex justify-between items-center mb-2">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('pipeline.progress') }}</span>
          <span class="text-sm text-gray-500">{{ Math.round(pipeline.progress.value * 100) }}%</span>
        </div>
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
          <div class="bg-blue-600 h-3 rounded-full transition-all duration-500" :style="{ width: `${pipeline.progress.value * 100}%` }" />
        </div>
        <!-- Stage Indicators -->
        <div class="mt-4 flex justify-between">
          <div v-for="stage in stages" :key="stage" class="flex flex-col items-center">
            <div :class="[
              'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold',
              pipeline.currentStage.value === stage ? 'bg-blue-600 text-white animate-pulse' :
              stages.indexOf(stage) < stages.indexOf(pipeline.currentStage.value) ? 'bg-green-500 text-white' :
              'bg-gray-200 dark:bg-gray-700 text-gray-500'
            ]">
              {{ stages.indexOf(stage) < stages.indexOf(pipeline.currentStage.value) ? '✓' : stages.indexOf(stage) + 1 }}
            </div>
            <span class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ t(`pipeline.stage.${stage}`) }}</span>
          </div>
        </div>
      </div>

      <!-- Status -->
      <div v-if="pipeline.status.value === 'running'" class="text-center text-blue-600 dark:text-blue-400 font-medium animate-pulse">
        {{ t('pipeline.running') }}
      </div>
      <div v-if="pipeline.status.value === 'completed'" class="text-center text-green-600 dark:text-green-400 font-medium">
        {{ t('pipeline.completed') }}
      </div>
      <div v-if="pipeline.status.value === 'error'" class="text-center text-red-600 dark:text-red-400 font-medium">
        {{ t('pipeline.error') }}: {{ pipeline.error.value }}
      </div>

      <!-- Stop Button -->
      <button v-if="pipeline.isRunning.value" @click="pipeline.stop()" class="w-full py-2 px-4 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors">
        {{ t('pipeline.stop') }}
      </button>

      <!-- Output -->
      <div v-if="pipeline.outputText.value" class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <pre class="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 max-h-96 overflow-y-auto">{{ pipeline.outputText.value }}</pre>
      </div>

      <!-- Reset -->
      <button v-if="!pipeline.isRunning.value" @click="pipeline.reset()" class="w-full py-2 px-4 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 font-medium transition-colors">
        {{ t('pipeline.start') }}
      </button>
    </div>
  </div>
</template>