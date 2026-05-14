<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import ChatPanel from '../components/ChatPanel.vue'
import { useWorldBuilder } from '../composables/useWorldBuilder'
import { useI18n } from '../i18n'
import { uploadDocument as apiUploadDocument } from '../api/client'

const { t } = useI18n()
const router = useRouter()
const {
  messages,
  sessionId,
  stage,
  extractedData,
  completeness,
  loading,
  error,
  worldState,
  finalized,
  isDone,
  startBuilding,
  continueBuilding,
  finalizeWorld,
  resetWorld,
} = useWorldBuilder()

const seedIdea = ref('')
const showUpload = ref(false)
const uploadError = ref<string | null>(null)
const uploadLoading = ref(false)

const stageOrder = ['rules', 'locations', 'factions', 'timeline'] as const

const stageKeys: Record<string, string> = {
  rules: 'world.stage_rules',
  locations: 'world.stage_locations',
  factions: 'world.stage_factions',
  timeline: 'world.stage_timeline',
}

const hasExtractedData = computed(() =>
  !!extractedData.value.name ||
  !!extractedData.value.description ||
  !!(extractedData.value.rules?.length) ||
  !!(extractedData.value.locations?.length) ||
  !!(extractedData.value.factions?.length) ||
  !!(extractedData.value.timeline?.length),
)

function stageStatus(s: string): 'completed' | 'current' | 'upcoming' {
  if (!sessionId.value) return 'upcoming'
  const order = ['rules', 'locations', 'factions', 'timeline']
  const currentIdx = order.indexOf(stage.value)
  if (currentIdx < 0) return 'completed' // stage is 'done'
  const sIdx = order.indexOf(s)
  if (sIdx < 0) return 'upcoming'
  if (sIdx < currentIdx) return 'completed'
  if (sIdx === currentIdx) return 'current'
  return 'upcoming'
}

function stageLabel(s: string): string {
  return t(stageKeys[s] || s)
}

function handleSend(text: string): void {
  if (sessionId.value) {
    continueBuilding(text)
  } else {
    startBuilding(text)
  }
}

async function handleUpload(event: Event): Promise<void> {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  uploadLoading.value = true
  uploadError.value = null
  try {
    const state = await apiUploadDocument(file)
    if (state.name) extractedData.value.name = state.name
    if (state.description) extractedData.value.description = state.description
    if (state.rules?.length) extractedData.value.rules = state.rules
    if (state.locations?.length) extractedData.value.locations = state.locations
    if (state.factions?.length) extractedData.value.factions = state.factions
    if (state.timeline?.length) extractedData.value.timeline = state.timeline
    stage.value = 'done'
    messages.value.push({
      role: 'assistant',
      content: `Document "${file.name}" processed. World data has been extracted. You can review the details and finalize.`,
    })
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : 'Failed to upload document'
  } finally {
    uploadLoading.value = false
    target.value = ''
  }
}

