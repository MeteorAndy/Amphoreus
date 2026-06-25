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
  <div class="flex flex-col h-full card">
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-4 space-y-3 scroll-smooth"
    >
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="flex"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[80%] rounded-lg px-3.5 py-2 text-sm leading-relaxed whitespace-pre-wrap"
          :class="
            msg.role === 'user'
              ? 'bg-chop text-white'
              : msg.role === 'system'
                ? 'bg-ink-elevated text-muted italic'
                : 'bg-ink-elevated text-parchment'
          "
        >
          {{ msg.content }}
        </div>
      </div>
      <div v-if="loading" class="flex justify-start">
        <div class="bg-ink-elevated rounded-lg px-3.5 py-2 text-sm text-muted">
          <span class="inline-flex gap-1">
            <span class="w-1.5 h-1.5 bg-muted rounded-full animate-bounce" style="animation-delay: 0s" />
            <span class="w-1.5 h-1.5 bg-muted rounded-full animate-bounce" style="animation-delay: 0.15s" />
            <span class="w-1.5 h-1.5 bg-muted rounded-full animate-bounce" style="animation-delay: 0.3s" />
          </span>
        </div>
      </div>
    </div>
    <div class="border-t border-ink-edge p-3">
      <form @submit.prevent="handleSend" class="flex gap-2">
        <input
          v-model="input"
          type="text"
          :placeholder="placeholder || t('chat.placeholder')"
          class="input flex-1 py-2"
          :disabled="loading"
        />
        <button
          type="submit"
          :disabled="loading || !input.trim()"
          class="btn btn-primary"
        >
          <Send :size="14" />
          {{ t('chat.send') }}
        </button>
      </form>
    </div>
  </div>
</template>
