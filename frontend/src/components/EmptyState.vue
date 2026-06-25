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
  <div class="empty-state">
    <div v-if="icon" class="empty-state-icon" aria-hidden="true">{{ icon }}</div>
    <h3 class="text-base font-medium text-parchment-dim mb-2">
      {{ title || t('empty.default_title') }}
    </h3>
    <p v-if="description" class="empty-state-text">{{ description }}</p>
    <button v-if="actionLabel" @click="emit('action')" class="btn btn-primary">
      {{ actionLabel }}
    </button>
  </div>
</template>
