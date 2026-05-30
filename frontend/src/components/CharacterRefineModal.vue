<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from '../i18n'

const { t } = useI18n()

defineProps<{
  characterName: string
  refining: boolean
}>()

const emit = defineEmits<{
  refine: [feedback: string]
  close: []
}>()

const refineFeedback = ref('')
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      @click.self="emit('close')"
    >
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md mx-4">
        <h2 class="text-lg font-semibold text-gray-100 mb-2">Refine Character</h2>
        <p class="text-xs text-gray-500 mb-4">
          Provide feedback on how to improve "{{ characterName }}"
        </p>
        <textarea
          v-model="refineFeedback"
          rows="4"
          placeholder="Describe what should change about this character..."
          class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 resize-none"
        />
        <div class="flex justify-end gap-2 mt-4">
          <button
            @click="emit('close')"
            class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
          >
            {{ t('general.cancel') }}
          </button>
          <button
            @click="emit('refine', refineFeedback)"
            :disabled="refining || !refineFeedback.trim()"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 transition-colors"
          >
            {{ refining ? t('general.loading') : t('general.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
