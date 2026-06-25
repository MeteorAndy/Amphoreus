<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Plus, Wand2, Trash2, X, CheckCircle, AlertCircle } from 'lucide-vue-next'
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
const consistencyOk = ref(true)
const checkingConsistency = ref(false)

const selectedStructure = ref('three_act')

const structures = computed(() => [
  { value: 'three_act', label: t('structure.three_act') },
  { value: 'hero_journey', label: t('structure.hero_journey') },
  { value: 'save_the_cat', label: t('structure.save_the_cat') },
  { value: 'qi_cheng_zhuan_he', label: t('structure.qi_cheng_zhuan_he') },
])

const sceneForm = ref<CreateSceneRequest>({
  title: '',
  description: '',
  setting: '',
  characters: [],
  act_id: '',
  order: 0,
})

const charInput = ref('')

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

function structureLabel(value: string): string {
  const key = `structure.${value}`
  const translated = t(key)
  return translated === key ? value : translated
}

async function saveOutline(): Promise<void> {
  const worldId = getWorldId()
  if (!worldId) {
    error.value = t('plot.no_world')
    return
  }
  const characterIds = getCharacterIds()
  if (characterIds.length === 0) {
    error.value = t('plot.no_chars')
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
      consistencyOk.value = result.consistent
      if (result.consistent) {
        consistencyResult.value = t('plot.consistent')
      } else {
        consistencyResult.value = t('plot.issues').replace('{issues}', result.issues.join(', '))
      }
    }
  } finally {
    checkingConsistency.value = false
  }
}

