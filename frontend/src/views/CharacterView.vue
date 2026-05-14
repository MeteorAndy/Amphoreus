<script setup lang="ts">
import { ref, onMounted } from 'vue'
import CharacterCard from '../components/CharacterCard.vue'
import RelationshipGraph from '../components/RelationshipGraph.vue'
import { useCharacters } from '../composables/useCharacters'
import { useI18n } from '../i18n'
import type { CharacterProfile, CreateCharacterRequest } from '../types/api'

const { t } = useI18n()

const {
  characters,
  relationships,
  loading,
  error,
  selectedCharacter,
  fetchCharacters,
  createCharacter,
  updateCharacter,
  removeCharacter,
  fetchRelationships,
  selectCharacter,
} = useCharacters()

const showCreateModal = ref(false)
const editingCharacter = ref<CharacterProfile | null>(null)

const form = ref<CreateCharacterRequest>({
  name: '',
  role: '',
  traits: [],
  background: '',
  goals: [],
})

const traitInput = ref('')
const goalInput = ref('')

onMounted(() => {
  fetchCharacters()
  fetchRelationships()
})

function openCreate(): void {
  form.value = { name: '', role: '', traits: [], background: '', goals: [] }
  editingCharacter.value = null
  showCreateModal.value = true
}

function openEdit(char: CharacterProfile): void {
  form.value = {
    name: char.name,
    age: char.age,
    role: char.role,
    traits: [...char.traits],
    background: char.background,
    goals: [...char.goals],
    appearance: char.appearance,
  }
  editingCharacter.value = char
  showCreateModal.value = true
}

function addTrait(): void {
  const t = traitInput.value.trim()
  if (t && !form.value.traits.includes(t)) {
    form.value.traits.push(t)
  }
  traitInput.value = ''
}

function removeTrait(idx: number): void {
  form.value.traits.splice(idx, 1)
}

function addGoal(): void {
  const g = goalInput.value.trim()
  if (g && !form.value.goals.includes(g)) {
    form.value.goals.push(g)
  }
  goalInput.value = ''
}

function removeGoal(idx: number): void {
  form.value.goals.splice(idx, 1)
}

async function saveCharacter(): Promise<void> {
  if (editingCharacter.value) {
    await updateCharacter(editingCharacter.value.id, form.value)
  } else {
    await createCharacter(form.value)
  }
  showCreateModal.value = false
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

</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-100">{{ t('chars.title') }}</h1>
      <button
        @click="openCreate"
        class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 transition-colors"
      >
        {{ t('chars.add') }}
      </button>
    </div>
    <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
      {{ error }}
    </div>
    <div v-if="loading && characters.length === 0" class="flex items-center justify-center h-32 text-gray-500 text-sm">
      {{ t('chars.loading') }}
    </div>
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
    <div>
      <h2 class="text-lg font-semibold text-gray-200 mb-3">{{ t('chars.relationships') }}</h2>
      <RelationshipGraph
        :characters="characters"
        :relationships="relationships"
        @select="handleGraphSelect"
      />
    </div>
    <Teleport to="body">
      <div
        v-if="showCreateModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showCreateModal = false"
      >
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto">
          <h2 class="text-lg font-semibold text-gray-100 mb-4">
            {{ editingCharacter ? t('chars.edit_title') : t('chars.create_title') }}
          </h2>
          <div class="space-y-4">
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('chars.name') }}</label>
              <input
                v-model="form.name"
                type="text"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs text-gray-500 mb-1">{{ t('chars.role') }}</label>
                <input
                  v-model="form.role"
                  type="text"
                  class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">{{ t('chars.age') }}</label>
                <input
                  v-model="form.age"
                  type="number"
                  class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('chars.background') }}</label>
              <textarea
                v-model="form.background"
                rows="3"
                class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('chars.traits') }}</label>
              <div class="flex flex-wrap gap-1 mb-2">
                <span
                  v-for="(trait, idx) in form.traits"
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
                  :placeholder="t('chars.trait_placeholder')"
                  class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                  @keydown.enter.prevent="addTrait"
                />
                <button @click="addTrait" class="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-xs hover:bg-gray-600 transition-colors">{{ t('chars.add_trait') }}</button>
              </div>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">{{ t('chars.goals') }}</label>
              <div class="flex flex-wrap gap-1 mb-2">
                <span
                  v-for="(goal, idx) in form.goals"
                  :key="idx"
                  class="flex items-center gap-1 px-2 py-0.5 bg-gray-800 text-gray-300 text-xs rounded-full"
                >
                  {{ goal }}
                  <button @click="removeGoal(idx)" class="hover:text-red-400">&times;</button>
                </span>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="goalInput"
                  type="text"
                  :placeholder="t('chars.goal_placeholder')"
                  class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
                  @keydown.enter.prevent="addGoal"
                />
                <button @click="addGoal" class="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-xs hover:bg-gray-600 transition-colors">{{ t('chars.add_trait') }}</button>
              </div>
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-6">
            <button
              @click="showCreateModal = false"
              class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              {{ t('general.cancel') }}
            </button>
            <button
              @click="saveCharacter"
              :disabled="!form.name || !form.role"
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {{ editingCharacter ? t('general.save') : t('general.create') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
