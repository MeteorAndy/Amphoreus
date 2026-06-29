<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { Send, Eraser } from 'lucide-vue-next'
import type { AssistantAction, AssistantSuggestion } from '../composables/useAssistant'

const props = withDefaults(defineProps<{
  messages: Array<{
    id?: string
    role: 'assistant' | 'user' | 'system' | 'action'
    content: string
    actions?: AssistantAction[]
    timestamp?: number
  }>
  loading: boolean
  placeholder?: string
  embedded?: boolean
  suggestions?: AssistantSuggestion[]
  showClear?: boolean
  contextTitle?: string
}>(), {
  suggestions: () => [],
  showClear: true,
})

const emit = defineEmits<{
  send: [text: string]
  clear: []
}>()

const input = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

function handleSend(): void {
  const text = input.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  input.value = ''
}

function handleSuggestionClick(suggestion: AssistantSuggestion): void {
  suggestion.action()
}

function handleActionClick(action: AssistantAction): void {
  action.handler()
}

function handleClear(): void {
  emit('clear')
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
  <div
    class="hsr-chat flex flex-col h-full overflow-hidden"
    :class="embedded ? 'hsr-chat--embedded' : 'glass-card'"
  >
    <div
      ref="messagesContainer"
      class="hsr-chat__messages flex-1 overflow-y-auto p-4 space-y-3 scroll-smooth"
    >
      <div
        v-for="(msg, idx) in messages"
        :key="msg.id ?? idx"
        class="flex hsr-message"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="hsr-bubble max-w-[88%] px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap"
          :class="{
            'hsr-bubble--user': msg.role === 'user',
            'hsr-bubble--system': msg.role === 'system',
            'hsr-bubble--action': msg.role === 'action',
            'hsr-bubble--assistant': msg.role === 'assistant',
          }"
        >
          {{ msg.content }}
          <div
            v-if="msg.actions && msg.actions.length > 0"
            class="flex flex-wrap gap-2 mt-3 pt-2.5 hsr-bubble__actions"
          >
            <button
              v-for="action in msg.actions"
              :key="action.id"
              @click="handleActionClick(action)"
              class="hsr-action-chip"
              :class="{ 'hsr-action-chip--primary': action.primary }"
            >
              {{ action.label }}
            </button>
          </div>
        </div>
      </div>
      <div v-if="loading" class="flex justify-start hsr-message">
        <div class="hsr-bubble hsr-bubble--assistant hsr-bubble--typing px-4 py-3">
          <span class="inline-flex gap-1.5 items-center">
            <span class="typing-dot" />
            <span class="typing-dot" />
            <span class="typing-dot" />
          </span>
        </div>
      </div>
    </div>

    <div
      v-if="suggestions && suggestions.length > 0"
      class="hsr-chat__suggestions px-4 py-2.5"
    >
      <div class="flex flex-wrap gap-2">
        <button
          v-for="(suggestion, sIdx) in suggestions"
          :key="sIdx"
          @click="handleSuggestionClick(suggestion)"
          class="badge-hsr badge-gold hsr-suggestion-badge cursor-pointer transition-all duration-200"
        >
          {{ suggestion.text }}
        </button>
      </div>
    </div>

    <div class="hsr-chat__input-area p-3" :class="embedded ? 'hsr-chat__input-area--embedded' : ''">
      <form @submit.prevent="handleSend" class="flex gap-2 items-center">
        <button
          v-if="showClear"
          type="button"
          @click="handleClear"
          class="btn-hsr-ghost px-2.5"
          title="清空对话"
        >
          <Eraser :size="16" />
        </button>
        <input
          v-model="input"
          type="text"
          :placeholder="placeholder || '有什么可以帮助你的？'"
          class="hsr-chat__input flex-1 text-sm"
          :disabled="loading"
        />
        <button
          type="submit"
          :disabled="loading || !input.trim()"
          class="btn-hsr-primary px-4"
        >
          <Send :size="16" />
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.hsr-chat {
  background: rgba(15, 18, 40, 0.7);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(212, 168, 67, 0.15);
  border-radius: 12px;
  position: relative;
}

.hsr-chat--embedded {
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border: none;
  border-radius: 0;
}

.hsr-chat__messages {
  scrollbar-width: thin;
  scrollbar-color: rgba(212, 168, 67, 0.2) transparent;
}

