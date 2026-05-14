<script setup lang="ts">
import { ref } from 'vue'
import type { SceneStatus } from '../types/api'

const props = defineProps<{
  status: SceneStatus
  connected: boolean
  sceneId: string | null
}>()

const emit = defineEmits<{
  intervene: [text: string]
  endScene: []
  startScene: []
  reset: []
}>()

const intervention = ref('')

function handleIntervene(): void {
  const text = intervention.value.trim()
  if (!text) return
  emit('intervene', text)
  intervention.value = ''
}

function getStatusLabel(): string {
  switch (props.status.status) {
    case 'idle':
      return 'Ready'
    case 'running':
      return `Running (Round ${props.status.current_round})`
    case 'completed':
      return 'Completed'
    case 'error':
      return 'Error'
    default:
      return 'Unknown'
  }
}

function getStatusColor(): string {
  switch (props.status.status) {
    case 'idle':
      return 'text-gray-400'
    case 'running':
      return 'text-green-400'
    case 'completed':
      return 'text-blue-400'
    case 'error':
      return 'text-red-400'
    default:
      return 'text-gray-400'
  }
}
</script>

<template>
  <div class="flex flex-col h-full bg-gray-900 rounded-lg border border-gray-800">
    <div class="px-4 py-3 border-b border-gray-800">
      <h3 class="text-sm font-semibold text-gray-200">Director Panel</h3>
    </div>
    <div class="flex-1 p-4 space-y-4">
      <div class="bg-gray-800/50 rounded-lg p-3 space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-xs text-gray-500">Status</span>
          <span class="text-xs font-medium" :class="getStatusColor()">{{ getStatusLabel() }}</span>
        </div>
        <div v-if="sceneId" class="flex items-center justify-between">
          <span class="text-xs text-gray-500">Scene ID</span>
          <span class="text-xs text-gray-400 font-mono">{{ sceneId.slice(0, 8) }}...</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-xs text-gray-500">Connection</span>
          <span
            class="text-xs"
            :class="connected ? 'text-green-400' : 'text-gray-500'"
          >
            {{ connected ? 'Connected' : 'Disconnected' }}
          </span>
        </div>
      </div>
      <div v-if="status.status === 'idle' || status.status === 'completed' || status.status === 'error'">
        <button
          v-if="status.status === 'idle'"
          @click="emit('startScene')"
          class="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 transition-colors"
        >
          Run Scene
        </button>
        <button
          v-else
          @click="emit('reset')"
          class="w-full px-4 py-2 bg-gray-700 text-gray-200 rounded-lg text-sm font-medium hover:bg-gray-600 transition-colors"
        >
          Reset
        </button>
      </div>
      <div v-if="status.status === 'running'" class="space-y-3">
        <div>
          <label class="block text-xs text-gray-500 mb-1">Director Intervention</label>
          <textarea
            v-model="intervention"
            placeholder="Guide the scene..."
            rows="3"
            class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
          />
          <button
            @click="handleIntervene"
            :disabled="!intervention.trim()"
            class="mt-2 w-full px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send Intervention
          </button>
        </div>
        <button
          @click="emit('endScene')"
          class="w-full px-4 py-2 bg-red-600/20 text-red-400 border border-red-800 rounded-lg text-sm font-medium hover:bg-red-600/30 transition-colors"
        >
          End Scene
        </button>
      </div>
    </div>
  </div>
</template>
