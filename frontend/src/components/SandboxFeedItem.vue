<script setup lang="ts">
import type { SandboxEvent } from '../types/api'

defineProps<{ event: SandboxEvent }>()
</script>

<template>
  <div v-if="event.type === 'round_end'" class="flex items-center gap-2 my-2">
    <div class="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
    <span class="text-xs text-gray-400 dark:text-gray-500 px-2">Round {{ event.round }}</span>
    <div class="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
  </div>

  <div v-else-if="event.type === 'stopped'" class="text-center py-2 text-sm text-gray-500 dark:text-gray-400">
    ✅ Stopped after {{ event.rounds }} rounds
  </div>

  <div v-else-if="event.type === 'connected'" class="text-xs text-gray-400 dark:text-gray-500 italic">
    Connected
  </div>

  <div v-else-if="event.type === 'action'" class="flex gap-2 py-1">
    <span class="text-base leading-5 mt-0.5">🧑</span>
    <div class="text-sm text-gray-800 dark:text-gray-200">
      <span class="font-semibold">{{ event.character }}</span>: {{ event.content }}
    </div>
  </div>

  <div v-else-if="event.type === 'thought'" class="flex gap-2 py-1">
    <span class="text-base leading-5 mt-0.5">💭</span>
    <div class="text-sm text-gray-500 dark:text-gray-400 italic">
      <span class="font-semibold not-italic text-gray-600 dark:text-gray-300">{{ event.character }}</span> thinks: {{ event.content }}
    </div>
  </div>

  <div v-else-if="event.type === 'environment'" class="flex gap-2 py-1">
    <span class="text-base leading-5 mt-0.5">🌍</span>
    <div class="text-sm text-gray-600 dark:text-gray-300">{{ event.content }}</div>
  </div>

  <div v-else-if="event.type === 'injected'" class="flex gap-2 py-1">
    <span class="text-base leading-5 mt-0.5">⚡</span>
    <div class="text-sm text-yellow-700 dark:text-yellow-400">{{ event.event ?? event.content }}</div>
  </div>
</template>
