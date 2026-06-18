<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '../i18n'
import { useProjects } from '../composables/useProjects'

const { t } = useI18n()
const router = useRouter()
const { projects, loading, error, fetchProjects, createProject, deleteProject } = useProjects()

// Create dialog state
const showCreateDialog = ref(false)
const newName = ref('')
const newSeedIdea = ref('')
const creating = ref(false)
const createError = ref('')

onMounted(() => {
  fetchProjects()
})

function openCreateDialog() {
  newName.value = ''
  newSeedIdea.value = ''
  createError.value = ''
  showCreateDialog.value = true
}

function closeCreateDialog() {
  showCreateDialog.value = false
}

async function handleCreate() {
  if (!newName.value.trim()) return
  creating.value = true
  createError.value = ''
  try {
    const id = await createProject(newName.value.trim(), newSeedIdea.value.trim())
    showCreateDialog.value = false
    router.push({ path: '/pipeline', query: { project: id } })
  } catch (e: unknown) {
    createError.value = (e as Error).message
  } finally {
    creating.value = false
  }
}

async function handleDelete(id: string, name: string) {
  const msg = `${t('projects.delete_confirm')}\n"${name}"`
  if (!window.confirm(msg)) return
  try {
    await deleteProject(id)
  } catch {
    // silently ignore — project list will still reflect local state
  }
}

function openProject(id: string) {
  router.push({ path: '/pipeline', query: { project: id } })
}

function formatDate(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-2xl font-bold text-parchment dark:text-white">{{ t('projects.title') }}</h1>
      <button
        @click="openCreateDialog"
        class="rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 transition-colors"
      >
        + {{ t('projects.new') }}
      </button>
    </div>

    <!-- Error banner -->
    <div
      v-if="error"
      class="mb-6 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 text-red-700 dark:text-red-400 text-sm"
    >
      {{ error }}
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="n in 6"
        :key="n"
        class="bg-white dark:bg-ink-elevated rounded-xl shadow-sm border border-ink-edge dark:border-ink-edge p-6 animate-pulse"
      >
        <div class="h-5 bg-ink-elevated dark:bg-ink-elevated rounded w-3/4 mb-3" />
        <div class="h-4 bg-ink-elevated dark:bg-ink-elevated rounded w-1/2 mb-2" />
        <div class="h-4 bg-ink-elevated dark:bg-ink-elevated rounded w-1/3" />
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!loading && projects.length === 0"
      class="flex flex-col items-center justify-center py-24 text-center"
    >
      <span class="text-5xl mb-4">📁</span>
      <p class="text-muted dark:text-parchment-dim text-lg mb-6">{{ t('projects.empty') }}</p>
      <button
        @click="openCreateDialog"
        class="rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium px-5 py-2.5 transition-colors"
      >
        + {{ t('projects.new') }}
      </button>
    </div>

    <!-- Project grid -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="project in projects"
        :key="project.id"
        class="group bg-white dark:bg-ink-elevated rounded-xl shadow-sm border border-ink-edge dark:border-ink-edge p-6 cursor-pointer hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-md transition-all relative"
        @click="openProject(project.id)"
      >
        <!-- Delete button -->
        <button
          class="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity text-parchment-dim hover:text-red-500 dark:hover:text-red-400 p-1 rounded"
          @click.stop="handleDelete(project.id, project.name)"
          :title="t('general.delete')"
        >
          ✕
        </button>

        <h2 class="text-base font-semibold text-parchment dark:text-white mb-3 pr-6 truncate">
          {{ project.name }}
        </h2>

        <!-- Last stage badge -->
        <div v-if="project.last_stage" class="mb-3">
          <span class="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-chop/15 dark:bg-chop/20/40 text-chop dark:text-chop">
            {{ t('projects.last_stage') }}: {{ project.last_stage }}
          </span>
        </div>

        <!-- Dates -->
        <div class="text-xs text-muted dark:text-parchment-dim space-y-1">
          <div v-if="project.updated_at">
            {{ t('projects.updated') }}: {{ formatDate(project.updated_at) }}
          </div>
          <div v-if="project.created_at">
            {{ t('projects.created') }}: {{ formatDate(project.created_at) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Create dialog -->
    <Teleport to="body">
      <div
        v-if="showCreateDialog"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        @click.self="closeCreateDialog"
      >
        <div class="bg-white dark:bg-ink-elevated rounded-2xl shadow-xl border border-ink-edge dark:border-ink-edge w-full max-w-md mx-4 p-6">
          <h2 class="text-lg font-semibold text-parchment dark:text-white mb-5">
            {{ t('projects.new') }}
          </h2>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-parchment-dim dark:text-parchment-dim mb-1">
                {{ t('projects.name') }}
              </label>
              <input
                v-model="newName"
                type="text"
                :placeholder="t('projects.name_placeholder')"
                class="w-full rounded-lg border border-ink-edge dark:border-ink-edge bg-white dark:bg-ink-elevated text-parchment dark:text-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                @keydown.enter="handleCreate"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-parchment-dim dark:text-parchment-dim mb-1">
                {{ t('projects.seed_idea') }}
              </label>
              <textarea
                v-model="newSeedIdea"
                :placeholder="t('projects.seed_idea_placeholder')"
                rows="3"
                class="w-full rounded-lg border border-ink-edge dark:border-ink-edge bg-white dark:bg-ink-elevated text-parchment dark:text-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            <div v-if="createError" class="text-sm text-red-600 dark:text-red-400">
              {{ createError }}
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button
              @click="closeCreateDialog"
              class="rounded-lg border border-ink-edge dark:border-ink-edge text-parchment-dim dark:text-parchment-dim font-medium px-4 py-2 hover:bg-ink-elevated dark:hover:bg-ink-elevated transition-colors text-sm"
            >
              {{ t('general.cancel') }}
            </button>
            <button
              @click="handleCreate"
              :disabled="creating || !newName.trim()"
              class="rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-4 py-2 transition-colors text-sm"
            >
              {{ creating ? t('projects.creating') : t('general.create') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
