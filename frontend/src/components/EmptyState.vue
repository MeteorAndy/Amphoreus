<script setup lang="ts">
import { useI18n } from '../i18n'

const props = withDefaults(
  defineProps<{
    icon?: string
    title: string
    description?: string
    actionLabel?: string
  }>(),
  {
    icon: undefined,
    description: undefined,
    actionLabel: undefined,
  }
)

const emit = defineEmits<{
  action: []
}>()

const { t } = useI18n()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 px-6 text-center">
    <div
      v-if="icon"
      class="text-5xl mb-4 opacity-40"
      aria-hidden="true"
    >{{ icon }}</div>
    <h3 class="text-lg font-medium text-parchment-dim mb-2">
      {{ title || t('empty.default_title') }}
    </h3>
    <p
      v-if="description"
      class="text-sm text-muted max-w-xs mb-6"
    >{{ description }}</p>
    <button
      v-if="actionLabel"
      @click="emit('action')"
      class="mt-2 px-4 py-2 rounded-lg bg-chop hover:bg-chop text-white text-sm font-medium transition-colors"
    >{{ actionLabel }}</button>
  </div>
</template>
