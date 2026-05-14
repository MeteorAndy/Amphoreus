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
  <div class="flex flex-col h-full bg-gray-900 rounded-lg border border-gray-800">
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
              ? 'bg-indigo-600 text-white'
              : msg.role === 'system'
                ? 'bg-gray-800 text-gray-400 italic'
                : 'bg-gray-800 text-gray-200'
          "
        >
          {{ msg.content }}
        </div>
      </div>
      <div v-if="loading" class="flex justify-start">
        <div class="bg-gray-800 rounded-lg px-4 py-2 text-sm text-gray-400">
          <span class="inline-flex gap-1">
            <span class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0s" />
            <span class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0.15s" />
            <span class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0.3s" />
          </span>
        </div>
      </div>
    </div>
    <div class="border-t border-gray-800 p-4">
      <form @submit.prevent="handleSend" class="flex gap-2">
        <input
          v-model="input"
          type="text"
          :placeholder="placeholder || 'Type a message...'"
          class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
          :disabled="loading"
        />
        <button
          type="submit"
          :disabled="loading || !input.trim()"
          class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  </div>
</template>
