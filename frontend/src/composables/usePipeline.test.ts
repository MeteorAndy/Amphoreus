import { describe, it, expect } from 'vitest'
import { usePipeline } from './usePipeline'

describe('usePipeline', () => {
  it('starts in idle state with zeroed fields', () => {
    const { status, progress, currentStage, events, error, outputText, isRunning } =
      usePipeline()

    expect(status.value).toBe('idle')
    expect(progress.value).toBe(0)
    expect(currentStage.value).toBe('')
    expect(events.value).toEqual([])
    expect(error.value).toBe('')
    expect(outputText.value).toBe('')
    expect(isRunning.value).toBe(false)
  })

  it('isRunning reflects a running status', () => {
    const pipeline = usePipeline()
    pipeline.status.value = 'running'
    expect(pipeline.isRunning.value).toBe(true)
    pipeline.status.value = 'completed'
    expect(pipeline.isRunning.value).toBe(false)
  })

  it('reset() restores all fields to their initial values', () => {
    const pipeline = usePipeline()
    pipeline.status.value = 'completed'
    pipeline.progress.value = 80
    pipeline.currentStage.value = 'writing'
    pipeline.events.value.push({
      stage: 'writing',
      type: 'completed',
      data: {},
      progress: 80,
      session_id: 's1',
    })
    pipeline.error.value = 'boom'
    pipeline.outputText.value = 'some text'
    pipeline.sessionId.value = 's1'

    pipeline.reset()

    expect(pipeline.status.value).toBe('idle')
    expect(pipeline.progress.value).toBe(0)
    expect(pipeline.currentStage.value).toBe('')
    expect(pipeline.events.value).toEqual([])
    expect(pipeline.error.value).toBe('')
    expect(pipeline.outputText.value).toBe('')
    expect(pipeline.sessionId.value).toBe('')
  })

  it('stop() sets status back to idle', () => {
    const pipeline = usePipeline()
    pipeline.status.value = 'running'
    pipeline.stop()
    expect(pipeline.status.value).toBe('idle')
  })
})
