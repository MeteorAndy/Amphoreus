<script setup lang="ts">
import { ref, computed } from 'vue'
import { Clapperboard, Play, RotateCcw, Zap, Send, Square, CircleDot, Users, Radio } from 'lucide-vue-next'
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

const intervention = ref('')
const showEndConfirm = ref(false)
const directorLog = ref<{ text: string; ts: string }[]>([])

const isRunning = computed(() => props.status.status === 'running')
const activeCharacters = computed(() => {
  if (!props.rounds || props.rounds.length === 0) return []
  const seen = new Set<string>()
  for (const r of props.rounds) {
    const name = (r as { actor_name?: string; character?: string }).actor_name ||
      (r as { actor_name?: string; character?: string }).character
    if (name) seen.add(name)
  }
  return [...seen]
})

const quickActions = computed(() => [
  { key: 'new_char', label: t('scene.quick_new_char') },
  { key: 'conflict', label: t('scene.quick_conflict') },
  { key: 'timeskip', label: t('scene.quick_timeskip') },
  { key: 'reveal', label: t('scene.quick_reveal') },
])

function getStatusBadge() {
  switch (props.status.status) {
    case 'running': return { class: 'badge-editor', text: props.status.current_round ? `Round ${props.status.current_round}` : 'Running' }
    case 'completed': return { class: 'badge-accent', text: 'Completed' }
    case 'error': return { class: '', text: 'Error' }
    default: return { class: 'badge-muted', text: 'Idle' }
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
  <div class="flex flex-col h-full card overflow-hidden">
    <div class="px-4 py-3 border-b border-ink-edge flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-full bg-chop-soft flex items-center justify-center">
          <Clapperboard :size="15" class="text-chop-light" />
        </div>
        <h3 class="text-sm font-display font-semibold text-parchment">{{ t('scene.director_panel') }}</h3>
      </div>
      <span class="badge" :class="getStatusBadge().class">
        {{ getStatusBadge().text }}
      </span>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-4 stagger-children">
      <div class="bg-ink-bg-deep/50 rounded-lg p-3 space-y-2.5 border border-ink-edge">
        <div class="flex items-center justify-between">
          <span class="text-xs text-muted font-display tracking-wide">Status</span>
          <span class="text-xs font-medium" :class="{
            'text-editor': props.status.status === 'running',
            'text-chop-light': props.status.status === 'completed',
            'text-danger': props.status.status === 'error',
            'text-parchment-dim': !['running', 'completed', 'error'].includes(props.status.status)
          }">{{ props.status.status }}</span>
        </div>
        <div v-if="activeCharacters.length > 0" class="flex items-start justify-between gap-2">
          <span class="text-xs text-muted font-display tracking-wide shrink-0 flex items-center gap-1">
            <Users :size="11" />
            Characters
          </span>
          <div class="flex flex-wrap gap-1 justify-end">
            <span
              v-for="char in activeCharacters"
              :key="char"
              class="badge badge-accent text-[10px] py-0.5"
            >{{ char }}</span>
          </div>
        </div>
        <div v-if="sceneId" class="flex items-center justify-between">
          <span class="text-xs text-muted font-display tracking-wide">Scene ID</span>
          <span class="text-xs text-parchment-dim font-mono">{{ sceneId.slice(0, 8) }}…</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-xs text-muted font-display tracking-wide flex items-center gap-1">
            <Radio :size="11" />
            WS
          </span>
          <span class="flex items-center gap-1.5 text-xs" :class="connected ? 'text-editor' : 'text-muted'">
            <span class="w-1.5 h-1.5 rounded-full" :class="connected ? 'bg-editor animate-pulse' : 'bg-muted'"></span>
            {{ connected ? 'Connected' : 'Disconnected' }}
          </span>
        </div>
      </div>

      <div v-if="!isRunning">
        <button
          v-if="status.status === 'idle'"
          @click="emit('startScene')"
          class="btn btn-primary w-full"
        >
          <Play :size="14" />
          {{ t('scene.run') }}
        </button>
        <button
          v-else
          @click="emit('reset')"
          class="btn btn-secondary w-full"
        >
          <RotateCcw :size="14" />
          Reset
        </button>
      </div>

      <template v-if="isRunning">
        <div class="space-y-2">
          <p class="text-xs text-muted font-display tracking-wide flex items-center gap-1.5">
            <Zap :size="11" class="text-gold" />
            Quick Actions
          </p>
          <div class="grid grid-cols-2 gap-1.5">
            <button
              v-for="action in quickActions"
              :key="action.key"
              @click="handleQuickAction(action.label)"
              class="chip text-xs py-1.5 justify-center truncate"
            >
              {{ action.label }}
            </button>
          </div>
        </div>

        <div class="space-y-2">
          <label class="field-label flex items-center gap-1.5">
            <Send :size="11" />
            {{ t('scene.inject_event') }}
          </label>
          <textarea
            v-model="intervention"
            :placeholder="t('scene.inject_placeholder')"
            rows="3"
            class="input resize-none"
          />
          <button
            @click="handleIntervene"
            :disabled="!intervention.trim()"
            class="btn btn-primary w-full"
          >
            <Send :size="14" />
            {{ t('scene.inject_event') }}
          </button>
        </div>

        <div>
          <button
            v-if="!showEndConfirm"
            @click="confirmEndScene"
            class="btn btn-danger w-full"
          >
            <Square :size="14" />
            {{ t('scene.end_scene') }}
          </button>
          <div v-else class="bg-danger-soft border border-chop-border rounded-lg p-3 space-y-3">
            <div class="flex items-start gap-2">
              <CircleDot :size="14" class="text-danger mt-0.5 shrink-0" />
              <p class="text-xs text-danger leading-relaxed">{{ t('scene.end_confirm') }}</p>
            </div>
            <div class="flex gap-2">
              <button
                @click="doEndScene"
                class="btn btn-danger flex-1 btn-sm"
              >
                {{ t('general.confirm') }}
              </button>
              <button
                @click="showEndConfirm = false"
                class="btn btn-secondary flex-1 btn-sm"
              >
                {{ t('general.cancel') }}
              </button>
            </div>
          </div>
        </div>
      </template>

      <div v-if="directorLog.length > 0" class="space-y-2">
        <p class="text-xs text-muted font-display tracking-wide">Director Log</p>
        <div class="space-y-1.5 max-h-40 overflow-y-auto">
          <div
            v-for="(entry, i) in directorLog"
            :key="i"
            class="bg-ink-bg-deep/50 rounded-lg px-3 py-2 border border-ink-edge"
          >
            <p class="text-xs text-parchment-dim leading-snug">{{ entry.text }}</p>
            <p class="text-[10px] text-muted mt-0.5 font-mono">{{ entry.ts }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
</style>
