<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Check, Globe, Sparkles, UploadCloud,
  Loader2,
} from 'lucide-vue-next'
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
  initFromProject,
} = useWorldBuilder()

onMounted(() => {
  initFromProject()
})

const seedIdea = ref('')
const activeEntryTab = ref<'idea' | 'upload'>('idea')
const uploadError = ref<string | null>(null)
const uploadLoading = ref(false)
const isDragging = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const acceptedFormats = '.md,.txt,.pdf,.doc,.docx'

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

function triggerFilePick(): void {
  fileInputRef.value?.click()
}

async function processFile(file: File): Promise<void> {
  uploadLoading.value = true
  uploadError.value = null
  try {
    const res = await apiUploadDocument(file)
    const ew = res.extracted_world || (res as unknown as { rules?: unknown; locations?: unknown; factions?: unknown; timeline?: unknown })
    if (Array.isArray(ew.rules) && ew.rules.length) {
      extractedData.value.rules = ew.rules.filter((r): r is string => typeof r === 'string')
    }
    if (Array.isArray(ew.locations) && ew.locations.length) {
      extractedData.value.locations = ew.locations as typeof extractedData.value.locations
    }
    if (Array.isArray(ew.factions) && ew.factions.length) {
      extractedData.value.factions = ew.factions as typeof extractedData.value.factions
    }
    if (Array.isArray(ew.timeline) && ew.timeline.length) {
      extractedData.value.timeline = ew.timeline as typeof extractedData.value.timeline
    }
    stage.value = 'done'
    messages.value.push({
      role: 'assistant',
      content: t('world.document_processed').replace('{name}', file.name),
    })
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : t('world.upload_failed')
  } finally {
    uploadLoading.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

async function handleFileInput(event: Event): Promise<void> {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  await processFile(file)
}

function handleDragOver(e: DragEvent): void {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave(): void {
  isDragging.value = false
}

async function handleDrop(e: DragEvent): Promise<void> {
  e.preventDefault()
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  await processFile(file)
}

function goToCharacters(): void {
  router.push('/characters')
}
</script>

<template>
  <div class="space-y-6 fade-in-up">
    <div class="page-header">
      <div class="flex items-start gap-4">
        <div class="w-12 h-12 rounded-seal flex items-center justify-center flex-shrink-0 seal-glow" style="background: var(--gradient-chop-seal);">
          <Globe :size="22" class="text-white" />
        </div>
        <div>
          <h1 class="font-display">{{ t('world.title') }}</h1>
          <p class="text-sm text-muted italic mt-1">{{ t('world.page_subtitle') }}</p>
        </div>
      </div>
      <button
        v-if="(sessionId || hasExtractedData) && !finalized"
        @click="resetWorld"
        class="btn btn-danger btn-sm"
      >
        {{ t('world.reset') }}
      </button>
    </div>
    <div class="rule-ornament rule-ornament-diamond text-xs">
      <span class="font-display small-caps tracking-widest opacity-70">WORLD BUILDING</span>
    </div>

    <div v-if="error" class="error-banner">
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
            :class="stageStatus(s) === 'completed' ? 'bg-editor' : 'bg-ink-edge'"
          />
        </div>
        <div class="ml-auto text-xs text-muted">
          {{ t('world.completeness') }}: {{ Math.round(completeness * 100) }}%
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2">
          <div
            v-if="!sessionId && !loading && messages.length === 0 && !hasExtractedData"
            class="card overflow-hidden"
          >
            <div class="flex border-b border-ink-edge">
              <button
                @click="activeEntryTab = 'idea'"
                class="flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors relative"
                :class="activeEntryTab === 'idea'
                  ? 'text-chop'
                  : 'text-muted hover:text-parchment-dim'"
              >
                <Sparkles :size="14" />
                {{ t('world.new') }}
                <span
                  v-if="activeEntryTab === 'idea'"
                  class="absolute bottom-0 left-0 right-0 h-0.5 bg-chop"
                />
              </button>
              <button
                @click="activeEntryTab = 'upload'"
                class="flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors relative"
                :class="activeEntryTab === 'upload'
                  ? 'text-chop'
                  : 'text-muted hover:text-parchment-dim'"
              >
                <UploadCloud :size="14" />
                {{ t('world.upload') }}
                <span
                  v-if="activeEntryTab === 'upload'"
                  class="absolute bottom-0 left-0 right-0 h-0.5 bg-chop"
                />
              </button>
            </div>

            <div class="p-8">
              <div class="max-w-md mx-auto text-center space-y-4">
                <div class="flex justify-center">
                  <div class="w-14 h-14 rounded-full bg-chop/10 flex items-center justify-center">
                    <component
                      :is="activeEntryTab === 'idea' ? Sparkles : UploadCloud"
                      :size="24"
                      class="text-chop"
                    />
                  </div>
                </div>

                <template v-if="activeEntryTab === 'idea'">
                  <h2 class="text-lg font-semibold text-parchment">
                    {{ t('world.welcome_title') }}
                  </h2>
                  <p class="text-sm text-parchment-dim leading-relaxed">
                    {{ t('world.welcome_desc') }}
                  </p>
                  <form
                    @submit.prevent="handleSend(seedIdea)"
                    class="flex gap-2 pt-2"
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
                </template>

                <template v-else>
                  <h2 class="text-lg font-semibold text-parchment">
                    {{ t('world.upload_title') }}
                  </h2>
                  <p class="text-sm text-parchment-dim leading-relaxed">
                    {{ t('world.upload_desc') }}
                  </p>

                  <div
                    @click="triggerFilePick"
                    @dragover="handleDragOver"
                    @dragleave="handleDragLeave"
                    @drop="handleDrop"
                    class="mt-4 border-2 border-dashed rounded-lg p-8 cursor-pointer transition-all text-center"
                    :class="isDragging
                      ? 'border-chop bg-chop/5'
                      : uploadError
                        ? 'border-danger bg-danger-soft/30'
                        : 'border-ink-edge hover:border-chop-border hover:bg-ink-elevated/50'"
                  >
                    <input
                      ref="fileInputRef"
                      type="file"
                      :accept="acceptedFormats"
                      @change="handleFileInput"
                      class="hidden"
                      :disabled="uploadLoading"
                    >

                    <div v-if="uploadLoading" class="flex flex-col items-center gap-3">
                      <Loader2 :size="28" class="text-chop animate-spin" />
                      <p class="text-sm text-parchment-dim">{{ t('world.upload_processing') }}</p>
                    </div>

                    <div v-else-if="uploadError" class="flex flex-col items-center gap-2">
                      <p class="text-sm text-danger">{{ uploadError }}</p>
                      <p class="text-xs text-muted">{{ t('world.retry') }}</p>
                    </div>

                    <div v-else class="flex flex-col items-center gap-2">
                      <UploadCloud :size="28" class="text-muted" />
                      <p class="text-sm text-parchment-dim">{{ t('world.drop_hint') }}</p>
                      <p class="text-xs text-muted">{{ t('world.supported_formats') }}</p>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <div v-else-if="hasExtractedData && !sessionId" class="space-y-4">
            <div class="card p-6">
              <div class="flex items-center gap-3 mb-4">
                <div class="w-10 h-10 rounded-full bg-editor/15 flex items-center justify-center flex-shrink-0">
                  <Check :size="18" class="text-editor" />
                </div>
                <div>
                  <h2 class="text-base font-semibold text-parchment">
                    {{ t('world.upload_ready_title') }}
                  </h2>
                  <p class="text-sm text-muted mt-0.5">
                    {{ t('world.upload_ready_desc') }}
                  </p>
                </div>
              </div>

              <div v-if="extractedData.name" class="py-3 border-t border-ink-edge">
                <h3 class="text-sm font-semibold text-parchment">{{ t('world.sidebar_world') }}</h3>
                <p class="text-sm text-parchment-dim mt-1">{{ extractedData.name }}</p>
                <p v-if="extractedData.description" class="text-xs text-muted mt-1">{{ extractedData.description }}</p>
              </div>

              <div v-if="extractedData.rules?.length" class="py-3 border-t border-ink-edge">
                <h3 class="text-sm font-semibold text-parchment mb-2">{{ t('world.rules') }} ({{ extractedData.rules.length }})</h3>
                <ul class="space-y-1">
                  <li v-for="(rule, idx) in extractedData.rules" :key="idx" class="text-xs text-parchment-dim flex gap-2">
                    <span class="text-chop flex-shrink-0">-</span>
                    <span>{{ rule }}</span>
                  </li>
                </ul>
              </div>

              <div v-if="extractedData.locations?.length" class="py-3 border-t border-ink-edge">
                <h3 class="text-sm font-semibold text-parchment mb-2">{{ t('world.locations') }} ({{ extractedData.locations.length }})</h3>
                <div class="space-y-2">
                  <div v-for="(loc, idx) in extractedData.locations" :key="idx">
                    <p class="text-sm text-parchment-dim">{{ loc.name }}</p>
                    <p class="text-xs text-muted">{{ loc.description }}</p>
                  </div>
                </div>
              </div>

              <div v-if="extractedData.factions?.length" class="py-3 border-t border-ink-edge">
                <h3 class="text-sm font-semibold text-parchment mb-2">{{ t('world.factions') }} ({{ extractedData.factions.length }})</h3>
                <div class="space-y-2">
                  <div v-for="(faction, idx) in extractedData.factions" :key="idx">
                    <p class="text-sm text-parchment-dim">{{ faction.name }}</p>
                    <p class="text-xs text-muted">{{ faction.description }}</p>
                  </div>
                </div>
              </div>

              <div v-if="extractedData.timeline?.length" class="py-3 border-t border-ink-edge">
                <h3 class="text-sm font-semibold text-parchment mb-2">{{ t('world.timeline') }} ({{ extractedData.timeline.length }})</h3>
                <div class="space-y-2">
                  <div v-for="(entry, idx) in extractedData.timeline" :key="idx" class="flex gap-2">
                    <span class="text-xs text-chop flex-shrink-0 min-w-[4rem]">{{ entry.date }}</span>
                    <div>
                      <p class="text-xs text-parchment-dim">{{ entry.event }}</p>
                      <p v-if="entry.description" class="text-xs text-muted">{{ entry.description }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div class="flex gap-3 justify-center pt-4 border-t border-ink-edge mt-2">
                <button @click="finalizeWorld" :disabled="loading" class="btn btn-primary">
                  <Check :size="14" />
                  {{ loading ? t('world.finalizing') : t('world.finalize') }}
                </button>
                <button @click="resetWorld" class="btn btn-secondary">
                  {{ t('world.start_again') }}
                </button>
              </div>
            </div>
          </div>

          <div v-else class="h-[500px]">
            <ChatPanel
              :messages="messages"
              :loading="loading"
              :placeholder="t('world.idea_placeholder')"
              @send="handleSend"
            />
          </div>
        </div>

        <div class="space-y-4">
          <template v-if="hasExtractedData && !sessionId">
            <div class="card p-4">
              <h3 class="text-sm font-semibold text-parchment mb-2 flex items-center gap-2">
                <Check :size="14" class="text-editor" />
                {{ t('world.upload_extracted') }}
              </h3>
              <div class="grid grid-cols-2 gap-2 text-center">
                <div class="bg-ink-elevated rounded p-2">
                  <div class="text-lg font-bold text-chop">{{ extractedData.rules?.length || 0 }}</div>
                  <div class="text-[0.65rem] text-muted">{{ t('world.rules') }}</div>
                </div>
                <div class="bg-ink-elevated rounded p-2">
                  <div class="text-lg font-bold text-chop">{{ extractedData.locations?.length || 0 }}</div>
                  <div class="text-[0.65rem] text-muted">{{ t('world.locations') }}</div>
                </div>
                <div class="bg-ink-elevated rounded p-2">
                  <div class="text-lg font-bold text-chop">{{ extractedData.factions?.length || 0 }}</div>
                  <div class="text-[0.65rem] text-muted">{{ t('world.factions') }}</div>
                </div>
                <div class="bg-ink-elevated rounded p-2">
                  <div class="text-lg font-bold text-chop">{{ extractedData.timeline?.length || 0 }}</div>
                  <div class="text-[0.65rem] text-muted">{{ t('world.timeline') }}</div>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="hasExtractedData">
            <div v-if="extractedData.name" class="card p-4">
              <h3 class="text-sm font-semibold text-parchment mb-2">
                {{ t('world.sidebar_world') }}
              </h3>
              <p class="text-sm text-parchment-dim">{{ extractedData.name }}</p>
              <p v-if="extractedData.description" class="text-xs text-muted mt-1">
                {{ extractedData.description }}
              </p>
            </div>

            <div v-if="extractedData.rules?.length" class="card p-4">
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

            <div v-if="extractedData.locations?.length" class="card p-4">
              <h3 class="text-sm font-semibold text-parchment mb-2">
                {{ t('world.locations') }}
              </h3>
              <div class="space-y-2">
                <div v-for="(loc, idx) in extractedData.locations" :key="idx">
                  <p class="text-sm text-parchment-dim">{{ loc.name }}</p>
                  <p class="text-xs text-muted">{{ loc.description }}</p>
                </div>
              </div>
            </div>

            <div v-if="extractedData.factions?.length" class="card p-4">
              <h3 class="text-sm font-semibold text-parchment mb-2">
                {{ t('world.factions') }}
              </h3>
              <div class="space-y-2">
                <div v-for="(faction, idx) in extractedData.factions" :key="idx">
                  <p class="text-sm text-parchment-dim">{{ faction.name }}</p>
                  <p class="text-xs text-muted">{{ faction.description }}</p>
                </div>
              </div>
            </div>

            <div v-if="extractedData.timeline?.length" class="card p-4">
              <h3 class="text-sm font-semibold text-parchment mb-2">
                {{ t('world.timeline') }}
              </h3>
              <div class="space-y-2">
                <div v-for="(entry, idx) in extractedData.timeline" :key="idx" class="flex gap-2">
                  <span class="text-xs text-chop flex-shrink-0 min-w-[4rem]">{{ entry.date }}</span>
                  <div>
                    <p class="text-xs text-parchment-dim">{{ entry.event }}</p>
                    <p v-if="entry.description" class="text-xs text-muted">{{ entry.description }}</p>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <div v-else class="card p-6 text-center text-muted text-sm">
            <Globe :size="24" class="mx-auto mb-2 opacity-40" />
            <p>{{ t('world.start_hint') }}</p>
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
          class="btn btn-primary btn-lg"
        >
          <Check :size="16" />
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
        <p class="text-sm text-muted">{{ t('world.finalized_message') }}</p>
      </div>

      <div class="card p-6 space-y-4">
        <div>
          <h3 class="text-xl font-semibold text-parchment">
            {{ worldState.name || t('world.unnamed') }}
          </h3>
          <p v-if="worldState.description" class="text-sm text-parchment-dim mt-1">
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
        <button @click="goToCharacters" class="btn btn-primary">
          {{ t('world.proceed_chars') }}
        </button>
        <button @click="resetWorld" class="btn btn-secondary">
          {{ t('world.start_again') }}
        </button>
      </div>
    </div>
  </div>
</template>
