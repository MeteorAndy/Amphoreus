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
  connect,
  intervene,
  endSceneSession,
  fetchStatus,
  reset,
} = useSceneEngine()

const { fetchOutlines, outlines, selectOutline, selectedOutline } = usePlotArchitect()
const { fetchCharacters, characters } = useCharacters()

const selectedPlotId = ref('')
const selectedSceneId = ref('')
const maxRounds = ref(10)

onMounted(() => {
  fetchStatus()
  fetchOutlines()
  fetchCharacters()
})

async function handleSelectPlot(plotId: string): Promise<void> {
  selectedPlotId.value = plotId
  if (plotId) {
    await selectOutline(plotId)
  }
}

function handleStartScene(): void {
  if (!selectedPlotId.value || !selectedSceneId.value) return

  const req: SceneRunRequest = {
    scene_spec_id: selectedSceneId.value,
    plot_id: selectedPlotId.value,
    character_ids: characters.value.map((c) => c.id),
    max_rounds: maxRounds.value,
  }
  connect(req)
}

function canStart(): boolean {
  return (
    !!selectedPlotId.value &&
    !!selectedSceneId.value &&
    characters.value.length > 0 &&
    status.value.status === 'idle'
  )
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-parchment">{{ t('scene.title') }}</h1>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
      {{ error }}
    </div>

    <!-- Configuration (idle state) -->
    <div v-if="status.status === 'idle'" class="bg-ink-panel rounded-lg border border-ink-edge p-6 space-y-4">
      <h2 class="text-sm font-semibold text-parchment">{{ t('scene.config') }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-muted mb-1">{{ t('scene.select_plot') }}</label>
          <select
            v-model="selectedPlotId"
            @change="handleSelectPlot(selectedPlotId)"
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
        <div>
          <label class="block text-xs text-muted mb-1">{{ t('scene.select_scene') }}</label>
          <select
            v-model="selectedSceneId"
            class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
          >
            <option value="" disabled>{{ t('scene.select_scene') }}</option>
            <template v-if="selectedOutline">
              <template v-for="act in selectedOutline.acts" :key="act.id">
                <option
                  :value="'act-' + act.id"
                  disabled
                  class="text-muted italic"
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
          <label class="block text-xs text-muted mb-1">{{ t('scene.max_rounds') }}</label>
          <input
            v-model.number="maxRounds"
            type="number"
            min="1"
            max="50"
            class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
          />
        </div>
        <div>
          <label class="block text-xs text-muted mb-1">{{ t('chars.title') }} ({{ characters.length }})</label>
          <div class="bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment-dim">
            <div class="flex flex-wrap gap-1">
              <span
                v-for="char in characters.slice(0, 5)"
                :key="char.id"
                class="text-xs text-chop bg-chop/20/30 px-1.5 py-0.5 rounded"
              >
                {{ char.name }}
              </span>
              <span v-if="characters.length > 5" class="text-xs text-muted">
                +{{ characters.length - 5 }} more
              </span>
            </div>
          </div>
        </div>
      </div>
      <button
        @click="handleStartScene"
        :disabled="!canStart()"
        class="px-6 py-2 bg-chop text-white rounded-lg text-sm font-medium hover:bg-chop disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {{ t('scene.run') }}
      </button>
    </div>

    <!-- Running / completed scene -->
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
          :scene-id="selectedSceneId"
          :rounds="rounds"
          @intervene="intervene"
          @end-scene="endSceneSession"
          @start-scene="handleStartScene"
          @reset="reset"
        />
      </div>
    </div>
  </div>
</template>
