<script setup lang="ts">
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-vue-next'
import { useToast } from '../composables/useToast'
import { useI18n } from '../i18n'
import { ref, onMounted, onUnmounted } from 'vue'
import type { Component } from 'vue'
import type { ToastType } from '../composables/useToast'

const { toasts, dismiss, pause, resume, getRemaining, getDuration } = useToast()
const { t } = useI18n()

const iconMap: Record<ToastType, Component> = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
  warning: AlertTriangle,
}

const typeClass: Record<ToastType, string> = {
  success: 'toast-success',
  error: 'toast-error',
  info: 'toast-info',
  warning: 'toast-warning',
}

const progressPct = ref<Map<string, number>>(new Map())
let rafId: number | null = null

function tick() {
  for (const toast of toasts) {
    const remaining = getRemaining(toast.id)
    const duration = getDuration(toast.id)
    const pct = duration > 0 ? (remaining / duration) * 100 : 0
    progressPct.value.set(toast.id, Math.max(0, Math.min(100, pct)))
  }
  for (const [id] of Array.from(progressPct.value)) {
    if (!toasts.find(t => t.id === id)) {
      progressPct.value.delete(id)
    }
  }
  rafId = requestAnimationFrame(tick)
}

function getProgress(toastId: string): number {
  return progressPct.value.get(toastId) ?? 100
}

function onToastEnter(el: Element) {
  const hel = el as HTMLElement
  hel.style.opacity = '0'
  hel.style.transform = 'translateX(20px) scale(0.97)'
  hel.style.filter = 'blur(2px)'
  requestAnimationFrame(() => {
    hel.style.transition = 'opacity 300ms var(--ease-ink), transform 350ms var(--ease-ink), filter 300ms var(--ease-ink)'
    hel.style.opacity = '1'
    hel.style.transform = 'translateX(0) scale(1)'
    hel.style.filter = 'blur(0)'
  })
}

function onAfterEnter(el: Element) {
  const hel = el as HTMLElement
  hel.style.transition = ''
  hel.style.transform = ''
  hel.style.filter = ''
  hel.style.opacity = ''
}

function onToastLeave(el: Element, done: () => void) {
  const hel = el as HTMLElement
  hel.style.transition = 'opacity 250ms var(--ease-ink), transform 250ms var(--ease-ink)'
  hel.style.opacity = '0'
  hel.style.transform = 'translateX(20px) scale(0.97)'
  setTimeout(done, 260)
}

onMounted(() => {
  for (const toast of toasts) {
    progressPct.value.set(toast.id, 100)
  }
  rafId = requestAnimationFrame(tick)
})

