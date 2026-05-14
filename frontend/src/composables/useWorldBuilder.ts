import { ref } from 'vue'
import type { ChatMessage, WorldState } from '../types/api'
import { worldChat, uploadDocument as apiUploadDocument, getWorldState, resetWorld as apiResetWorld } from '../api/client'

export function useWorldBuilder() {
  const messages = ref<ChatMessage[]>([])
  const worldState = ref<WorldState | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function sendMessage(text: string): Promise<void> {
    loading.value = true
    error.value = null
    messages.value.push({ role: 'user', content: text })
    try {
      const res = await worldChat({ message: text, world_id: worldState.value?.world_id })
      messages.value.push({ role: 'assistant', content: res.reply })
      if (res.world_state) {
        worldState.value = res.world_state
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to send message'
      messages.value.push({ role: 'assistant', content: `Error: ${error.value}` })
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(file: File): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const state = await apiUploadDocument(file)
      worldState.value = state
      messages.value.push({
        role: 'assistant',
        content: `Document "${file.name}" processed successfully. World state updated.`,
      })
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to upload document'
    } finally {
      loading.value = false
    }
  }

  async function loadWorldState(): Promise<void> {
    try {
      worldState.value = await getWorldState()
    } catch {
      worldState.value = null
    }
  }

  async function resetWorldState(): Promise<void> {
    try {
      await apiResetWorld()
      worldState.value = null
      messages.value = []
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to reset world'
    }
  }

  function clearMessages(): void {
    messages.value = []
  }

  return {
    messages,
    worldState,
    loading,
    error,
    sendMessage,
    uploadDocument,
    loadWorldState,
    resetWorldState,
    clearMessages,
  }
}
