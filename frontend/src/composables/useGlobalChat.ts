import { ref } from 'vue'
import type { ChatMessage } from '../types/api'

const messages = ref<ChatMessage[]>([
  { role: 'assistant', content: '你好，我是 Amphoreus AI 助手。有什么可以帮助你的吗？' },
])
const loading = ref(false)

let replyTimer: ReturnType<typeof setTimeout> | null = null

function sendMessage(text: string): void {
  const trimmed = text.trim()
  if (!trimmed || loading.value) return

  messages.value.push({ role: 'user', content: trimmed })
  loading.value = true

  if (replyTimer) clearTimeout(replyTimer)
  replyTimer = setTimeout(() => {
    messages.value.push({ role: 'assistant', content: '（AI对话功能正在接入中...）' })
    loading.value = false
  }, 1000)
}

function clearMessages(): void {
  if (replyTimer) {
    clearTimeout(replyTimer)
    replyTimer = null
  }
  loading.value = false
  messages.value = [
    { role: 'assistant', content: '你好，我是 Amphoreus AI 助手。有什么可以帮助你的吗？' },
  ]
}

export function useGlobalChat() {
  return {
    messages,
    loading,
    sendMessage,
    clearMessages,
  }
}