onUnmounted(() => {
  if (rafId !== null) {
    cancelAnimationFrame(rafId)
  }
})
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed top-4 right-4 z-50 flex flex-col-reverse gap-3 pointer-events-none max-w-sm w-full"
      aria-live="polite"
    >
      <TransitionGroup
        :css="false"
        @enter="onToastEnter"
        @after-enter="onAfterEnter"
        @leave="onToastLeave"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="['toast-item', typeClass[toast.type]]"
          class="pointer-events-auto relative overflow-hidden will-change-transform"
          role="alert"
          @mouseenter="pause(toast.id)"
          @mouseleave="resume(toast.id)"
        >
          <div class="toast-progress-track">
            <div
              class="toast-progress-fill"
              :style="{ width: getProgress(toast.id) + '%' }"
            />
          </div>

          <div class="toast-body">
            <div class="toast-bar" />

            <div class="toast-icon-wrap">
              <component :is="iconMap[toast.type]" :size="15" class="toast-icon" />
            </div>

            <span class="toast-message">{{ toast.message }}</span>

            <button
              @click="dismiss(toast.id)"
              class="toast-close"
              :aria-label="t('toast.dismiss')"
            >
              <X :size="13" />
            </button>
          </div>

          <div class="toast-gloss" />
          <div class="toast-corners" />
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-item {
  --ease-ink: cubic-bezier(0.22, 1, 0.36, 1);
  --ease-editorial: cubic-bezier(0.22, 1, 0.36, 1);
  --duration-fast: 180ms;
  --radius-card: 8px;

  background: rgba(20, 24, 50, 0.95);
  backdrop-filter: blur(20px) saturate(1.4);
  -webkit-backdrop-filter: blur(20px) saturate(1.4);
  border: 1px solid rgba(212, 168, 67, 0.2);
  border-radius: var(--radius-card);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(212, 168, 67, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.toast-success {
  border-color: rgba(52, 211, 153, 0.3);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.5),
    0 0 20px rgba(52, 211, 153, 0.12),
    0 0 0 1px rgba(52, 211, 153, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
.toast-error {
  border-color: rgba(248, 113, 113, 0.3);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.5),
    0 0 20px rgba(248, 113, 113, 0.15),
    0 0 0 1px rgba(248, 113, 113, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
.toast-info {
  border-color: rgba(74, 127, 255, 0.3);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.5),
    0 0 20px rgba(74, 127, 255, 0.15),
    0 0 0 1px rgba(74, 127, 255, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
.toast-warning {
  border-color: rgba(212, 168, 67, 0.4);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.5),
    0 0 20px rgba(212, 168, 67, 0.15),
    0 0 0 1px rgba(212, 168, 67, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.toast-progress-track {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  z-index: 10;
  background: rgba(212, 168, 67, 0.12);
  overflow: hidden;
}
.toast-progress-fill {
  height: 100%;
  transition: width 100ms linear;
  border-radius: 0 1px 1px 0;
  background: linear-gradient(90deg, #d4a843 0%, #f0d78c 50%, #d4a843 100%);
  box-shadow: 0 0 8px rgba(212, 168, 67, 0.6), 0 0 16px rgba(212, 168, 67, 0.25);
}

.toast-bar {
  width: 3px;
  align-self: stretch;
  flex-shrink: 0;
  border-radius: 999px;
  opacity: 1;
  margin-right: 0.25rem;
}
.toast-success .toast-bar {
  background: linear-gradient(180deg, #34d399 0%, #059669 100%);
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.5);
}
.toast-error .toast-bar {
  background: linear-gradient(180deg, #f87171 0%, #dc2626 100%);
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.5);
}
.toast-info .toast-bar {
  background: linear-gradient(180deg, #4a7fff 0%, #2563eb 100%);
  box-shadow: 0 0 8px rgba(74, 127, 255, 0.5);
}
.toast-warning .toast-bar {
  background: linear-gradient(180deg, #f0d78c 0%, #d4a843 100%);
  box-shadow: 0 0 8px rgba(212, 168, 67, 0.5);
}

.toast-body {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem;
  position: relative;
  z-index: 1;
}

.toast-icon-wrap {
  flex-shrink: 0;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.125rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.toast-success .toast-icon-wrap {
  background: rgba(52, 211, 153, 0.1);
  border-color: rgba(52, 211, 153, 0.25);
}
.toast-error .toast-icon-wrap {
  background: rgba(248, 113, 113, 0.1);
  border-color: rgba(248, 113, 113, 0.25);
}
.toast-info .toast-icon-wrap {
  background: rgba(74, 127, 255, 0.1);
  border-color: rgba(74, 127, 255, 0.25);
}
.toast-warning .toast-icon-wrap {
  background: rgba(212, 168, 67, 0.1);
  border-color: rgba(212, 168, 67, 0.3);
}

.toast-success .toast-icon { color: #34d399; }
.toast-error .toast-icon { color: #f87171; }
.toast-info .toast-icon { color: #4a7fff; }
.toast-warning .toast-icon { color: #d4a843; }

.toast-message {
  flex: 1;
  font-size: 0.875rem;
  line-height: 1.5;
  padding-top: 0.25rem;
  padding-right: 0.25rem;
  color: #e2e8f0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  letter-spacing: 0.01em;
}

.toast-close {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.125rem;
  color: rgba(226, 232, 240, 0.5);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-editorial);
}
.toast-close:hover {
  background: rgba(212, 168, 67, 0.15);
  color: #f0d78c;
  border-color: rgba(212, 168, 67, 0.3);
}
.toast-close:active {
  transform: scale(0.9);
}

.toast-gloss {
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: var(--radius-card);
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.06) 0%,
    rgba(255, 255, 255, 0.02) 30%,
    transparent 60%
  );
}

.toast-corners {
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: var(--radius-card);
  background:
    linear-gradient(135deg, rgba(212, 168, 67, 0.4) 0%, transparent 12%) top left / 8px 8px no-repeat,
    linear-gradient(225deg, rgba(212, 168, 67, 0.4) 0%, transparent 12%) top right / 8px 8px no-repeat,
    linear-gradient(315deg, rgba(212, 168, 67, 0.4) 0%, transparent 12%) bottom right / 8px 8px no-repeat,
    linear-gradient(45deg, rgba(212, 168, 67, 0.4) 0%, transparent 12%) bottom left / 8px 8px no-repeat;
  z-index: 2;
  opacity: 0.6;
}
.toast-success .toast-corners {
  background:
    linear-gradient(135deg, rgba(52, 211, 153, 0.5) 0%, transparent 12%) top left / 8px 8px no-repeat,
    linear-gradient(225deg, rgba(52, 211, 153, 0.5) 0%, transparent 12%) top right / 8px 8px no-repeat,
    linear-gradient(315deg, rgba(52, 211, 153, 0.5) 0%, transparent 12%) bottom right / 8px 8px no-repeat,
    linear-gradient(45deg, rgba(52, 211, 153, 0.5) 0%, transparent 12%) bottom left / 8px 8px no-repeat;
}
.toast-error .toast-corners {
  background:
    linear-gradient(135deg, rgba(248, 113, 113, 0.5) 0%, transparent 12%) top left / 8px 8px no-repeat,
    linear-gradient(225deg, rgba(248, 113, 113, 0.5) 0%, transparent 12%) top right / 8px 8px no-repeat,
    linear-gradient(315deg, rgba(248, 113, 113, 0.5) 0%, transparent 12%) bottom right / 8px 8px no-repeat,
    linear-gradient(45deg, rgba(248, 113, 113, 0.5) 0%, transparent 12%) bottom left / 8px 8px no-repeat;
}
.toast-info .toast-corners {
  background:
    linear-gradient(135deg, rgba(74, 127, 255, 0.5) 0%, transparent 12%) top left / 8px 8px no-repeat,
    linear-gradient(225deg, rgba(74, 127, 255, 0.5) 0%, transparent 12%) top right / 8px 8px no-repeat,
    linear-gradient(315deg, rgba(74, 127, 255, 0.5) 0%, transparent 12%) bottom right / 8px 8px no-repeat,
    linear-gradient(45deg, rgba(74, 127, 255, 0.5) 0%, transparent 12%) bottom left / 8px 8px no-repeat;
}
.toast-warning .toast-corners {
  background:
    linear-gradient(135deg, rgba(240, 215, 140, 0.5) 0%, transparent 12%) top left / 8px 8px no-repeat,
    linear-gradient(225deg, rgba(240, 215, 140, 0.5) 0%, transparent 12%) top right / 8px 8px no-repeat,
    linear-gradient(315deg, rgba(240, 215, 140, 0.5) 0%, transparent 12%) bottom right / 8px 8px no-repeat,
    linear-gradient(45deg, rgba(240, 215, 140, 0.5) 0%, transparent 12%) bottom left / 8px 8px no-repeat;
}
</style>
