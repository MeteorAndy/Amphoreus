<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from '../i18n'
import { useInteractive } from '../composables/useInteractive'
import { useWorldBuilder } from '../composables/useWorldBuilder'
import { useSceneEngine } from '../composables/useSceneEngine'
import StepProgress from '../components/StepProgress.vue'
import ChatPanel from '../components/ChatPanel.vue'
import CharacterCard from '../components/CharacterCard.vue'
import type { CharacterProfile, SceneSpec } from '../types/api'

const { t } = useI18n()

const interactive = useInteractive()
const worldBuilder = useWorldBuilder()
const sceneEngine = useSceneEngine()

// Step 1 — World Building
const seedIdea = ref('')

// Step 2 — Characters
const editingChar = ref<CharacterProfile | null>(null)

// Step 3 — Plot
const plotStructure = ref('three_act')
const structures = [
  { value: 'three_act', label: { zh: '三幕结构', en: 'Three-Act' } },
  { value: 'hero_journey', label: { zh: '英雄之旅', en: "Hero's Journey" } },
  { value: 'save_the_cat', label: { zh: 'Save the Cat', en: 'Save the Cat' } },
  { value: 'qi_cheng_zhuan_he', label: { zh: '起承转合', en: 'Qi Cheng Zhuan He' } },
]

// Step 4 — Scenes
const currentSceneIdx = ref(0)
const allScenes = computed<SceneSpec[]>(() =>
  interactive.plotOutline.value?.acts.flatMap((a) => a.scenes) ?? [],
)

// Step 5 — Writing
const outputFormat = ref<'novel' | 'screenplay'>('novel')

const stepLabels = computed(() => [
  t('interactive.step_world'),
  t('interactive.step_characters'),
  t('interactive.step_plot'),
  t('interactive.step_scenes'),
  t('interactive.step_writing'),
])

// ---- Step 1 handlers ----
function handleWorldSend(text: string): void {
  if (worldBuilder.sessionId.value) {
    worldBuilder.continueBuilding(text)
  } else {
    worldBuilder.startBuilding(text)
  }
}

async function handleFinalizeWorld(): Promise<void> {
  await worldBuilder.finalizeWorld()
  if (worldBuilder.worldState.value) {
    interactive.worldState.value = worldBuilder.worldState.value
  }
}

// ---- Step 2 handlers ----
async function handleGenerateCharacters(): Promise<void> {
  const worldId = interactive.worldState.value?.world_id
  if (!worldId) return
  await interactive.generateCharacters(worldId, 5)
}

function handleEditChar(char: CharacterProfile): void {
  editingChar.value = { ...char }
}

function handleSaveChar(): void {
  if (!editingChar.value) return
  const idx = interactive.characters.value.findIndex((c) => c.id === editingChar.value!.id)
  if (idx !== -1) interactive.characters.value[idx] = { ...editingChar.value }
  editingChar.value = null
}

function handleDeleteChar(id: string): void {
  interactive.characters.value = interactive.characters.value.filter((c) => c.id !== id)
}

// ---- Step 3 handlers ----
async function handleGeneratePlot(): Promise<void> {
  const worldId = interactive.worldState.value?.world_id
  if (!worldId) return
  await interactive.generatePlot(worldId, plotStructure.value)
}

// ---- Step 4 handlers ----
function runCurrentScene(): void {
  const scene = allScenes.value[currentSceneIdx.value]
  if (!scene || !interactive.plotOutline.value) return
  sceneEngine.connect({
    scene_spec_id: scene.id,
    plot_id: interactive.plotOutline.value.id,
    character_ids: interactive.characters.value.map((c) => c.id),
    max_rounds: 10,
  })
}

function skipScene(): void {
  if (currentSceneIdx.value < allScenes.value.length - 1) {
    currentSceneIdx.value++
    sceneEngine.reset()
  }
}

function nextScene(): void {
  interactive.addSceneArchive(sceneEngine.rounds.value)
  sceneEngine.reset()
  if (currentSceneIdx.value < allScenes.value.length - 1) {
    currentSceneIdx.value++
  }
}

