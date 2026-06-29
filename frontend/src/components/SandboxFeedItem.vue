<script setup lang="ts">
import { User, Brain, Globe, Zap, CheckCircle } from 'lucide-vue-next'
import { useI18n } from '../i18n'
import type { SandboxEvent } from '../types/api'

const { t } = useI18n()

defineProps<{ event: SandboxEvent }>()
</script>

<template>
  <div v-if="event.type === 'round_end'" class="flex items-center gap-3 my-3">
    <div class="flex-1 h-px bg-gradient-to-r from-transparent via-ink-edge to-transparent" />
    <span class="text-xs text-muted px-3 font-mono tracking-wider bg-ink-panel py-1 rounded-full border border-ink-edge">
      {{ t('sandbox.round_n', { n: event.round ?? 0 }) }}
    </span>
    <div class="flex-1 h-px bg-gradient-to-r from-transparent via-ink-edge to-transparent" />
  </div>

  <div v-else-if="event.type === 'stopped'" class="flex items-center justify-center gap-2 py-2.5 text-sm text-editor fade-in">
    <CheckCircle :size="14" class="text-editor" />
    <span class="text-muted">{{ t('sandbox.stopped_after', { n: event.rounds ?? 0 }) }}</span>
  </div>

  <div v-else-if="event.type === 'connected'" class="text-xs text-muted italic px-2 py-1 fade-in">
    {{ t('sandbox.connected') }}
  </div>

  <div v-else-if="event.type === 'action'" class="flex gap-2.5 py-2 px-2 rounded-lg hover:bg-ink-wash-light transition-colors group fade-in-up">
    <span class="w-7 h-7 rounded-full bg-chop-soft flex items-center justify-center flex-shrink-0 mt-0.5 border border-chop-border">
      <User :size="12" class="text-chop-light" />
    </span>
    <div class="text-sm text-parchment leading-relaxed flex-1">
      <span class="font-semibold text-chop font-display">{{ event.character }}</span>
      <span class="text-muted"> {{ t('sandbox.action_says') }} </span>
      {{ event.content }}
    </div>
  </div>

  <div v-else-if="event.type === 'thought'" class="flex gap-2.5 py-2 px-2 rounded-lg hover:bg-ink-wash-light transition-colors group fade-in-up">
    <span class="w-7 h-7 rounded-full bg-gold-soft flex items-center justify-center flex-shrink-0 mt-0.5 border border-gold/30">
      <Brain :size="12" class="text-gold-light" />
    </span>
    <div class="text-sm text-parchment-dim italic leading-relaxed flex-1">
      <span class="font-semibold not-italic text-parchment font-display">{{ event.character }}</span>
      {{ t('sandbox.thought_thinks') }}
      <span class="text-gold-light/80">{{ event.content }}</span>
    </div>
  </div>

  <div v-else-if="event.type === 'environment'" class="flex gap-2.5 py-2 px-2 rounded-lg hover:bg-ink-wash-light transition-colors group fade-in-up">
    <span class="w-7 h-7 rounded-full bg-editor-soft flex items-center justify-center flex-shrink-0 mt-0.5 border border-editor/30">
      <Globe :size="12" class="text-editor" />
    </span>
    <div class="text-sm text-parchment-dim leading-relaxed flex-1">{{ event.content }}</div>
  </div>

  <div v-else-if="event.type === 'injected'" class="flex gap-2.5 py-2 px-2 rounded-lg bg-gold-soft/30 border border-gold/20 fade-in-up">
    <span class="w-7 h-7 rounded-full bg-gold-soft flex items-center justify-center flex-shrink-0 mt-0.5 border border-gold/30">
      <Zap :size="12" class="text-gold-light" />
    </span>
    <div class="text-sm text-gold-light leading-relaxed flex-1 font-medium">{{ event.event ?? event.content }}</div>
  </div>
</template>
