<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import WritingPreview from '../components/WritingPreview.vue'
import { useNarrativeWriter } from '../composables/useNarrativeWriter'
import { usePlotArchitect } from '../composables/usePlotArchitect'
import { useCharacters } from '../composables/useCharacters'
import { useProjectStore } from '../composables/useProjectStore'
import { useI18n } from '../i18n'
import type { NarrativeFormat, SceneSpec, CharacterProfile } from '../types/api'

const { t } = useI18n()
const projectStore = useProjectStore()

const {
  output,
  titleCandidates,
  loading,
  error,
  format,
  narrativeVoice,
  enhanceEnabled,
  generate,
  fetchTitles,
  exportOutput,
  setFormat,
  setVoice,
  toggleEnhance,
} = useNarrativeWriter()

const { fetchTemplates, outlines, selectOutline, selectedOutline, initFromProject: initPlot } = usePlotArchitect()
const { fetchCharacters, characters } = useCharacters()

const selectedPlotId = ref('')
const selectedSceneIds = ref<Set<string>>(new Set())
const selectedCharacterIds = ref<Set<string>>(new Set())
const chapterTitle = ref('')
const povCharacterId = ref<string>('')

const narrativeVoices = [
  { value: 'first_person', label: 'First Person', desc: 'I/me perspective' },
  { value: 'third_person_limited', label: 'Third Person Limited', desc: 'Following one character' },
  { value: 'third_person_omniscient', label: 'Third Person Omniscient', desc: 'All-knowing narrator' },
]

const allScenes = computed<SceneSpec[]>(() => {
  if (!selectedOutline.value) return []
  const scenes: SceneSpec[] = []
  for (const act of selectedOutline.value.acts) {
    for (const scene of act.scenes) {
      scenes.push(scene)
    }
  }
  return scenes
})

const selectedCharacterObjects = computed<CharacterProfile[]>(() => {
  return characters.value.filter((c) => selectedCharacterIds.value.has(c.id))
})

onMounted(() => {
  initPlot()
  fetchTemplates()
  if (projectStore.currentCharacters.value.length > 0) {
    characters.value = [...projectStore.currentCharacters.value]
    characters.value.forEach((c) => selectedCharacterIds.value.add(c.id))
  } else {
    fetchCharacters()
  }
  if (projectStore.currentPlotId.value) {
    selectedPlotId.value = projectStore.currentPlotId.value
    if (projectStore.currentPlotOutline.value) {
      selectOutline(selectedPlotId.value)
    }
  }
})

watch(selectedPlotId, async (newId) => {
  if (newId) {
    fetchTitles(newId)
    await selectOutline(newId)
    selectedSceneIds.value.clear()
  }
})

watch(allScenes, (scenes) => {
  if (scenes.length > 0 && selectedSceneIds.value.size === 0) {
    scenes.forEach((s) => selectedSceneIds.value.add(s.id))
  }
})

watch(characters, (chars) => {
  if (chars.length > 0 && selectedCharacterIds.value.size === 0) {
    chars.forEach((c) => selectedCharacterIds.value.add(c.id))
  }
})

function toggleScene(sceneId: string): void {
  if (selectedSceneIds.value.has(sceneId)) {
    selectedSceneIds.value.delete(sceneId)
  } else {
    selectedSceneIds.value.add(sceneId)
  }
}

function selectAllScenes(): void {
  allScenes.value.forEach((s) => selectedSceneIds.value.add(s.id))
}

function clearSceneSelection(): void {
  selectedSceneIds.value.clear()
}

function toggleCharacter(charId: string): void {
  if (selectedCharacterIds.value.has(charId)) {
    selectedCharacterIds.value.delete(charId)
  } else {
    selectedCharacterIds.value.add(charId)
  }
}

function handleGenerate(): void {
  if (!selectedPlotId.value || selectedSceneIds.value.size === 0 || selectedCharacterIds.value.size === 0) return
  const sceneIds = Array.from(selectedSceneIds.value)
  const characterIds = Array.from(selectedCharacterIds.value)
  generate(
    sceneIds,
    characterIds,
    format.value,
    narrativeVoice.value,
    chapterTitle.value || undefined,
    povCharacterId.value || undefined,
  )
}

function handleToggleFormat(fmt: NarrativeFormat): void {
  setFormat(fmt)
  if (output.value && selectedSceneIds.value.size > 0) {
    const sceneIds = Array.from(selectedSceneIds.value)
    const characterIds = Array.from(selectedCharacterIds.value)
    generate(sceneIds, characterIds, fmt, narrativeVoice.value, chapterTitle.value || undefined, povCharacterId.value || undefined)
  }
}

function handleExport(): void {
  exportOutput(format.value)
}

