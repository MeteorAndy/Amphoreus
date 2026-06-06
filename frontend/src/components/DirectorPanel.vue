<script setup lang="ts">
import { ref, computed } from 'vue'
import type { SceneStatus, SceneRound } from '../types/api'
import { useI18n } from '../i18n'
import { useToast } from '../composables/useToast'

const { t } = useI18n()
const { success } = useToast()

const props = defineProps<{
  status: SceneStatus
  connected: boolean
  sceneId: string | null
  rounds?: SceneRound[]
}>()

const emit = defineEmits<{
  intervene: [text: string]
  endScene: []
  startScene: []
  reset: []
}>()

// --- State ---
const intervention = ref('')
const showEndConfirm = ref(false)
const directorLog = ref<{ text: string; ts: string }[]>([])

// --- Computed ---
const isRunning = computed(() => props.status.status === 'running')
const activeCharacters = computed(() => {
  if (!props.rounds || props.rounds.length === 0) return []
  const seen = new Set<string>()
  for (const r of props.rounds) {
    if (r.character) seen.add(r.character)
  }
  return [...seen]
})

const quickActions = computed(() => [
  { key: 'new_char', label: t('scene.quick_new_char') },
  { key: 'conflict', label: t('scene.quick_conflict') },
  { key: 'timeskip', label: t('scene.quick_timeskip') },
  { key: 'reveal', label: t('scene.quick_reveal') },
])

// --- Methods ---
function getStatusColor(): string {
  switch (props.status.status) {
    case 'running': return 'text-green-400'
    case 'completed': return 'text-blue-400'
    case 'error': return 'text-red-400'
    default: return 'text-gray-400'
  }
}

function handleIntervene(): void {
  const text = intervention.value.trim()
  if (!text) return
  emit('intervene', text)
  directorLog.value.unshift({ text, ts: new Date().toLocaleTimeString() })
  success(t('scene.injected'))
  intervention.value = ''
}

function handleQuickAction(label: string): void {
  emit('intervene', label)
  directorLog.value.unshift({ text: label, ts: new Date().toLocaleTimeString() })
  success(t('scene.injected'))
}

function confirmEndScene(): void {
  showEndConfirm.value = true
}

function doEndScene(): void {
  showEndConfirm.value = false
  emit('endScene')
  success(t('scene.ended'))
}
</script>

<template>
  <div class="flex flex-col h-full bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
    <!-- Header -->
    <div class="px-4 py-3 border-b border-gray-800 flex items-center justify-between shrink-0">
      <h3 class="text-sm font-semibold text-gray-200">{{ t('scene.director_panel') }}</h3>
      <span class="text-xs font-medium" :class="getStatusColor()">
        {{ props.status.status === 'running'
          ? `Round ${props.status.current_round}`
          : props.status.status }}
      </span>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <!-- Status block -->
      <div class="bg-gray-800/50 rounded-lg p-3 space-y-1.5">
        <div class="flex items-center justify-between">
          <span class="text-xs text-gray-500">Status</span>
          <span class="text-xs font-medium" :class="getStatusColor()">{{ props.status.status }}</span>
        </div>
        <div v-if="activeCharacters.length > 0" class="flex items-start justify-between gap-2">
          <span class="text-xs text-gray-500 shrink-0">Characters</span>
          <div class="flex flex-wrap gap-1 justify-end">
            <span
              v-for="char in activeCharacters"
              :key="char"
              class="text-xs text-indigo-400 bg-indigo-900/30 px-1.5 py-0.5 rounded"
            >{{ char }}</span>
          </div>
        </div>
        <div v-if="sceneId" class="flex items-center justify-between">
          <span class="text-xs text-gray-500">Scene ID</span>
          <span class="text-xs text-gray-400 font-mono">{{ sceneId.slice(0, 8) }}…</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-xs text-gray-500">WS</span>
          <span class="text-xs" :class="connected ? 'text-green-400' : 'text-gray-500'">
            {{ connected ? 'Connected' : 'Disconnected' }}
          </span>
        </div>
      </div>

      <!-- Idle / completed / error actions -->
      <div v-if="!isRunning">
        <button
          v-if="status.status === 'idle'"
          @click="emit('startScene')"
          class="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 transition-colors"
        >
          {{ t('scene.run') }}
        </button>
        <button
          v-else
          @click="emit('reset')"
          class="w-full px-4 py-2 bg-gray-700 text-gray-200 rounded-lg text-sm font-medium hover:bg-gray-600 transition-colors"
        >
          Reset
        </button>
      </div>

      <!-- Running: quick actions + inject + end -->
      <template v-if="isRunning">
        <!-- Quick Actions -->
        <div class="space-y-2">
          <p class="text-xs text-gray-500">Quick Actions</p>
          <div class="grid grid-cols-2 gap-1.5">
            <button
              v-for="action in quickActions"
              :key="action.key"
              @click="handleQuickAction(action.label)"
              class="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-300 hover:bg-gray-700 hover:border-indigo-600 transition-colors text-left truncate"
            >
              {{ action.label }}
            </button>
          </div>
        </div>

        <!-- Custom inject -->
        <div class="space-y-2">
          <label class="block text-xs text-gray-500">{{ t('scene.inject_event') }}</label>
          <textarea
            v-model="intervention"
            :placeholder="t('scene.inject_placeholder')"
            rows="3"
            class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
          />
          <button
            @click="handleIntervene"
            :disabled="!intervention.trim()"
            class="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {{ t('scene.inject_event') }}
          </button>
        </div>

        <!-- End Scene -->
        <div>
          <button
            v-if="!showEndConfirm"
            @click="confirmEndScene"
            class="w-full px-4 py-2 bg-red-600/20 text-red-400 border border-red-800 rounded-lg text-sm font-medium hover:bg-red-600/30 transition-colors"
          >
            {{ t('scene.end_scene') }}
          </button>
          <div v-else class="space-y-2 bg-red-900/20 border border-red-800 rounded-lg p-3">
            <p class="text-xs text-red-300">{{ t('scene.end_confirm') }}</p>
            <div class="flex gap-2">
              <button
                @click="doEndScene"
                class="flex-1 px-3 py-1.5 bg-red-600 text-white rounded text-xs font-medium hover:bg-red-500 transition-colors"
              >
                {{ t('general.confirm') }}
              </button>
              <button
                @click="showEndConfirm = false"
                class="flex-1 px-3 py-1.5 bg-gray-700 text-gray-300 rounded text-xs font-medium hover:bg-gray-600 transition-colors"
              >
                {{ t('general.cancel') }}
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- Director Log -->
      <div v-if="directorLog.length > 0" class="space-y-2">
        <p class="text-xs text-gray-500">Director Log</p>
        <div class="space-y-1 max-h-40 overflow-y-auto">
          <div
            v-for="(entry, i) in directorLog"
            :key="i"
            class="bg-gray-800/50 rounded px-2 py-1.5"
          >
            <p class="text-xs text-gray-300 leading-snug">{{ entry.text }}</p>
            <p class="text-xs text-gray-600 mt-0.5">{{ entry.ts }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

