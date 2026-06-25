<script setup lang="ts">
import { User, Brain, Globe, Zap, CheckCircle } from 'lucide-vue-next'
import { useI18n } from '../i18n'
import type { SandboxEvent } from '../types/api'

const { t } = useI18n()

defineProps<{ event: SandboxEvent }>()
</script>

<template>
  <div v-if="event.type === 'round_end'" class="flex items-center gap-2 my-2">
    <div class="flex-1 h-px bg-ink-edge" />
    <span class="text-xs text-muted px-2 font-mono">{{ t('sandbox.round_n', { n: event.round ?? 0 }) }}</span>
    <div class="flex-1 h-px bg-ink-edge" />
  </div>

  <div v-else-if="event.type === 'stopped'" class="text-center py-2 text-sm text-muted flex items-center justify-center gap-1.5">
    <CheckCircle :size="13" class="text-editor" />
    {{ t('sandbox.stopped_after', { n: event.rounds ?? 0 }) }}
  </div>

  <div v-else-if="event.type === 'connected'" class="text-xs text-muted italic px-1">
    {{ t('sandbox.connected') }}
  </div>

  <div v-else-if="event.type === 'action'" class="flex gap-2 py-1">
    <span class="w-5 h-5 rounded-full bg-ink-elevated flex items-center justify-center flex-shrink-0 mt-0.5">
      <User :size="11" class="text-parchment-dim" />
    </span>
    <div class="text-sm text-parchment leading-relaxed">
      <span class="font-semibold text-chop">{{ event.character }}</span><span class="text-muted"> {{ t('sandbox.action_says') }}</span> {{ event.content }}
    </div>
  </div>

  <div v-else-if="event.type === 'thought'" class="flex gap-2 py-1">
    <span class="w-5 h-5 rounded-full bg-ink-elevated flex items-center justify-center flex-shrink-0 mt-0.5">
      <Brain :size="11" class="text-gold" />
    </span>
    <div class="text-sm text-muted italic leading-relaxed">
      <span class="font-semibold not-italic text-parchment-dim">{{ event.character }}</span> {{ t('sandbox.thought_thinks') }} {{ event.content }}
    </div>
  </div>

  <div v-else-if="event.type === 'environment'" class="flex gap-2 py-1">
    <span class="w-5 h-5 rounded-full bg-ink-elevated flex items-center justify-center flex-shrink-0 mt-0.5">
      <Globe :size="11" class="text-editor" />
    </span>
    <div class="text-sm text-parchment-dim leading-relaxed">{{ event.content }}</div>
  </div>

  <div v-else-if="event.type === 'injected'" class="flex gap-2 py-1">
    <span class="w-5 h-5 rounded-full bg-gold/20 flex items-center justify-center flex-shrink-0 mt-0.5">
      <Zap :size="11" class="text-gold" />
    </span>
    <div class="text-sm text-gold leading-relaxed">{{ event.event ?? event.content }}</div>
  </div>
</template>
