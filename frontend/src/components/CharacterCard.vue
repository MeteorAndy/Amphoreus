<script setup lang="ts">
import type { CharacterProfile } from '../types/api'

const props = defineProps<{
  character: CharacterProfile
  selected?: boolean
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
</script>

<template>
  <div
    class="bg-gray-900 border rounded-lg p-4 cursor-pointer transition-all hover:border-indigo-500 hover:shadow-lg hover:shadow-indigo-500/10"
    :class="selected ? 'border-indigo-500 ring-1 ring-indigo-500' : 'border-gray-800'"
    @click="emit('select', character)"
  >
    <div class="flex items-start gap-3">
      <div
        class="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
      >
        {{ getInitials(character.name) }}
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-sm font-semibold text-gray-100 truncate">{{ character.name }}</h3>
        <p class="text-xs text-gray-400 truncate">{{ character.role }}</p>
      </div>
    </div>
    <div class="mt-3 flex flex-wrap gap-1">
      <span
        v-for="trait in character.traits?.slice(0, 4)"
        :key="trait"
        class="px-2 py-0.5 bg-gray-800 text-gray-300 text-xs rounded-full"
      >
        {{ trait }}
      </span>
      <span
        v-if="character.traits && character.traits.length > 4"
        class="px-2 py-0.5 bg-gray-800 text-gray-500 text-xs rounded-full"
      >
        +{{ character.traits.length - 4 }}
      </span>
    </div>
    <div class="mt-2 flex items-center gap-3 text-xs text-gray-500">
      <span>{{ character.relationships?.length || 0 }} relationships</span>
      <span v-if="character.age">Age: {{ character.age }}</span>
    </div>
    <div class="mt-2 flex gap-2">
      <button
        @click.stop="emit('edit', character)"
        class="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
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
