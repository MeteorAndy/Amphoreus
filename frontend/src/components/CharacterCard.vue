<script setup lang="ts">
import type { CharacterProfile, Relationship } from '../types/api'

const props = defineProps<{
  character: CharacterProfile
  selected?: boolean
  relationships?: Relationship[]
  allCharacters?: CharacterProfile[]
}>()

const emit = defineEmits<{
  select: [character: CharacterProfile]
  edit: [character: CharacterProfile]
  delete: [id: string]
}>()

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function getOtherCharacterId(rel: Relationship): string {
  if (rel.source_id && rel.source_id !== props.character.id) return rel.source_id
  if (rel.target_id && rel.target_id !== props.character.id) return rel.target_id
  if (rel.from_id && rel.from_id !== props.character.id) return rel.from_id
  if (rel.to_id && rel.to_id !== props.character.id) return rel.to_id
  return ''
}

function getCharacterName(id: string): string {
  return props.allCharacters?.find((c) => c.id === id)?.name || id
}

function getRelationshipType(rel: Relationship): string {
  return rel.rel_type || rel.relationship_type || 'related'
}
</script>

<template>
  <div
    class="bg-ink-panel border rounded-lg p-4 cursor-pointer transition-all hover:border-chop hover:shadow-lg hover:shadow-chop/10"
    :class="selected ? 'border-chop ring-1 ring-chop' : 'border-ink-edge'"
    @click="emit('select', character)"
  >
    <div class="flex items-start gap-3">
      <div
        class="w-10 h-10 rounded-full bg-chop flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
      >
        {{ getInitials(character.name) }}
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-sm font-semibold text-parchment truncate">{{ character.name }}</h3>
        <p class="text-xs text-parchment-dim truncate">{{ character.role }}</p>
      </div>
    </div>

    <div v-if="character.personality?.core_traits?.length" class="mt-3 flex flex-wrap gap-1">
      <span
        v-for="trait in character.personality.core_traits.slice(0, 4)"
        :key="trait"
        class="px-2 py-0.5 bg-ink-elevated text-parchment-dim text-xs rounded-full"
      >
        {{ trait }}
      </span>
      <span
        v-if="character.personality.core_traits.length > 4"
        class="px-2 py-0.5 bg-ink-elevated text-muted text-xs rounded-full"
      >
        +{{ character.personality.core_traits.length - 4 }}
      </span>
    </div>

    <div v-if="relationships && relationships.length > 0" class="mt-3 space-y-1.5 border-t border-ink-edge pt-3">
      <div class="text-xs text-muted mb-1">Relationships ({{ relationships.length }})</div>
      <div class="flex flex-wrap gap-1">
        <span
          v-for="(rel, idx) in relationships.slice(0, 3)"
          :key="idx"
          class="text-xs bg-purple-900/20 text-purple-300 px-2 py-0.5 rounded"
          :title="rel.description"
        >
          {{ getRelationshipType(rel) }} → {{ getCharacterName(getOtherCharacterId(rel)) }}
        </span>
        <span
          v-if="relationships.length > 3"
          class="text-xs text-muted px-2 py-0.5"
        >
          +{{ relationships.length - 3 }} more
        </span>
      </div>
    </div>

    <div v-if="selected" class="mt-3 space-y-2 text-xs text-parchment-dim border-t border-ink-edge pt-3">
      <div v-if="character.core_desire">
        <span class="text-muted">Desire: </span>{{ character.core_desire }}
      </div>
      <div v-if="character.deep_fear">
        <span class="text-muted">Fear: </span>{{ character.deep_fear }}
      </div>
      <div v-if="character.voice_sample" class="italic text-muted">
        "{{ character.voice_sample.slice(0, 100) }}{{ character.voice_sample.length > 100 ? '...' : '' }}"
      </div>
      <div v-if="character.personality?.mbti">
        <span class="text-muted">MBTI: </span>{{ character.personality.mbti }}
      </div>
      <div v-if="character.arc_stage">
        <span class="text-muted">Arc: </span>{{ character.arc_stage }}
      </div>
    </div>

    <div v-if="!selected && character.voice_sample && !(relationships && relationships.length > 0)" class="mt-2 text-xs text-muted italic truncate">
      "{{ character.voice_sample.slice(0, 60) }}{{ character.voice_sample.length > 60 ? '...' : '' }}"
    </div>

    <div class="mt-2 flex gap-2">
      <button
        @click.stop="emit('edit', character)"
        class="text-xs text-chop hover:text-chop transition-colors"
      >
        Edit
      </button>
      <button
        @click.stop="emit('delete', character.id)"
        class="text-xs text-red-400 hover:text-red-300 transition-colors"
      >
        Delete
      </button>
    </div>
  </div>
</template>
