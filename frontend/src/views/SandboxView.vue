<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { useI18n } from '../i18n'
import { useSandbox } from '../composables/useSandbox'
import { useCharacters } from '../composables/useCharacters'
import { useToast } from '../composables/useToast'
import SandboxFeedItem from '../components/SandboxFeedItem.vue'

const { t } = useI18n()
const sandbox = useSandbox()
const { characters, fetchCharacters } = useCharacters()
const toast = useToast()

const selectedCharIds = ref<string[]>([])
const location = ref('')
const customEvent = ref('')
const feedContainer = ref<HTMLElement | null>(null)

const worldId = localStorage.getItem('amphoreus-world-id') ?? ''

onMounted(() => {
  fetchCharacters()
})

watch(
  () => sandbox.events.value.length,
  async () => {
    await nextTick()
    if (feedContainer.value) {
      feedContainer.value.scrollTop = feedContainer.value.scrollHeight
    }
  },
)

function toggleChar(id: string): void {
  const idx = selectedCharIds.value.indexOf(id)
  if (idx === -1) selectedCharIds.value.push(id)
  else selectedCharIds.value.splice(idx, 1)
}

async function handleStart(): Promise<void> {
  if (selectedCharIds.value.length === 0) return
  await sandbox.start({
    world_id: worldId,
    character_ids: selectedCharIds.value,
    location: location.value.trim() || undefined,
  })
}

async function handleInject(event: string): Promise<void> {
  if (!event.trim()) return
  await sandbox.inject(event.trim())
  toast.success(t('sandbox.inject'))
  customEvent.value = ''
}

async function handleStop(): Promise<void> {
  await sandbox.stop()
  toast.success(t('sandbox.stopped'))
}
</script>

<template>
  <div class="max-w-5xl mx-auto p-6 space-y-6">
    <!-- Header -->
    <div class="text-center">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{{ t('sandbox.title') }}</h1>
      <p class="mt-2 text-gray-500 dark:text-gray-400">{{ t('sandbox.subtitle') }}</p>
    </div>

    <!-- SETUP STATE -->
    <div v-if="!sandbox.isRunning.value && sandbox.events.value.length === 0"
      class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {{ t('sandbox.select_chars') }}
        </label>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-2">
          <label
            v-for="char in characters"
            :key="char.id"
            class="flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors"
            :class="selectedCharIds.includes(char.id)
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
              : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-700 dark:text-gray-300'"
          >
            <input
              type="checkbox"
              :value="char.id"
              :checked="selectedCharIds.includes(char.id)"
              @change="toggleChar(char.id)"
              class="rounded text-blue-600"
            />
            <span class="text-sm font-medium truncate">{{ char.name }}</span>
          </label>
        </div>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {{ t('sandbox.location') }}
        </label>
        <input
          v-model="location"
          type="text"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
      <button
        @click="handleStart"
        :disabled="selectedCharIds.length === 0"
        class="w-full py-3 px-6 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium transition-colors"
      >
        {{ t('sandbox.start') }}
      </button>
    </div>

    <!-- OBSERVING STATE -->
    <div v-if="sandbox.isRunning.value || sandbox.events.value.length > 0"
      class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- LEFT: Live Feed -->
      <div class="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 flex flex-col">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Live Feed</h2>
        <div
          ref="feedContainer"
          class="flex-1 overflow-y-auto min-h-64 max-h-[60vh] space-y-0.5"
        >
          <p v-if="sandbox.events.value.length === 0" class="text-sm text-gray-400 dark:text-gray-500 italic">
            {{ t('sandbox.feed_empty') }}
          </p>
          <SandboxFeedItem
            v-for="(evt, idx) in sandbox.events.value"
            :key="idx"
            :event="evt"
          />
        </div>
      </div>

      <!-- RIGHT: Injection Panel -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 flex flex-col gap-4">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{{ t('sandbox.inject') }}</h2>
        <textarea
          v-model="customEvent"
          :placeholder="t('sandbox.inject_placeholder')"
          rows="3"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
        />
        <button
          @click="handleInject(customEvent)"
          :disabled="!customEvent.trim()"
          class="rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium px-4 py-2 text-sm transition-colors"
        >
          {{ t('sandbox.inject') }}
        </button>
        <div class="grid grid-cols-2 gap-2">
          <button @click="handleInject(t('sandbox.quick_storm'))"
            class="rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 px-2 py-1.5 text-xs font-medium transition-colors">
            {{ t('sandbox.quick_storm') }}
          </button>
          <button @click="handleInject(t('sandbox.quick_npc'))"
            class="rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 px-2 py-1.5 text-xs font-medium transition-colors">
            {{ t('sandbox.quick_npc') }}
          </button>
          <button @click="handleInject(t('sandbox.quick_quake'))"
            class="rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 px-2 py-1.5 text-xs font-medium transition-colors">
            {{ t('sandbox.quick_quake') }}
          </button>
          <button @click="handleInject(t('sandbox.quick_news'))"
            class="rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 px-2 py-1.5 text-xs font-medium transition-colors">
            {{ t('sandbox.quick_news') }}
          </button>
        </div>
        <button
          v-if="sandbox.isRunning.value"
          @click="handleStop"
          class="mt-auto rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium px-4 py-2 text-sm transition-colors"
        >
          {{ t('sandbox.stop') }}
        </button>
      </div>
    </div>
  </div>
</template>
