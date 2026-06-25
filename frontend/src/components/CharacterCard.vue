<script setup lang="ts">
import { Pencil, Trash2 } from 'lucide-vue-next'
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
    class="card p-4 cursor-pointer fade-in-up"
    :class="selected ? 'border-chop seal-glow' : ''"
    @click="emit('select', character)"
  >
    <div class="flex items-start gap-3">
      <div
        class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0"
        :class="selected ? 'bg-gradient-chop text-white shadow-md' : 'bg-chop-soft text-chop-light border border-chop-border'"
      >
        {{ getInitials(character.name) }}
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-base font-display font-semibold text-parchment truncate">{{ character.name }}</h3>
        <p class="text-xs text-parchment-dim truncate font-body">{{ character.role }}</p>
      </div>
    </div>

    <div v-if="character.personality?.core_traits?.length" class="mt-3 flex flex-wrap gap-1.5">
      <span
        v-for="trait in character.personality.core_traits.slice(0, 4)"
        :key="trait"
        class="badge badge-muted"
      >
        {{ trait }}
      </span>
      <span
        v-if="character.personality.core_traits.length > 4"
        class="badge badge-muted text-muted"
      >
        +{{ character.personality.core_traits.length - 4 }}
      </span>
    </div>

    <div v-if="relationships && relationships.length > 0" class="mt-3 space-y-2 border-t border-ink-edge pt-3">
      <div class="text-xs text-muted font-display tracking-wide">Relationships ({{ relationships.length }})</div>
      <div class="flex flex-wrap gap-1">
        <span
          v-for="(rel, idx) in relationships.slice(0, 3)"
          :key="idx"
          class="text-xs bg-ink-wash-light text-parchment-dim px-2 py-0.5 rounded border border-ink-edge"
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
      <div v-if="character.core_desire" class="flex gap-1.5">
        <span class="text-muted font-medium shrink-0">Desire:</span>
        <span>{{ character.core_desire }}</span>
      </div>
      <div v-if="character.deep_fear" class="flex gap-1.5">
        <span class="text-muted font-medium shrink-0">Fear:</span>
        <span>{{ character.deep_fear }}</span>
      </div>
      <div v-if="character.voice_sample" class="italic text-muted text-xs leading-relaxed">
        "{{ character.voice_sample.slice(0, 100) }}{{ character.voice_sample.length > 100 ? '...' : '' }}"
      </div>
      <div v-if="character.personality?.mbti" class="flex gap-1.5">
        <span class="text-muted font-medium shrink-0">MBTI:</span>
        <span>{{ character.personality.mbti }}</span>
      </div>
      <div v-if="character.arc_stage" class="flex gap-1.5">
        <span class="text-muted font-medium shrink-0">Arc:</span>
        <span>{{ character.arc_stage }}</span>
      </div>
    </div>

    <div v-if="!selected && character.voice_sample && !(relationships && relationships.length > 0)" class="mt-2 text-xs text-muted italic truncate">
      "{{ character.voice_sample.slice(0, 60) }}{{ character.voice_sample.length > 60 ? '...' : '' }}"
    </div>

    <div class="mt-3 flex gap-2 pt-2 border-t border-ink-edge/50">
      <button
        @click.stop="emit('edit', character)"
        class="btn btn-ghost btn-xs flex-1 text-chop"
      >
        <Pencil :size="12" />
        Edit
      </button>
      <button
        @click.stop="emit('delete', character.id)"
        class="btn btn-ghost btn-xs flex-1 text-danger hover:text-danger"
      >
        <Trash2 :size="12" />
        Delete
      </button>
    </div>
  </div>
</template>

<style scoped>
.bg-gradient-chop {
  background: var(--gradient-chop-seal);
}
.btn-xs {
  padding: 0.25rem 0.5rem;
  font-size: var(--text-xs);
  border-radius: var(--radius-scroll);
}
</style>
