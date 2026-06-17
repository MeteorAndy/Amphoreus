<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import type { ChatMessage } from '../types/api'

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
  <div class="flex flex-col h-full bg-ink-panel rounded-lg border border-ink-edge">
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
    >
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="flex"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[80%] rounded-lg px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap"
          :class="
            msg.role === 'user'
              ? 'bg-chop text-white'
              : msg.role === 'system'
                ? 'bg-ink-elevated text-parchment-dim italic'
                : 'bg-ink-elevated text-parchment'
          "
        >
          {{ msg.content }}
        </div>
      </div>
      <div v-if="loading" class="flex justify-start">
        <div class="bg-ink-elevated rounded-lg px-4 py-2 text-sm text-parchment-dim">
          <span class="inline-flex gap-1">
            <span class="w-2 h-2 bg-muted rounded-full animate-bounce" style="animation-delay: 0s" />
            <span class="w-2 h-2 bg-muted rounded-full animate-bounce" style="animation-delay: 0.15s" />
            <span class="w-2 h-2 bg-muted rounded-full animate-bounce" style="animation-delay: 0.3s" />
          </span>
        </div>
      </div>
    </div>
    <div class="border-t border-ink-edge p-4">
      <form @submit.prevent="handleSend" class="flex gap-2">
        <input
          v-model="input"
          type="text"
          :placeholder="placeholder || 'Type a message...'"
          class="flex-1 bg-ink-elevated border border-ink-edge rounded-lg px-4 py-2 text-sm text-parchment placeholder-muted focus:outline-none focus:border-chop transition-colors"
          :disabled="loading"
        />
        <button
          type="submit"
          :disabled="loading || !input.trim()"
          class="px-4 py-2 bg-chop text-white rounded-lg text-sm font-medium hover:bg-chop disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  </div>
</template>
