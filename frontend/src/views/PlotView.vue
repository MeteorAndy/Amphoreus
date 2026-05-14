<script setup lang="ts">
import { ref, onMounted } from 'vue'
import PlotTimeline from '../components/PlotTimeline.vue'
import { usePlotArchitect } from '../composables/usePlotArchitect'
import type { CreateOutlineRequest, CreateSceneRequest, SceneSpec } from '../types/api'

const {
  outlines,
  selectedOutline,
  loading,
  error,
  fetchOutlines,
  createOutline,
  selectOutline,
  removeOutline,
  createScene,
  updateSceneById,
  removeScene,
} = usePlotArchitect()

const showCreateModal = ref(false)
const showSceneModal = ref(false)
const editingScene = ref<SceneSpec | null>(null)

const outlineForm = ref<CreateOutlineRequest>({
  title: '',
  description: '',
  structure: 'three-act',
})

const sceneForm = ref<CreateSceneRequest>({
  title: '',
  description: '',
  setting: '',
  characters: [],
  act_id: '',
  order: 0,
})

const charInput = ref('')

const structures = ['three-act', 'five-act', 'hero-journey', 'save-the-cat', 'custom']

onMounted(() => {
  fetchOutlines()
})

function openCreateOutline(): void {
  outlineForm.value = { title: '', description: '', structure: 'three-act' }
  showCreateModal.value = true
}

async function saveOutline(): Promise<void> {
  await createOutline(outlineForm.value)
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
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-100">Plot Architect</h1>
      <button
        @click="openCreateOutline"
        class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 transition-colors"
      >
        + New Outline
      </button>
    </div>
    <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
      {{ error }}
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <div class="lg:col-span-1 space-y-3">
        <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h3 class="text-sm font-semibold text-gray-200 mb-3">Outlines</h3>
          <div v-if="outlines.length === 0 && !loading" class="text-center py-6 text-gray-600 text-sm">
            No outlines yet
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
        <div v-if="selectedOutline" class="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h3 class="text-sm font-semibold text-gray-200 mb-3">Actions</h3>
          <button
            @click="openCreateOutline"
            class="w-full mb-2 px-3 py-2 text-sm text-gray-400 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
          >
            New Outline
          </button>
          <button
            @click="deleteOutline(selectedOutline.id)"
            class="w-full px-3 py-2 text-sm text-red-400 bg-gray-800 rounded-lg hover:bg-red-900/20 transition-colors"
          >
            Delete Outline
          </button>
        </div>
      </div>
      <div class="lg:col-span-3">
        <div v-if="loading && !selectedOutline" class="flex items-center justify-center h-64 text-gray-500 text-sm">
          Loading...
        </div>
        <PlotTimeline
          :outline="selectedOutline"
          @select-scene="(s: SceneSpec) => { editingScene = s }"
          @add-scene="openAddScene"
          @edit-scene="openEditScene"
          @delete-scene="removeScene"
        />
      </div>
    </div>
    <Teleport to="body">
      <div
        v-if="showCreateModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showCreateModal = false"
      >
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md mx-4">
          <h2 class="text-lg font-semibold text-gray-100 mb-4">New Plot Outline</h2>
          <div class="space-y-4">
            <div>
              <label class="block text-xs text-gray-500 mb-1">Title</label>
              <input
                v-model="outlineForm.title"
                type="text"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Description</label>
              <textarea
                v-model="outlineForm.description"
                rows="3"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Structure</label>
              <select
                v-model="outlineForm.structure"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              >
                <option v-for="s in structures" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-6">
            <button @click="showCreateModal = false" class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200">Cancel</button>
            <button
              @click="saveOutline"
              :disabled="!outlineForm.title"
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </div>
      </div>
      <div
        v-if="showSceneModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showSceneModal = false"
      >
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md mx-4">
          <h2 class="text-lg font-semibold text-gray-100 mb-4">
            {{ editingScene ? 'Edit Scene' : 'Add Scene' }}
          </h2>
          <div class="space-y-4">
            <div>
              <label class="block text-xs text-gray-500 mb-1">Title</label>
              <input
                v-model="sceneForm.title"
                type="text"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Description</label>
              <textarea
                v-model="sceneForm.description"
                rows="2"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Setting</label>
              <input
                v-model="sceneForm.setting"
                type="text"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Characters</label>
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
            <button @click="showSceneModal = false" class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200">Cancel</button>
            <button
              @click="saveScene"
              :disabled="!sceneForm.title"
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
            >
              {{ editingScene ? 'Save' : 'Create' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
