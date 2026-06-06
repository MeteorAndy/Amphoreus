<script setup lang="ts">
import { ref, onMounted } from 'vue'
import PlotTimeline from '../components/PlotTimeline.vue'
import { usePlotArchitect } from '../composables/usePlotArchitect'
import { useCharacters } from '../composables/useCharacters'
import { useI18n } from '../i18n'
import { useToast } from '../composables/useToast'
import type { CreateSceneRequest, SceneSpec } from '../types/api'

const { t } = useI18n()
const toast = useToast()

const {
  outlines,
  selectedOutline,
  loading,
  error,
  fetchOutlines,
  createOutline,
  selectOutline,
  removeOutline,
  updateOutline,
  refineOutline,
  checkConsistency,
  createScene,
  updateSceneById,
  removeScene,
} = usePlotArchitect()

const { fetchCharacters, characters } = useCharacters()

const showCreateModal = ref(false)
const showSceneModal = ref(false)
const showRefineModal = ref(false)
const editingScene = ref<SceneSpec | null>(null)
const refineFeedback = ref('')
const refining = ref(false)
const consistencyResult = ref<string | null>(null)
const checkingConsistency = ref(false)

const selectedStructure = ref('three_act')

const sceneForm = ref<CreateSceneRequest>({
  title: '',
  description: '',
  setting: '',
  characters: [],
  act_id: '',
  order: 0,
})

const charInput = ref('')

const structures = [
  { value: 'three_act', label: 'Three-Act Structure' },
  { value: 'hero_journey', label: "Hero's Journey" },
  { value: 'save_the_cat', label: 'Save the Cat' },
  { value: 'qi_cheng_zhuan_he', label: 'Qi Cheng Zhuan He' },
]

onMounted(() => {
  fetchOutlines()
  fetchCharacters()
})

function getWorldId(): string | null {
  return localStorage.getItem('amphoreus-world-id')
}

function getCharacterIds(): string[] {
  return characters.value.map((c) => c.id)
}

async function saveOutline(): Promise<void> {
  const worldId = getWorldId()
  if (!worldId) {
    error.value = 'No world found. Please build a world first.'
    return
  }
  const characterIds = getCharacterIds()
  if (characterIds.length === 0) {
    error.value = 'No characters found. Please generate characters first.'
    return
  }
  await createOutline(worldId, selectedStructure.value, characterIds)
  showCreateModal.value = false
}

async function deleteOutline(id: string): Promise<void> {
  await removeOutline(id)
}

function openAddScene(actId: string): void {
  sceneForm.value = {
    title: '',
    description: '',
    setting: '',
    characters: [],
    act_id: actId,
    order: (selectedOutline.value?.acts.find((a) => a.id === actId)?.scenes.length ?? 0) + 1,
  }
  editingScene.value = null
  showSceneModal.value = true
}

function openEditScene(scene: SceneSpec): void {
  sceneForm.value = {
    title: scene.title,
    description: scene.description,
    setting: scene.setting,
    characters: [...scene.characters],
    act_id: scene.act_id,
    order: scene.order,
  }
  editingScene.value = scene
  showSceneModal.value = true
}

async function saveScene(): Promise<void> {
  if (!selectedOutline.value) return
  if (editingScene.value) {
    await updateSceneById(editingScene.value.id, sceneForm.value)
  } else {
    await createScene(selectedOutline.value.id, sceneForm.value)
  }
  showSceneModal.value = false
}

function addCharacter(): void {
  const c = charInput.value.trim()
  if (c && !sceneForm.value.characters.includes(c)) {
    sceneForm.value.characters.push(c)
  }
  charInput.value = ''
}

function removeCharacter(idx: number): void {
  sceneForm.value.characters.splice(idx, 1)
}

function openRefine(): void {
  refineFeedback.value = ''
  showRefineModal.value = true
}

async function handleRefine(): Promise<void> {
  if (!selectedOutline.value || !refineFeedback.value.trim()) return
  refining.value = true
  try {
    await refineOutline(selectedOutline.value.id, refineFeedback.value)
    showRefineModal.value = false
  } finally {
    refining.value = false
  }
}

async function handleCheckConsistency(sceneId: string): Promise<void> {
  if (!selectedOutline.value) return
  checkingConsistency.value = true
  consistencyResult.value = null
  try {
    const result = await checkConsistency(selectedOutline.value.id, sceneId)
    if (result) {
      consistencyResult.value = result.consistent
        ? 'Scene is consistent with the plot.'
        : `Issues: ${result.issues.join(', ')}`
    }
  } finally {
    checkingConsistency.value = false
  }
}

