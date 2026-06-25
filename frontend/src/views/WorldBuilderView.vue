<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Check, Globe, FileText } from 'lucide-vue-next'
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
  if (currentIdx < 0) return 'completed'
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
    const processedMsg = t('world.document_processed').replace('{name}', file.name)
    messages.value.push({
      role: 'assistant',
      content: processedMsg,
    })
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : t('world.upload_failed')
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
    <div class="page-header">
      <h1>{{ t('world.title') }}</h1>
      <button
        v-if="sessionId && !finalized"
        @click="resetWorld"
        class="btn btn-danger btn-sm"
      >
        {{ t('world.reset') }}
      </button>
    </div>

    <div
      v-if="error"
      class="error-banner"
    >
      {{ error }}
    </div>

    <template v-if="!finalized">
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
                'bg-chop text-white': stageStatus(s) === 'current',
                'bg-editor text-white': stageStatus(s) === 'completed',
                'bg-ink-elevated text-muted': stageStatus(s) === 'upcoming',
              }"
            >
              <Check v-if="stageStatus(s) === 'completed'" :size="12" />
              <span v-else>{{ idx + 1 }}</span>
            </div>
            <span
              class="text-xs whitespace-nowrap"
              :class="{
                'text-chop font-medium': stageStatus(s) === 'current',
                'text-parchment-dim': stageStatus(s) !== 'current',
              }"
            >
              {{ stageLabel(s) }}
            </span>
          </div>
          <div
            v-if="idx < stageOrder.length - 1"
            class="w-8 h-px mx-2"
            :class="stageStatus(s) === 'completed' ? 'bg-editor' : 'bg-ink-elevated'"
          />
        </div>
        <div class="ml-auto text-xs text-muted">
          {{ t('world.completeness') }}: {{ Math.round(completeness * 100) }}%
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2">
          <div
            v-if="!sessionId && !loading && messages.length === 0"
            class="card p-8 text-center"
          >
            <div class="max-w-md mx-auto space-y-4">
              <div class="flex justify-center mb-2">
                <Globe :size="48" class="text-muted opacity-50" />
              </div>
              <h2 class="text-xl font-semibold text-parchment">
                {{ t('world.welcome_title') }}
              </h2>
              <p class="text-sm text-parchment-dim">
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
                  class="input flex-1"
                  :disabled="loading"
                >
                <button
                  type="submit"
                  :disabled="loading || !seedIdea.trim()"
                  class="btn btn-primary"
                >
                  {{ t('world.start_building') }}
                </button>
              </form>
            </div>
          </div>
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

        <div class="space-y-4">
          <template v-if="hasExtractedData">
            <div
              v-if="extractedData.name"
              class="card p-4"
            >
              <h3 class="text-sm font-semibold text-parchment mb-2">
                {{ t('world.sidebar_world') }}
              </h3>
              <p class="text-sm text-parchment-dim">{{ extractedData.name }}</p>
              <p
                v-if="extractedData.description"
                class="text-xs text-muted mt-1"
              >
                {{ extractedData.description }}
              </p>
            </div>

            <div
              v-if="extractedData.rules?.length"
              class="card p-4"
            >
              <h3 class="text-sm font-semibold text-parchment mb-2">
                {{ t('world.rules') }}
              </h3>
              <ul class="space-y-1">
                <li
                  v-for="(rule, idx) in extractedData.rules"
                  :key="idx"
                  class="text-xs text-parchment-dim flex gap-2"
                >
                  <span class="text-chop flex-shrink-0">-</span>
                  <span>{{ rule }}</span>
                </li>
              </ul>
            </div>

            <div
              v-if="extractedData.locations?.length"
              class="card p-4"
            >
              <h3 class="text-sm font-semibold text-parchment mb-2">
                {{ t('world.locations') }}
              </h3>
              <div class="space-y-2">
                <div
                  v-for="(loc, idx) in extractedData.locations"
                  :key="idx"
                >
                  <p class="text-sm text-parchment-dim">{{ loc.name }}</p>
                  <p class="text-xs text-muted">{{ loc.description }}</p>
                </div>
              </div>
            </div>

            <div
              v-if="extractedData.factions?.length"
              class="card p-4"
            >
              <h3 class="text-sm font-semibold text-parchment mb-2">
                {{ t('world.factions') }}
              </h3>
              <div class="space-y-2">
                <div
                  v-for="(faction, idx) in extractedData.factions"
                  :key="idx"
                >
                  <p class="text-sm text-parchment-dim">{{ faction.name }}</p>
                  <p class="text-xs text-muted">{{ faction.description }}</p>
                </div>
              </div>
            </div>

            <div
              v-if="extractedData.timeline?.length"
              class="card p-4"
            >
              <h3 class="text-sm font-semibold text-parchment mb-2">
                {{ t('world.timeline') }}
              </h3>
              <div class="space-y-2">
                <div
                  v-for="(entry, idx) in extractedData.timeline"
                  :key="idx"
                  class="flex gap-2"
                >
                  <span class="text-xs text-chop flex-shrink-0 w-auto min-w-[4rem]">{{ entry.date }}</span>
                  <div>
                    <p class="text-xs text-parchment-dim">{{ entry.event }}</p>
                    <p
                      v-if="entry.description"
                      class="text-xs text-muted"
                    >
                      {{ entry.description }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <div
            v-else
            class="card p-6 text-center text-muted text-sm"
          >
            <p>{{ t('world.start_hint') }}</p>
          </div>

          <div
            v-if="sessionId"
            class="pt-3 border-t border-ink-edge"
          >
            <button
              @click="showUpload = !showUpload"
              class="btn btn-ghost btn-sm"
            >
              <FileText :size="14" />
              {{ t('world.upload_tab') }}
            </button>
            <div
              v-if="showUpload"
              class="mt-2 space-y-2"
            >
              <input
                type="file"
                accept=".md,.txt,.pdf"
                @change="handleUpload"
                class="text-xs text-parchment-dim file:mr-2 file:btn file:btn-sm file:btn-primary"
                :disabled="uploadLoading"
              >
              <p
                v-if="uploadLoading"
                class="text-xs text-muted"
              >
                {{ t('world.upload_processing') }}
              </p>
              <p
                v-if="uploadError"
                class="text-xs text-danger"
              >
                {{ uploadError }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="isDone"
        class="text-center pt-4"
      >
        <button
          @click="finalizeWorld"
          :disabled="loading"
          class="btn btn-lg"
          :class="loading ? 'bg-ink-elevated text-muted border-ink-edge' : 'bg-editor border-editor text-white hover:bg-editor hover:border-editor'"
        >
          {{ loading ? t('world.finalizing') : t('world.finalize') }}
        </button>
      </div>
    </template>

    <div
      v-if="finalized && worldState"
      class="max-w-2xl mx-auto space-y-6"
    >
      <div class="text-center space-y-2">
        <div class="flex justify-center">
          <Globe :size="48" class="text-muted opacity-50" />
        </div>
        <h2 class="text-2xl font-bold text-parchment">
          {{ t('world.finalized_title') }}
        </h2>
      </div>

      <div class="card p-6 space-y-4">
        <div>
          <h3 class="text-xl font-semibold text-parchment">
            {{ worldState.name || t('world.unnamed') }}
          </h3>
          <p
            v-if="worldState.description"
            class="text-sm text-parchment-dim mt-1"
          >
            {{ worldState.description }}
          </p>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-ink-edge">
          <div class="text-center">
            <div class="text-2xl font-bold text-chop">{{ worldState.rules?.length || 0 }}</div>
            <div class="text-xs text-muted">{{ t('world.rules') }}</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-chop">{{ worldState.locations?.length || 0 }}</div>
            <div class="text-xs text-muted">{{ t('world.locations') }}</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-chop">{{ worldState.factions?.length || 0 }}</div>
            <div class="text-xs text-muted">{{ t('world.factions') }}</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-chop">{{ worldState.timeline?.length || 0 }}</div>
            <div class="text-xs text-muted">{{ t('world.timeline') }}</div>
          </div>
        </div>
      </div>

      <div class="flex gap-4 justify-center">
        <button
          @click="goToCharacters"
          class="btn btn-primary"
        >
          {{ t('world.proceed_chars') }}
        </button>
        <button
          @click="resetWorld"
          class="btn btn-secondary"
        >
          {{ t('world.start_again') }}
        </button>
      </div>
    </div>
  </div>
</template>
