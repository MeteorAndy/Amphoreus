<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import CharacterCard from '../components/CharacterCard.vue'
import RelationshipGraph from '../components/RelationshipGraph.vue'
import CharacterEditModal from '../components/CharacterEditModal.vue'
import CharacterRefineModal from '../components/CharacterRefineModal.vue'
import RelationshipPathPanel from '../components/RelationshipPathPanel.vue'
import { useCharacters } from '../composables/useCharacters'
import { useProjectStore } from '../composables/useProjectStore'
import { useI18n } from '../i18n'
import { listRelationships, getRelationshipPath } from '../api/client'
import type { CharacterProfile, Relationship, PathStep } from '../types/api'

const { t } = useI18n()
const router = useRouter()
const projectStore = useProjectStore()

const {
  characters,
  loading,
  error,
  selectedCharacter,
  buildingRelationships,
  fetchCharacters,
  generateCharacters,
  updateCharacter,
  removeCharacter,
  refineCharacter,
  fetchCharacterNetwork,
  generateRelationships,
  selectCharacter,
} = useCharacters()

type ViewMode = 'list' | 'graph'
const viewMode = ref<ViewMode>('list')

const allRelationships = ref<Relationship[]>([])
const relationshipsLoading = ref(false)
const selectedForRelationship = ref<Set<string>>(new Set())
const pathSource = ref<string>('')
const pathTarget = ref<string>('')
const pathResult = ref<PathStep[] | null>(null)
const pathLoading = ref(false)
const showPathPanel = ref(false)

const selectedForRelationshipList = computed(() => Array.from(selectedForRelationship.value))

const canBuildRelationships = computed(() => selectedForRelationship.value.size >= 2)

