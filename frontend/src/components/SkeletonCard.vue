<script setup lang="ts">
withDefaults(
  defineProps<{
    lines?: number
    showAvatar?: boolean
  }>(),
  {
    lines: 3,
    showAvatar: false,
  }
)

const lineWidths = ['w-full', 'w-4/5', 'w-3/5', 'w-2/3', 'w-1/2', 'w-3/4']
</script>

<template>
  <div class="card p-4 space-y-3 animate-pulse">
    <div v-if="showAvatar" class="flex items-center gap-3 mb-1">
      <div class="w-10 h-10 rounded-full bg-ink-edge shrink-0" />
      <div class="flex-1 space-y-2">
        <div class="h-3 rounded bg-ink-edge w-1/3" />
        <div class="h-2.5 rounded bg-ink-edge/60 w-1/4" />
      </div>
    </div>
    <div
      v-for="i in lines"
      :key="i"
      class="h-3 rounded bg-ink-edge/70"
      :class="lineWidths[(i - 1) % lineWidths.length]"
    />
  </div>
</template>
