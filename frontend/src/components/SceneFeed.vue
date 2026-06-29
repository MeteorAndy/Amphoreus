<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { Film, Brain, Users, CheckCircle2, Loader2 } from 'lucide-vue-next'
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
  <div class="flex flex-col h-full card overflow-hidden">
    <div class="px-4 py-3 border-b border-ink-edge flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-full bg-chop-soft flex items-center justify-center">
          <Film :size="15" class="text-chop-light" />
        </div>
        <h3 class="text-sm font-display font-semibold text-parchment">Scene Feed</h3>
      </div>
      <div class="flex items-center gap-2">
        <span
          class="w-2 h-2 rounded-full"
          :class="
            connected
              ? status.status === 'running'
                ? 'bg-editor animate-pulse'
                : 'bg-editor'
              : 'bg-muted'
          "
        />
        <span class="badge" :class="status.status === 'running' ? 'badge-editor' : 'badge-muted'">
          {{ status.status === 'running' ? `Round ${status.current_round}` : status.status }}
        </span>
      </div>
    </div>
    <div ref="feedContainer" class="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
      <div v-if="rounds.length === 0 && status.status === 'idle'" class="empty-state h-full">
        <p class="empty-state-text">No rounds yet. Start a scene to see the feed.</p>
      </div>
      <div v-if="rounds.length === 0 && status.status === 'running'" class="flex items-center justify-center h-full">
        <div class="flex items-center gap-2 text-muted">
          <Loader2 :size="16" class="animate-spin text-chop" />
          <span class="text-sm">Scene initializing...</span>
        </div>
      </div>

      <div
        v-for="round in rounds"
        :key="round.round_number"
        class="bg-ink-bg-deep/40 rounded-lg p-4 space-y-3 border border-ink-edge fade-in-up hover:border-ink-highlight transition-colors"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="badge badge-accent">
              Round {{ round.round_number }}
            </span>
            <span class="text-sm font-display font-semibold text-parchment">{{ getActorName(round) }}</span>
            <span v-if="getEmotion(round)" class="text-xs text-muted italic">
              ({{ getEmotion(round) }})
            </span>
          </div>
          <div class="flex items-center gap-1">
            <button
              v-if="getInnerThought(round)"
              @click="toggleInnerThought(round.round_number)"
              class="btn btn-ghost !p-1.5"
              :class="showInnerThoughts[round.round_number] ? 'text-gold' : 'text-muted'"
              title="Inner thought"
            >
              <Brain :size="13" />
            </button>
            <button
              v-if="getReactions(round).length > 0"
              @click="toggleReactions(round.round_number)"
              class="btn btn-ghost !p-1.5 gap-1"
              :class="showReactions[round.round_number] ? 'text-editor' : 'text-muted'"
              title="Reactions"
            >
              <Users :size="13" />
              <span class="text-[10px]">{{ getReactions(round).length }}</span>
            </button>
          </div>
        </div>

        <p v-if="round.narration" class="text-sm text-parchment-dim italic leading-relaxed manuscript-rail !py-0">
          {{ round.narration }}
        </p>

        <p v-if="getAction(round)" class="text-sm text-parchment-dim leading-relaxed">
          <span class="text-muted font-medium">* </span>{{ getAction(round) }}
        </p>

        <p v-if="round.dialogue" class="text-sm text-parchment leading-relaxed bg-ink-wash-light rounded-lg px-3 py-2 border-l-2 border-chop">
          <span class="font-semibold text-chop font-display">{{ getActorName(round) }}:</span>
          <span class="text-parchment"> "{{ round.dialogue }}"</span>
        </p>

        <div v-if="showInnerThoughts[round.round_number] && getInnerThought(round)" class="bg-gold-soft border border-gold/30 rounded-lg p-3">
          <div class="text-xs font-display font-semibold text-gold-light mb-1.5 flex items-center gap-1.5">
            <Brain :size="12" />
            Inner Thought
          </div>
          <p class="text-sm text-gold-light/90 italic leading-relaxed">
            "{{ getInnerThought(round) }}"
          </p>
        </div>

        <div v-if="showReactions[round.round_number] && getReactions(round).length > 0" class="space-y-2">
          <div class="text-xs font-display font-semibold text-editor flex items-center gap-1.5">
            <Users :size="12" />
            Reactions
          </div>
          <div
            v-for="(reaction, idx) in getReactions(round)"
            :key="idx"
            class="bg-editor-soft border border-editor/30 rounded-lg p-2.5 space-y-1"
          >
            <div class="flex items-center gap-2">
              <span class="text-xs font-display font-semibold text-editor">{{ reaction.reactor_name }}</span>
            </div>
            <p v-if="reaction.visible_reaction" class="text-xs text-parchment-dim leading-relaxed">
              {{ reaction.visible_reaction }}
            </p>
            <p v-if="reaction.inner_thought" class="text-xs text-gold-light/80 italic flex items-start gap-1">
              <Brain :size="10" class="mt-0.5 shrink-0" />
              "{{ reaction.inner_thought }}"
            </p>
          </div>
        </div>
      </div>

      <div v-if="status.status === 'completed' && resolutionText" class="bg-editor-soft border border-editor/40 rounded-lg p-4 mt-4">
        <div class="text-xs font-display font-semibold text-editor mb-2 flex items-center gap-1.5">
          <CheckCircle2 :size="13" />
          Scene Resolution
        </div>
        <p class="text-sm text-parchment leading-relaxed">{{ resolutionText }}</p>
      </div>
    </div>
  </div>
</template>
