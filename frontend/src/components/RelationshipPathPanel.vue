<script setup lang="ts">
import type { CharacterProfile, PathStep } from '../types/api'

const props = defineProps<{
  characters: CharacterProfile[]
  pathSource: string
  pathTarget: string
  pathResult: PathStep[] | null
  loading: boolean
}>()

const emit = defineEmits<{
  'update:pathSource': [value: string]
  'update:pathTarget': [value: string]
  'findPath': []
  'close': []
}>()

function getCharacterName(id: string): string {
  return props.characters.find((c) => c.id === id)?.name || id
}

function getStepCharacterNames(step: PathStep): string {
  const names: string[] = []
  for (const node of step.path) {
    names.push(getCharacterName(node.character_id || node))
  }
  return names.join(' → ')
}
</script>

<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="emit('close')">
    <div class="bg-ink-panel rounded-lg border border-ink-edge w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
      <div class="px-6 py-4 border-b border-ink-edge flex items-center justify-between">
        <h2 class="text-lg font-semibold text-parchment">Find Relationship Path</h2>
        <button
          @click="emit('close')"
          class="text-muted hover:text-parchment transition-colors"
        >
          ✕
        </button>
      </div>

      <div class="p-6 space-y-4 overflow-y-auto">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-muted mb-1">From Character</label>
            <select
              :value="pathSource"
              @change="emit('update:pathSource', ($event.target as HTMLSelectElement).value)"
              class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
            >
              <option value="">Select character...</option>
              <option
                v-for="char in characters"
                :key="char.id"
                :value="char.id"
              >
                {{ char.name }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-muted mb-1">To Character</label>
            <select
              :value="pathTarget"
              @change="emit('update:pathTarget', ($event.target as HTMLSelectElement).value)"
              class="w-full bg-ink-elevated border border-ink-edge rounded-lg px-3 py-2 text-sm text-parchment focus:outline-none focus:border-chop"
            >
              <option value="">Select character...</option>
              <option
                v-for="char in characters"
                :key="char.id"
                :value="char.id"
                :disabled="char.id === pathSource"
              >
                {{ char.name }}
              </option>
            </select>
          </div>
        </div>

        <button
          @click="emit('findPath')"
          :disabled="!pathSource || !pathTarget || loading"
          class="w-full px-4 py-2 bg-chop text-white rounded-lg text-sm font-medium hover:bg-chop disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ loading ? 'Finding path...' : 'Find Path' }}
        </button>

        <div v-if="pathResult !== null" class="space-y-3">
          <div v-if="pathResult.length === 0" class="text-center py-8 text-muted text-sm">
            No relationship path found between these characters.
          </div>
          <div v-else class="space-y-3">
            <div class="text-xs text-muted">
              Found {{ pathResult.length }} connection path(s):
            </div>
            <div
              v-for="(step, idx) in pathResult"
              :key="idx"
              class="bg-ink-elevated/50 rounded-lg p-4 space-y-2"
            >
              <div class="flex items-center gap-2">
                <span class="text-xs font-medium text-chop bg-chop/10 px-2 py-0.5 rounded">
                  Path {{ idx + 1 }}
                </span>
                <span class="text-xs text-muted">
                  {{ (step as { length?: number }).length || step.path.length }} steps
                </span>
              </div>
              <div class="text-sm text-parchment">
                {{ getStepCharacterNames(step) }}
              </div>
              <div v-if="(step as { relationship_types?: string[] }).relationship_types" class="flex flex-wrap gap-1">
                <span
                  v-for="(relType, rIdx) in (step as { relationship_types?: string[] }).relationship_types"
                  :key="rIdx"
                  class="text-xs bg-purple-900/20 text-purple-400 px-2 py-0.5 rounded"
                >
                  {{ relType }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