async function handleReorder(actId: string, sceneIds: string[]): Promise<void> {
  if (!selectedOutline.value) return
  const outline = selectedOutline.value

  const act = outline.acts.find((a) => a.id === actId)
  if (!act) return
  const previousScenes = [...act.scenes]

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
    <div class="page-header">
      <div>
        <h1>{{ t('plot.title') }}</h1>
      </div>
      <button @click="showCreateModal = true" class="btn btn-primary">
        <Plus :size="14" />
        {{ t('plot.new_outline') }}
      </button>
    </div>

    <div v-if="error" class="error-banner">
      <AlertCircle :size="14" class="flex-shrink-0 mt-0.5" />
      {{ error }}
    </div>

    <div
      v-if="consistencyResult"
      class="rounded-lg p-3 text-sm flex items-start gap-2 border"
      :class="consistencyOk
        ? 'bg-editor/10 border-editor/30 text-editor'
        : 'bg-danger-soft border-danger text-danger'"
    >
      <CheckCircle v-if="consistencyOk" :size="14" class="flex-shrink-0 mt-0.5" />
      <AlertCircle v-else :size="14" class="flex-shrink-0 mt-0.5" />
      {{ consistencyResult }}
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <div class="lg:col-span-1 space-y-3">
        <div class="card p-4">
          <h3 class="text-sm font-semibold text-parchment mb-3">{{ t('plot.outlines') }}</h3>
          <div v-if="outlines.length === 0 && !loading" class="text-center py-6 text-muted text-sm">
            {{ t('plot.empty') }}
          </div>
          <div class="space-y-1">
            <button
              v-for="outline in outlines"
              :key="outline.id"
              @click="selectOutline(outline.id)"
              class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors"
              :class="selectedOutline?.id === outline.id
                ? 'bg-chop-soft text-chop border border-chop-border'
                : 'text-parchment-dim hover:bg-ink-elevated border border-transparent'"
            >
              <div class="font-medium truncate">{{ outline.title }}</div>
              <div class="text-xs text-muted">{{ structureLabel(outline.structure) }}</div>
            </button>
          </div>
        </div>

        <div v-if="selectedOutline" class="card p-4 space-y-2">
          <h3 class="text-sm font-semibold text-parchment mb-2">{{ t('plot.actions') }}</h3>
          <button @click="openRefine" class="btn btn-secondary w-full">
            <Wand2 :size="13" />
            {{ t('plot.refine_outline') }}
          </button>
          <button @click="deleteOutline(selectedOutline.id)" class="btn btn-danger w-full">
            <Trash2 :size="13" />
            {{ t('plot.delete_outline') }}
          </button>
        </div>
      </div>

      <div class="lg:col-span-3">
        <div v-if="loading && !selectedOutline" class="flex items-center justify-center h-64 text-muted text-sm">
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

    <Teleport to="body">
      <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
        <div class="modal-panel">
          <h2 class="text-lg font-semibold text-parchment mb-4">{{ t('plot.new_outline_title') }}</h2>
          <div class="space-y-4">
            <div>
              <label class="field-label">{{ t('plot.structure') }}</label>
              <select v-model="selectedStructure" class="input">
                <option v-for="s in structures" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-6">
            <button @click="showCreateModal = false" class="btn btn-secondary btn-sm">
              {{ t('general.cancel') }}
            </button>
            <button @click="saveOutline" class="btn btn-primary btn-sm">
              <Wand2 :size="13" />
              {{ t('plot.generate') }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="showSceneModal" class="modal-overlay" @click.self="showSceneModal = false">
        <div class="modal-panel">
          <h2 class="text-lg font-semibold text-parchment mb-4">
            {{ editingScene ? t('plot.edit_scene') : t('plot.add_scene') }}
          </h2>
          <div class="space-y-4">
            <div>
              <label class="field-label">{{ t('plot.title_field') }}</label>
              <input v-model="sceneForm.title" type="text" class="input" />
            </div>
            <div>
              <label class="field-label">{{ t('plot.description') }}</label>
              <textarea v-model="sceneForm.description" rows="2" class="input" />
            </div>
            <div>
              <label class="field-label">{{ t('plot.setting') }}</label>
              <input v-model="sceneForm.setting" type="text" class="input" />
            </div>
            <div>
              <label class="field-label">{{ t('chars.name') }}</label>
              <div class="flex flex-wrap gap-1 mb-2">
                <span
                  v-for="(char, idx) in sceneForm.characters"
                  :key="idx"
                  class="inline-flex items-center gap-1 badge badge-muted"
                >
                  {{ char }}
                  <button @click="removeCharacter(idx)" class="hover:text-danger transition-colors">
                    <X :size="10" />
                  </button>
                </span>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="charInput"
                  type="text"
                  :placeholder="t('plot.char_name_placeholder')"
                  class="input flex-1"
                  @keydown.enter.prevent="addCharacter"
                />
                <button @click="addCharacter" class="btn btn-secondary btn-sm">
                  <Plus :size="12" />
                  {{ t('plot.add') }}
                </button>
              </div>
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-6">
            <button @click="showSceneModal = false" class="btn btn-secondary btn-sm">
              {{ t('general.cancel') }}
            </button>
            <button @click="saveScene" :disabled="!sceneForm.title" class="btn btn-primary btn-sm">
              {{ editingScene ? t('general.save') : t('general.create') }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="showRefineModal" class="modal-overlay" @click.self="showRefineModal = false">
        <div class="modal-panel">
          <h2 class="text-lg font-semibold text-parchment mb-2">{{ t('plot.refine_title') }}</h2>
          <p class="text-xs text-muted mb-4">{{ t('plot.refine_desc') }}</p>
          <textarea
            v-model="refineFeedback"
            rows="4"
            :placeholder="t('plot.refine_placeholder')"
            class="input"
          />
          <div class="flex justify-end gap-2 mt-4">
            <button @click="showRefineModal = false" class="btn btn-secondary btn-sm">
              {{ t('general.cancel') }}
            </button>
            <button
              @click="handleRefine"
              :disabled="refining || !refineFeedback.trim()"
              class="btn btn-primary btn-sm"
            >
              {{ refining ? t('general.loading') : t('general.confirm') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
