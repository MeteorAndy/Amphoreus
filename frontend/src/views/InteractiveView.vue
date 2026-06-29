<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Check, ChevronRight, ChevronLeft, MessageSquare } from 'lucide-vue-next'
import { useI18n } from '../i18n'
import { useInteractive } from '../composables/useInteractive'
import { useWorldBuilder } from '../composables/useWorldBuilder'
import { useSceneEngine } from '../composables/useSceneEngine'
import { useAssistant } from '../composables/useAssistant'
import StepProgress from '../components/StepProgress.vue'
import ChatPanel from '../components/ChatPanel.vue'
import CharacterCard from '../components/CharacterCard.vue'
import type { CharacterProfile, SceneSpec } from '../types/api'

const { t } = useI18n()
const router = useRouter()

const interactive = useInteractive()
const worldBuilder = useWorldBuilder()
const sceneEngine = useSceneEngine()
const assistant = useAssistant()

let unregisterActions: Array<() => void> = []

const seedIdea = ref('')

const editingChar = ref<CharacterProfile | null>(null)

const plotStructure = ref('three_act')
const structures = computed(() => [
  { value: 'three_act', label: t('structure.three_act') },
  { value: 'hero_journey', label: t('structure.hero_journey') },
  { value: 'save_the_cat', label: t('structure.save_the_cat') },
  { value: 'qi_cheng_zhuan_he', label: t('structure.qi_cheng_zhuan_he') },
])

const currentSceneIdx = ref(0)
const allScenes = computed<SceneSpec[]>(() =>
  interactive.plotOutline.value?.acts.flatMap((a) => a.scenes) ?? [],
)

const outputFormat = ref<'novel' | 'screenplay'>('novel')

const stepLabels = computed(() => [
  t('interactive.step_world'),
  t('interactive.step_characters'),
  t('interactive.step_plot'),
  t('interactive.step_scenes'),
  t('interactive.step_writing'),
])

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

async function handleGeneratePlot(): Promise<void> {
  const worldId = interactive.worldState.value?.world_id
  if (!worldId) return
  await interactive.generatePlot(worldId, plotStructure.value)
}

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

async function handleWriteNarrative(): Promise<void> {
  await interactive.writeNarrative(outputFormat.value)
}

