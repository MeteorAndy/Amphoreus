<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ChatPanel from '../components/ChatPanel.vue'
import { useWorldBuilder } from '../composables/useWorldBuilder'
import { useI18n } from '../i18n'

const { t } = useI18n()
const { messages, worldState, loading, error, sendMessage, uploadDocument, loadWorldState, resetWorldState } = useWorldBuilder()

const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

onMounted(() => {
  loadWorldState()
})

function handleFileDrop(event: DragEvent): void {
  dragOver.value = false
  const file = event.dataTransfer?.files[0]
  if (file) uploadDocument(file)
}

function handleFileSelect(event: Event): void {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) uploadDocument(file)
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-100">{{ t('world.title') }}</h1>
      <button
        @click="resetWorldState"
        class="px-3 py-1.5 text-xs text-red-400 border border-red-800 rounded-lg hover:bg-red-900/20 transition-colors"
      >
        {{ t('world.reset') }}
      </button>
    </div>
    <div
      @drop="handleFileDrop"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      class="border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer"
      :class="dragOver ? 'border-indigo-500 bg-indigo-900/20' : 'border-gray-700 hover:border-gray-600'"
      @click="fileInput?.click()"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".md,.txt,.pdf,.doc,.docx"
        class="hidden"
        @change="handleFileSelect"
      />
      <p class="text-sm text-gray-400">
        {{ t('world.drop_hint') }}
      </p>
      <p class="text-xs text-gray-600 mt-1">{{ t('world.supported_formats') }}</p>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2">
        <div class="h-[500px]">
          <ChatPanel
            :messages="messages"
            :loading="loading"
            :placeholder="t('world.idea_placeholder')"
            @send="sendMessage"
          />
        </div>
      </div>
      <div class="space-y-4">
        <div v-if="error" class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-400">
          {{ error }}
        </div>
        <div v-if="worldState" class="space-y-4">
          <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <h3 class="text-sm font-semibold text-gray-200 mb-2">{{ t('world.sidebar_world') }}</h3>
            <p class="text-sm text-gray-300">{{ worldState.name || t('world.unnamed') }}</p>
            <p v-if="worldState.description" class="text-xs text-gray-500 mt-1">{{ worldState.description }}</p>
          </div>
          <div v-if="worldState.rules && worldState.rules.length > 0" class="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <h3 class="text-sm font-semibold text-gray-200 mb-2">{{ t('world.rules') }}</h3>
            <ul class="space-y-1">
              <li v-for="(rule, idx) in worldState.rules" :key="idx" class="text-xs text-gray-400 flex gap-2">
                <span class="text-indigo-500">-</span>
                {{ rule }}
              </li>
            </ul>
          </div>
          <div v-if="worldState.locations && worldState.locations.length > 0" class="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <h3 class="text-sm font-semibold text-gray-200 mb-2">{{ t('world.locations') }}</h3>
            <div class="space-y-2">
              <div v-for="(loc, idx) in worldState.locations" :key="idx">
                <p class="text-sm text-gray-300">{{ loc.name }}</p>
                <p class="text-xs text-gray-500">{{ loc.description }}</p>
              </div>
            </div>
          </div>
          <div v-if="worldState.factions && worldState.factions.length > 0" class="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <h3 class="text-sm font-semibold text-gray-200 mb-2">{{ t('world.factions') }}</h3>
            <div class="space-y-2">
              <div v-for="(faction, idx) in worldState.factions" :key="idx">
                <p class="text-sm text-gray-300">{{ faction.name }}</p>
                <p class="text-xs text-gray-500">{{ faction.description }}</p>
              </div>
            </div>
          </div>
          <div v-if="worldState.timeline && worldState.timeline.length > 0" class="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <h3 class="text-sm font-semibold text-gray-200 mb-2">{{ t('world.timeline') }}</h3>
            <div class="space-y-2">
              <div v-for="(entry, idx) in worldState.timeline" :key="idx" class="flex gap-2">
                <span class="text-xs text-indigo-400 flex-shrink-0">{{ entry.date }}</span>
                <div>
                  <p class="text-xs text-gray-300">{{ entry.event }}</p>
                  <p v-if="entry.description" class="text-xs text-gray-500">{{ entry.description }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="bg-gray-900 rounded-lg border border-gray-800 p-6 text-center text-gray-600 text-sm">
          {{ t('world.start_hint') }}
        </div>
      </div>
    </div>
  </div>
</template>
