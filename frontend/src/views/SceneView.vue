<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Play, RotateCcw, Users, ChevronRight, Clapperboard } from 'lucide-vue-next'
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
const router = useRouter()

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

onMounted(async () => {
  initPlot()
  await fetchTemplates()
  if (projectStore.currentCharacters.value.length > 0) {
    characters.value = [...projectStore.currentCharacters.value]
  } else {
    await fetchCharacters()
  }
  const plotId = projectStore.currentPlotId.value || localStorage.getItem('amphoreus-outline-id')
  if (plotId) {
    selectedPlotId.value = plotId
    await selectOutline(plotId)
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

const isCompleted = computed(() => status.value.status === 'completed')

function goToWriter(): void {
  if (selectedPlotId.value) {
    localStorage.setItem('amphoreus-outline-id', selectedPlotId.value)
  }
  router.push('/writer')
}
</script>

<template>
  <div class="flex-1 min-h-0 overflow-y-auto space-y-6 fade-in-up pr-1">
    <div class="page-header">
      <div class="flex items-start gap-4">
        <div class="w-12 h-12 rounded-seal flex items-center justify-center flex-shrink-0 seal-glow" style="background: var(--gradient-chop-seal);">
          <Clapperboard :size="22" class="text-white" />
        </div>
        <div>
          <h1 class="font-display">{{ t('scene.title') }}</h1>
        </div>
      </div>
      <button v-if="isCompleted" @click="goToWriter" class="btn btn-primary">
        <ChevronRight :size="14" />
        {{ t('plot.proceed_writer') || '前往叙事写作' }}
      </button>
    </div>
    <div class="rule-ornament rule-ornament-diamond text-xs">
      <span class="font-display small-caps tracking-widest opacity-70">SCENE ENGINE</span>
    </div>

    <div v-if="error" class="error-banner">
      {{ error }}
    </div>

    <div v-if="status.status === 'idle'" class="card p-6 space-y-4">
      <h2 class="text-sm font-semibold text-parchment">{{ t('scene.config') }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="field-label">{{ t('scene.select_plot') }}</label>
          <select
            v-model="selectedPlotId"
            @change="handleSelectPlot(selectedPlotId)"
            class="input"
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
          <label class="field-label">{{ t('scene.select_scene') }}</label>
          <select
            v-model="selectedSceneId"
            class="input"
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
          <label class="field-label">{{ t('scene.max_rounds') }}</label>
          <input
            v-model.number="maxRounds"
            type="number"
            min="1"
            max="50"
            class="input"
          />
        </div>
      </div>

      <div v-if="characters.length > 0">
        <label class="field-label flex items-center gap-1.5">
          <Users :size="12" />
          {{ t('scene.select_chars') }}
          <span class="font-normal text-muted normal-case tracking-normal ml-1">
            {{ t('scene.chars_selected', { s: selectedCharacterIds.length, t: characters.length }) }}
          </span>
        </label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="char in characters"
            :key="char.id"
            @click="toggleCharacter(char.id)"
            class="chip"
            :class="selectedCharacterIds.includes(char.id) ? 'chip-active' : ''"
          >
            {{ char.name }}
          </button>
        </div>
      </div>

      <div class="flex gap-2">
        <button
          @click="handleStartScene"
          :disabled="!canStart()"
          class="btn btn-primary"
        >
          <Play :size="14" />
          {{ t('scene.run') }}
        </button>
        <button
          @click="handleReset"
          class="btn btn-secondary"
        >
          <RotateCcw :size="14" />
          {{ t('scene.reset') }}
        </button>
      </div>
    </div>

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