async function fetchAllRelationships(): Promise<void> {
  relationshipsLoading.value = true
  try {
    allRelationships.value = await listRelationships()
  } catch {
    allRelationships.value = projectStore.currentRelationships.value
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

onMounted(() => {
  if (projectStore.currentCharacters.value.length > 0) {
    characters.value = [...projectStore.currentCharacters.value]
  } else {
    fetchCharacters()
  }
  fetchAllRelationships()
  allRelationships.value = projectStore.currentRelationships.value
})

watch(
  () => projectStore.currentRelationships.value,
  (rels) => {
    if (rels.length > 0) {
      allRelationships.value = rels
    }
  },
)

function getWorldId(): string | null {
  return projectStore.currentWorldId.value || localStorage.getItem('amphoreus-world-id')
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
    await fetchAllRelationships()
  } finally {
    generating.value = false
  }
}

function openEdit(char: CharacterProfile): void {
  editingCharacter.value = char
  showEditModal.value = true
}

async function saveCharacter(data: Partial<CharacterProfile>): Promise<void> {
  if (!editingCharacter.value) return
  await updateCharacter(editingCharacter.value.id, data)
  showEditModal.value = false
}

async function deleteCharacterById(id: string): Promise<void> {
  await removeCharacter(id)
  selectedForRelationship.value.delete(id)
}

function handleSelect(char: CharacterProfile): void {
  selectCharacter(char)
  if (char) {
    fetchCharacterNetwork(char.id)
  }
}

function handleGraphSelect(characterId: string): void {
  const char = characters.value.find((c) => c.id === characterId)
  if (char) selectCharacter(char)
}

function openRefine(): void {
  showRefineModal.value = true
}

async function handleRefine(feedback: string): Promise<void> {
  if (!selectedCharacter.value || !feedback.trim()) return
  refining.value = true
  try {
    await refineCharacter(selectedCharacter.value.id, feedback)
    showRefineModal.value = false
  } finally {
    refining.value = false
  }
}

function toggleForRelationship(charId: string): void {
  if (selectedForRelationship.value.has(charId)) {
    selectedForRelationship.value.delete(charId)
  } else {
    selectedForRelationship.value.add(charId)
  }
}

function selectAllForRelationship(): void {
  characters.value.forEach((c) => selectedForRelationship.value.add(c.id))
}

function clearRelationshipSelection(): void {
  selectedForRelationship.value.clear()
}

async function handleBuildRelationships(): Promise<void> {
  if (!canBuildRelationships.value) return
  const rels = await generateRelationships(selectedForRelationshipList.value)
  if (rels.length > 0) {
    allRelationships.value = rels
  } else {
    await fetchAllRelationships()
  }
}

function openPathFinder(): void {
  pathSource.value = selectedCharacter?.value?.id || ''
  pathTarget.value = ''
  pathResult.value = null
  showPathPanel.value = true
}

async function findPath(): Promise<void> {
  if (!pathSource.value || !pathTarget.value) return
  pathLoading.value = true
  try {
    pathResult.value = await getRelationshipPath(pathSource.value, pathTarget.value)
  } catch {
    pathResult.value = []
  } finally {
    pathLoading.value = false
  }
}

function goToPlot(): void {
  router.push('/plot')
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-parchment">{{ t('chars.title') }}</h1>
      <div class="flex gap-2">
        <button
          @click="openPathFinder"
          class="px-4 py-2 bg-ink-elevated text-parchment rounded-lg text-sm font-medium hover:bg-ink-elevated border border-ink-edge transition-colors"
        >
          Find Path
        </button>
        <button
          @click="handleGenerate"
          :disabled="generating || loading"
          class="px-4 py-2 bg-chop text-white rounded-lg text-sm font-medium hover:bg-chop disabled:opacity-50 transition-colors"
        >
          {{ generating ? t('general.loading') : t('chars.generate') }}
        </button>
      </div>
    </div>

    <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
      {{ error }}
    </div>

    <div v-if="loading && characters.length === 0" class="flex items-center justify-center h-32 text-muted text-sm">
      {{ t('chars.loading') }}
    </div>

    <div v-if="characters.length > 0" class="bg-ink-panel rounded-lg border border-ink-edge p-4">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-parchment">Relationship Builder</h2>
        <div class="flex gap-2">
          <button
            @click="selectAllForRelationship"
            class="text-xs text-muted hover:text-parchment-dim transition-colors"
          >
            Select All
          </button>
          <button
            @click="clearRelationshipSelection"
            class="text-xs text-muted hover:text-parchment-dim transition-colors"
          >
            Clear
          </button>
        </div>
      </div>
      <p class="text-xs text-muted mb-3">Select 2+ characters to generate relationships between them.</p>
      <div class="flex flex-wrap gap-2 mb-3">
        <button
          v-for="char in characters"
          :key="char.id"
          @click="toggleForRelationship(char.id)"
          class="px-3 py-1.5 rounded-lg text-sm transition-colors border"
          :class="selectedForRelationship.has(char.id)
            ? 'bg-chop/20 border-chop text-chop'
            : 'bg-ink-elevated border-ink-edge text-parchment-dim hover:border-chop/50'"
        >
          {{ char.name }}
        </button>
      </div>
      <button
        @click="handleBuildRelationships"
        :disabled="!canBuildRelationships || buildingRelationships"
        class="px-4 py-2 bg-purple-700 text-white rounded-lg text-sm font-medium hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {{ buildingRelationships ? 'Building...' : `Build Relationships (${selectedForRelationship.size} selected)` }}
      </button>
    </div>

    <div v-if="selectedCharacter" class="bg-ink-panel rounded-lg border border-ink-edge p-4">
      <div class="flex items-center gap-3">
        <h3 class="text-sm font-semibold text-parchment">Selected: {{ selectedCharacter.name }}</h3>
        <button
          @click="openRefine"
          class="px-3 py-1.5 bg-chop/20 text-chop border border-oxblood rounded-lg text-xs font-medium hover:bg-chop/30 transition-colors"
        >
          Refine
        </button>
        <button
          @click="() => { selectCharacter(null); }"
          class="ml-auto text-xs text-muted hover:text-parchment-dim"
        >
          Deselect
        </button>
      </div>
    </div>

    <div>
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-lg font-semibold text-parchment">{{ t('chars.relationships') }}</h2>
        <div class="flex rounded-lg overflow-hidden border border-ink-edge text-xs font-medium">
          <button
            @click="viewMode = 'list'"
            :class="viewMode === 'list'
              ? 'bg-chop text-white'
              : 'bg-ink-elevated text-parchment-dim hover:text-parchment hover:bg-ink-elevated'"
            class="px-3 py-1.5 transition-colors"
          >
            {{ t('chars.view_list') }}
          </button>
          <button
            @click="switchToGraph"
            :class="viewMode === 'graph'
              ? 'bg-chop text-white'
              : 'bg-ink-elevated text-parchment-dim hover:text-parchment hover:bg-ink-elevated'"
            class="px-3 py-1.5 transition-colors"
          >
            {{ t('chars.view_graph') }}
          </button>
        </div>
      </div>

      <template v-if="viewMode === 'list'">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <CharacterCard
            v-for="char in characters"
            :key="char.id"
            :character="char"
            :selected="selectedCharacter?.id === char.id"
            :relationships="allRelationships.filter(r => r.source_id === char.id || r.target_id === char.id)"
            :all-characters="characters"
            @select="handleSelect"
            @edit="openEdit"
            @delete="deleteCharacterById"
          />
        </div>
        <div v-if="characters.length === 0 && !loading" class="text-center py-12 text-muted text-sm">
          {{ t('chars.empty') }}
        </div>
      </template>

      <template v-else>
        <div v-if="relationshipsLoading" class="flex items-center justify-center h-32 text-muted text-sm">
          {{ t('general.loading') }}
        </div>
        <RelationshipGraph
          v-else
          :characters="characters"
          :relationships="allRelationships"
          :selected-character-id="selectedCharacter?.id"
          @select-character="handleGraphSelect"
        />
      </template>
    </div>

    <div v-if="characters.length > 0" class="flex justify-center pt-4">
      <button
        @click="goToPlot"
        class="px-6 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-500 transition-colors"
      >
        Proceed to Plot
      </button>
    </div>

    <CharacterEditModal
      v-if="showEditModal && editingCharacter"
      :character="editingCharacter"
      @save="saveCharacter"
      @close="showEditModal = false"
    />

    <CharacterRefineModal
      v-if="showRefineModal"
      :character-name="selectedCharacter?.name ?? ''"
      :refining="refining"
      @refine="handleRefine"
      @close="showRefineModal = false"
    />

    <RelationshipPathPanel
      v-if="showPathPanel"
      :characters="characters"
      :path-source="pathSource"
      :path-target="pathTarget"
      :path-result="pathResult"
      :loading="pathLoading"
      @update:path-source="pathSource = $event"
      @update:path-target="pathTarget = $event"
      @find-path="findPath"
      @close="showPathPanel = false"
    />
  </div>
</template>
