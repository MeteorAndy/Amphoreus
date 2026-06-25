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
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-item {
  background: var(--color-ink-panel);
  border: 1px solid var(--color-ink-edge);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-elevated),
              0 0 0 1px rgba(237, 228, 211, 0.03);
}

.toast-success {
  border-color: rgba(90, 138, 79, 0.3);
  box-shadow: var(--shadow-elevated),
              0 0 0 1px rgba(237, 228, 211, 0.03),
              0 0 20px rgba(90, 138, 79, 0.15);
}
.toast-error {
  border-color: var(--color-chop-border);
  box-shadow: var(--shadow-elevated),
              0 0 0 1px rgba(237, 228, 211, 0.03),
              0 0 20px var(--color-chop-glow);
}
.toast-info {
  border-color: var(--color-chop-border);
  box-shadow: var(--shadow-elevated),
              0 0 0 1px rgba(237, 228, 211, 0.03),
              0 0 20px var(--color-chop-glow);
}
.toast-warning {
  border-color: rgba(201, 148, 74, 0.3);
  box-shadow: var(--shadow-elevated),
              0 0 0 1px rgba(237, 228, 211, 0.03),
              0 0 20px rgba(201, 148, 74, 0.12);
}

.toast-progress-track {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  z-index: 10;
  background: var(--color-ink-edge);
}
.toast-progress-fill {
  height: 100%;
  transition: width 100ms linear;
  border-radius: 0 1px 1px 0;
}

.toast-success .toast-bar,
.toast-success .toast-progress-fill { background: var(--gradient-editor-seal); }
.toast-error .toast-bar,
.toast-error .toast-progress-fill { background: var(--gradient-danger-seal); }
.toast-info .toast-bar,
.toast-info .toast-progress-fill { background: var(--gradient-chop-seal); }
.toast-warning .toast-bar,
.toast-warning .toast-progress-fill { background: var(--gradient-gold-seal); }

.toast-body {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem;
}

.toast-bar {
  width: 4px;
  align-self: stretch;
  flex-shrink: 0;
  border-radius: 999px;
  opacity: 0.85;
}

.toast-icon-wrap {
  flex-shrink: 0;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.125rem;
}
.toast-success .toast-icon-wrap {
  background: var(--color-editor-soft);
  border: 1px solid rgba(90, 138, 79, 0.3);
}
.toast-error .toast-icon-wrap {
  background: var(--color-danger-soft);
  border: 1px solid var(--color-chop-border);
}
.toast-info .toast-icon-wrap {
  background: var(--color-chop-soft);
  border: 1px solid var(--color-chop-border);
}
.toast-warning .toast-icon-wrap {
  background: var(--color-gold-soft);
  border: 1px solid rgba(201, 148, 74, 0.3);
}

.toast-success .toast-icon { color: var(--color-editor-light); }
.toast-error .toast-icon { color: var(--color-chop-light); }
.toast-info .toast-icon { color: var(--color-chop-light); }
.toast-warning .toast-icon { color: var(--color-gold-light); }

.toast-message {
  flex: 1;
  font-size: var(--text-sm);
  line-height: 1.5;
  padding-top: 0.25rem;
  padding-right: 0.25rem;
  color: var(--color-parchment);
}

.toast-close {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.125rem;
  color: var(--color-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-editorial);
}
.toast-close:hover {
  background: var(--color-ink-wash-light);
  color: var(--color-parchment);
}
.toast-close:active {
  transform: scale(0.9);
}

.toast-gloss {
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: var(--radius-card);
  background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 30%);
}

/* Paper theme overrides */
html[data-theme="paper"] .toast-item {
  background: var(--color-paper-cream);
  background-image: linear-gradient(180deg, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0.15) 40%, transparent 100%);
  box-shadow: var(--shadow-card),
              var(--shadow-inset-paper),
              inset 0 0 0 1px rgba(255,255,255,0.3);
}
html[data-theme="paper"] .toast-success {
  border-color: rgba(61, 107, 50, 0.25);
  box-shadow: 0 2px 8px rgba(61, 107, 50, 0.1),
              var(--shadow-card),
              var(--shadow-inset-paper);
}
html[data-theme="paper"] .toast-error,
html[data-theme="paper"] .toast-info {
  border-color: rgba(168, 54, 47, 0.3);
  box-shadow: 0 2px 8px rgba(168, 54, 47, 0.1),
              var(--shadow-card),
              var(--shadow-inset-paper);
}
html[data-theme="paper"] .toast-warning {
  border-color: rgba(154, 115, 48, 0.25);
  box-shadow: 0 2px 8px rgba(154, 115, 48, 0.1),
              var(--shadow-card),
              var(--shadow-inset-paper);
}
html[data-theme="paper"] .toast-gloss {
  background: linear-gradient(180deg, rgba(255,255,255,0.5) 0%, transparent 30%);
}
html[data-theme="paper"] .toast-progress-track {
  background: var(--color-paper-edge);
}
</style>