// ---- Step 5 handlers ----
async function handleWriteNarrative(): Promise<void> {
  await interactive.writeNarrative(outputFormat.value)
}
</script>

<template>
  <div class="space-y-6 max-w-4xl mx-auto">
    <!-- Header -->
    <div>
      <h1 class="text-xl font-bold text-parchment">{{ t('interactive.title') }}</h1>
      <p class="text-sm text-muted mt-1">{{ t('interactive.subtitle') }}</p>
    </div>

    <!-- Step Progress -->
    <StepProgress :steps="stepLabels" :current="interactive.currentStep.value" />

    <!-- Error banner -->
    <div v-if="interactive.error.value" class="bg-red-900/20 border border-red-800 rounded-lg p-3">
      <span class="text-sm text-red-400">{{ interactive.error.value }}</span>
    </div>

    <!-- ===== STEP 1: World Building ===== -->
    <div v-if="interactive.currentStep.value === 1" class="space-y-4">
      <div class="bg-ink-panel rounded-lg border border-ink-edge p-4">
        <h2 class="text-base font-semibold text-parchment mb-3">{{ t('interactive.step_world') }}</h2>

        <!-- Not yet finalized -->
        <template v-if="!worldBuilder.finalized.value">
          <div v-if="!worldBuilder.sessionId.value" class="space-y-3">
            <form @submit.prevent="handleWorldSend(seedIdea)" class="flex gap-2">
              <input
                v-model="seedIdea"
                type="text"
                :placeholder="t('world.idea_placeholder')"
                class="flex-1 bg-ink-elevated border border-ink-edge rounded-lg px-4 py-2.5 text-sm text-parchment placeholder-muted focus:outline-none focus:border-chop transition-colors"
                :disabled="worldBuilder.loading.value"
              >
              <button
                type="submit"
                :disabled="worldBuilder.loading.value || !seedIdea.trim()"
                class="px-5 py-2.5 bg-chop text-white rounded-lg text-sm font-medium hover:bg-chop disabled:opacity-50 transition-colors"
              >
                {{ t('world.start_building') }}
              </button>
            </form>
          </div>
          <div v-else class="h-80">
            <ChatPanel
              :messages="worldBuilder.messages.value"
              :loading="worldBuilder.loading.value"
              :placeholder="t('world.idea_placeholder')"
              @send="handleWorldSend"
            />
          </div>
          <div v-if="worldBuilder.isDone.value" class="pt-3 text-center">
            <button
              @click="handleFinalizeWorld"
              :disabled="worldBuilder.loading.value"
              class="px-6 py-2.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {{ worldBuilder.loading.value ? t('world.finalizing') : t('world.finalize') }}
            </button>
          </div>
        </template>

        <!-- Finalized world summary -->
        <div v-if="worldBuilder.finalized.value && interactive.worldState.value" class="space-y-3">
          <div class="flex items-center gap-2">
            <span class="text-green-400 text-lg">&#10003;</span>
            <span class="text-sm font-medium text-parchment">{{ interactive.worldState.value.name }}</span>
          </div>
          <p v-if="interactive.worldState.value.description" class="text-xs text-parchment-dim">
            {{ interactive.worldState.value.description }}
          </p>
          <div class="grid grid-cols-4 gap-3 pt-2 border-t border-ink-edge">
            <div class="text-center">
              <div class="text-lg font-bold text-chop">{{ interactive.worldState.value.rules?.length || 0 }}</div>
              <div class="text-xs text-muted">{{ t('world.rules') }}</div>
            </div>
            <div class="text-center">
              <div class="text-lg font-bold text-chop">{{ interactive.worldState.value.locations?.length || 0 }}</div>
              <div class="text-xs text-muted">{{ t('world.locations') }}</div>
            </div>
            <div class="text-center">
              <div class="text-lg font-bold text-chop">{{ interactive.worldState.value.factions?.length || 0 }}</div>
              <div class="text-xs text-muted">{{ t('world.factions') }}</div>
            </div>
            <div class="text-center">
              <div class="text-lg font-bold text-chop">{{ interactive.worldState.value.timeline?.length || 0 }}</div>
              <div class="text-xs text-muted">{{ t('world.timeline') }}</div>
            </div>
          </div>
          <p class="text-xs text-muted italic">{{ t('interactive.edit_hint') }}</p>
        </div>
      </div>

      <!-- Navigation -->
      <div class="flex justify-end">
        <button
          @click="interactive.nextStep()"
          :disabled="!interactive.worldState.value"
          class="px-6 py-2.5 bg-chop hover:bg-chop disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
        >
          {{ t('interactive.next') }} &rarr;
        </button>
      </div>
    </div>

    <!-- ===== STEP 3: Plot ===== -->
    <div v-if="interactive.currentStep.value === 3" class="space-y-4">
      <div class="bg-ink-panel rounded-lg border border-ink-edge p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-parchment">{{ t('interactive.step_plot') }}</h2>
          <div class="flex items-center gap-2">
            <select v-model="plotStructure" class="bg-ink-elevated border border-ink-edge rounded px-2 py-1 text-xs text-parchment focus:outline-none focus:border-chop">
              <option v-for="s in structures" :key="s.value" :value="s.value">{{ s.label.zh }}</option>
            </select>
            <button
              @click="handleGeneratePlot"
              :disabled="interactive.generating.value"
              class="px-4 py-1.5 bg-chop hover:bg-chop disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors"
            >
              {{ interactive.generating.value ? t('interactive.generating') : t('plot.generate') }}
            </button>
          </div>
        </div>

        <div v-if="interactive.generating.value" class="text-sm text-chop animate-pulse">
          {{ t('interactive.generating') }}
        </div>

        <div v-if="interactive.plotOutline.value" class="space-y-3">
          <div v-for="act in interactive.plotOutline.value.acts" :key="act.id" class="border border-ink-edge rounded-lg p-3">
            <h3 class="text-sm font-semibold text-parchment mb-2">{{ act.title }}</h3>
            <p v-if="act.summary" class="text-xs text-muted mb-2">{{ act.summary }}</p>
            <div class="space-y-2">
              <div v-for="scene in act.scenes" :key="scene.id" class="bg-ink-elevated rounded p-2">
                <div class="flex items-start justify-between gap-2">
                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-medium text-parchment">{{ scene.title }}</p>
                    <p v-if="scene.setting" class="text-xs text-muted">{{ scene.setting }}</p>
                    <p v-if="scene.description" class="text-xs text-parchment-dim mt-1">{{ scene.description }}</p>
                  </div>
                  <span class="text-xs text-muted flex-shrink-0">#{{ scene.order }}</span>
                </div>
              </div>
            </div>
          </div>
          <p class="text-xs text-muted italic">{{ t('interactive.edit_hint') }}</p>
        </div>

        <p v-else-if="!interactive.generating.value" class="text-sm text-muted">{{ t('plot.empty') }}</p>
      </div>

      <div class="flex justify-between">
        <button @click="interactive.prevStep()" class="px-5 py-2 text-parchment-dim border border-ink-edge rounded-lg text-sm hover:text-parchment hover:border-ink-edge transition-colors">
          &larr; {{ t('interactive.back') }}
        </button>
        <button @click="interactive.nextStep()" :disabled="!interactive.plotOutline.value" class="px-6 py-2.5 bg-chop hover:bg-chop disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors">
          {{ t('interactive.next') }} &rarr;
        </button>
      </div>
    </div>
    <!-- ===== STEP 2: Characters ===== -->
    <div v-if="interactive.currentStep.value === 2" class="space-y-4">
      <div class="bg-ink-panel rounded-lg border border-ink-edge p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-parchment">{{ t('interactive.step_characters') }}</h2>
          <button
            @click="handleGenerateCharacters"
            :disabled="interactive.generating.value"
            class="px-4 py-1.5 bg-chop hover:bg-chop disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors"
          >
            {{ interactive.generating.value ? t('interactive.generating') : t('chars.generate') }}
          </button>
        </div>
        <p v-if="interactive.characters.value.length === 0 && !interactive.generating.value" class="text-sm text-muted">
          {{ t('chars.empty') }}
        </p>
        <div v-if="interactive.generating.value" class="text-sm text-chop animate-pulse">
          {{ t('interactive.generating') }}
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <CharacterCard
            v-for="char in interactive.characters.value"
            :key="char.id"
            :character="char"
            @edit="handleEditChar"
            @delete="handleDeleteChar"
          />
        </div>
        <div v-if="editingChar" class="bg-ink-elevated rounded-lg border border-ink-edge p-4 space-y-3">
          <h3 class="text-sm font-semibold text-parchment">{{ t('chars.edit_title') }}</h3>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs text-parchment-dim mb-1">{{ t('chars.name') }}</label>
              <input v-model="editingChar.name" class="w-full bg-ink-elevated border border-ink-edge rounded px-3 py-1.5 text-sm text-parchment focus:outline-none focus:border-chop" />
            </div>
            <div>
              <label class="block text-xs text-parchment-dim mb-1">{{ t('chars.role') }}</label>
              <input v-model="editingChar.role" class="w-full bg-ink-elevated border border-ink-edge rounded px-3 py-1.5 text-sm text-parchment focus:outline-none focus:border-chop" />
            </div>
          </div>
          <div>
            <label class="block text-xs text-parchment-dim mb-1">{{ t('chars.background') }}</label>
            <textarea v-model="editingChar.appearance" rows="2" class="w-full bg-ink-elevated border border-ink-edge rounded px-3 py-1.5 text-sm text-parchment focus:outline-none focus:border-chop" />
          </div>
          <div class="flex gap-2">
            <button @click="handleSaveChar" class="px-4 py-1.5 bg-chop hover:bg-chop text-white rounded text-xs font-medium transition-colors">{{ t('chars.save') }}</button>
            <button @click="editingChar = null" class="px-4 py-1.5 text-parchment-dim border border-ink-edge rounded text-xs hover:text-parchment transition-colors">{{ t('general.cancel') }}</button>
          </div>
        </div>
        <p class="text-xs text-muted italic">{{ t('interactive.review') }}</p>
      </div>
      <div class="flex justify-between">
        <button @click="interactive.prevStep()" class="px-5 py-2 text-parchment-dim border border-ink-edge rounded-lg text-sm hover:text-parchment hover:border-ink-edge transition-colors">
          &larr; {{ t('interactive.back') }}
        </button>
        <button @click="interactive.nextStep()" :disabled="interactive.characters.value.length === 0" class="px-6 py-2.5 bg-chop hover:bg-chop disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors">
          {{ t('interactive.next') }} &rarr;
        </button>
      </div>
    </div>

    <!-- ===== STEP 4: Scenes ===== -->
    <div v-if="interactive.currentStep.value === 4" class="space-y-4">
      <div class="bg-ink-panel rounded-lg border border-ink-edge p-4 space-y-4">
        <h2 class="text-base font-semibold text-parchment">{{ t('interactive.step_scenes') }}</h2>
        <div v-if="allScenes.length === 0" class="text-sm text-muted">{{ t('plot.empty') }}</div>
        <div v-else class="space-y-3">
          <div class="flex flex-wrap gap-2">
            <button
              v-for="(scene, idx) in allScenes"
              :key="scene.id"
              @click="currentSceneIdx = idx; sceneEngine.reset()"
              class="px-3 py-1 rounded text-xs font-medium transition-colors"
              :class="idx === currentSceneIdx ? 'bg-chop text-white' : 'bg-ink-elevated text-parchment-dim hover:text-parchment'"
            >
              {{ idx + 1 }}. {{ scene.title }}
            </button>
          </div>
          <div v-if="allScenes[currentSceneIdx]" class="bg-ink-elevated rounded-lg p-3 space-y-2">
            <h3 class="text-sm font-semibold text-parchment">{{ allScenes[currentSceneIdx].title }}</h3>
            <p v-if="allScenes[currentSceneIdx].setting" class="text-xs text-parchment-dim">{{ allScenes[currentSceneIdx].setting }}</p>
            <p v-if="allScenes[currentSceneIdx].description" class="text-xs text-muted">{{ allScenes[currentSceneIdx].description }}</p>
          </div>
          <div class="flex gap-2">
            <button @click="runCurrentScene" :disabled="sceneEngine.status.value.status === 'running'" class="px-4 py-1.5 bg-chop hover:bg-chop disabled:opacity-50 text-white rounded text-xs font-medium transition-colors">
              {{ sceneEngine.status.value.status === 'running' ? t('interactive.generating') : t('scene.run') }}
            </button>
            <button v-if="sceneEngine.status.value.status === 'completed'" @click="nextScene" class="px-4 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded text-xs font-medium transition-colors">
              {{ t('interactive.next') }}
            </button>
            <button @click="skipScene" :disabled="currentSceneIdx >= allScenes.length - 1" class="px-4 py-1.5 text-parchment-dim border border-ink-edge rounded text-xs hover:text-parchment transition-colors disabled:opacity-40">
              Skip
            </button>
          </div>
          <div v-if="sceneEngine.rounds.value.length > 0" class="max-h-64 overflow-y-auto space-y-2 border border-ink-edge rounded-lg p-3">
            <div v-for="round in sceneEngine.rounds.value" :key="round.round_number" class="text-xs text-parchment-dim border-b border-ink-edge pb-2 last:border-0">
              <span class="text-chop font-medium">{{ round.character }}</span>
              <span v-if="round.dialogue" class="ml-2 italic text-parchment-dim">"{{ round.dialogue }}"</span>
              <p v-if="round.narration" class="text-muted mt-0.5">{{ round.narration }}</p>
            </div>
          </div>
          <p class="text-xs text-muted">{{ t('interactive.review') }}</p>
        </div>
      </div>
      <div class="flex justify-between">
        <button @click="interactive.prevStep()" class="px-5 py-2 text-parchment-dim border border-ink-edge rounded-lg text-sm hover:text-parchment hover:border-ink-edge transition-colors">
          &larr; {{ t('interactive.back') }}
        </button>
        <button @click="interactive.nextStep()" class="px-6 py-2.5 bg-chop hover:bg-chop text-white rounded-lg text-sm font-medium transition-colors">
          {{ t('interactive.next') }} &rarr;
        </button>
      </div>
    </div>

    <!-- ===== STEP 5: Writing ===== -->
    <div v-if="interactive.currentStep.value === 5" class="space-y-4">
      <div class="bg-ink-panel rounded-lg border border-ink-edge p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-parchment">{{ t('interactive.step_writing') }}</h2>
          <div class="flex items-center gap-2">
            <select v-model="outputFormat" class="bg-ink-elevated border border-ink-edge rounded px-2 py-1 text-xs text-parchment focus:outline-none focus:border-chop">
              <option value="novel">{{ t('writer.format_novel') }}</option>
              <option value="screenplay">{{ t('writer.format_screenplay') }}</option>
            </select>
            <button @click="handleWriteNarrative" :disabled="interactive.generating.value" class="px-4 py-1.5 bg-chop hover:bg-chop disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors">
              {{ interactive.generating.value ? t('interactive.generating') : t('writer.convert') }}
            </button>
          </div>
        </div>
        <div v-if="interactive.generating.value" class="text-sm text-chop animate-pulse">
          {{ t('interactive.generating') }}
        </div>
        <div v-if="interactive.writtenOutput.value" class="space-y-3">
          <div class="bg-ink-elevated rounded-lg p-4 max-h-96 overflow-y-auto">
            <pre class="whitespace-pre-wrap text-sm text-parchment font-sans">{{ interactive.writtenOutput.value }}</pre>
          </div>
          <div class="flex gap-2">
            <button @click="interactive.exportNarrative(outputFormat)" class="px-4 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded text-xs font-medium transition-colors">
              {{ t('writer.export') }}
            </button>
          </div>
          <p class="text-xs text-muted italic">{{ t('interactive.edit_hint') }}</p>
        </div>
        <p v-else-if="!interactive.generating.value" class="text-sm text-muted">{{ t('writer.preview_hint') }}</p>
      </div>
      <div class="flex justify-between">
        <button @click="interactive.prevStep()" class="px-5 py-2 text-parchment-dim border border-ink-edge rounded-lg text-sm hover:text-parchment hover:border-ink-edge transition-colors">
          &larr; {{ t('interactive.back') }}
        </button>
      </div>
    </div>

  </div>
</template>
