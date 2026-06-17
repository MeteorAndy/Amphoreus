<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import CharacterCard from '../components/CharacterCard.vue'
import RelationshipGraph from '../components/RelationshipGraph.vue'
import CharacterEditModal from '../components/CharacterEditModal.vue'
import CharacterRefineModal from '../components/CharacterRefineModal.vue'
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
  showEditModal.value = true
}

async function saveCharacter(data: Partial<CharacterProfile>): Promise<void> {
  if (!editingCharacter.value) return
  await updateCharacter(editingCharacter.value.id, data)
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
          @click="handleGenerate"
          :disabled="generating || loading"
          class="px-4 py-2 bg-chop text-white rounded-lg text-sm font-medium hover:bg-chop disabled:opacity-50 transition-colors"
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
    <div v-if="loading && characters.length === 0" class="flex items-center justify-center h-32 text-muted text-sm">
      {{ t('chars.loading') }}
    </div>

    <!-- Selected character actions -->
    <div v-if="selectedCharacter" class="bg-ink-panel rounded-lg border border-ink-edge p-4">
      <div class="flex items-center gap-3 mb-3">
        <button
          @click="openRefine"
          class="px-3 py-1.5 bg-chop/20 text-chop border border-oxblood rounded-lg text-xs font-medium hover:bg-chop/30 transition-colors"
        >
          Refine
        </button>
      </div>
    </div>

    <!-- Relationships section with List / Graph toggle -->
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
        <div v-if="characters.length === 0 && !loading" class="text-center py-12 text-muted text-sm">
          {{ t('chars.empty') }}
        </div>
      </template>

      <!-- Graph view: d3-force relationship graph -->
      <template v-else>
        <div v-if="relationshipsLoading" class="flex items-center justify-center h-32 text-muted text-sm">
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
    <CharacterEditModal
      v-if="showEditModal && editingCharacter"
      :character="editingCharacter"
      @save="saveCharacter"
      @close="showEditModal = false"
    />

    <!-- Refine Modal -->
    <CharacterRefineModal
      v-if="showRefineModal"
      :character-name="selectedCharacter?.name ?? ''"
      :refining="refining"
      @refine="handleRefine"
      @close="showRefineModal = false"
    />
  </div>
</template>