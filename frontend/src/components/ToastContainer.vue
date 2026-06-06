<script setup lang="ts">
import { useToast } from '../composables/useToast'
import { useI18n } from '../i18n'

const { toasts, dismiss } = useToast()
const { t } = useI18n()

const icons: Record<string, string> = {
  success: '✓',
  error: '✕',
  info: 'ℹ',
  warning: '⚠',
}

const colorClasses: Record<string, string> = {
  success: 'bg-green-900 border-green-700 text-green-100',
  error: 'bg-red-900 border-red-700 text-red-100',
  info: 'bg-blue-900 border-blue-700 text-blue-100',
  warning: 'bg-yellow-900 border-yellow-700 text-yellow-100',
}

const iconColorClasses: Record<string, string> = {
  success: 'text-green-400',
  error: 'text-red-400',
  info: 'text-blue-400',
  warning: 'text-yellow-400',
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
      aria-label="Notifications"
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
          class="pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg max-w-sm w-full"
          :class="colorClasses[toast.type]"
          role="alert"
        >
          <span
            class="flex-shrink-0 text-sm font-bold mt-0.5"
            :class="iconColorClasses[toast.type]"
            aria-hidden="true"
          >{{ icons[toast.type] }}</span>
          <span class="flex-1 text-sm leading-snug">{{ toast.message }}</span>
          <button
            @click="dismiss(toast.id)"
            class="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity text-sm leading-none mt-0.5"
            :aria-label="t('toast.dismiss')"
          >✕</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
