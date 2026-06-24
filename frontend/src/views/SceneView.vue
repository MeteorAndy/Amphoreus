<script setup lang="ts">
import { ref, onMounted } from 'vue'
import SceneFeed from '../components/SceneFeed.vue'
import DirectorPanel from '../components/DirectorPanel.vue'
import EnvironmentPanel from '../components/EnvironmentPanel.vue'
import { useSceneEngine } from '../composables/useSceneEngine'
import { usePlotArchitect } from '../composables/usePlotArchitect'
import { useCharacters } from '../composables/useCharacters'
import { useProjectStore } from '../composables/useProjectStore'
import { useI18n } from '../i18n'
import type { SceneRunRequest } from '../types/api'

const { t } = useI18n()
const projectStore = useProjectStore()

const {
  status,
  rounds,
  connected,
  error,
  connect,
  intervene,
  endSceneSession,
  reset,
  environmentState,
  resolutionText,
} = useSceneEngine()

const { fetchTemplates, outlines, selectOutline, selectedOutline, initFromProject: initPlot } = usePlotArchitect()
const { fetchCharacters, characters } = useCharacters()

const selectedPlotId = ref('')
const selectedSceneId = ref('')
const maxRounds = ref(10)
const selectedCharacterIds = ref<string[]>([])

onMounted(() => {
  initPlot()
  fetchTemplates()
  if (projectStore.currentCharacters.value.length > 0) {
    characters.value = [...projectStore.currentCharacters.value]
  } else {
    fetchCharacters()
  }
  if (projectStore.currentPlotId.value) {
    selectedPlotId.value = projectStore.currentPlotId.value
    if (projectStore.currentPlotOutline.value) {
      selectOutline(selectedPlotId.value)
    }
  }
  selectedCharacterIds.value = characters.value.map((c) => c.id)
})

async function handleSelectPlot(plotId: string): Promise<void> {
  selectedPlotId.value = plotId
  selectedSceneId.value = ''
  if (plotId) {
    await selectOutline(plotId)
  }
}

function toggleCharacter(charId: string): void {
  const idx = selectedCharacterIds.value.indexOf(charId)
  if (idx !== -1) {
    selectedCharacterIds.value.splice(idx, 1)
  } else {
    selectedCharacterIds.value.push(charId)
  }
}

function handleStartScene(): void {
  if (!selectedPlotId.value || !selectedSceneId.value || selectedCharacterIds.value.length === 0) return

  const req: SceneRunRequest = {
    scene_spec_id: selectedSceneId.value,
    plot_id: selectedPlotId.value,
    character_ids: selectedCharacterIds.value,
    max_rounds: maxRounds.value,
  }
  connect(req)
}

function canStart(): boolean {
  return (
    !!selectedPlotId.value &&
    !!selectedSceneId.value &&
    selectedCharacterIds.value.length > 0 &&
    status.value.status === 'idle'
  )
}

function handleReset(): void {
  reset()
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
      </div>

      <div v-if="characters.length > 0">
        <label class="block text-xs text-muted mb-2">选择参与角色 ({{ selectedCharacterIds.length }}/{{ characters.length }})</label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="char in characters"
            :key="char.id"
            @click="toggleCharacter(char.id)"
            class="px-3 py-1.5 rounded-lg text-sm transition-colors border"
            :class="selectedCharacterIds.includes(char.id)
              ? 'bg-chop/20 border-chop text-chop'
              : 'bg-ink-elevated border-ink-edge text-parchment-dim hover:border-chop/50'"
          >
            {{ char.name }}
          </button>
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
    <div v-if="status.status !== 'idle'" class="grid grid-cols-1 lg:grid-cols-4 gap-4" style="height: calc(100vh - 12rem)">
      <div class="lg:col-span-3 h-full flex flex-col gap-4">
        <div class="flex-1 min-h-0">
          <SceneFeed
            :rounds="rounds"
            :status="status"
            :connected="connected"
            :resolution-text="resolutionText"
          />
        </div>
      </div>
      <div class="h-full flex flex-col gap-4">
        <EnvironmentPanel
          :environment-state="environmentState"
          :rounds="rounds"
          class="flex-1 min-h-0"
        />
        <DirectorPanel
          :status="status"
          :connected="connected"
          :scene-id="selectedSceneId"
          :rounds="rounds"
          @intervene="intervene"
          @end-scene="endSceneSession"
          @start-scene="handleStartScene"
          @reset="handleReset"
        />
      </div>
    </div>
  </div>
</template>
