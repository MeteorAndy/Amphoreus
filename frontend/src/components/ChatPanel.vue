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
  <div class="flex flex-col h-full overflow-hidden" :class="embedded ? 'chat-embedded' : 'card'">
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-4 space-y-3 scroll-smooth"
    >
      <div
        v-for="(msg, idx) in messages"
        :key="msg.id ?? idx"
        class="flex message-bubble"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[88%] px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap"
          :class="
            msg.role === 'user'
              ? 'bg-gradient-chop text-white rounded-tl-2xl rounded-bl-2xl rounded-tr-md rounded-br-md shadow-md'
              : msg.role === 'system'
                ? 'bg-transparent text-gold italic text-xs px-2 py-1 opacity-80 tracking-wide text-center w-full'
                : msg.role === 'action'
                  ? 'bg-chop-soft text-chop rounded-lg border border-chop-border/50 px-3 py-2 text-xs'
                  : 'bg-ink-elevated text-parchment rounded-tr-2xl rounded-br-2xl rounded-tl-md rounded-bl-md shadow-sm border border-ink-edge/50'
          "
        >
          {{ msg.content }}
          <div v-if="msg.actions && msg.actions.length > 0" class="flex flex-wrap gap-1.5 mt-2.5 pt-2 border-t border-ink-edge/30">
            <button
              v-for="action in msg.actions"
              :key="action.id"
              @click="handleActionClick(action)"
              class="action-chip"
              :class="{ 'action-chip--primary': action.primary }"
            >
              {{ action.label }}
            </button>
          </div>
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

    <div v-if="suggestions && suggestions.length > 0" class="suggestions-area px-3 py-2 border-t border-ink-edge/50">
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="(suggestion, sIdx) in suggestions"
          :key="sIdx"
          @click="handleSuggestionClick(suggestion)"
          class="suggestion-chip"
        >
          {{ suggestion.text }}
        </button>
      </div>
    </div>

    <div class="p-3 bg-ink-bg-deep/30" :class="embedded ? 'chat-embedded-input' : 'border-t border-ink-edge/70'">
      <form @submit.prevent="handleSend" class="flex gap-2">
        <button
          v-if="showClear"
          type="button"
          @click="handleClear"
          class="btn btn-ghost px-2.5"
          title="清空对话"
        >
          <Eraser :size="15" />
        </button>
        <input
          v-model="input"
          type="text"
          :placeholder="placeholder || '有什么可以帮助你的？'"
          class="input flex-1 py-2 text-sm"
          :disabled="loading"
        />
        <button
          type="submit"
          :disabled="loading || !input.trim()"
          class="btn btn-primary px-3.5"
        >
          <Send :size="15" />
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

.chat-embedded {
  background: transparent;
}

.chat-embedded-input {
  border-top: 1px solid var(--color-ink-edge);
}

html[data-theme="paper"] .chat-embedded-input {
  border-top-color: var(--color-paper-edge);
}

.message-bubble {
  animation: fadeInUp 0.3s var(--ease-ink) both;
}

.message-bubble:nth-child(1) { animation-delay: 0ms; }
.message-bubble:nth-child(2) { animation-delay: 50ms; }
.message-bubble:nth-child(3) { animation-delay: 100ms; }
.message-bubble:nth-child(4) { animation-delay: 150ms; }
.message-bubble:nth-child(5) { animation-delay: 200ms; }

.action-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  font-size: 11px;
  font-weight: 500;
  border-radius: var(--radius-scroll);
  background: rgba(237, 228, 211, 0.06);
  color: var(--color-parchment-dim);
  border: 1px solid var(--color-ink-edge);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-editorial);
}

.action-chip:hover {
  background: var(--color-ink-wash-light);
  color: var(--color-parchment);
  border-color: var(--color-muted-soft);
  transform: translateY(-1px);
}

.action-chip--primary {
  background: var(--color-chop-soft);
  color: var(--color-chop-light);
  border-color: var(--color-chop-border);
}

.action-chip--primary:hover {
  background: rgba(200, 66, 59, 0.2);
  color: var(--color-chop);
  border-color: var(--color-chop);
  box-shadow: 0 0 8px var(--color-chop-glow);
}

.suggestions-area {
  background: rgba(20, 17, 14, 0.3);
  max-height: 120px;
  overflow-y: auto;
}

.suggestion-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 500;
  border-radius: var(--radius-scroll);
  background: linear-gradient(180deg, var(--color-ink-elevated), var(--color-ink-panel));
  color: var(--color-parchment-dim);
  border: 1px solid var(--color-ink-edge);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-editorial);
  white-space: nowrap;
}

.suggestion-chip:hover {
  background: linear-gradient(180deg, var(--color-ink-highlight), var(--color-ink-elevated));
  color: var(--color-parchment);
  border-color: var(--color-chop-border);
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
}

html[data-theme="paper"] .bg-gradient-chop {
  box-shadow: 0 2px 6px rgba(168, 54, 47, 0.15),
              inset 0 1px 0 rgba(255,255,255,0.2);
}

html[data-theme="paper"] .action-chip {
  background: rgba(26, 21, 16, 0.04);
  border-color: var(--color-paper-edge);
  color: var(--color-ink-on-paper);
}

html[data-theme="paper"] .action-chip:hover {
  background: rgba(26, 21, 16, 0.08);
  border-color: var(--color-paper-edge-soft);
}

html[data-theme="paper"] .action-chip--primary {
  background: var(--color-chop-soft);
  color: var(--color-chop);
  border-color: var(--color-chop-border);
}

html[data-theme="paper"] .suggestions-area {
  background: rgba(255, 253, 248, 0.5);
}

html[data-theme="paper"] .suggestion-chip {
  background: linear-gradient(180deg, var(--color-paper-warm), var(--color-paper-cream));
  border-color: var(--color-paper-edge);
  color: var(--color-ink-on-paper);
  box-shadow: var(--shadow-inset-paper);
}

html[data-theme="paper"] .suggestion-chip:hover {
  background: linear-gradient(180deg, #fffdf8, var(--color-paper-warm));
  border-color: var(--color-chop-border);
  color: var(--color-chop);
}
</style>
