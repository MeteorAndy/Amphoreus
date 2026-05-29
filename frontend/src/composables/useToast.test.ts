import { describe, it, expect, afterEach, vi } from 'vitest'
import { useToast } from './useToast'

describe('useToast', () => {
  const { toasts, show, success, error, warning, dismiss } = useToast()

  afterEach(() => {
    vi.useRealTimers()
    for (const toast of [...toasts]) dismiss(toast.id)
  })

  it('starts with no toasts for a fresh test', () => {
    expect(toasts.length).toBe(0)
  })

  it('show() adds a toast with the given message and default info type', () => {
    show('hello')
    expect(toasts.length).toBe(1)
    expect(toasts[0].message).toBe('hello')
    expect(toasts[0].type).toBe('info')
  })

  it('success/error/warning set the correct type', () => {
    success('ok')
    error('bad')
    warning('careful')
    expect(toasts.map((t) => t.type)).toEqual(['success', 'error', 'warning'])
  })

  it('dismiss() removes a toast by id', () => {
    show('a')
    show('b')
    const firstId = toasts[0].id
    dismiss(firstId)
    expect(toasts.length).toBe(1)
    expect(toasts.find((t) => t.id === firstId)).toBeUndefined()
  })

  it('auto-dismisses a toast after its duration elapses', () => {
    vi.useFakeTimers()
    show('temp', 'info', 1000)
    expect(toasts.length).toBe(1)
    vi.advanceTimersByTime(1000)
    expect(toasts.length).toBe(0)
  })
})
