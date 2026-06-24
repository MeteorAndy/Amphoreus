<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { RoundEntry, SceneStatus } from '../types/api'

interface SceneRound {
  round_number: number
  actor_id?: string
  actor_name?: string
  character?: string
  dialogue?: string
  action?: string
  actions?: string[]
  narration?: string
  inner_thought?: string
  emotion?: string
  reactions?: {
    reactor_id: string
    reactor_name: string
    visible_reaction: string
    inner_thought: string
  }[]
}

const props = defineProps<{
  rounds: (RoundEntry | SceneRound)[]
  status: SceneStatus
  connected: boolean
  resolutionText?: string
}>()

const feedContainer = ref<HTMLElement | null>(null)
const showInnerThoughts = ref<Record<number, boolean>>({})
const showReactions = ref<Record<number, boolean>>({})

watch(
  () => props.rounds.length,
  async () => {
    await nextTick()
    if (feedContainer.value) {
      feedContainer.value.scrollTop = feedContainer.value.scrollHeight
    }
  },
)

function toggleInnerThought(roundNum: number): void {
  showInnerThoughts.value[roundNum] = !showInnerThoughts.value[roundNum]
}

function toggleReactions(roundNum: number): void {
  showReactions.value[roundNum] = !showReactions.value[roundNum]
}

function getActorName(round: RoundEntry | SceneRound): string {
  return round.actor_name || round.character || 'Unknown'
}

function getAction(round: RoundEntry | SceneRound): string {
  if ('action' in round && round.action) return round.action
  if ('actions' in round && round.actions && round.actions.length > 0) return round.actions.join(' ')
  return ''
}

function getInnerThought(round: RoundEntry | SceneRound): string {
  if ('inner_thought' in round) return round.inner_thought || ''
  return ''
}

function getEmotion(round: RoundEntry | SceneRound): string {
  if ('emotion' in round) return round.emotion || ''
  return ''
}

function getReactions(round: RoundEntry | SceneRound) {
  if ('reactions' in round) return round.reactions || []
  return []
}
</script>

<template>
  <div class="flex flex-col h-full bg-ink-panel rounded-lg border border-ink-edge">
    <div class="px-4 py-3 border-b border-ink-edge flex items-center justify-between">
      <h3 class="text-sm font-semibold text-parchment">Scene Feed</h3>
      <div class="flex items-center gap-2">
        <span
          class="w-2 h-2 rounded-full"
          :class="
            connected
              ? status.status === 'running'
                ? 'bg-green-500 animate-pulse'
                : 'bg-green-500'
              : 'bg-muted'
          "
        />
        <span class="text-xs text-muted">
          {{ status.status === 'running' ? `Round ${status.current_round}` : status.status }}
        </span>
      </div>
    </div>
    <div ref="feedContainer" class="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
      <div v-if="rounds.length === 0 && status.status === 'idle'" class="flex items-center justify-center h-full text-muted text-sm">
        No rounds yet. Start a scene to see the feed.
      </div>
      <div v-if="rounds.length === 0 && status.status === 'running'" class="flex items-center justify-center h-full text-muted text-sm">
        <div class="flex items-center gap-2">
          <div class="w-4 h-4 border-2 border-chop border-t-transparent rounded-full animate-spin"></div>
          <span>Scene initializing...</span>
        </div>
      </div>

      <div
        v-for="round in rounds"
        :key="round.round_number"
        class="bg-ink-elevated/50 rounded-lg p-4 space-y-3"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-xs font-medium text-chop bg-chop/10 px-2 py-0.5 rounded">
              Round {{ round.round_number }}
            </span>
            <span class="text-sm font-medium text-parchment">{{ getActorName(round) }}</span>
            <span v-if="getEmotion(round)" class="text-xs text-muted italic">
              ({{ getEmotion(round) }})
            </span>
          </div>
          <div class="flex items-center gap-1">
            <button
              v-if="getInnerThought(round)"
              @click="toggleInnerThought(round.round_number)"
              class="text-xs px-2 py-0.5 rounded transition-colors"
              :class="showInnerThoughts[round.round_number] ? 'bg-purple-900/30 text-purple-400' : 'text-muted hover:text-parchment-dim'"
              title="Inner thought"
            >
              💭
            </button>
            <button
              v-if="getReactions(round).length > 0"
              @click="toggleReactions(round.round_number)"
              class="text-xs px-2 py-0.5 rounded transition-colors"
              :class="showReactions[round.round_number] ? 'bg-blue-900/30 text-blue-400' : 'text-muted hover:text-parchment-dim'"
              title="Reactions"
            >
              👥 {{ getReactions(round).length }}
            </button>
          </div>
        </div>

        <p v-if="round.narration" class="text-sm text-parchment-dim italic leading-relaxed border-l-2 border-ink-edge pl-3">
          {{ round.narration }}
        </p>

        <p v-if="getAction(round)" class="text-sm text-parchment-dim leading-relaxed">
          <span class="text-muted">* </span>{{ getAction(round) }}
        </p>

        <p v-if="round.dialogue" class="text-sm text-parchment leading-relaxed">
          <span class="font-semibold text-chop">{{ getActorName(round) }}:</span>
          <span class="text-parchment">"{{ round.dialogue }}"</span>
        </p>

        <div v-if="showInnerThoughts[round.round_number] && getInnerThought(round)" class="bg-purple-900/10 border border-purple-900/30 rounded p-3">
          <div class="text-xs font-medium text-purple-400 mb-1">💭 Inner Thought</div>
          <p class="text-sm text-purple-200/80 italic leading-relaxed">
            "{{ getInnerThought(round) }}"
          </p>
        </div>

        <div v-if="showReactions[round.round_number] && getReactions(round).length > 0" class="space-y-2">
          <div class="text-xs font-medium text-blue-400">👥 Reactions</div>
          <div
            v-for="(reaction, idx) in getReactions(round)"
            :key="idx"
            class="bg-blue-900/10 border border-blue-900/30 rounded p-2 space-y-1"
          >
            <div class="flex items-center gap-2">
              <span class="text-xs font-medium text-blue-300">{{ reaction.reactor_name }}</span>
            </div>
            <p v-if="reaction.visible_reaction" class="text-xs text-parchment-dim">
              {{ reaction.visible_reaction }}
            </p>
            <p v-if="reaction.inner_thought" class="text-xs text-blue-200/70 italic">
              💭 "{{ reaction.inner_thought }}"
            </p>
          </div>
        </div>
      </div>

      <div v-if="status.status === 'completed' && resolutionText" class="bg-green-900/20 border border-green-800/50 rounded-lg p-4 mt-4">
        <div class="text-xs font-semibold text-green-400 mb-2">Scene Resolution</div>
        <p class="text-sm text-parchment leading-relaxed">{{ resolutionText }}</p>
      </div>
    </div>
  </div>
</template>