async function handleReorder(actId: string, sceneIds: string[]): Promise<void> {
  if (!selectedOutline.value) return
  const outline = selectedOutline.value

  // Snapshot previous act scenes for rollback
  const act = outline.acts.find((a) => a.id === actId)
  if (!act) return
  const previousScenes = [...act.scenes]

  // Apply new order locally
  const reordered = sceneIds
    .map((id) => act.scenes.find((s) => s.id === id))
    .filter((s): s is NonNullable<typeof s> => s !== undefined)
    .map((s, i) => ({ ...s, order: i + 1 }))
  act.scenes = reordered

  try {
    await updateOutline(outline.id, { acts: outline.acts })
    if (!error.value) {
      toast.success(t('plot.reorder_saved'))
    } else {
      // Revert on error
      act.scenes = previousScenes
      toast.error(t('general.error'))
    }
  } catch {
    act.scenes = previousScenes
    toast.error(t('general.error'))
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-100">{{ t('plot.title') }}</h1>
      <button
        @click="showCreateModal = true"
        class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 transition-colors"
      >
        {{ t('plot.new_outline') }}
      </button>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
      {{ error }}
    </div>

    <!-- Consistency result -->
    <div
      v-if="consistencyResult"
      class="bg-blue-900/20 border border-blue-800 rounded-lg p-3 text-sm text-blue-400"
    >
      {{ consistencyResult }}
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Sidebar -->
      <div class="lg:col-span-1 space-y-3">
        <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h3 class="text-sm font-semibold text-gray-200 mb-3">{{ t('plot.outlines') }}</h3>
          <div v-if="outlines.length === 0 && !loading" class="text-center py-6 text-gray-600 text-sm">
            {{ t('plot.empty') }}
          </div>
          <div class="space-y-1">
            <button
              v-for="outline in outlines"
              :key="outline.id"
              @click="selectOutline(outline.id)"
              class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors"
              :class="selectedOutline?.id === outline.id ? 'bg-indigo-900/30 text-indigo-300' : 'text-gray-400 hover:bg-gray-800'"
            >
              <div class="font-medium truncate">{{ outline.title }}</div>
              <div class="text-xs text-gray-500">{{ outline.structure }}</div>
            </button>
          </div>
        </div>

        <div v-if="selectedOutline" class="bg-gray-900 rounded-lg border border-gray-800 p-4 space-y-2">
          <h3 class="text-sm font-semibold text-gray-200 mb-2">{{ t('plot.actions') }}</h3>
          <button
            @click="openRefine"
            class="w-full px-3 py-2 text-sm text-gray-400 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
          >
            Refine Outline
          </button>
          <button
            @click="deleteOutline(selectedOutline.id)"
            class="w-full px-3 py-2 text-sm text-red-400 bg-gray-800 rounded-lg hover:bg-red-900/20 transition-colors"
          >
            {{ t('plot.delete_outline') }}
          </button>
        </div>
      </div>

      <!-- Main content -->
      <div class="lg:col-span-3">
        <div v-if="loading && !selectedOutline" class="flex items-center justify-center h-64 text-gray-500 text-sm">
          {{ t('general.loading') }}
        </div>
        <PlotTimeline
          :outline="selectedOutline"
          @select-scene="(s: SceneSpec) => { editingScene = s; handleCheckConsistency(s.id) }"
          @add-scene="openAddScene"
          @edit-scene="openEditScene"
          @delete-scene="removeScene"
          @reorder="handleReorder"
        />
      </div>
    </div>

    <!-- Create Outline Modal -->
    <Teleport to="body">
      <div
        v-if="showCreateModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showCreateModal = false"
      >
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md mx-4">
          <h2 class="text-lg font-semibold text-gray-100 mb-4">{{ t('plot.new_outline_title') }}</h2>
          <div class="space-y-4">
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('plot.structure') }}</label>
              <select
                v-model="selectedStructure"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              >
                <option v-for="s in structures" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-6">
            <button @click="showCreateModal = false" class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200">
              {{ t('general.cancel') }}
            </button>
            <button
              @click="saveOutline"
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
            >
              {{ t('plot.generate') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Scene Modal -->
      <div
        v-if="showSceneModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showSceneModal = false"
      >
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md mx-4">
          <h2 class="text-lg font-semibold text-gray-100 mb-4">
            {{ editingScene ? t('plot.edit_scene') : t('plot.add_scene') }}
          </h2>
          <div class="space-y-4">
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('plot.title_field') }}</label>
              <input
                v-model="sceneForm.title"
                type="text"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('plot.description') }}</label>
              <textarea
                v-model="sceneForm.description"
                rows="2"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('plot.setting') }}</label>
              <input
                v-model="sceneForm.setting"
                type="text"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('chars.name') }}</label>
              <div class="flex flex-wrap gap-1 mb-2">
                <span
                  v-for="(char, idx) in sceneForm.characters"
                  :key="idx"
                  class="flex items-center gap-1 px-2 py-0.5 bg-gray-800 text-gray-300 text-xs rounded-full"
                >
                  {{ char }}
                  <button @click="removeCharacter(idx)" class="hover:text-red-400">&times;</button>
                </span>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="charInput"
                  type="text"
                  placeholder="Character name..."
                  class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                  @keydown.enter.prevent="addCharacter"
                />
                <button @click="addCharacter" class="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-xs hover:bg-gray-600">Add</button>
              </div>
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-6">
            <button @click="showSceneModal = false" class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200">{{ t('general.cancel') }}</button>
            <button
              @click="saveScene"
              :disabled="!sceneForm.title"
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
            >
              {{ editingScene ? t('general.save') : t('general.create') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Refine Modal -->
      <div
        v-if="showRefineModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showRefineModal = false"
      >
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md mx-4">
          <h2 class="text-lg font-semibold text-gray-100 mb-2">Refine Plot Outline</h2>
          <p class="text-xs text-gray-500 mb-4">
            Provide feedback on how to improve the plot outline.
          </p>
          <textarea
            v-model="refineFeedback"
            rows="4"
            placeholder="Describe what should change..."
            class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 resize-none"
          />
          <div class="flex justify-end gap-2 mt-4">
            <button
              @click="showRefineModal = false"
              class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              {{ t('general.cancel') }}
            </button>
            <button
              @click="handleRefine"
              :disabled="refining || !refineFeedback.trim()"
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {{ refining ? t('general.loading') : t('general.confirm') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