function goToCharacters(): void {
  router.push('/characters')
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-100">
        {{ t('world.title') }}
      </h1>
      <button
        v-if="sessionId && !finalized"
        @click="resetWorld"
        class="px-3 py-1.5 text-xs text-red-400 border border-red-800 rounded-lg hover:bg-red-900/20 transition-colors"
      >
        {{ t('world.reset') }}
      </button>
    </div>

    <!-- Error banner -->
    <div
      v-if="error"
      class="bg-red-900/20 border border-red-800 rounded-lg p-3"
    >
      <span class="text-sm text-red-400">{{ error }}</span>
    </div>

    <!-- Non-finalized: chat-based world building -->
    <template v-if="!finalized">
      <!-- Stage progress indicator -->
      <div
        v-if="sessionId"
        class="flex items-center"
      >
        <div
          v-for="(s, idx) in stageOrder"
          :key="s"
          class="flex items-center"
        >
          <div class="flex items-center gap-1.5">
            <div
              class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors flex-shrink-0"
              :class="{
                'bg-indigo-500 text-white': stageStatus(s) === 'current',
                'bg-green-600 text-white': stageStatus(s) === 'completed',
                'bg-gray-800 text-gray-500': stageStatus(s) === 'upcoming',
              }"
            >
              <span v-if="stageStatus(s) === 'completed'">&check;</span>
              <span v-else>{{ idx + 1 }}</span>
            </div>
            <span
              class="text-xs whitespace-nowrap"
              :class="{
                'text-indigo-300 font-medium': stageStatus(s) === 'current',
                'text-gray-400': stageStatus(s) !== 'current',
              }"
            >
              {{ stageLabel(s) }}
            </span>
          </div>
          <div
            v-if="idx < stageOrder.length - 1"
            class="w-8 h-px mx-2"
            :class="stageStatus(s) === 'completed' ? 'bg-green-600' : 'bg-gray-800'"
          />
        </div>
        <div class="ml-auto text-xs text-gray-500">
          {{ t('world.completeness') }}: {{ Math.round(completeness * 100) }}%
        </div>
      </div>

      <!-- Main grid: chat + sidebar -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Chat / Welcome area -->
        <div class="lg:col-span-2">
          <!-- Welcome screen (initial state, no session yet) -->
          <div
            v-if="!sessionId && !loading && messages.length === 0"
            class="bg-gray-900 rounded-lg border border-gray-800 p-8 text-center"
          >
            <div class="max-w-md mx-auto space-y-4">
              <div class="text-5xl mb-2">&#127758;</div>
              <h2 class="text-xl font-semibold text-gray-100">
                {{ t('world.welcome_title') }}
              </h2>
              <p class="text-sm text-gray-400">
                {{ t('world.welcome_desc') }}
              </p>
              <form
                @submit.prevent="handleSend(seedIdea)"
                class="flex gap-2 mt-6"
              >
                <input
                  v-model="seedIdea"
                  type="text"
                  :placeholder="t('world.idea_placeholder')"
                  class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  :disabled="loading"
                >
                <button
                  type="submit"
                  :disabled="loading || !seedIdea.trim()"
                  class="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {{ t('world.start_building') }}
                </button>
              </form>
            </div>
          </div>
          <!-- ChatPanel (during or after building) -->
          <div
            v-else
            class="h-[500px]"
          >
            <ChatPanel
              :messages="messages"
              :loading="loading"
              :placeholder="t('world.idea_placeholder')"
              @send="handleSend"
            />
          </div>
        </div>

        <!-- Sidebar: world data cards + upload -->
        <div class="space-y-4">
          <template v-if="hasExtractedData">
            <!-- World name & description -->
            <div
              v-if="extractedData.name"
              class="bg-gray-900 rounded-lg border border-gray-800 p-4"
            >
              <h3 class="text-sm font-semibold text-gray-200 mb-2">
                {{ t('world.sidebar_world') }}
              </h3>
              <p class="text-sm text-gray-300">{{ extractedData.name }}</p>
              <p
                v-if="extractedData.description"
                class="text-xs text-gray-500 mt-1"
              >
                {{ extractedData.description }}
              </p>
            </div>

            <!-- Rules -->
            <div
              v-if="extractedData.rules?.length"
              class="bg-gray-900 rounded-lg border border-gray-800 p-4"
            >
              <h3 class="text-sm font-semibold text-gray-200 mb-2">
                {{ t('world.rules') }}
              </h3>
              <ul class="space-y-1">
                <li
                  v-for="(rule, idx) in extractedData.rules"
                  :key="idx"
                  class="text-xs text-gray-400 flex gap-2"
                >
                  <span class="text-indigo-500 flex-shrink-0">-</span>
                  <span>{{ rule }}</span>
                </li>
              </ul>
            </div>

            <!-- Locations -->
            <div
              v-if="extractedData.locations?.length"
              class="bg-gray-900 rounded-lg border border-gray-800 p-4"
            >
              <h3 class="text-sm font-semibold text-gray-200 mb-2">
                {{ t('world.locations') }}
              </h3>
              <div class="space-y-2">
                <div
                  v-for="(loc, idx) in extractedData.locations"
                  :key="idx"
                >
                  <p class="text-sm text-gray-300">{{ loc.name }}</p>
                  <p class="text-xs text-gray-500">{{ loc.description }}</p>
                </div>
              </div>
            </div>

            <!-- Factions -->
            <div
              v-if="extractedData.factions?.length"
              class="bg-gray-900 rounded-lg border border-gray-800 p-4"
            >
              <h3 class="text-sm font-semibold text-gray-200 mb-2">
                {{ t('world.factions') }}
              </h3>
              <div class="space-y-2">
                <div
                  v-for="(faction, idx) in extractedData.factions"
                  :key="idx"
                >
                  <p class="text-sm text-gray-300">{{ faction.name }}</p>
                  <p class="text-xs text-gray-500">{{ faction.description }}</p>
                </div>
              </div>
            </div>

            <!-- Timeline -->
            <div
              v-if="extractedData.timeline?.length"
              class="bg-gray-900 rounded-lg border border-gray-800 p-4"
            >
              <h3 class="text-sm font-semibold text-gray-200 mb-2">
                {{ t('world.timeline') }}
              </h3>
              <div class="space-y-2">
                <div
                  v-for="(entry, idx) in extractedData.timeline"
                  :key="idx"
                  class="flex gap-2"
                >
                  <span class="text-xs text-indigo-400 flex-shrink-0 w-auto min-w-[4rem]">{{ entry.date }}</span>
                  <div>
                    <p class="text-xs text-gray-300">{{ entry.event }}</p>
                    <p
                      v-if="entry.description"
                      class="text-xs text-gray-500"
                    >
                      {{ entry.description }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- Empty sidebar state -->
          <div
            v-else
            class="bg-gray-900 rounded-lg border border-gray-800 p-6 text-center text-gray-600 text-sm"
          >
            <p>{{ t('world.start_hint') }}</p>
          </div>

          <!-- Upload document (secondary option) -->
          <div
            v-if="sessionId"
            class="border-t border-gray-800 pt-3"
          >
            <button
              @click="showUpload = !showUpload"
              class="text-xs text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1"
            >
              <span>&#128196;</span>
              <span>{{ t('world.upload_tab') }}</span>
            </button>
            <div
              v-if="showUpload"
              class="mt-2"
            >
              <input
                type="file"
                accept=".md,.txt,.pdf"
                @change="handleUpload"
                class="text-xs text-gray-400 file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:bg-indigo-600 file:text-white hover:file:bg-indigo-500"
                :disabled="uploadLoading"
              >
              <p
                v-if="uploadLoading"
                class="text-xs text-gray-500 mt-1"
              >
                {{ t('world.upload_processing') }}
              </p>
              <p
                v-if="uploadError"
                class="text-xs text-red-400 mt-1"
              >
                {{ uploadError }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Finalize button -->
      <div
        v-if="isDone"
        class="text-center pt-4"
      >
        <button
          @click="finalizeWorld"
          :disabled="loading"
          class="px-8 py-3 bg-green-600 hover:bg-green-500 disabled:bg-green-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
        >
          {{ loading ? t('world.finalizing') : t('world.finalize') }}
        </button>
      </div>
    </template>

    <!-- Finalized: summary -->
    <div
      v-if="finalized && worldState"
      class="max-w-2xl mx-auto space-y-6"
    >
      <div class="text-center space-y-2">
        <div class="text-5xl">&#127758;</div>
        <h2 class="text-2xl font-bold text-gray-100">
          {{ t('world.finalized_title') }}
        </h2>
      </div>

      <div class="bg-gray-900 rounded-lg border border-gray-800 p-6 space-y-4">
        <div>
          <h3 class="text-xl font-semibold text-gray-100">
            {{ worldState.name || t('world.unnamed') }}
          </h3>
          <p
            v-if="worldState.description"
            class="text-sm text-gray-400 mt-1"
          >
            {{ worldState.description }}
          </p>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-gray-800">
          <div class="text-center">
            <div class="text-2xl font-bold text-indigo-400">{{ worldState.rules?.length || 0 }}</div>
            <div class="text-xs text-gray-500">{{ t('world.rules') }}</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-indigo-400">{{ worldState.locations?.length || 0 }}</div>
            <div class="text-xs text-gray-500">{{ t('world.locations') }}</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-indigo-400">{{ worldState.factions?.length || 0 }}</div>
            <div class="text-xs text-gray-500">{{ t('world.factions') }}</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-indigo-400">{{ worldState.timeline?.length || 0 }}</div>
            <div class="text-xs text-gray-500">{{ t('world.timeline') }}</div>
          </div>
        </div>
      </div>

      <div class="flex gap-4 justify-center">
        <button
          @click="goToCharacters"
          class="px-6 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 transition-colors"
        >
          {{ t('world.proceed_chars') }}
        </button>
        <button
          @click="resetWorld"
          class="px-6 py-2.5 text-gray-400 border border-gray-700 rounded-lg text-sm font-medium hover:text-gray-200 hover:border-gray-600 transition-colors"
        >
          {{ t('world.start_again') }}
        </button>
      </div>
    </div>
  </div>
</template>
