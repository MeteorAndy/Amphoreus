<script setup lang="ts">
import { computed } from 'vue'
import { TreePine, Cloud, Wind, History } from 'lucide-vue-next'
import type { RoundEntry } from '../types/api'

interface SceneRound {
  round_number: number
  actor_id?: string
  actor_name?: string
  character?: string
  environment?: {
    atmosphere?: string
    changes?: string[]
    background_activity?: string
  }
}

const props = defineProps<{
  environmentState: string
  rounds: (RoundEntry | SceneRound)[]
}>()

const latestEnvironment = computed(() => {
  for (let i = props.rounds.length - 1; i >= 0; i--) {
    const round = props.rounds[i] as SceneRound
    if (round.environment) {
      return round.environment
    }
  }
  return null
})

const environmentChanges = computed(() => {
  const changes: { round: number; changes: string[] }[] = []
  for (const round of props.rounds) {
    const r = round as SceneRound
    if (r.environment?.changes && r.environment.changes.length > 0) {
      changes.push({ round: r.round_number, changes: r.environment.changes })
    }
  }
  return changes
})
</script>

<template>
  <div class="flex flex-col h-full card overflow-hidden">
    <div class="px-4 py-3 border-b border-ink-edge flex items-center gap-2 shrink-0">
      <div class="w-8 h-8 rounded-full bg-gold-soft flex items-center justify-center">
        <TreePine :size="15" class="text-gold-light" />
      </div>
      <h3 class="text-sm font-display font-semibold text-parchment">Environment</h3>
    </div>
    <div class="flex-1 overflow-y-auto p-4 space-y-4 stagger-children">
      <div v-if="!environmentState && !latestEnvironment && rounds.length === 0" class="empty-state py-8">
        <p class="empty-state-text">Environment will appear when the scene starts.</p>
      </div>

      <div v-if="environmentState" class="space-y-2 bg-ink-bg-deep/40 rounded-lg p-3.5 border border-ink-edge">
        <div class="text-xs font-display font-semibold text-gold-light flex items-center gap-1.5 tracking-wide">
          <Cloud :size="12" />
          Current Setting
        </div>
        <p class="text-sm text-parchment-dim leading-relaxed">
          {{ environmentState }}
        </p>
      </div>

      <div v-if="latestEnvironment" class="space-y-3">
        <div v-if="latestEnvironment.atmosphere" class="space-y-1.5 bg-ink-bg-deep/40 rounded-lg p-3.5 border border-ink-edge">
          <div class="text-xs font-display font-semibold text-gold-light flex items-center gap-1.5 tracking-wide">
            <Wind :size="12" />
            Atmosphere
          </div>
          <p class="text-sm text-parchment-dim leading-relaxed">{{ latestEnvironment.atmosphere }}</p>
        </div>

        <div v-if="latestEnvironment.background_activity" class="space-y-1.5 bg-ink-bg-deep/40 rounded-lg p-3.5 border border-ink-edge">
          <div class="text-xs font-display font-semibold text-gold-light flex items-center gap-1.5 tracking-wide">
            <Wind :size="12" />
            Background Activity
          </div>
          <p class="text-sm text-parchment-dim italic leading-relaxed">{{ latestEnvironment.background_activity }}</p>
        </div>
      </div>

      <div v-if="environmentChanges.length > 0" class="space-y-2.5">
        <div class="text-xs font-display font-semibold text-parchment flex items-center gap-1.5 tracking-wide">
          <History :size="12" class="text-muted" />
          Environment Changes
        </div>
        <div class="space-y-2">
          <div
            v-for="change in environmentChanges"
            :key="change.round"
            class="bg-ink-bg-deep/40 rounded-lg p-3 border border-ink-edge hover:border-ink-highlight transition-colors"
          >
            <div class="text-xs font-display font-semibold text-chop-light mb-1.5 flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-chop"></span>
              Round {{ change.round }}
            </div>
            <ul class="space-y-1">
              <li
                v-for="(c, idx) in change.changes"
                :key="idx"
                class="text-xs text-parchment-dim flex items-start gap-1.5 leading-relaxed"
              >
                <span class="text-gold-light mt-1">•</span>
                <span>{{ c }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
