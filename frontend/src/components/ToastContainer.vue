<script setup lang="ts">
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-vue-next'
import { useToast } from '../composables/useToast'
import { useI18n } from '../i18n'
import type { Component } from 'vue'

const { toasts, dismiss } = useToast()
const { t } = useI18n()

const iconMap: Record<string, Component> = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
  warning: AlertTriangle,
}

const barColors: Record<string, string> = {
  success: 'bg-editor',
  error: 'bg-danger',
  info: 'bg-chop',
  warning: 'bg-gold',
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
    >
      <TransitionGroup
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 translate-x-8"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition-all duration-200 ease-in"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 translate-x-8"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-start gap-3 pl-0 rounded-lg shadow-elevated max-w-sm w-full overflow-hidden"
          style="background: var(--color-ink-panel); border: 1px solid var(--color-ink-edge)"
          role="alert"
        >
          <div :class="['w-1 self-stretch flex-shrink-0', barColors[toast.type]]" />
          <div class="flex items-start gap-2.5 py-3 pr-3 flex-1">
            <component
              :is="iconMap[toast.type]"
              :size="16"
              :class="[
                'flex-shrink-0 mt-0.5',
                toast.type === 'success' ? 'text-editor' :
                toast.type === 'error' ? 'text-danger' :
                toast.type === 'warning' ? 'text-gold' : 'text-chop'
              ]"
            />
            <span class="flex-1 text-sm leading-snug text-parchment">{{ toast.message }}</span>
            <button
              @click="dismiss(toast.id)"
              class="flex-shrink-0 text-muted hover:text-parchment transition-colors"
              :aria-label="t('toast.dismiss')"
            >
              <X :size="14" />
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
