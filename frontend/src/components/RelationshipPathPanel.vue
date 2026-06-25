<script setup lang="ts">
import { GitBranch, X, Search, ArrowRight } from 'lucide-vue-next'
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
</script>

<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="emit('close')">
      <div class="modal-panel max-w-2xl max-h-[80vh] overflow-hidden flex flex-col !p-0">
        <div class="px-6 py-4 border-b border-ink-edge flex items-center justify-between relative">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-full bg-chop-soft flex items-center justify-center border border-chop-border">
              <GitBranch :size="16" class="text-chop-light" />
            </div>
            <div>
              <h2 class="text-lg font-display font-semibold text-parchment">Find Relationship Path</h2>
              <p class="text-xs text-muted mt-0.5">Discover connections between characters</p>
            </div>
          </div>
          <button
            @click="emit('close')"
            class="btn btn-ghost p-2"
          >
            <X :size="16" />
          </button>
        </div>

        <div class="p-6 space-y-4 overflow-y-auto flex-1">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="field-label">From Character</label>
              <select
                :value="pathSource"
                @change="emit('update:pathSource', ($event.target as HTMLSelectElement).value)"
                class="input"
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
              <label class="field-label">To Character</label>
              <select
                :value="pathTarget"
                @change="emit('update:pathTarget', ($event.target as HTMLSelectElement).value)"
                class="input"
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
            class="btn btn-primary w-full"
          >
            <Search :size="14" />
            {{ loading ? 'Finding path...' : 'Find Path' }}
          </button>

          <div v-if="pathResult !== null" class="space-y-3 stagger-children">
            <div v-if="pathResult.length === 0" class="empty-state py-8">
              <p class="empty-state-text">No relationship path found between these characters.</p>
            </div>
            <div v-else class="space-y-3">
              <div class="text-xs text-muted font-display tracking-wide">
                Found {{ pathResult.length }} connection path(s):
              </div>
              <div
                v-for="(step, idx) in pathResult"
                :key="idx"
                class="card p-4 space-y-2.5"
              >
                <div class="flex items-center gap-2">
                  <span class="badge badge-accent">
                    Path {{ idx + 1 }}
                  </span>
                  <span class="text-xs text-muted">
                    {{ (step as { length?: number }).length || step.path.length }} steps
                  </span>
                </div>
                <div class="text-sm text-parchment flex items-center flex-wrap gap-1.5 leading-relaxed">
                  <template v-for="(node, nIdx) in step.path" :key="nIdx">
                    <span v-if="nIdx > 0" class="text-muted"><ArrowRight :size="12" class="inline" /></span>
                    <span class="font-medium">{{ getCharacterName(node.character_id || node) }}</span>
                  </template>
                </div>
                <div v-if="(step as { relationship_types?: string[] }).relationship_types" class="flex flex-wrap gap-1.5">
                  <span
                    v-for="(relType, rIdx) in (step as { relationship_types?: string[] }).relationship_types"
                    :key="rIdx"
                    class="badge badge-gold text-[10px] py-0"
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
  </Teleport>
</template>
