<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { Send } from 'lucide-vue-next'
import { useI18n } from '../i18n'
import type { ChatMessage } from '../types/api'

const { t } = useI18n()

const props = defineProps<{
  messages: ChatMessage[]
  loading: boolean
  placeholder?: string
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const input = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

function handleSend(): void {
  const text = input.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  input.value = ''
}

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  },
)
</script>

<template>
  <div class="flex flex-col h-full card overflow-hidden">
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-5 space-y-4 scroll-smooth"
    >
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="flex message-bubble"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[82%] px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap"
          :class="
            msg.role === 'user'
              ? 'bg-gradient-chop text-white rounded-tl-2xl rounded-bl-2xl rounded-tr-md rounded-br-md shadow-md'
              : msg.role === 'system'
                ? 'bg-transparent text-gold italic text-xs px-2 py-1 opacity-80 tracking-wide'
                : 'bg-ink-elevated text-parchment rounded-tr-2xl rounded-br-2xl rounded-tl-md rounded-bl-md shadow-sm border border-ink-edge/50'
          "
        >
          {{ msg.content }}
        </div>
      </div>
      <div v-if="loading" class="flex justify-start message-bubble">
        <div class="bg-ink-elevated rounded-tr-2xl rounded-br-2xl rounded-tl-md rounded-bl-md px-4 py-3 shadow-sm border border-ink-edge/50">
          <span class="inline-flex gap-1.5 items-center">
            <span class="w-1.5 h-1.5 bg-muted rounded-full" style="animation: inkDrip 1.2s infinite var(--ease-editorial); animation-delay: 0s" />
            <span class="w-1.5 h-1.5 bg-muted rounded-full" style="animation: inkDrip 1.2s infinite var(--ease-editorial); animation-delay: 0.2s" />
            <span class="w-1.5 h-1.5 bg-muted rounded-full" style="animation: inkDrip 1.2s infinite var(--ease-editorial); animation-delay: 0.4s" />
          </span>
        </div>
      </div>
    </div>
    <div class="border-t border-ink-edge/70 p-4 bg-ink-bg-deep/30">
      <form @submit.prevent="handleSend" class="flex gap-2.5">
        <input
          v-model="input"
          type="text"
          :placeholder="placeholder || t('chat.placeholder')"
          class="input flex-1 py-2.5"
          :disabled="loading"
        />
        <button
          type="submit"
          :disabled="loading || !input.trim()"
          class="btn btn-primary px-4"
        >
          <Send :size="16" />
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.bg-gradient-chop {
  background: var(--gradient-chop-seal);
  box-shadow: 0 2px 8px rgba(200, 66, 59, 0.25),
              inset 0 1px 0 rgba(255,255,255,0.15);
}

.message-bubble {
  animation: fadeInUp 0.3s var(--ease-ink) both;
}

.message-bubble:nth-child(1) { animation-delay: 0ms; }
.message-bubble:nth-child(2) { animation-delay: 50ms; }
.message-bubble:nth-child(3) { animation-delay: 100ms; }
.message-bubble:nth-child(4) { animation-delay: 150ms; }
.message-bubble:nth-child(5) { animation-delay: 200ms; }

html[data-theme="paper"] .bg-gradient-chop {
  box-shadow: 0 2px 6px rgba(168, 54, 47, 0.15),
              inset 0 1px 0 rgba(255,255,255,0.2);
}
</style>
