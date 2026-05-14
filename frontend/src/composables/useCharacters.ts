import { ref } from 'vue'
import type { CharacterProfile, Relationship, CreateCharacterRequest, UpdateCharacterRequest, RelationshipRequest } from '../types/api'
import {
  listCharacters,
  createCharacter as apiCreateCharacter,
  updateCharacter as apiUpdateCharacter,
  deleteCharacter as apiDeleteCharacter,
  listRelationships,
  createRelationship as apiCreateRelationship,
} from '../api/client'

export function useCharacters() {
  const characters = ref<CharacterProfile[]>([])
  const relationships = ref<Relationship[]>([])
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

  async function createCharacter(data: CreateCharacterRequest): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const created = await apiCreateCharacter(data)
      characters.value.push(created)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create character'
    } finally {
      loading.value = false
    }
  }

  async function updateCharacter(id: string, data: UpdateCharacterRequest): Promise<void> {
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

  async function fetchRelationships(): Promise<void> {
    try {
      relationships.value = await listRelationships()
    } catch {
      relationships.value = []
    }
  }

  async function setRelationship(data: RelationshipRequest): Promise<void> {
    error.value = null
    try {
      const rel = await apiCreateRelationship(data)
      const idx = relationships.value.findIndex(
        (r) => r.character_id === data.target_id,
      )
      if (idx !== -1) relationships.value[idx] = rel
      else relationships.value.push(rel)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to set relationship'
    }
  }

  function selectCharacter(char: CharacterProfile | null): void {
    selectedCharacter.value = char
  }

  return {
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
    setRelationship,
    selectCharacter,
  }
}
