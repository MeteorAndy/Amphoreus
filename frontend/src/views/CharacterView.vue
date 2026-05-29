<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import CharacterCard from '../components/CharacterCard.vue'
import RelationshipGraph from '../components/RelationshipGraph.vue'
import { useCharacters } from '../composables/useCharacters'
import { useI18n } from '../i18n'
import { listRelationships } from '../api/client'
import type { CharacterProfile, Relationship } from '../types/api'

const { t } = useI18n()
const router = useRouter()

const {
  characters,
  loading,
  error,
  selectedCharacter,
  fetchCharacters,
  generateCharacters,
  updateCharacter,
  removeCharacter,
  refineCharacter,
  selectCharacter,
} = useCharacters()

// ── View toggle: list vs graph ────────────────────────────────────────────────
type ViewMode = 'list' | 'graph'
const viewMode = ref<ViewMode>('list')

// ── All relationships (for graph view) ───────────────────────────────────────
const allRelationships = ref<Relationship[]>([])
const relationshipsLoading = ref(false)

async function fetchAllRelationships(): Promise<void> {
  relationshipsLoading.value = true
  try {
    allRelationships.value = await listRelationships()
  } catch {
    allRelationships.value = []
  } finally {
    relationshipsLoading.value = false
  }
}

function switchToGraph(): void {
  viewMode.value = 'graph'
  if (allRelationships.value.length === 0) fetchAllRelationships()
}

const showEditModal = ref(false)
const showRefineModal = ref(false)
const editingCharacter = ref<CharacterProfile | null>(null)
const generateCount = ref(5)
const generating = ref(false)
const refining = ref(false)
const refineFeedback = ref('')

// Form fields (partial character data for editing)
const formName = ref('')
const formRole = ref('')
const formAppearance = ref('')
const formCoreDesire = ref('')
const formDeepFear = ref('')
const formVoiceSample = ref('')
const formArcStage = ref('')
const formCoreTraits = ref<string[]>([])
const formSecrets = ref<string[]>([])
const formKnowledgeScope = ref<string[]>([])
const traitInput = ref('')
const secretInput = ref('')
const knowledgeInput = ref('')

onMounted(() => {
  fetchCharacters()
  fetchAllRelationships()
})

function getWorldId(): string | null {
  return localStorage.getItem('amphoreus-world-id')
}

async function handleGenerate(): Promise<void> {
  const worldId = getWorldId()
  if (!worldId) {
    error.value = 'No world found. Please build a world first.'
    return
  }
  generating.value = true
  error.value = null
  try {
    await generateCharacters(worldId, generateCount.value)
  } finally {
    generating.value = false
  }
}

function openEdit(char: CharacterProfile): void {
  editingCharacter.value = char
  formName.value = char.name
  formRole.value = char.role
  formAppearance.value = char.appearance
  formCoreDesire.value = char.core_desire
  formDeepFear.value = char.deep_fear
  formVoiceSample.value = char.voice_sample
  formArcStage.value = char.arc_stage
  formCoreTraits.value = [...(char.personality?.core_traits || [])]
  formSecrets.value = [...(char.secrets || [])]
  formKnowledgeScope.value = [...(char.knowledge_scope || [])]
  showEditModal.value = true
}

async function saveCharacter(): Promise<void> {
  if (!editingCharacter.value) return
  await updateCharacter(editingCharacter.value.id, {
    name: formName.value,
    role: formRole.value,
    appearance: formAppearance.value,
    core_desire: formCoreDesire.value,
    deep_fear: formDeepFear.value,
    voice_sample: formVoiceSample.value,
    arc_stage: formArcStage.value,
    personality: {
      ...editingCharacter.value.personality,
      core_traits: formCoreTraits.value,
    },
    secrets: formSecrets.value,
    knowledge_scope: formKnowledgeScope.value,
  })
  showEditModal.value = false
}

async function deleteCharacterById(id: string): Promise<void> {
  await removeCharacter(id)
}

function handleSelect(char: CharacterProfile): void {
  selectCharacter(char)
}

function handleGraphSelect(characterId: string): void {
  const char = characters.value.find((c) => c.id === characterId)
  if (char) selectCharacter(char)
}

function addTrait(): void {
  const t = traitInput.value.trim()
  if (t && !formCoreTraits.value.includes(t)) {
    formCoreTraits.value.push(t)
  }
  traitInput.value = ''
}

function removeTrait(idx: number): void {
  formCoreTraits.value.splice(idx, 1)
}