function updateAssistantActions(): void {
  unregisterActions.forEach((fn) => fn())
  unregisterActions = []

  const step = interactive.currentStep.value

  unregisterActions.push(
    assistant.registerPageSuggestion({
      text: '改用一键生成',
      action: () => router.push('/pipeline'),
    }),
  )

  if (step === 1) {
    if (!worldBuilder.finalized.value) {
      unregisterActions.push(
        assistant.registerPageAction({
          id: 'interactive-world-start',
          label: '开始构建世界',
          description: '从你的灵感种子开始对话构建世界观',
          primary: true,
          handler: () => {
            if (seedIdea.value.trim() || worldBuilder.sessionId.value) {
              handleWorldSend(seedIdea.value)
            } else {
              assistant.triggerEvent('focus-world-input')
            }
          },
        }),
      )
      if (worldBuilder.isDone.value) {
        unregisterActions.push(
          assistant.registerPageAction({
            id: 'interactive-world-finalize',
            label: '确认世界设定',
            description: '完成世界观构建进入下一步',
            primary: true,
            handler: handleFinalizeWorld,
          }),
        )
      }
    } else {
      unregisterActions.push(
        assistant.registerPageAction({
          id: 'interactive-next-characters',
          label: '进入角色生成',
          description: '基于世界设定生成角色',
          primary: true,
          handler: () => interactive.nextStep(),
        }),
      )
    }
  } else if (step === 2) {
    if (interactive.characters.value.length === 0) {
      unregisterActions.push(
        assistant.registerPageAction({
          id: 'interactive-gen-chars',
          label: '生成角色',
          description: '自动生成故事角色',
          primary: true,
          handler: handleGenerateCharacters,
        }),
      )
    } else {
      unregisterActions.push(
        assistant.registerPageAction({
          id: 'interactive-regen-chars',
          label: '重新生成角色',
          description: '重新生成角色档案',
          handler: handleGenerateCharacters,
        }),
        assistant.registerPageAction({
          id: 'interactive-next-plot',
          label: '进入剧情架构',
          description: '角色完成后开始搭建剧情',
          primary: true,
          handler: () => interactive.nextStep(),
        }),
      )
    }
    unregisterActions.push(
      assistant.registerPageAction({
        id: 'interactive-back-world',
        label: '返回世界构建',
        handler: () => interactive.prevStep(),
      }),
    )
  } else if (step === 3) {
    if (!interactive.plotOutline.value) {
      unregisterActions.push(
        assistant.registerPageAction({
          id: 'interactive-gen-plot',
          label: '生成剧情大纲',
          description: '基于世界和角色生成剧情结构',
          primary: true,
          handler: handleGeneratePlot,
        }),
      )
    } else {
      unregisterActions.push(
        assistant.registerPageAction({
          id: 'interactive-next-scenes',
          label: '进入场景演绎',
          description: '开始逐场景模拟角色对话',
          primary: true,
          handler: () => interactive.nextStep(),
        }),
      )
    }
    unregisterActions.push(
      assistant.registerPageAction({
        id: 'interactive-back-chars',
        label: '返回角色管理',
        handler: () => interactive.prevStep(),
      }),
    )
  } else if (step === 4) {
    unregisterActions.push(
      assistant.registerPageAction({
        id: 'interactive-run-scene',
        label: '演绎当前场景',
        description: 'AI模拟此场景的角色对话',
        primary: true,
        handler: runCurrentScene,
      }),
    )
    if (sceneEngine.status.value.status === 'completed') {
      unregisterActions.push(
        assistant.registerPageAction({
          id: 'interactive-next-scene',
          label: '下一场景',
          handler: nextScene,
        }),
      )
    }
    unregisterActions.push(
      assistant.registerPageAction({
        id: 'interactive-skip-scene',
        label: '跳过此场景',
        handler: skipScene,
      }),
      assistant.registerPageAction({
        id: 'interactive-next-writing',
        label: '直接进入写作',
        description: '跳过场景演绎直接生成正文',
        primary: true,
        handler: () => interactive.nextStep(),
      }),
      assistant.registerPageAction({
        id: 'interactive-back-plot',
        label: '返回剧情架构',
        handler: () => interactive.prevStep(),
      }),
    )
  } else if (step === 5) {
    if (!interactive.writtenOutput.value) {
      unregisterActions.push(
        assistant.registerPageAction({
          id: 'interactive-write',
          label: '生成叙事正文',
          description: '将剧情大纲转换成小说/剧本',
          primary: true,
          handler: handleWriteNarrative,
        }),
      )
    } else {
      unregisterActions.push(
        assistant.registerPageAction({
          id: 'interactive-export',
          label: '导出作品',
          description: '导出为Markdown或Fountain格式',
          primary: true,
          handler: () => interactive.exportNarrative(outputFormat.value),
        }),
        assistant.registerPageAction({
          id: 'interactive-goto-quality',
          label: '前往质量审稿',
          handler: () => router.push('/quality'),
        }),
      )
    }
    unregisterActions.push(
      assistant.registerPageAction({
        id: 'interactive-back-scenes',
        label: '返回场景演绎',
        handler: () => interactive.prevStep(),
      }),
    )
  }
}

onMounted(() => {
  updateAssistantActions()
  watch(
    () => [interactive.currentStep.value, worldBuilder.finalized.value, worldBuilder.isDone.value, interactive.characters.value.length, interactive.plotOutline.value?.id, sceneEngine.status.value.status, interactive.writtenOutput.value],
    updateAssistantActions,
  )
})

onUnmounted(() => {
  unregisterActions.forEach((fn) => fn())
  unregisterActions = []
})
</script>

