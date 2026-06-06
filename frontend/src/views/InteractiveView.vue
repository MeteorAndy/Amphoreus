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
      <h1 class="text-xl font-bold text-gray-100">{{ t('interactive.title') }}</h1>
      <p class="text-sm text-gray-500 mt-1">{{ t('interactive.subtitle') }}</p>
    </div>

    <!-- Step Progress -->
    <StepProgress :steps="stepLabels" :current="interactive.currentStep.value" />

    <!-- Error banner -->
    <div v-if="interactive.error.value" class="bg-red-900/20 border border-red-800 rounded-lg p-3">
      <span class="text-sm text-red-400">{{ interactive.error.value }}</span>
    </div>

    <!-- ===== STEP 1: World Building ===== -->
    <div v-if="interactive.currentStep.value === 1" class="space-y-4">
      <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <h2 class="text-base font-semibold text-gray-100 mb-3">{{ t('interactive.step_world') }}</h2>

        <!-- Not yet finalized -->
        <template v-if="!worldBuilder.finalized.value">
          <div v-if="!worldBuilder.sessionId.value" class="space-y-3">
            <form @submit.prevent="handleWorldSend(seedIdea)" class="flex gap-2">
              <input
                v-model="seedIdea"
                type="text"
                :placeholder="t('world.idea_placeholder')"
                class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                :disabled="worldBuilder.loading.value"
              >
              <button
                type="submit"
                :disabled="worldBuilder.loading.value || !seedIdea.trim()"
                class="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 transition-colors"
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
            <span class="text-sm font-medium text-gray-200">{{ interactive.worldState.value.name }}</span>
          </div>
          <p v-if="interactive.worldState.value.description" class="text-xs text-gray-400">
            {{ interactive.worldState.value.description }}
          </p>
          <div class="grid grid-cols-4 gap-3 pt-2 border-t border-gray-800">
            <div class="text-center">
              <div class="text-lg font-bold text-indigo-400">{{ interactive.worldState.value.rules?.length || 0 }}</div>
              <div class="text-xs text-gray-500">{{ t('world.rules') }}</div>
            </div>
            <div class="text-center">
              <div class="text-lg font-bold text-indigo-400">{{ interactive.worldState.value.locations?.length || 0 }}</div>
              <div class="text-xs text-gray-500">{{ t('world.locations') }}</div>
            </div>
            <div class="text-center">
              <div class="text-lg font-bold text-indigo-400">{{ interactive.worldState.value.factions?.length || 0 }}</div>
              <div class="text-xs text-gray-500">{{ t('world.factions') }}</div>
            </div>
            <div class="text-center">
              <div class="text-lg font-bold text-indigo-400">{{ interactive.worldState.value.timeline?.length || 0 }}</div>
              <div class="text-xs text-gray-500">{{ t('world.timeline') }}</div>
            </div>
          </div>
          <p class="text-xs text-gray-500 italic">{{ t('interactive.edit_hint') }}</p>
        </div>
      </div>

      <!-- Navigation -->
      <div class="flex justify-end">
        <button
          @click="interactive.nextStep()"
          :disabled="!interactive.worldState.value"
          class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
        >
          {{ t('interactive.next') }} &rarr;
        </button>
      </div>
    </div>

    <!-- ===== STEP 3: Plot ===== -->
    <div v-if="interactive.currentStep.value === 3" class="space-y-4">
      <div class="bg-gray-900 rounded-lg border border-gray-800 p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-gray-100">{{ t('interactive.step_plot') }}</h2>
          <div class="flex items-center gap-2">
            <select v-model="plotStructure" class="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-indigo-500">
              <option v-for="s in structures" :key="s.value" :value="s.value">{{ s.label.zh }}</option>
            </select>
            <button
              @click="handleGeneratePlot"
              :disabled="interactive.generating.value"
              class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors"
            >
              {{ interactive.generating.value ? t('interactive.generating') : t('plot.generate') }}
            </button>
          </div>
        </div>

        <div v-if="interactive.generating.value" class="text-sm text-indigo-400 animate-pulse">
          {{ t('interactive.generating') }}
        </div>

        <div v-if="interactive.plotOutline.value" class="space-y-3">
          <div v-for="act in interactive.plotOutline.value.acts" :key="act.id" class="border border-gray-800 rounded-lg p-3">
            <h3 class="text-sm font-semibold text-gray-200 mb-2">{{ act.title }}</h3>
            <p v-if="act.summary" class="text-xs text-gray-500 mb-2">{{ act.summary }}</p>
            <div class="space-y-2">
              <div v-for="scene in act.scenes" :key="scene.id" class="bg-gray-800 rounded p-2">
                <div class="flex items-start justify-between gap-2">
                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-medium text-gray-200">{{ scene.title }}</p>
                    <p v-if="scene.setting" class="text-xs text-gray-500">{{ scene.setting }}</p>
                    <p v-if="scene.description" class="text-xs text-gray-400 mt-1">{{ scene.description }}</p>
                  </div>
                  <span class="text-xs text-gray-600 flex-shrink-0">#{{ scene.order }}</span>
                </div>
              </div>
            </div>
          </div>
          <p class="text-xs text-gray-500 italic">{{ t('interactive.edit_hint') }}</p>
        </div>

        <p v-else-if="!interactive.generating.value" class="text-sm text-gray-500">{{ t('plot.empty') }}</p>
      </div>

      <div class="flex justify-between">
        <button @click="interactive.prevStep()" class="px-5 py-2 text-gray-400 border border-gray-700 rounded-lg text-sm hover:text-gray-200 hover:border-gray-600 transition-colors">
          &larr; {{ t('interactive.back') }}
        </button>
        <button @click="interactive.nextStep()" :disabled="!interactive.plotOutline.value" class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors">
          {{ t('interactive.next') }} &rarr;
        </button>
      </div>
    </div>
    <!-- ===== STEP 2: Characters ===== -->
    <div v-if="interactive.currentStep.value === 2" class="space-y-4">
      <div class="bg-gray-900 rounded-lg border border-gray-800 p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-gray-100">{{ t('interactive.step_characters') }}</h2>
          <button
            @click="handleGenerateCharacters"
            :disabled="interactive.generating.value"
            class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors"
          >
            {{ interactive.generating.value ? t('interactive.generating') : t('chars.generate') }}
          </button>
        </div>
        <p v-if="interactive.characters.value.length === 0 && !interactive.generating.value" class="text-sm text-gray-500">
          {{ t('chars.empty') }}
        </p>
        <div v-if="interactive.generating.value" class="text-sm text-indigo-400 animate-pulse">
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
        <div v-if="editingChar" class="bg-gray-800 rounded-lg border border-gray-700 p-4 space-y-3">
          <h3 class="text-sm font-semibold text-gray-200">{{ t('chars.edit_title') }}</h3>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs text-gray-400 mb-1">{{ t('chars.name') }}</label>
              <input v-model="editingChar.name" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-indigo-500" />
            </div>
            <div>
              <label class="block text-xs text-gray-400 mb-1">{{ t('chars.role') }}</label>
              <input v-model="editingChar.role" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-indigo-500" />
            </div>
          </div>
          <div>
            <label class="block text-xs text-gray-400 mb-1">{{ t('chars.background') }}</label>
            <textarea v-model="editingChar.appearance" rows="2" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-indigo-500" />
          </div>
          <div class="flex gap-2">
            <button @click="handleSaveChar" class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition-colors">{{ t('chars.save') }}</button>
            <button @click="editingChar = null" class="px-4 py-1.5 text-gray-400 border border-gray-600 rounded text-xs hover:text-gray-200 transition-colors">{{ t('general.cancel') }}</button>
          </div>
        </div>
        <p class="text-xs text-gray-500 italic">{{ t('interactive.review') }}</p>
      </div>
      <div class="flex justify-between">
        <button @click="interactive.prevStep()" class="px-5 py-2 text-gray-400 border border-gray-700 rounded-lg text-sm hover:text-gray-200 hover:border-gray-600 transition-colors">
          &larr; {{ t('interactive.back') }}
        </button>
        <button @click="interactive.nextStep()" :disabled="interactive.characters.value.length === 0" class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors">
          {{ t('interactive.next') }} &rarr;
        </button>
      </div>
    </div>

    <!-- ===== STEP 4: Scenes ===== -->
    <div v-if="interactive.currentStep.value === 4" class="space-y-4">
      <div class="bg-gray-900 rounded-lg border border-gray-800 p-4 space-y-4">
        <h2 class="text-base font-semibold text-gray-100">{{ t('interactive.step_scenes') }}</h2>
        <div v-if="allScenes.length === 0" class="text-sm text-gray-500">{{ t('plot.empty') }}</div>
        <div v-else class="space-y-3">
          <div class="flex flex-wrap gap-2">
            <button
              v-for="(scene, idx) in allScenes"
              :key="scene.id"
              @click="currentSceneIdx = idx; sceneEngine.reset()"
              class="px-3 py-1 rounded text-xs font-medium transition-colors"
              :class="idx === currentSceneIdx ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-200'"
            >
              {{ idx + 1 }}. {{ scene.title }}
            </button>
          </div>
          <div v-if="allScenes[currentSceneIdx]" class="bg-gray-800 rounded-lg p-3 space-y-2">
            <h3 class="text-sm font-semibold text-gray-200">{{ allScenes[currentSceneIdx].title }}</h3>
            <p v-if="allScenes[currentSceneIdx].setting" class="text-xs text-gray-400">{{ allScenes[currentSceneIdx].setting }}</p>
            <p v-if="allScenes[currentSceneIdx].description" class="text-xs text-gray-500">{{ allScenes[currentSceneIdx].description }}</p>
          </div>
          <div class="flex gap-2">
            <button @click="runCurrentScene" :disabled="sceneEngine.status.value.status === 'running'" class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-medium transition-colors">
              {{ sceneEngine.status.value.status === 'running' ? t('interactive.generating') : t('scene.run') }}
            </button>
            <button v-if="sceneEngine.status.value.status === 'completed'" @click="nextScene" class="px-4 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded text-xs font-medium transition-colors">
              {{ t('interactive.next') }}
            </button>
            <button @click="skipScene" :disabled="currentSceneIdx >= allScenes.length - 1" class="px-4 py-1.5 text-gray-400 border border-gray-700 rounded text-xs hover:text-gray-200 transition-colors disabled:opacity-40">
              Skip
            </button>
          </div>
          <div v-if="sceneEngine.rounds.value.length > 0" class="max-h-64 overflow-y-auto space-y-2 border border-gray-800 rounded-lg p-3">
            <div v-for="round in sceneEngine.rounds.value" :key="round.round_number" class="text-xs text-gray-300 border-b border-gray-800 pb-2 last:border-0">
              <span class="text-indigo-400 font-medium">{{ round.character }}</span>
              <span v-if="round.dialogue" class="ml-2 italic text-gray-400">"{{ round.dialogue }}"</span>
              <p v-if="round.narration" class="text-gray-500 mt-0.5">{{ round.narration }}</p>
            </div>
          </div>
          <p class="text-xs text-gray-500">{{ t('interactive.review') }}</p>
        </div>
      </div>
      <div class="flex justify-between">
        <button @click="interactive.prevStep()" class="px-5 py-2 text-gray-400 border border-gray-700 rounded-lg text-sm hover:text-gray-200 hover:border-gray-600 transition-colors">
          &larr; {{ t('interactive.back') }}
        </button>
        <button @click="interactive.nextStep()" class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors">
          {{ t('interactive.next') }} &rarr;
        </button>
      </div>
    </div>

    <!-- ===== STEP 5: Writing ===== -->
    <div v-if="interactive.currentStep.value === 5" class="space-y-4">
      <div class="bg-gray-900 rounded-lg border border-gray-800 p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-gray-100">{{ t('interactive.step_writing') }}</h2>
          <div class="flex items-center gap-2">
            <select v-model="outputFormat" class="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-indigo-500">
              <option value="novel">{{ t('writer.format_novel') }}</option>
              <option value="screenplay">{{ t('writer.format_screenplay') }}</option>
            </select>
            <button @click="handleWriteNarrative" :disabled="interactive.generating.value" class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors">
              {{ interactive.generating.value ? t('interactive.generating') : t('writer.convert') }}
            </button>
          </div>
        </div>
        <div v-if="interactive.generating.value" class="text-sm text-indigo-400 animate-pulse">
          {{ t('interactive.generating') }}
        </div>
        <div v-if="interactive.writtenOutput.value" class="space-y-3">
          <div class="bg-gray-800 rounded-lg p-4 max-h-96 overflow-y-auto">
            <pre class="whitespace-pre-wrap text-sm text-gray-200 font-sans">{{ interactive.writtenOutput.value }}</pre>
          </div>
          <div class="flex gap-2">
            <button @click="interactive.exportNarrative(outputFormat)" class="px-4 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded text-xs font-medium transition-colors">
              {{ t('writer.export') }}
            </button>
          </div>
          <p class="text-xs text-gray-500 italic">{{ t('interactive.edit_hint') }}</p>
        </div>
        <p v-else-if="!interactive.generating.value" class="text-sm text-gray-500">{{ t('writer.preview_hint') }}</p>
      </div>
      <div class="flex justify-between">
        <button @click="interactive.prevStep()" class="px-5 py-2 text-gray-400 border border-gray-700 rounded-lg text-sm hover:text-gray-200 hover:border-gray-600 transition-colors">
          &larr; {{ t('interactive.back') }}
        </button>
      </div>
    </div>

  </div>
</template>
