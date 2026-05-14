import { ref } from 'vue'
import type { CharacterProfile, NetworkData } from '../types/api'
import {
  generateCharacters as apiGenerateCharacters,
  listCharacters,
  updateCharacter as apiUpdateCharacter,
  deleteCharacter as apiDeleteCharacter,
  refineCharacter as apiRefineCharacter,
  getCharacterNetwork,
  createRelationship as apiCreateRelationship,
} from '../api/client'

export function useCharacters() {
  const characters = ref<CharacterProfile[]>([])
  const networkData = ref<NetworkData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedCharacter = ref<CharacterProfile | null>(null)

  async function fetchCharacters(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      characters.value = await listCharacters()
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
      // Merge generated characters into existing list, dedup by id
      const existingIds = new Set(characters.value.map((c) => c.id))
      for (const char of generated) {
        if (!existingIds.has(char.id)) {
          characters.value.push(char)
          existingIds.add(char.id)
        }
      }
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
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to refine character'
    }
  }

  async function fetchCharacterNetwork(charId: string): Promise<void> {
    try {
      networkData.value = await getCharacterNetwork(charId)
    } catch {
      networkData.value = null
    }
  }

  async function buildRelationships(characterIds: string[]): Promise<void> {
    error.value = null
    try {
      await apiCreateRelationship({
        source_id: characterIds[0],
        target_id: characterIds[1],
        relationship_type: 'built',
        strength: 0.5,
      })
    } catch {
      // Relationship building may fail if there aren't enough characters; that's OK
    }
  }

  function selectCharacter(char: CharacterProfile | null): void {
    selectedCharacter.value = char
  }

  return {
    characters,
    networkData,
    loading,
    error,
    selectedCharacter,
    fetchCharacters,
    generateCharacters,
    updateCharacter,
    removeCharacter,
    refineCharacter,
    fetchCharacterNetwork,
    buildRelationships,
    selectCharacter,
  }
}
