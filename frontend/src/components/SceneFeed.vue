<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { SceneRound, SceneStatus } from '../types/api'

const props = defineProps<{
  rounds: SceneRound[]
  status: SceneStatus
  connected: boolean
}>()

const feedContainer = ref<HTMLElement | null>(null)

watch(
  () => props.rounds.length,
  async () => {
    await nextTick()
    if (feedContainer.value) {
      feedContainer.value.scrollTop = feedContainer.value.scrollHeight
    }
  },
)
</script>

<template>
  <div class="flex flex-col h-full bg-gray-900 rounded-lg border border-gray-800">
    <div class="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
      <h3 class="text-sm font-semibold text-gray-200">Scene Feed</h3>
      <div class="flex items-center gap-2">
        <span
          class="w-2 h-2 rounded-full"
          :class="
            connected
              ? status.status === 'running'
                ? 'bg-green-500 animate-pulse'
                : 'bg-green-500'
              : 'bg-gray-600'
          "
        />
        <span class="text-xs text-gray-500">
          {{ status.status === 'running' ? `Round ${status.current_round}` : status.status }}
        </span>
      </div>
    </div>
    <div ref="feedContainer" class="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
      <div v-if="rounds.length === 0" class="flex items-center justify-center h-full text-gray-600 text-sm">
        No rounds yet. Start a scene to see the feed.
      </div>
      <div
        v-for="round in rounds"
        :key="round.round_number"
        class="bg-gray-800/50 rounded-lg p-4 space-y-2"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-indigo-400">Round {{ round.round_number }}</span>
          <span v-if="round.character" class="text-xs text-gray-500">{{ round.character }}</span>
        </div>
        <p v-if="round.narration" class="text-sm text-gray-300 italic leading-relaxed">
          {{ round.narration }}
        </p>
        <p v-if="round.dialogue" class="text-sm text-gray-100 leading-relaxed">
          <span v-if="round.character" class="font-semibold text-indigo-300">{{ round.character }}:</span>
          "{{ round.dialogue }}"
        </p>
        <div v-if="round.actions && round.actions.length > 0" class="flex flex-wrap gap-1">
          <span
            v-for="(action, idx) in round.actions"
            :key="idx"
            class="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded"
          >
            {{ action }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