.hsr-message {
  animation: hsrFadeInUp 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.hsr-message:nth-child(1) { animation-delay: 0ms; }
.hsr-message:nth-child(2) { animation-delay: 40ms; }
.hsr-message:nth-child(3) { animation-delay: 80ms; }
.hsr-message:nth-child(4) { animation-delay: 120ms; }
.hsr-message:nth-child(5) { animation-delay: 160ms; }

.hsr-bubble {
  position: relative;
  word-break: break-word;
}

.hsr-bubble--user {
  background: linear-gradient(135deg, rgba(212, 168, 67, 0.25), rgba(240, 208, 120, 0.18));
  color: #f5e6b8;
  border: 1px solid rgba(212, 168, 67, 0.35);
  border-radius: 16px 4px 16px 16px;
  box-shadow:
    0 2px 12px rgba(212, 168, 67, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.hsr-bubble--assistant {
  background: rgba(20, 24, 50, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: #e8e6f0;
  border: 1px solid rgba(212, 168, 67, 0.12);
  border-radius: 4px 16px 16px 16px;
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.hsr-bubble--system {
  background: transparent;
  color: rgba(212, 168, 67, 0.7);
  font-style: italic;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  opacity: 0.8;
  letter-spacing: 0.06em;
  text-align: center;
  width: 100%;
  text-transform: uppercase;
}

.hsr-bubble--action {
  background: rgba(74, 127, 255, 0.08);
  color: #93b4ff;
  border: 1px solid rgba(74, 127, 255, 0.2);
  border-radius: 10px;
  font-size: 0.75rem;
  box-shadow: 0 1px 6px rgba(74, 127, 255, 0.08);
}

.hsr-bubble--typing {
  min-width: 56px;
}

.hsr-bubble__actions {
  border-top: 1px solid rgba(212, 168, 67, 0.1);
}

.hsr-action-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  font-size: 0.6875rem;
  font-weight: 500;
  border-radius: 6px;
  background: rgba(212, 168, 67, 0.06);
  color: #a09cb8;
  border: 1px solid rgba(100, 95, 128, 0.25);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
  letter-spacing: 0.02em;
}

.hsr-action-chip:hover {
  background: rgba(30, 35, 70, 0.6);
  color: #e8e6f0;
  border-color: rgba(212, 168, 67, 0.3);
  transform: translateY(-1px);
}

.hsr-action-chip--primary {
  background: rgba(212, 168, 67, 0.12);
  color: #d4a843;
  border-color: rgba(212, 168, 67, 0.3);
}

.hsr-action-chip--primary:hover {
  background: rgba(212, 168, 67, 0.2);
  color: #f0d078;
  border-color: rgba(212, 168, 67, 0.5);
  box-shadow: 0 0 12px rgba(212, 168, 67, 0.2);
}

.hsr-chat__suggestions {
  border-top: 1px solid rgba(212, 168, 67, 0.1);
  background: rgba(11, 13, 26, 0.4);
  max-height: 120px;
  overflow-y: auto;
}

.hsr-suggestion-badge {
  padding: 0.35rem 0.75rem;
  font-size: 0.75rem;
}

.hsr-suggestion-badge:hover {
  background: rgba(212, 168, 67, 0.2) !important;
  border-color: rgba(212, 168, 67, 0.5) !important;
  color: #f0d078 !important;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(212, 168, 67, 0.15);
}

.hsr-chat__input-area {
  background: rgba(11, 13, 26, 0.5);
  border-top: 1px solid rgba(212, 168, 67, 0.12);
}

.hsr-chat__input-area--embedded {
  border-top: 1px solid rgba(212, 168, 67, 0.15);
}

.hsr-chat__input {
  padding: 9px 14px;
  border-radius: 8px;
  background: rgba(11, 13, 26, 0.85);
  border: 1px solid rgba(100, 95, 128, 0.25);
  color: #e8e6f0;
  font-size: 0.875rem;
  line-height: 1.5;
  outline: none;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.hsr-chat__input::placeholder {
  color: #6b6780;
}

.hsr-chat__input:focus {
  border-color: rgba(212, 168, 67, 0.55);
  box-shadow: 0 0 0 2px rgba(212, 168, 67, 0.12), 0 0 16px rgba(212, 168, 67, 0.08);
  background: rgba(11, 13, 26, 0.95);
}

.hsr-chat__input:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@keyframes hsrFadeInUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
