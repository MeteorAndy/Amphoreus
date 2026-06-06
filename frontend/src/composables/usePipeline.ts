import { ref, computed } from 'vue'

export interface PipelineConfig {
  seed_idea: string
  lang: string
  character_count: number
  narrative_structure: string
  output_format: string
  max_rounds_per_scene: number
  auto_refine: boolean
}

export interface PipelineEvent {
  stage: string
  type: string
  data: Record<string, unknown>
  progress: number
  session_id: string
}

type PipelineStatus = 'idle' | 'running' | 'completed' | 'error'

export function usePipeline() {
  const status = ref<PipelineStatus>('idle')
  const progress = ref(0)
  const currentStage = ref('')
  const events = ref<PipelineEvent[]>([])
  const error = ref('')
  const sessionId = ref('')
  const outputText = ref('')
  let abortController: AbortController | null = null

  const isRunning = computed(() => status.value === 'running')

  async function start(config: PipelineConfig) {
    status.value = 'running'
    progress.value = 0
    events.value = []
    error.value = ''
    outputText.value = ''
    abortController = new AbortController()

    try {
      const res = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
        signal: abortController.signal,
      })

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const data = line.replace(/^data: /, '').trim()
          if (!data || data === '[DONE]') {
            if (data === '[DONE]') {
              status.value = 'completed'
            }
            continue
          }
          try {
            const event: PipelineEvent = JSON.parse(data)
            events.value.push(event)
            progress.value = event.progress
            currentStage.value = event.stage
            sessionId.value = event.session_id

            if (event.stage === 'writing' && event.type === 'completed') {
              outputText.value = (event.data.output_text as string) || ''
            }
          } catch {
            // skip malformed events
          }
        }
      }

      if (status.value !== 'completed') {
        status.value = 'completed'
      }
    } catch (e: unknown) {
      if ((e as Error).name === 'AbortError') {
        status.value = 'idle'
      } else {
        status.value = 'error'
        error.value = (e as Error).message
      }
    }
  }

  function stop() {
    abortController?.abort()
    abortController = null
    status.value = 'idle'
  }

  function reset() {
    status.value = 'idle'
    progress.value = 0
    currentStage.value = ''
    events.value = []
    error.value = ''
    outputText.value = ''
    sessionId.value = ''
  }

  return {
    status,
    progress,
    currentStage,
    events,
    error,
    sessionId,
    outputText,
    isRunning,
    start,
    stop,
    reset,
  }
}