function addSecret(): void {
  const s = secretInput.value.trim()
  if (s && !formSecrets.value.includes(s)) {
    formSecrets.value.push(s)
  }
  secretInput.value = ''
}

function removeSecret(idx: number): void {
  formSecrets.value.splice(idx, 1)
}

function addKnowledge(): void {
  const k = knowledgeInput.value.trim()
  if (k && !formKnowledgeScope.value.includes(k)) {
    formKnowledgeScope.value.push(k)
  }
  knowledgeInput.value = ''
}

function removeKnowledge(idx: number): void {
  formKnowledgeScope.value.splice(idx, 1)
}

function openRefine(): void {
  refineFeedback.value = ''
  showRefineModal.value = true
}

async function handleRefine(): Promise<void> {
  if (!selectedCharacter.value || !refineFeedback.value.trim()) return
  refining.value = true
  try {
    await refineCharacter(selectedCharacter.value.id, refineFeedback.value)
    showRefineModal.value = false
  } finally {
    refining.value = false
  }
}

function goToPlot(): void {
  router.push('/plot')
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-100">{{ t('chars.title') }}</h1>
      <div class="flex gap-2">
        <button
          @click="handleGenerate"
          :disabled="generating || loading"
          class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 transition-colors"
        >
          {{ generating ? t('general.loading') : t('chars.generate') }}
        </button>
      </div>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
      {{ error }}
    </div>

    <!-- Loading -->
    <div v-if="loading && characters.length === 0" class="flex items-center justify-center h-32 text-gray-500 text-sm">
      {{ t('chars.loading') }}
    </div>

    <!-- Selected character actions -->
    <div v-if="selectedCharacter" class="bg-gray-900 rounded-lg border border-gray-800 p-4">
      <div class="flex items-center gap-3 mb-3">
        <button
          @click="openRefine"
          class="px-3 py-1.5 bg-indigo-600/20 text-indigo-300 border border-indigo-800 rounded-lg text-xs font-medium hover:bg-indigo-600/30 transition-colors"
        >
          Refine
        </button>
      </div>
    </div>

    <!-- Relationships section with List / Graph toggle -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-lg font-semibold text-gray-200">{{ t('chars.relationships') }}</h2>
        <div class="flex rounded-lg overflow-hidden border border-gray-700 text-xs font-medium">
          <button
            @click="viewMode = 'list'"
            :class="viewMode === 'list'
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700'"
            class="px-3 py-1.5 transition-colors"
          >
            {{ t('chars.view_list') }}
          </button>
          <button
            @click="switchToGraph"
            :class="viewMode === 'graph'
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700'"
            class="px-3 py-1.5 transition-colors"
          >
            {{ t('chars.view_graph') }}
          </button>
        </div>
      </div>

      <!-- List view: character grid -->
      <template v-if="viewMode === 'list'">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <CharacterCard
            v-for="char in characters"
            :key="char.id"
            :character="char"
            :selected="selectedCharacter?.id === char.id"
            @select="handleSelect"
            @edit="openEdit"
            @delete="deleteCharacterById"
          />
        </div>
        <div v-if="characters.length === 0 && !loading" class="text-center py-12 text-gray-600 text-sm">
          {{ t('chars.empty') }}
        </div>
      </template>

      <!-- Graph view: d3-force relationship graph -->
      <template v-else>
        <div v-if="relationshipsLoading" class="flex items-center justify-center h-32 text-gray-500 text-sm">
          {{ t('general.loading') }}
        </div>
        <RelationshipGraph
          v-else
          :characters="characters"
          :relationships="allRelationships"
          @select-character="handleGraphSelect"
        />
      </template>
    </div>

    <!-- Proceed to Plot -->
    <div v-if="characters.length > 0" class="flex justify-center pt-4">
      <button
        @click="goToPlot"
        class="px-6 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-500 transition-colors"
      >
        Proceed to Plot
      </button>
    </div>

    <!-- Edit Modal -->
    <Teleport to="body">
      <div
        v-if="showEditModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showEditModal = false"
      >
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto">
          <h2 class="text-lg font-semibold text-gray-100 mb-4">{{ t('chars.edit_title') }}</h2>
          <div class="space-y-4">
            <!-- Name -->
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('chars.name') }}</label>
              <input
                v-model="formName"
                type="text"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <!-- Role -->
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('chars.role') }}</label>
              <select
                v-model="formRole"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="protagonist">Protagonist</option>
                <option value="antagonist">Antagonist</option>
                <option value="supporting">Supporting</option>
                <option value="minor">Minor</option>
              </select>
            </div>

            <!-- Appearance -->
            <div>
              <label class="block text-xs text-gray-500 mb-1">Appearance</label>
              <textarea
                v-model="formAppearance"
                rows="2"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>

            <!-- Core Desire -->
            <div>
              <label class="block text-xs text-gray-500 mb-1">Core Desire</label>
              <input
                v-model="formCoreDesire"
                type="text"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <!-- Deep Fear -->
            <div>
              <label class="block text-xs text-gray-500 mb-1">Deep Fear</label>
              <input
                v-model="formDeepFear"
                type="text"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <!-- Voice Sample -->
            <div>
              <label class="block text-xs text-gray-500 mb-1">Voice Sample</label>
              <textarea
                v-model="formVoiceSample"
                rows="2"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>

            <!-- Arc Stage -->
            <div>
              <label class="block text-xs text-gray-500 mb-1">Arc Stage</label>
              <select
                v-model="formArcStage"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="introduction">Introduction</option>
                <option value="rising_action">Rising Action</option>
                <option value="climax">Climax</option>
                <option value="resolution">Resolution</option>
              </select>
            </div>

            <!-- Core Traits -->
            <div>
              <label class="block text-xs text-gray-500 mb-1">Core Traits</label>
              <div class="flex flex-wrap gap-1 mb-2">
                <span
                  v-for="(trait, idx) in formCoreTraits"
                  :key="idx"
                  class="flex items-center gap-1 px-2 py-0.5 bg-indigo-900/30 text-indigo-300 text-xs rounded-full"
                >
                  {{ trait }}
                  <button @click="removeTrait(idx)" class="hover:text-red-400">&times;</button>
                </span>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="traitInput"
                  type="text"
                  placeholder="Add trait..."
                  class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                  @keydown.enter.prevent="addTrait"
                />
                <button @click="addTrait" class="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-xs hover:bg-gray-600 transition-colors">Add</button>
              </div>
            </div>

            <!-- Secrets -->
            <div>
              <label class="block text-xs text-gray-500 mb-1">Secrets</label>
              <div class="flex flex-wrap gap-1 mb-2">
                <span
                  v-for="(secret, idx) in formSecrets"
                  :key="idx"
                  class="flex items-center gap-1 px-2 py-0.5 bg-gray-800 text-gray-300 text-xs rounded-full"
                >
                  {{ secret }}
                  <button @click="removeSecret(idx)" class="hover:text-red-400">&times;</button>
                </span>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="secretInput"
                  type="text"
                  placeholder="Add secret..."
                  class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                  @keydown.enter.prevent="addSecret"
                />
                <button @click="addSecret" class="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-xs hover:bg-gray-600 transition-colors">Add</button>
              </div>
            </div>

            <!-- Knowledge Scope -->
            <div>
              <label class="block text-xs text-gray-500 mb-1">Knowledge Scope</label>
              <div class="flex flex-wrap gap-1 mb-2">
                <span
                  v-for="(k, idx) in formKnowledgeScope"
                  :key="idx"
                  class="flex items-center gap-1 px-2 py-0.5 bg-gray-800 text-gray-300 text-xs rounded-full"
                >
                  {{ k }}
                  <button @click="removeKnowledge(idx)" class="hover:text-red-400">&times;</button>
                </span>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="knowledgeInput"
                  type="text"
                  placeholder="Add knowledge area..."
                  class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                  @keydown.enter.prevent="addKnowledge"
                />
                <button @click="addKnowledge" class="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-xs hover:bg-gray-600 transition-colors">Add</button>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2 mt-6">
            <button
              @click="showEditModal = false"
              class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              {{ t('general.cancel') }}
            </button>
            <button
              @click="saveCharacter"
              :disabled="!formName"
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {{ t('general.save') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Refine Modal -->
    <Teleport to="body">
      <div
        v-if="showRefineModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showRefineModal = false"
      >
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md mx-4">
          <h2 class="text-lg font-semibold text-gray-100 mb-2">Refine Character</h2>
          <p class="text-xs text-gray-500 mb-4">
            Provide feedback on how to improve "{{ selectedCharacter?.name }}"
          </p>
          <textarea
            v-model="refineFeedback"
            rows="4"
            placeholder="Describe what should change about this character..."
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
