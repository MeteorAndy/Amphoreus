<script setup lang="ts">
import { ref, onMounted } from 'vue'
import SceneFeed from '../components/SceneFeed.vue'
import DirectorPanel from '../components/DirectorPanel.vue'
import { useSceneEngine } from '../composables/useSceneEngine'
import { usePlotArchitect } from '../composables/usePlotArchitect'
import { useCharacters } from '../composables/useCharacters'
import { useI18n } from '../i18n'
import type { SceneRunRequest } from '../types/api'

const { t } = useI18n()

const {
  status,
  rounds,
  connected,
  error,
  sceneId,
  connect,
  intervene,
  endSceneSession,
  fetchStatus,
  reset,
} = useSceneEngine()

const { fetchOutlines, outlines, selectOutline, selectedOutline } = usePlotArchitect()
const { fetchCharacters, characters } = useCharacters()

const selectedSceneId = ref('')
const maxRounds = ref(10)

onMounted(() => {
  fetchStatus()
  fetchOutlines()
  fetchCharacters()
})

function handleStartScene(): void {
  if (!selectedOutline.value) {
    fetchOutlines()
    return
  }

  const req: SceneRunRequest = {
    scene_spec_id: selectedSceneId.value,
    plot_id: selectedOutline.value.id,
    character_ids: characters.value.map((c) => c.id),
    max_rounds: maxRounds.value,
  }
  connect(req)
}

function canStart(): boolean {
  return (
    !!selectedOutline.value &&
    !!selectedSceneId.value &&
    characters.value.length > 0 &&
    status.value.status === 'idle'
  )
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-100">{{ t('scene.title') }}</h1>
    </div>
    <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
      {{ error }}
    </div>
    <div v-if="status.status === 'idle'" class="bg-gray-900 rounded-lg border border-gray-800 p-6 space-y-4">
      <h2 class="text-sm font-semibold text-gray-200">{{ t('scene.config') }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-gray-500 mb-1">{{ t('scene.select_plot') }}</label>
          <select
            v-model="selectedOutline"
            @change="(e: Event) => selectOutline((e.target as HTMLSelectElement).value)"
            class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
          >
            <option :value="null" disabled>{{ t('writer.select_outline') }}</option>
            <option
              v-for="outline in outlines"
              :key="outline.id"
              :value="outline.id"
            >
              {{ outline.title }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">{{ t('scene.select_scene') }}</label>
          <select
            v-model="selectedSceneId"
            class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="" disabled>{{ t('scene.select_scene') }}</option>
            <template v-if="selectedOutline">
              <template v-for="act in selectedOutline.acts" :key="act.id">
                <option
                  :value="act.id"
                  disabled
                  class="text-gray-500 italic"
                >
                  -- {{ act.title }} --
                </option>
                <option
                  v-for="scene in act.scenes"
                  :key="scene.id"
                  :value="scene.id"
                >
                  {{ scene.order }}. {{ scene.title }}
                </option>
              </template>
            </template>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">{{ t('scene.max_rounds') }}</label>
          <input
            v-model.number="maxRounds"
            type="number"
            min="1"
            max="50"
            class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">{{ t('chars.title') }} ({{ characters.length }})</label>
          <div class="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-400">
            <div class="flex flex-wrap gap-1">
              <span
                v-for="char in characters.slice(0, 5)"
                :key="char.id"
                class="text-xs text-indigo-400 bg-indigo-900/30 px-1.5 py-0.5 rounded"
              >
                {{ char.name }}
              </span>
              <span v-if="characters.length > 5" class="text-xs text-gray-500">
                +{{ characters.length - 5 }} more
              </span>
            </div>
          </div>
        </div>
      </div>
      <button
        @click="handleStartScene"
        :disabled="!canStart()"
        class="px-6 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {{ t('scene.run') }}
      </button>
    </div>
    <div v-if="status.status !== 'idle'" class="grid grid-cols-1 lg:grid-cols-3 gap-6" style="height: calc(100vh - 12rem)">
      <div class="lg:col-span-2 h-full">
        <SceneFeed
          :rounds="rounds"
          :status="status"
          :connected="connected"
        />
      </div>
      <div class="h-full">
        <DirectorPanel
          :status="status"
          :connected="connected"
          :scene-id="sceneId"
          @intervene="intervene"
          @end-scene="endSceneSession"
          @start-scene="handleStartScene"
          @reset="reset"
        />
      </div>
    </div>
  </div>
</template>
