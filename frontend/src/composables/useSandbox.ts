import { ref } from 'vue'
import type { SandboxEvent, SandboxStartRequest } from '../types/api'
import { startSandbox, injectSandboxEvent, stopSandbox } from '../api/client'

export function useSandbox() {
  const sessionId = ref('')
  const events = ref<SandboxEvent[]>([])
  const isRunning = ref(false)
  const rounds = ref(0)
  let abortController: AbortController | null = null

  async function feedLoop(sid: string): Promise<void> {
    while (isRunning.value) {
      await connectFeed(sid)
    }
  }

  async function connectFeed(sid: string): Promise<void> {
    abortController = new AbortController()
    try {
      const res = await fetch(`/api/sandbox/${sid}/feed`, {
        signal: abortController.signal,
      })
      if (!res.ok || !res.body) return

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() ?? ''

        for (const chunk of chunks) {
          const data = chunk.replace(/^data: /, '').trim()
          if (!data || data === '[DONE]') continue
          try {
            const evt: SandboxEvent = JSON.parse(data)
            events.value.push(evt)
            if (evt.type === 'round_end' && evt.round !== undefined) {
              rounds.value = evt.round
            }
            if (evt.type === 'stopped' && evt.rounds !== undefined) {
              rounds.value = evt.rounds
              isRunning.value = false
            }
          } catch {
            // skip malformed events
          }
        }
      }
    } catch (e: unknown) {
      if ((e as Error).name === 'AbortError') return
    }
  }

  async function start(req: SandboxStartRequest): Promise<void> {
    events.value = []
    rounds.value = 0
    const res = await startSandbox(req)
    sessionId.value = res.session_id
    isRunning.value = true
    feedLoop(res.session_id)
  }

  async function inject(event: string): Promise<void> {
    if (!sessionId.value) return
    await injectSandboxEvent(sessionId.value, event)
  }

  async function stop(): Promise<void> {
    isRunning.value = false
    abortController?.abort()
    abortController = null
    if (sessionId.value) {
      try {
        const res = await stopSandbox(sessionId.value)
        rounds.value = res.rounds
      } catch {
        // ignore stop errors
      }
    }
  }

  return { sessionId, events, isRunning, rounds, start, inject, stop }
}
