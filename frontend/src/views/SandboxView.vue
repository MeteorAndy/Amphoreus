<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { useI18n } from '../i18n'
import { useSandbox } from '../composables/useSandbox'
import { useCharacters } from '../composables/useCharacters'
import { useToast } from '../composables/useToast'
import SandboxFeedItem from '../components/SandboxFeedItem.vue'
import { Play, Square, Send, Radio } from 'lucide-vue-next'

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
    <div class="text-center mb-8 pt-4">
      <h1 class="text-2xl font-bold text-parchment mb-2">{{ t('sandbox.title') }}</h1>
      <p class="text-sm text-muted">{{ t('sandbox.subtitle') }}</p>
    </div>

    <!-- SETUP STATE -->
    <div v-if="!sandbox.isRunning.value && sandbox.events.value.length === 0"
      class="card p-6 space-y-4">
      <div>
        <label class="field-label">
          {{ t('sandbox.select_chars') }}
        </label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="char in characters"
            :key="char.id"
            type="button"
            class="chip"
            :class="selectedCharIds.includes(char.id) ? 'chip-active' : ''"
            @click="toggleChar(char.id)"
          >
            {{ char.name }}
          </button>
        </div>
      </div>
      <div>
        <label class="field-label">
          {{ t('sandbox.location') }}
        </label>
        <input
          v-model="location"
          type="text"
          class="input"
        />
      </div>
      <button
        @click="handleStart"
        :disabled="selectedCharIds.length === 0"
        class="btn btn-primary btn-lg w-full"
      >
        <Play :size="16" />
        {{ t('sandbox.start') }}
      </button>
    </div>

    <!-- OBSERVING STATE -->
    <div v-if="sandbox.isRunning.value || sandbox.events.value.length > 0"
      class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- LEFT: Live Feed -->
      <div class="lg:col-span-2 card p-6 flex flex-col">
        <h2 class="flex items-center gap-2 text-sm font-semibold text-parchment-dim mb-3">
          <Radio :size="14" />
          {{ t('sandbox.live_feed') }}
        </h2>
        <div
          ref="feedContainer"
          class="flex-1 overflow-y-auto min-h-64 max-h-[60vh] space-y-0.5"
        >
          <p v-if="sandbox.events.value.length === 0" class="text-sm text-muted italic">
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
      <div class="card p-6 flex flex-col gap-4">
        <h2 class="text-sm font-semibold text-parchment-dim">{{ t('sandbox.inject') }}</h2>
        <textarea
          v-model="customEvent"
          :placeholder="t('sandbox.inject_placeholder')"
          rows="3"
          class="input resize-none"
        />
        <button
          @click="handleInject(customEvent)"
          :disabled="!customEvent.trim()"
          class="btn btn-primary"
        >
          <Send :size="14" />
          {{ t('sandbox.inject') }}
        </button>
        <div class="grid grid-cols-2 gap-2">
          <button @click="handleInject(t('sandbox.quick_storm'))"
            class="btn btn-secondary text-xs">
            {{ t('sandbox.quick_storm') }}
          </button>
          <button @click="handleInject(t('sandbox.quick_npc'))"
            class="btn btn-secondary text-xs">
            {{ t('sandbox.quick_npc') }}
          </button>
          <button @click="handleInject(t('sandbox.quick_quake'))"
            class="btn btn-secondary text-xs">
            {{ t('sandbox.quick_quake') }}
          </button>
          <button @click="handleInject(t('sandbox.quick_news'))"
            class="btn btn-secondary text-xs">
            {{ t('sandbox.quick_news') }}
          </button>
        </div>
        <button
          v-if="sandbox.isRunning.value"
          @click="handleStop"
          class="mt-auto btn btn-danger"
        >
          <Square :size="14" />
          {{ t('sandbox.stop') }}
        </button>
      </div>
    </div>
  </div>
</template>
