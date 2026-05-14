import { ref, onUnmounted } from 'vue'
import type { SceneRound, SceneStatus, SceneStreamMessage, SceneRunRequest, InterventionRequest } from '../types/api'
import { getSceneStatus, interveneScene as apiIntervene, endScene as apiEndScene, createSceneWebSocket } from '../api/client'

export function useSceneEngine() {
  const status = ref<SceneStatus>({ status: 'idle', current_round: 0, total_rounds: 0 })
  const rounds = ref<SceneRound[]>([])
  const connected = ref(false)
  const error = ref<string | null>(null)
  const sceneId = ref<string | null>(null)

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function handleStreamMessage(msg: SceneStreamMessage): void {
    switch (msg.type) {
      case 'setup': {
        const data = msg.data as { scene_id: string; characters: string[]; setting: string }
        sceneId.value = data.scene_id
        status.value = { status: 'running', current_round: 0, total_rounds: 0 }
        break
      }
      case 'environment':
        status.value = { ...status.value, status: 'running' }
        break
      case 'round': {
        const round = msg.data as SceneRound
        rounds.value.push(round)
        status.value = {
          ...status.value,
          current_round: round.round_number,
        }
        break
      }
      case 'resolution':
        status.value = { ...status.value, status: 'running' }
        break
      case 'complete': {
        const data = msg.data as { summary: string; total_rounds: number }
        status.value = {
          status: 'completed',
          current_round: data.total_rounds,
          total_rounds: data.total_rounds,
        }
        break
      }
      case 'error': {
        const errMsg = typeof msg.data === 'string' ? msg.data : 'Scene execution error'
        error.value = errMsg
        status.value = { ...status.value, status: 'error' }
        break
      }
    }
  }

  function connect(req: SceneRunRequest): void {
    disconnect()
    rounds.value = []
    error.value = null
    connected.value = false

    try {
      ws = createSceneWebSocket()

      ws.onopen = () => {
        connected.value = true
        ws!.send(JSON.stringify(req))
      }

      ws.onmessage = (event: MessageEvent) => {
        try {
          const msg: SceneStreamMessage = JSON.parse(event.data)
          handleStreamMessage(msg)
        } catch {
          error.value = 'Failed to parse server message'
        }
      }

      ws.onerror = () => {
        error.value = 'WebSocket connection error'
        connected.value = false
      }

      ws.onclose = () => {
        connected.value = false
        if (status.value.status === 'running') {
          status.value = { ...status.value, status: 'error' }
        }
      }
    } catch {
      error.value = 'Failed to create WebSocket connection'
    }
  }

  function disconnect(): void {
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
    connected.value = false
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  async function intervene(intervention: string): Promise<void> {
    error.value = null
    try {
      await apiIntervene({ scene_id: sceneId.value || undefined, intervention } as InterventionRequest)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to send intervention'
    }
  }

  async function endSceneSession(): Promise<void> {
    error.value = null
    try {
      await apiEndScene()
      disconnect()
      status.value = { status: 'idle', current_round: 0, total_rounds: 0 }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to end scene'
    }
  }

  async function fetchStatus(): Promise<void> {
    try {
      status.value = await getSceneStatus()
    } catch {
      status.value = { status: 'idle', current_round: 0, total_rounds: 0 }
    }
  }

  function reset(): void {
    disconnect()
    rounds.value = []
    status.value = { status: 'idle', current_round: 0, total_rounds: 0 }
    error.value = null
    sceneId.value = null
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    status,
    rounds,
    connected,
    error,
    sceneId,
    connect,
    disconnect,
    intervene,
    endSceneSession,
    fetchStatus,
    reset,
  }
}
