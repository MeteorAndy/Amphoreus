<script setup lang="ts">
import { computed } from 'vue'
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
  <div class="flex flex-col h-full bg-ink-panel rounded-lg border border-ink-edge">
    <div class="px-4 py-3 border-b border-ink-edge">
      <h3 class="text-sm font-semibold text-parchment">Environment</h3>
    </div>
    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <div v-if="!environmentState && !latestEnvironment && rounds.length === 0" class="text-muted text-sm">
        Environment will appear when the scene starts.
      </div>

      <div v-if="environmentState" class="space-y-2">
        <div class="text-xs font-medium text-amber-400">Current Setting</div>
        <p class="text-sm text-parchment-dim leading-relaxed">
          {{ environmentState }}
        </p>
      </div>

      <div v-if="latestEnvironment" class="space-y-3">
        <div v-if="latestEnvironment.atmosphere" class="space-y-1">
          <div class="text-xs font-medium text-amber-400">Atmosphere</div>
          <p class="text-sm text-parchment-dim">{{ latestEnvironment.atmosphere }}</p>
        </div>

        <div v-if="latestEnvironment.background_activity" class="space-y-1">
          <div class="text-xs font-medium text-amber-400">Background Activity</div>
          <p class="text-sm text-parchment-dim italic">{{ latestEnvironment.background_activity }}</p>
        </div>
      </div>

      <div v-if="environmentChanges.length > 0" class="space-y-2">
        <div class="text-xs font-medium text-parchment">Environment Changes</div>
        <div class="space-y-2">
          <div
            v-for="change in environmentChanges"
            :key="change.round"
            class="bg-ink-elevated/50 rounded p-2"
          >
            <div class="text-xs text-chop mb-1">Round {{ change.round }}</div>
            <ul class="space-y-1">
              <li
                v-for="(c, idx) in change.changes"
                :key="idx"
                class="text-xs text-parchment-dim flex items-start gap-1"
              >
                <span class="text-amber-500">•</span>
                <span>{{ c }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
