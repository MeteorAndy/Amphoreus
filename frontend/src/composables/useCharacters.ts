import { ref, watch } from 'vue'
import type { CharacterProfile, NetworkData, Relationship } from '../types/api'
import {
  generateCharacters as apiGenerateCharacters,
  listCharacters as apiListCharacters,
  updateCharacter as apiUpdateCharacter,
  deleteCharacter as apiDeleteCharacter,
  refineCharacter as apiRefineCharacter,
  getCharacterNetwork as apiGetCharacterNetwork,
  buildRelationships as apiBuildRelationships,
} from '../api/client'
import { useProjectStore } from './useProjectStore'

export function useCharacters() {
  const projectStore = useProjectStore()

  const characters = ref<CharacterProfile[]>([])
  const networkData = ref<NetworkData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedCharacter = ref<CharacterProfile | null>(null)
  const buildingRelationships = ref(false)

  async function fetchCharacters(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      if (projectStore.currentCharacters.value.length > 0) {
        characters.value = [...projectStore.currentCharacters.value]
      } else {
        characters.value = await apiListCharacters()
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch characters'
    } finally {
      loading.value = false
    }
  }

  async function generateCharacters(worldId: string, count: number = 5): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const generated = await apiGenerateCharacters(worldId, count)
      const existingIds = new Set(characters.value.map((c) => c.id))
      const newChars: CharacterProfile[] = []
      for (const char of generated) {
        if (!existingIds.has(char.id)) {
          characters.value.push(char)
          newChars.push(char)
          existingIds.add(char.id)
        }
      }
      await projectStore.setCharacters([...characters.value])
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate characters'
    } finally {
      loading.value = false
    }
  }

  async function updateCharacter(id: string, data: Partial<CharacterProfile>): Promise<void> {
    error.value = null
    try {
      const updated = await apiUpdateCharacter(id, data)
      const idx = characters.value.findIndex((c) => c.id === id)
      if (idx !== -1) characters.value[idx] = updated
      if (selectedCharacter.value?.id === id) selectedCharacter.value = updated
      await projectStore.setCharacters([...characters.value])
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update character'
    }
  }

  async function removeCharacter(id: string): Promise<void> {
    error.value = null
    try {
      await apiDeleteCharacter(id)
      characters.value = characters.value.filter((c) => c.id !== id)
      if (selectedCharacter.value?.id === id) selectedCharacter.value = null
      await projectStore.setCharacters([...characters.value])
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete character'
    }
  }

  async function refineCharacter(charId: string, feedback: string): Promise<void> {
    error.value = null
    try {
      const updated = await apiRefineCharacter(charId, feedback)
      const idx = characters.value.findIndex((c) => c.id === charId)
      if (idx !== -1) characters.value[idx] = updated
      if (selectedCharacter.value?.id === charId) selectedCharacter.value = updated
      await projectStore.setCharacters([...characters.value])
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to refine character'
    }
  }

  async function fetchCharacterNetwork(charId: string, depth: number = 2): Promise<void> {
    try {
      networkData.value = await apiGetCharacterNetwork(charId, depth)
    } catch {
      networkData.value = null
    }
  }

  async function generateRelationships(characterIds: string[]): Promise<Relationship[]> {
    if (characterIds.length < 2) return []
    buildingRelationships.value = true
    error.value = null
    try {
      const relationships = await apiBuildRelationships(characterIds)
      await projectStore.setRelationships(relationships)
      return relationships
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to build relationships'
      return []
    } finally {
      buildingRelationships.value = false
    }
  }

  function selectCharacter(char: CharacterProfile | null): void {
    selectedCharacter.value = char
    if (char) {
      fetchCharacterNetwork(char.id)
    } else {
      networkData.value = null
    }
  }

  watch(
    () => projectStore.currentCharacters.value,
    (newChars) => {
      if (newChars && newChars.length > 0) {
        characters.value = [...newChars]
      }
    },
    { immediate: true },
  )

  return {
    characters,
    networkData,
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
  }
}
