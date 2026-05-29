import { reactive } from 'vue'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface Toast {
  id: string
  message: string
  type: ToastType
  duration: number
}

// Singleton state — shared across all component instances
const toasts = reactive<Toast[]>([])
const timers = new Map<string, ReturnType<typeof setTimeout>>()

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
      clearTimeout(timer)
      timers.delete(id)
    }
  }

  function show(message: string, type: ToastType = 'info', duration = 4000): void {
    const id = generateId()
    toasts.push({ id, message, type, duration })
    const timer = setTimeout(() => dismiss(id), duration)
    timers.set(id, timer)
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

  return { toasts, show, success, error, warning, dismiss }
}