<template>
  <div class="flex-1 min-h-0 overflow-y-auto space-y-6 max-w-4xl mx-auto fade-in-up pr-1">
    <div class="page-header">
      <div class="flex items-start gap-4">
        <div class="w-12 h-12 rounded-seal flex items-center justify-center flex-shrink-0 seal-glow-gold" style="background: var(--gradient-gold-seal);">
          <MessageSquare :size="22" class="text-white" />
        </div>
        <div>
          <h1 class="font-display">{{ t('interactive.title') }}</h1>
          <p class="text-sm text-muted italic mt-1">{{ t('interactive.subtitle') }}</p>
        </div>
      </div>
    </div>
    <div class="rule-ornament text-xs">
      <span class="font-display small-caps tracking-widest opacity-70">INTERACTIVE</span>
    </div>

    <StepProgress :steps="stepLabels" :current="interactive.currentStep.value" />

    <div v-if="interactive.error.value" class="error-banner">
      {{ interactive.error.value }}
    </div>

    <div v-if="interactive.currentStep.value === 1" class="space-y-4">
      <div class="card p-4">
        <h2 class="text-base font-semibold text-parchment mb-3">{{ t('interactive.step_world') }}</h2>

        <template v-if="!worldBuilder.finalized.value">
          <div v-if="!worldBuilder.sessionId.value" class="space-y-3">
            <form @submit.prevent="handleWorldSend(seedIdea)" class="flex gap-2">
              <input
                v-model="seedIdea"
                type="text"
                :placeholder="t('world.idea_placeholder')"
                class="input flex-1"
                :disabled="worldBuilder.loading.value"
              >
              <button
                type="submit"
                :disabled="worldBuilder.loading.value || !seedIdea.trim()"
                class="btn btn-primary"
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
              class="btn btn-primary btn-lg"
            >
              {{ worldBuilder.loading.value ? t('world.finalizing') : t('world.finalize') }}
            </button>
          </div>
        </template>

        <div v-if="worldBuilder.finalized.value && interactive.worldState.value" class="space-y-3">
          <div class="flex items-center gap-2">
            <Check :size="18" class="text-editor" />
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

      <div class="flex justify-end">
        <button
          @click="interactive.nextStep()"
          :disabled="!interactive.worldState.value"
          class="btn btn-primary"
        >
          {{ t('interactive.next') }}
          <ChevronRight :size="16" />
        </button>
      </div>
    </div>

    <div v-if="interactive.currentStep.value === 3" class="space-y-4">
      <div class="card p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-parchment">{{ t('interactive.step_plot') }}</h2>
          <div class="flex items-center gap-2">
            <select v-model="plotStructure" class="input py-1.5 text-xs w-auto">
              <option v-for="s in structures" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
            <button
              @click="handleGeneratePlot"
              :disabled="interactive.generating.value"
              class="btn btn-primary btn-sm"
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
        <button @click="interactive.prevStep()" class="btn btn-secondary">
          <ChevronLeft :size="16" />
          {{ t('interactive.back') }}
        </button>
        <button @click="interactive.nextStep()" :disabled="!interactive.plotOutline.value" class="btn btn-primary">
          {{ t('interactive.next') }}
          <ChevronRight :size="16" />
        </button>
      </div>
    </div>

    <div v-if="interactive.currentStep.value === 2" class="space-y-4">
      <div class="card p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-parchment">{{ t('interactive.step_characters') }}</h2>
          <button
            @click="handleGenerateCharacters"
            :disabled="interactive.generating.value"
            class="btn btn-primary btn-sm"
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
        <div v-if="editingChar" class="card p-4 bg-ink-elevated space-y-3">
          <h3 class="text-sm font-semibold text-parchment">{{ t('chars.edit_title') }}</h3>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="field-label">{{ t('chars.name') }}</label>
              <input v-model="editingChar.name" class="input" />
            </div>
            <div>
              <label class="field-label">{{ t('chars.role') }}</label>
              <input v-model="editingChar.role" class="input" />
            </div>
          </div>
          <div>
            <label class="field-label">{{ t('chars.background') }}</label>
            <textarea v-model="editingChar.appearance" rows="2" class="input" />
          </div>
          <div class="flex gap-2">
            <button @click="handleSaveChar" class="btn btn-primary btn-sm">{{ t('chars.save') }}</button>
            <button @click="editingChar = null" class="btn btn-secondary btn-sm">{{ t('general.cancel') }}</button>
          </div>
        </div>
        <p class="text-xs text-muted italic">{{ t('interactive.review') }}</p>
      </div>
      <div class="flex justify-between">
        <button @click="interactive.prevStep()" class="btn btn-secondary">
          <ChevronLeft :size="16" />
          {{ t('interactive.back') }}
        </button>
        <button @click="interactive.nextStep()" :disabled="interactive.characters.value.length === 0" class="btn btn-primary">
          {{ t('interactive.next') }}
          <ChevronRight :size="16" />
        </button>
      </div>
    </div>

    <div v-if="interactive.currentStep.value === 4" class="space-y-4">
      <div class="card p-4 space-y-4">
        <h2 class="text-base font-semibold text-parchment">{{ t('interactive.step_scenes') }}</h2>
        <div v-if="allScenes.length === 0" class="text-sm text-muted">{{ t('plot.empty') }}</div>
        <div v-else class="space-y-3">
          <div class="flex flex-wrap gap-2">
            <button
              v-for="(scene, idx) in allScenes"
              :key="scene.id"
              @click="currentSceneIdx = idx; sceneEngine.reset()"
              class="chip"
              :class="idx === currentSceneIdx ? 'chip-active' : ''"
            >
              {{ idx + 1 }}. {{ scene.title }}
            </button>
          </div>
          <div v-if="allScenes[currentSceneIdx]" class="card bg-ink-elevated p-3 space-y-2">
            <h3 class="text-sm font-semibold text-parchment">{{ allScenes[currentSceneIdx].title }}</h3>
            <p v-if="allScenes[currentSceneIdx].setting" class="text-xs text-parchment-dim">{{ allScenes[currentSceneIdx].setting }}</p>
            <p v-if="allScenes[currentSceneIdx].description" class="text-xs text-muted">{{ allScenes[currentSceneIdx].description }}</p>
          </div>
          <div class="flex gap-2">
            <button @click="runCurrentScene" :disabled="sceneEngine.status.value.status === 'running'" class="btn btn-primary btn-sm">
              {{ sceneEngine.status.value.status === 'running' ? t('interactive.generating') : t('scene.run') }}
            </button>
            <button v-if="sceneEngine.status.value.status === 'completed'" @click="nextScene" class="btn btn-primary btn-sm">
              {{ t('interactive.next') }}
            </button>
            <button @click="skipScene" :disabled="currentSceneIdx >= allScenes.length - 1" class="btn btn-secondary btn-sm">
              {{ t('interactive.skip') }}
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
        <button @click="interactive.prevStep()" class="btn btn-secondary">
          <ChevronLeft :size="16" />
          {{ t('interactive.back') }}
        </button>
        <button @click="interactive.nextStep()" class="btn btn-primary">
          {{ t('interactive.next') }}
          <ChevronRight :size="16" />
        </button>
      </div>
    </div>

    <div v-if="interactive.currentStep.value === 5" class="space-y-4">
      <div class="card p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-parchment">{{ t('interactive.step_writing') }}</h2>
          <div class="flex items-center gap-2">
            <select v-model="outputFormat" class="input py-1.5 text-xs w-auto">
              <option value="novel">{{ t('writer.format_novel') }}</option>
              <option value="screenplay">{{ t('writer.format_screenplay') }}</option>
            </select>
            <button @click="handleWriteNarrative" :disabled="interactive.generating.value" class="btn btn-primary btn-sm">
              {{ interactive.generating.value ? t('interactive.generating') : t('writer.convert') }}
            </button>
          </div>
        </div>
        <div v-if="interactive.generating.value" class="text-sm text-chop animate-pulse">
          {{ t('interactive.generating') }}
        </div>
        <div v-if="interactive.writtenOutput.value" class="space-y-3">
          <div class="card bg-ink-elevated p-4 max-h-96 overflow-y-auto">
            <pre class="whitespace-pre-wrap text-sm text-parchment font-sans">{{ interactive.writtenOutput.value }}</pre>
          </div>
          <div class="flex gap-2">
            <button @click="interactive.exportNarrative(outputFormat)" class="btn btn-secondary btn-sm">
              {{ t('writer.export') }}
            </button>
          </div>
          <p class="text-xs text-muted italic">{{ t('interactive.edit_hint') }}</p>
        </div>
        <p v-else-if="!interactive.generating.value" class="text-sm text-muted">{{ t('writer.preview_hint') }}</p>
      </div>
      <div class="flex justify-between">
        <button @click="interactive.prevStep()" class="btn btn-secondary">
          <ChevronLeft :size="16" />
          {{ t('interactive.back') }}
        </button>
      </div>
    </div>

  </div>
</template>
