<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { GitBranch, Users, UserPlus, Wand2, ChevronRight, X } from 'lucide-vue-next'
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
    error.value = t('chars.no_world')
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
  <div class="flex-1 min-h-0 overflow-y-auto space-y-6 fade-in-up pr-1">
    <div class="page-header">
      <div class="flex items-start gap-4">
        <div class="w-12 h-12 rounded-seal flex items-center justify-center flex-shrink-0 seal-glow" style="background: var(--gradient-chop-seal);">
          <Users :size="22" class="text-white" />
        </div>
        <div>
          <h1 class="font-display">{{ t('chars.title') }}</h1>
        </div>
      </div>
      <div class="flex gap-2">
        <button @click="openPathFinder" class="btn btn-secondary">
          <GitBranch :size="14" />
          {{ t('chars.find_path') }}
        </button>
        <button
          @click="handleGenerate"
          :disabled="generating || loading"
          class="btn btn-primary"
        >
          <Wand2 :size="14" />
          {{ generating ? t('general.loading') : t('chars.generate') }}
        </button>
      </div>
    </div>
    <div class="rule-ornament rule-ornament-diamond text-xs">
      <span class="font-display small-caps tracking-widest opacity-70">CHARACTERS</span>
    </div>

    <div v-if="error" class="error-banner">
      {{ error }}
    </div>

    <div v-if="loading && characters.length === 0" class="flex items-center justify-center h-32 text-muted text-sm">
      {{ t('chars.loading') }}
    </div>

    <div v-if="characters.length > 0" class="card p-4">
      <div class="flex items-center justify-between mb-3">
        <h2 class="flex items-center gap-2 text-sm font-semibold text-parchment">
          <Users :size="16" class="text-chop" />
          {{ t('chars.rel_builder') }}
        </h2>
        <div class="flex gap-1">
          <button @click="selectAllForRelationship" class="btn btn-ghost btn-sm">
            {{ t('chars.select_all') }}
          </button>
          <button @click="clearRelationshipSelection" class="btn btn-ghost btn-sm">
            {{ t('chars.clear') }}
          </button>
        </div>
      </div>
      <p class="text-xs text-muted mb-3">{{ t('chars.select_2plus') }}</p>
      <div class="flex flex-wrap gap-2 mb-3">
        <button
          v-for="char in characters"
          :key="char.id"
          @click="toggleForRelationship(char.id)"
          class="chip"
          :class="{ 'chip-active': selectedForRelationship.has(char.id) }"
        >
          {{ char.name }}
        </button>
      </div>
      <button
        @click="handleBuildRelationships"
        :disabled="!canBuildRelationships || buildingRelationships"
        class="btn btn-primary"
      >
        <UserPlus :size="14" />
        {{ buildingRelationships ? t('chars.building') : t('chars.build_rels', { n: selectedForRelationship.size }) }}
      </button>
    </div>

    <div v-if="selectedCharacter" class="card p-4">
      <div class="flex items-center gap-3">
        <h3 class="text-sm font-semibold text-parchment">{{ t('chars.selected') }} {{ selectedCharacter.name }}</h3>
        <button @click="openRefine" class="btn btn-secondary btn-sm">
          <Wand2 :size="12" />
          {{ t('chars.refine') }}
        </button>
        <button @click="() => { selectCharacter(null); }" class="btn btn-ghost btn-sm ml-auto">
          <X :size="12" />
          {{ t('chars.deselect') }}
        </button>
      </div>
    </div>

    <div>
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-lg font-semibold text-parchment">{{ t('chars.relationships') }}</h2>
        <div class="flex gap-1">
          <button
            @click="viewMode = 'list'"
            class="chip"
            :class="{ 'chip-active': viewMode === 'list' }"
          >
            {{ t('chars.view_list') }}
          </button>
          <button
            @click="switchToGraph"
            class="chip"
            :class="{ 'chip-active': viewMode === 'graph' }"
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
            :relationships="allRelationships.filter(r => r.from_id === char.id || r.to_id === char.id || r.source_id === char.id || r.target_id === char.id)"
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
      <button @click="goToPlot" class="btn btn-primary">
        {{ t('chars.proceed_plot') }}
        <ChevronRight :size="14" />
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
