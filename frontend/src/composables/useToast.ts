import { reactive } from 'vue'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface Toast {
  id: string
  message: string
  type: ToastType
  duration: number
}

interface ToastTimer {
  timeoutId: ReturnType<typeof setTimeout>
  startTime: number
  remaining: number
  duration: number
}

const toasts = reactive<Toast[]>([])
const timers = new Map<string, ToastTimer>()

function generateId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return Date.now().toString(36) + Math.random().toString(36).slice(2)
}

export function useToast() {
  function dismiss(id: string): void {
    const idx = toasts.findIndex((t) => t.id === id)
    if (idx !== -1) toasts.splice(idx, 1)
    const timer = timers.get(id)
    if (timer !== undefined) {
      clearTimeout(timer.timeoutId)
      timers.delete(id)
    }
  }

  function startDismissTimer(id: string, duration: number): void {
    const startTime = Date.now()
    const timeoutId = setTimeout(() => dismiss(id), duration)
    timers.set(id, { timeoutId, startTime, remaining: duration, duration })
  }

  function show(message: string, type: ToastType = 'info', duration = 4000): void {
    const id = generateId()
    toasts.push({ id, message, type, duration })
    startDismissTimer(id, duration)
  }

  function success(message: string): void {
    show(message, 'success')
  }

  function error(message: string): void {
    show(message, 'error')
  }

  function warning(message: string): void {
    show(message, 'warning')
  }

  function pause(id: string): void {
    const timer = timers.get(id)
    if (timer === undefined) return
    clearTimeout(timer.timeoutId)
    const elapsed = Date.now() - timer.startTime
    timer.remaining = Math.max(0, timer.remaining - elapsed)
  }

  function resume(id: string): void {
    const idx = toasts.findIndex((t) => t.id === id)
    if (idx === -1) return
    const toast = toasts[idx]
    const existing = timers.get(id)
    if (existing !== undefined) {
      existing.startTime = Date.now()
      const timeoutId = setTimeout(() => dismiss(id), existing.remaining)
      existing.timeoutId = timeoutId
    } else {
      startDismissTimer(id, toast.duration)
    }
  }

  function getRemaining(id: string): number {
    const timer = timers.get(id)
    if (timer === undefined) return 0
    const elapsed = Date.now() - timer.startTime
    return Math.max(0, timer.remaining - elapsed)
  }

  function getDuration(id: string): number {
    const timer = timers.get(id)
    return timer?.duration ?? 4000
  }

  return { toasts, show, success, error, warning, dismiss, pause, resume, getRemaining, getDuration }
}
