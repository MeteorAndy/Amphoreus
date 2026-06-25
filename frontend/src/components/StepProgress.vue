<script setup lang="ts">
import { Check } from 'lucide-vue-next'

defineProps<{
  steps: string[]
  current: number
}>()
</script>

<template>
  <div class="flex items-center w-full">
    <template v-for="(step, idx) in steps" :key="idx">
      <div class="flex flex-col items-center flex-shrink-0">
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all"
          :class="{
            'bg-editor text-white': idx + 1 < current,
            'bg-chop text-white ring-2 ring-chop/40 ring-offset-2 ring-offset-ink-bg animate-pulse': idx + 1 === current,
            'bg-ink-elevated text-muted': idx + 1 > current,
          }"
        >
          <Check v-if="idx + 1 < current" :size="14" />
          <span v-else>{{ idx + 1 }}</span>
        </div>
        <span
          class="mt-1 text-xs whitespace-nowrap"
          :class="{
            'text-editor': idx + 1 < current,
            'text-chop font-medium': idx + 1 === current,
            'text-muted': idx + 1 > current,
          }"
        >
          {{ step }}
        </span>
      </div>
      <div
        v-if="idx < steps.length - 1"
        class="flex-1 h-px mx-2 mt-[-12px] transition-colors"
        :class="idx + 1 < current ? 'bg-editor' : 'bg-ink-edge'"
      />
    </template>
  </div>
</template>
