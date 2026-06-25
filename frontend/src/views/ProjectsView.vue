<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '../i18n'
import { useProjects } from '../composables/useProjects'
import { FolderPlus, Trash2, Clock, Calendar, BookOpen } from 'lucide-vue-next'

const { t } = useI18n()
const router = useRouter()
const { projects, loading, error, fetchProjects, createProject, deleteProject } = useProjects()

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

async function handleDelete(id: string, name: string, e: Event) {
  e.stopPropagation()
  const msg = `${t('projects.delete_confirm')}\n"${name}"`
  if (!window.confirm(msg)) return
  try {
    await deleteProject(id)
  } catch {
    // silently ignore
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

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    idle: t('projects.last_stage'),
    world: t('nav.world'),
    characters: t('nav.characters'),
    plot: t('nav.plot'),
    scenes: t('nav.scene'),
    writing: t('nav.writer'),
  }
  return map[stage] || stage
}
</script>

<template>
  <div>
    <div class="page-header">
      <div>
        <h1>{{ t('projects.title') }}</h1>
        <p>{{ t('projects.empty') }}</p>
      </div>
      <button @click="openCreateDialog" class="btn btn-primary">
        <FolderPlus :size="14" />
        {{ t('projects.new') }}
      </button>
    </div>

    <div v-if="error" class="error-banner mb-6">
      {{ error }}
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="n in 6" :key="n" class="card p-5 animate-pulse">
        <div class="h-4 bg-ink-elevated rounded w-3/4 mb-3" />
        <div class="h-3 bg-ink-elevated rounded w-1/2 mb-2" />
        <div class="h-3 bg-ink-elevated rounded w-1/3" />
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading && projects.length === 0" class="empty-state">
      <div class="empty-state-icon">📁</div>
      <p class="empty-state-text">{{ t('projects.empty') }}</p>
      <button @click="openCreateDialog" class="btn btn-primary btn-lg">
        <FolderPlus :size="16" />
        {{ t('projects.new') }}
      </button>
    </div>

    <!-- Project grid -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="project in projects"
        :key="project.id"
        class="card p-5 cursor-pointer hover:border-chop/50 group relative"
        @click="openProject(project.id)"
      >
        <button
          class="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-danger-soft text-muted hover:text-danger"
          @click="handleDelete(project.id, project.name, $event)"
          :title="t('general.delete')"
        >
          <Trash2 :size="14" />
        </button>

        <div class="flex items-start gap-3 mb-3 pr-6">
          <div class="w-10 h-10 rounded-lg bg-chop/15 flex items-center justify-center flex-shrink-0">
            <BookOpen :size="18" class="text-chop" />
          </div>
          <div class="min-w-0">
            <h3 class="text-base font-semibold text-parchment truncate">{{ project.name }}</h3>
            <p v-if="project.seed_idea" class="text-xs text-muted mt-0.5 line-clamp-2">{{ project.seed_idea }}</p>
          </div>
        </div>

        <div v-if="project.last_stage && project.last_stage !== 'idle'" class="mb-3">
          <span class="badge badge-accent">
            {{ stageLabel(project.last_stage) }}
          </span>
        </div>

        <div class="flex items-center gap-3 text-xs text-muted pt-3 border-t border-ink-edge">
          <div v-if="project.updated_at" class="flex items-center gap-1">
            <Clock :size="11" />
            {{ formatDate(project.updated_at) }}
          </div>
          <div v-if="project.created_at" class="flex items-center gap-1">
            <Calendar :size="11" />
            {{ formatDate(project.created_at) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Create dialog -->
    <Teleport to="body">
      <div v-if="showCreateDialog" class="modal-overlay" @click.self="closeCreateDialog">
        <div class="modal-panel">
          <h2 class="text-lg font-semibold text-parchment mb-5">{{ t('projects.new') }}</h2>

          <div class="space-y-4">
            <div>
              <label class="field-label">{{ t('projects.name') }}</label>
              <input
                v-model="newName"
                type="text"
                :placeholder="t('projects.name_placeholder')"
                class="input"
                @keydown.enter="handleCreate"
                autofocus
              />
            </div>

            <div>
              <label class="field-label">{{ t('projects.seed_idea') }}</label>
              <textarea
                v-model="newSeedIdea"
                :placeholder="t('projects.seed_idea_placeholder')"
                rows="3"
                class="input"
              />
            </div>

            <div v-if="createError" class="text-sm text-danger">{{ createError }}</div>
          </div>

          <div class="flex justify-end gap-2 mt-6">
            <button @click="closeCreateDialog" class="btn btn-secondary btn-sm">
              {{ t('general.cancel') }}
            </button>
            <button @click="handleCreate" :disabled="creating || !newName.trim()" class="btn btn-primary btn-sm">
              {{ creating ? t('projects.creating') : t('general.create') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
