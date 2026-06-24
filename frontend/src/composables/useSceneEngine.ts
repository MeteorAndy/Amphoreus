import { ref, onUnmounted } from 'vue'
import type { SceneRound, SceneStatus, SceneStreamMessage, SceneRunRequest, SceneArchive } from '../types/api'
import { evaluateSceneIntervention, createSceneWebSocket } from '../api/client'
import { useProjectStore } from './useProjectStore'

export function useSceneEngine() {
  const projectStore = useProjectStore()

  const status = ref<SceneStatus>({ status: 'idle', current_round: 0, total_rounds: 0 })
  const rounds = ref<SceneRound[]>([])
  const connected = ref(false)
  const error = ref<string | null>(null)
  const sceneId = ref<string | null>(null)
  const environmentState = ref<string>('')
  const resolutionText = ref<string>('')

  let ws: WebSocket | null = null

  function handleStreamMessage(msg: SceneStreamMessage): void {
    switch (msg.type) {
      case 'setup': {
        const data = msg.data as { scene_id: string; characters: string[]; setting: string }
        sceneId.value = data.scene_id
        status.value = { status: 'running', current_round: 0, total_rounds: 0 }
        rounds.value = []
        environmentState.value = data.setting
        break
      }
      case 'environment': {
        const data = msg.data as { state?: string; description?: string }
        environmentState.value = data.state || data.description || ''
        status.value = { ...status.value, status: 'running' }
        break
      }
      case 'round': {
        const roundData = msg.data as SceneRound & { round_num?: number }
        const round: SceneRound = {
          ...roundData,
          round_number: roundData.round_number ?? roundData.round_num ?? 0,
        }
        rounds.value.push(round)
        status.value = {
          ...status.value,
          current_round: round.round_number,
        }
        break
      }
      case 'resolution': {
        const data = msg.data as { summary?: string; text?: string }
        resolutionText.value = data.summary || data.text || ''
        status.value = { ...status.value, status: 'running' }
        break
      }
      case 'complete': {
        const data = msg.data as { summary: string; total_rounds: number; scene_archive?: SceneArchive }
        status.value = {
          status: 'completed',
          current_round: data.total_rounds,
          total_rounds: data.total_rounds,
        }
        resolutionText.value = data.summary || resolutionText.value
        if (data.scene_archive) {
          projectStore.addSceneArchive(data.scene_archive, data.scene_archive.scene_id || sceneId.value || undefined)
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
    environmentState.value = ''
    resolutionText.value = ''

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
  }

  async function intervene(intervention: string): Promise<void> {
    error.value = null
    if (!sceneId.value) {
      error.value = 'No active scene'
      return
    }
    try {
      await evaluateSceneIntervention({
        scene_id: sceneId.value,
        intervention,
        current_round: status.value.current_round,
      })
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to send intervention'
    }
  }

  function endSceneSession(): void {
    disconnect()
    status.value = { status: 'idle', current_round: 0, total_rounds: 0 }
    rounds.value = []
    error.value = null
    sceneId.value = null
    environmentState.value = ''
    resolutionText.value = ''
  }

  function reset(): void {
    endSceneSession()
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
    environmentState,
    resolutionText,
    connect,
    disconnect,
    intervene,
    endSceneSession,
    reset,
  }
}