function handleSelectTitle(title: string): void {
  if (output.value) {
    output.value.title = title
    chapterTitle.value = title
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-parchment">{{ t('writer.title') }}</h1>
    </div>

    <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
      {{ error }}
    </div>

    <div class="bg-ink-panel rounded-lg border border-ink-edge p-4 space-y-4">
      <div class="flex items-end gap-4">
        <div class="flex-1">
          <label class="block text-xs text-muted mb-1">{{ t('writer.plot_outline') }}</label>
          <select
            v-model="selectedPlotId"
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
        <div class="flex-1">
          <label class="block text-xs text-muted mb-1">Chapter Title (optional)</label>
          <input
            v-model="chapterTitle"
            type="text"
            placeholder="Enter chapter title..."
            class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment placeholder-muted focus:outline-none focus:border-chop"
          />
        </div>
        <button
          @click="handleGenerate"
          :disabled="!selectedPlotId || selectedSceneIds.size === 0 || selectedCharacterIds.size === 0 || loading"
          class="px-6 py-2 bg-chop text-white rounded-lg text-sm font-medium hover:bg-chop disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ loading ? t('writer.generating') : t('writer.convert') }}
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-xs text-muted mb-2">Narrative Voice</label>
          <div class="space-y-1">
            <button
              v-for="voice in narrativeVoices"
              :key="voice.value"
              @click="setVoice(voice.value as typeof narrativeVoice)"
              class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors border"
              :class="narrativeVoice === voice.value
                ? 'bg-chop/20 border-chop text-chop'
                : 'bg-ink-elevated border-ink-edge text-parchment-dim hover:border-chop/50'"
            >
              <div class="font-medium">{{ voice.label }}</div>
              <div class="text-xs text-muted mt-0.5">{{ voice.desc }}</div>
            </button>
          </div>
        </div>

        <div>
          <label class="block text-xs text-muted mb-2">POV Character (optional)</label>
          <select
            v-model="povCharacterId"
            class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
          >
            <option value="">All characters</option>
            <option
              v-for="char in selectedCharacterObjects"
              :key="char.id"
              :value="char.id"
            >
              {{ char.name }}
            </option>
          </select>

          <div class="mt-3">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                :checked="enhanceEnabled"
                @change="toggleEnhance(($event.target as HTMLInputElement).checked)"
                class="w-4 h-4 rounded border-ink-edge bg-ink-elevated text-chop focus:ring-chop"
              />
              <span class="text-sm text-parchment-dim">
                Enhance prose quality
              </span>
            </label>
            <p class="text-xs text-muted mt-1">
                Applies stylistic improvements and descriptive detail
            </p>
          </div>
        </div>

        <div>
          <label class="block text-xs text-muted mb-2">Output Format</label>
          <div class="flex gap-2">
            <button
              @click="setFormat('novel')"
              class="flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors border"
              :class="format === 'novel'
                ? 'bg-chop/20 border-chop text-chop'
                : 'bg-ink-elevated border-ink-edge text-parchment-dim hover:border-chop/50'"
            >
              Novel
            </button>
            <button
              @click="setFormat('screenplay')"
              class="flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors border"
              :class="format === 'screenplay'
                ? 'bg-chop/20 border-chop text-chop'
                : 'bg-ink-elevated border-ink-edge text-parchment-dim hover:border-chop/50'"
            >
              Screenplay
            </button>
          </div>
        </div>
      </div>

      <div v-if="allScenes.length > 0">
        <div class="flex items-center justify-between mb-2">
          <label class="text-xs text-muted">Scenes ({{ selectedSceneIds.size }}/{{ allScenes.length }} selected)</label>
          <div class="flex gap-2">
            <button
              @click="selectAllScenes"
              class="text-xs text-chop hover:text-chop transition-colors"
            >
              Select All
            </button>
            <button
              @click="clearSceneSelection"
              class="text-xs text-muted hover:text-parchment-dim transition-colors"
            >
              Clear
            </button>
          </div>
        </div>
        <div class="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
          <button
            v-for="scene in allScenes"
            :key="scene.id"
            @click="toggleScene(scene.id)"
            class="px-3 py-1.5 rounded-lg text-sm transition-colors border"
            :class="selectedSceneIds.has(scene.id)
              ? 'bg-blue-900/20 border-blue-700 text-blue-400'
              : 'bg-ink-elevated border-ink-edge text-parchment-dim hover:border-blue-700/50'"
          >
            {{ scene.order }}. {{ scene.title }}
          </button>
        </div>
      </div>

      <div v-if="characters.length > 0">
        <div class="flex items-center justify-between mb-2">
          <label class="text-xs text-muted">Characters ({{ selectedCharacterIds.size }}/{{ characters.length }} selected)</label>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="char in characters"
            :key="char.id"
            @click="toggleCharacter(char.id)"
            class="px-3 py-1.5 rounded-lg text-sm transition-colors border"
            :class="selectedCharacterIds.has(char.id)
              ? 'bg-purple-900/20 border-purple-700 text-purple-400'
              : 'bg-ink-elevated border-ink-edge text-parchment-dim hover:border-purple-700/50'"
          >
            {{ char.name }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="titleCandidates.length > 0" class="bg-ink-panel rounded-lg border border-ink-edge p-4">
      <h3 class="text-sm font-semibold text-parchment mb-3">{{ t('writer.title_candidates') }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        <button
          v-for="candidate in titleCandidates"
          :key="candidate.title"
          @click="handleSelectTitle(candidate.title)"
          class="text-left bg-ink-elevated rounded-lg p-3 hover:border-chop border border-ink-edge transition-colors"
          :class="output?.title === candidate.title ? 'border-chop' : ''"
        >
          <p class="text-sm font-medium text-parchment">{{ candidate.title }}</p>
          <p v-if="candidate.subtitle" class="text-xs text-muted mt-0.5">{{ candidate.subtitle }}</p>
          <p v-if="candidate.description" class="text-xs text-muted mt-1 line-clamp-2">{{ candidate.description }}</p>
        </button>
      </div>
    </div>

    <WritingPreview
      :output="output"
      :format="format"
      :loading="loading"
      @toggle-format="handleToggleFormat"
      @export="handleExport"
      @select-title="handleSelectTitle"
    />
  </div>
</template>
