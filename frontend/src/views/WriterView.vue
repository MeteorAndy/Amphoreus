<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Sparkles, ChevronRight } from 'lucide-vue-next'
import WritingPreview from '../components/WritingPreview.vue'
import { useNarrativeWriter } from '../composables/useNarrativeWriter'
import { usePlotArchitect } from '../composables/usePlotArchitect'
import { useCharacters } from '../composables/useCharacters'
import { useProjectStore } from '../composables/useProjectStore'
import { useI18n } from '../i18n'
import type { NarrativeFormat, SceneSpec, CharacterProfile } from '../types/api'

const { t } = useI18n()
const projectStore = useProjectStore()
const router = useRouter()

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

const narrativeVoices = computed(() => [
  { value: 'first_person', label: t('writer.voice_first'), desc: t('writer.voice_first_desc') },
  { value: 'third_person_limited', label: t('writer.voice_third_limited'), desc: t('writer.voice_third_limited_desc') },
  { value: 'third_person_omniscient', label: t('writer.voice_third_omni'), desc: t('writer.voice_third_omni_desc') },
])

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

onMounted(async () => {
  initPlot()
  await fetchTemplates()
  if (projectStore.currentCharacters.value.length > 0) {
    characters.value = [...projectStore.currentCharacters.value]
    characters.value.forEach((c) => selectedCharacterIds.value.add(c.id))
  } else {
    await fetchCharacters()
  }
  const plotId = projectStore.currentPlotId.value || localStorage.getItem('amphoreus-outline-id')
  if (plotId) {
    selectedPlotId.value = plotId
    await selectOutline(plotId)
  }
  characters.value.forEach((c) => selectedCharacterIds.value.add(c.id))
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

const hasOutput = computed(() => !!output.value && !!output.value.content)

function goToQuality(): void {
  router.push('/quality')
}
</script>

<template>
  <div class="space-y-6">
    <div class="page-header">
      <div>
        <h1>{{ t('writer.title') }}</h1>
      </div>
      <button v-if="hasOutput" @click="goToQuality" class="btn btn-primary">
        <ChevronRight :size="14" />
        {{ t('plot.proceed_quality') || '前往质量审稿' }}
      </button>
    </div>

    <div v-if="error" class="error-banner">
      {{ error }}
    </div>

    <div class="card p-4 space-y-4">
      <div class="flex items-end gap-4">
        <div class="flex-1">
          <label class="field-label">{{ t('writer.plot_outline') }}</label>
          <select
            v-model="selectedPlotId"
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
        <div class="flex-1">
          <label class="field-label">{{ t('writer.chapter_title') }}</label>
          <input
            v-model="chapterTitle"
            type="text"
            :placeholder="t('writer.chapter_placeholder')"
            class="input"
          />
        </div>
        <button
          @click="handleGenerate"
          :disabled="!selectedPlotId || selectedSceneIds.size === 0 || selectedCharacterIds.size === 0 || loading"
          class="btn btn-primary"
        >
          <Sparkles :size="14" />
          {{ loading ? t('writer.generating') : t('writer.convert') }}
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="field-label">{{ t('writer.narrative_voice') }}</label>
          <div class="space-y-1">
            <button
              v-for="voice in narrativeVoices"
              :key="voice.value"
              @click="setVoice(voice.value as typeof narrativeVoice)"
              class="w-full text-left px-3 py-2 rounded-folio text-sm transition-colors border"
              :class="narrativeVoice === voice.value
                ? 'bg-chop-soft border-chop text-chop'
                : 'bg-ink-elevated border-ink-edge text-parchment-dim hover:border-chop/50'"
            >
              <div class="font-medium">{{ voice.label }}</div>
              <div class="text-xs text-muted mt-0.5">{{ voice.desc }}</div>
            </button>
          </div>
        </div>

        <div>
          <label class="field-label">{{ t('writer.pov_char') }}</label>
          <select
            v-model="povCharacterId"
            class="input"
          >
            <option value="">{{ t('writer.pov_all') }}</option>
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
                {{ t('writer.enhance') }}
              </span>
            </label>
            <p class="text-xs text-muted mt-1">
              {{ t('writer.enhance_desc') }}
            </p>
          </div>
        </div>

        <div>
          <label class="field-label">{{ t('writer.format') }}</label>
          <div class="flex gap-2">
            <button
              @click="setFormat('novel')"
              class="chip flex-1 justify-center"
              :class="format === 'novel' ? 'chip-active' : ''"
            >
              {{ t('writer.novel') }}
            </button>
            <button
              @click="setFormat('screenplay')"
              class="chip flex-1 justify-center"
              :class="format === 'screenplay' ? 'chip-active' : ''"
            >
              {{ t('writer.screenplay') }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="allScenes.length > 0">
        <div class="flex items-center justify-between mb-2">
          <label class="field-label !mb-0 flex items-center gap-2">
            {{ t('writer.scenes') }}
            <span class="badge badge-accent normal-case tracking-normal">
              {{ t('writer.scenes_selected', { s: selectedSceneIds.size, t: allScenes.length }) }}
            </span>
          </label>
          <div class="flex gap-2">
            <button
              @click="selectAllScenes"
              class="btn btn-ghost btn-sm"
            >
              {{ t('writer.select_all') }}
            </button>
            <button
              @click="clearSceneSelection"
              class="btn btn-ghost btn-sm"
            >
              {{ t('chars.clear') }}
            </button>
          </div>
        </div>
        <div class="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
          <button
            v-for="scene in allScenes"
            :key="scene.id"
            @click="toggleScene(scene.id)"
            class="chip"
            :class="selectedSceneIds.has(scene.id) ? 'chip-active' : ''"
          >
            {{ scene.order }}. {{ scene.title }}
          </button>
        </div>
      </div>

      <div v-if="characters.length > 0">
        <div class="flex items-center justify-between mb-2">
          <label class="field-label !mb-0 flex items-center gap-2">
            {{ t('writer.characters') }}
            <span class="badge badge-accent normal-case tracking-normal">
              {{ t('writer.characters_selected', { s: selectedCharacterIds.size, t: characters.length }) }}
            </span>
          </label>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="char in characters"
            :key="char.id"
            @click="toggleCharacter(char.id)"
            class="chip"
            :class="selectedCharacterIds.has(char.id) ? 'chip-active' : ''"
          >
            {{ char.name }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="titleCandidates.length > 0" class="card p-4">
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
