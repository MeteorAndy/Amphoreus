<script setup lang="ts">
import { ref } from 'vue'
import { Sparkles, X, Wand2 } from 'lucide-vue-next'
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
    <div class="modal-overlay" @click.self="emit('close')">
      <div class="modal-panel w-full max-w-md mx-4">
        <div class="flex items-center gap-3 mb-4 -mt-1">
          <div class="w-10 h-10 rounded-full bg-gold-soft flex items-center justify-center border border-gold/30">
            <Sparkles :size="18" class="text-gold-light" />
          </div>
          <div class="flex-1">
            <h2 class="text-lg font-display font-semibold text-parchment">Refine Character</h2>
            <p class="text-xs text-muted mt-0.5">
              Provide feedback for <span class="text-parchment-dim font-medium">"{{ characterName }}"</span>
            </p>
          </div>
          <button @click="emit('close')" class="btn btn-ghost p-2">
            <X :size="16" />
          </button>
        </div>

        <div class="divider !my-4" />

        <textarea
          v-model="refineFeedback"
          rows="4"
          placeholder="Describe what should change about this character..."
          class="input resize-none"
        />

        <div class="flex justify-end gap-2 mt-5">
          <button
            @click="emit('close')"
            class="btn btn-secondary"
          >
            {{ t('general.cancel') }}
          </button>
          <button
            @click="emit('refine', refineFeedback)"
            :disabled="refining || !refineFeedback.trim()"
            class="btn btn-primary"
          >
            <Wand2 :size="14" />
            {{ refining ? t('general.loading') : t('general.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
