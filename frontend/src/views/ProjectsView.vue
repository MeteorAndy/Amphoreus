<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
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

const hasProjects = computed(() => !loading.value && projects.value.length > 0)

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

function stageBadgeClass(stage: string): string {
  const classMap: Record<string, string> = {
    world: 'badge-globe',
    characters: 'badge-accent',
    plot: 'badge-gold',
    scenes: 'badge-editor',
    writing: 'badge-accent',
  }
  return classMap[stage] || 'badge-muted'
}
</script>

<template>
  <div class="projects-view">
    <section
      class="hero-section corner-flourish fade-in-up"
      :class="{ 'hero-compact': hasProjects }"
    >
      <div class="stagger-children">
        <div v-if="!hasProjects" class="hero-icon-wrapper">
          <div class="hero-icon">
            <BookOpen :size="40" />
          </div>
        </div>
        <div v-else class="hero-icon-wrapper hero-icon-small">
          <div class="hero-icon hero-icon-seal">
            <BookOpen :size="24" />
          </div>
        </div>
        <h1 class="hero-title font-display" :class="{ 'hero-title-compact': hasProjects }">
          {{ t('projects.title') }}
        </h1>
        <div class="rule-ornament" :class="hasProjects ? 'rule-ornament-line' : 'rule-ornament-diamond'">
          <span v-if="!hasProjects" class="hero-subtitle">{{ t('app.title') }}</span>
        </div>
        <p v-if="!hasProjects" class="hero-tagline">{{ t('projects.empty') }}</p>
        <button v-if="!hasProjects" @click="openCreateDialog" class="btn btn-primary btn-lg hero-cta">
          <FolderPlus :size="18" />
          {{ t('projects.new') }}
        </button>
        <button v-else @click="openCreateDialog" class="btn btn-primary hero-cta-compact">
          <FolderPlus :size="16" />
          {{ t('projects.new') }}
        </button>
      </div>
    </section>

    <div v-if="error" class="error-banner mb-6 fade-in-up">
      {{ error }}
    </div>

    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      <div v-for="n in 6" :key="n" class="skeleton-card">
        <div class="skeleton-shimmer"></div>
        <div class="skeleton-icon"></div>
        <div class="skeleton-line w-3/4"></div>
        <div class="skeleton-line w-1/2"></div>
        <div class="skeleton-line w-1/3"></div>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 stagger-children">
      <div
        v-for="project in projects"
        :key="project.id"
        class="project-card card group relative"
        @click="openProject(project.id)"
      >
        <button
          class="delete-btn"
          @click="handleDelete(project.id, project.name, $event)"
          :title="t('general.delete')"
        >
          <Trash2 :size="14" />
        </button>

        <div class="flex items-start gap-3 mb-4 pr-8">
          <div class="project-icon seal-glow flex-shrink-0">
            <BookOpen :size="20" />
          </div>
          <div class="min-w-0 flex-1">
            <h3 class="project-name font-display truncate">{{ project.name }}</h3>
            <p v-if="project.seed_idea" class="project-seed line-clamp-2">{{ project.seed_idea }}</p>
          </div>
        </div>

        <div v-if="project.last_stage && project.last_stage !== 'idle'" class="mb-4">
          <span :class="['badge', stageBadgeClass(project.last_stage)]">
            {{ stageLabel(project.last_stage) }}
          </span>
        </div>

        <div class="project-meta">
          <div v-if="project.updated_at" class="meta-item">
            <Clock :size="12" class="meta-icon" />
            <span>{{ formatDate(project.updated_at) }}</span>
          </div>
          <div v-if="project.created_at" class="meta-item">
            <Calendar :size="12" class="meta-icon" />
            <span>{{ formatDate(project.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showCreateDialog" class="modal-overlay" @click.self="closeCreateDialog">
        <div class="modal-panel fade-in-up">
          <div class="modal-header">
            <div class="modal-icon">
              <FolderPlus :size="20" />
            </div>
            <h2 class="modal-title font-display">{{ t('projects.new') }}</h2>
          </div>

          <div class="space-y-5">
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

            <div v-if="createError" class="error-banner">{{ createError }}</div>
          </div>

          <div class="flex justify-end gap-3 mt-7">
            <button @click="closeCreateDialog" class="btn btn-secondary">
              {{ t('general.cancel') }}
            </button>
            <button @click="handleCreate" :disabled="creating || !newName.trim()" class="btn btn-primary">
              {{ creating ? t('projects.creating') : t('general.create') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.projects-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-section) var(--space-page);
}

.hero-section {
  text-align: center;
  padding: 3rem 1.5rem 2.5rem;
  margin-bottom: 2.5rem;
  position: relative;
}

.hero-section.hero-compact {
  text-align: left;
  padding: 0 0 1.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-ink-edge);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hero-section.hero-compact .stagger-children {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  width: 100%;
}

.hero-section.hero-compact.corner-flourish::before,
.hero-section.hero-compact.corner-flourish::after {
  display: none;
}

.hero-section.hero-compact .stagger-children > * {
  animation: none !important;
  opacity: 1 !important;
  transform: none !important;
}

.hero-icon-wrapper {
  margin-bottom: 1.25rem;
}

.hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: var(--radius-card);
  background: var(--gradient-chop-seal);
  color: #fff;
  box-shadow: var(--shadow-chop-glow),
              var(--shadow-elevated),
              inset 0 1px 0 rgba(255,255,255,0.2),
              inset 0 -1px 0 rgba(0,0,0,0.1);
  position: relative;
}

.hero-icon::before {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: calc(var(--radius-card) + 4px);
  border: 1px solid var(--color-chop-border);
  opacity: 0.5;
}

.hero-title {
  font-size: clamp(2rem, 5vw, 2.75rem);
  font-weight: 700;
  color: var(--color-parchment-bright);
  margin: 0 0 0.75rem;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.hero-subtitle {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  color: var(--color-muted);
  font-style: italic;
  letter-spacing: 0.08em;
  padding: 0 1rem;
  white-space: nowrap;
}

.hero-tagline {
  font-size: var(--text-base);
  color: var(--color-parchment-dim);
  margin: 1rem auto 1.5rem;
  max-width: 40ch;
  line-height: 1.7;
}

.hero-cta {
  margin-top: 0.5rem;
}

.hero-icon-small {
  margin-bottom: 0 !important;
}

.hero-icon-seal {
  width: 40px !important;
  height: 40px !important;
  border-radius: var(--radius-folio) !important;
}

.hero-icon-seal::before {
  display: none;
}

.hero-title-compact {
  font-size: var(--text-2xl) !important;
  margin: 0 !important;
  flex: 1;
  text-align: left;
}

.hero-cta-compact {
  flex-shrink: 0;
}

.rule-ornament-line {
  display: none;
}

.project-card {
  padding: 1.25rem;
  cursor: pointer;
  border-color: var(--color-chop-border);
  border-width: 1px;
}

.project-card:hover {
  border-color: rgba(200, 66, 59, 0.6);
  box-shadow: var(--shadow-chop-glow),
              var(--shadow-elevated),
              var(--shadow-inset),
              inset 0 0 0 1px rgba(237, 228, 211, 0.03);
  transform: translateY(-3px);
}

.project-icon {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: var(--radius-folio);
  background: var(--gradient-chop-seal);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2),
              inset 0 -1px 0 rgba(0,0,0,0.1);
}

.project-icon::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: calc(var(--radius-folio) + 2px);
  border: 1px solid var(--color-chop-border);
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-editorial);
}

.project-card:hover .project-icon::after {
  opacity: 1;
}

.project-name {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-parchment-bright);
  margin: 0;
  line-height: 1.4;
}

.project-seed {
  font-size: var(--text-xs);
  color: var(--color-muted);
  margin: 0.35rem 0 0;
  line-height: 1.5;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-top: 0.875rem;
  border-top: 1px solid var(--color-ink-edge);
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: var(--text-xs);
  color: var(--color-parchment-muted);
  font-variant-numeric: tabular-nums;
}

.meta-icon {
  opacity: 0.7;
}

.delete-btn {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: transparent;
  color: var(--color-muted);
  border: none;
  cursor: pointer;
  opacity: 0;
  transform: scale(0.9);
  transition: all var(--duration-fast) var(--ease-editorial);
}

.delete-btn:hover {
  background: var(--color-danger-soft);
  color: var(--color-danger);
  opacity: 1 !important;
  transform: scale(1);
}

.project-card:hover .delete-btn {
  opacity: 0.7;
  transform: scale(1);
}

.skeleton-card {
  background: var(--color-ink-panel);
  border: 1px solid var(--color-ink-edge);
  border-radius: var(--radius-card);
  padding: 1.25rem;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-card), var(--shadow-inset);
}

.skeleton-shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(237, 228, 211, 0.06) 50%,
    transparent 100%
  );
  animation: skeletonShimmer 1.8s infinite;
}

.skeleton-icon {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: var(--radius-folio);
  background: var(--color-ink-elevated);
  margin-bottom: 0.875rem;
}

.skeleton-line {
  height: 0.75rem;
  background: var(--color-ink-elevated);
  border-radius: 2px;
  margin-bottom: 0.5rem;
}

@keyframes skeletonShimmer {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(100%);
  }
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.modal-icon {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-folio);
  background: var(--gradient-chop-seal);
  color: #fff;
  box-shadow: var(--shadow-chop-glow),
              inset 0 1px 0 rgba(255,255,255,0.2);
}

.modal-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--color-parchment-bright);
  margin: 0;
}

.badge-globe {
  background: rgba(74, 127, 181, 0.15);
  color: #6a9fd4;
  border: 1px solid rgba(74, 127, 181, 0.3);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
}

html[data-theme="paper"] .badge-globe {
  background: rgba(52, 101, 154, 0.12);
  color: #34659a;
  border-color: rgba(52, 101, 154, 0.3);
}

html[data-theme="paper"] .hero-icon {
  box-shadow: 0 0 20px rgba(168, 54, 47, 0.12),
              var(--shadow-elevated-paper),
              inset 0 1px 0 rgba(255,255,255,0.3),
              inset 0 -1px 0 rgba(0,0,0,0.06);
}

html[data-theme="paper"] .project-card:hover {
  border-color: rgba(168, 54, 47, 0.5);
  box-shadow: 0 0 16px rgba(168, 54, 47, 0.1),
              var(--shadow-elevated),
              var(--shadow-inset-paper);
}

html[data-theme="paper"] .skeleton-card {
  background: var(--color-paper-cream);
  border-color: var(--color-paper-edge-soft);
  box-shadow: var(--shadow-card-paper), var(--shadow-inset-paper);
}

html[data-theme="paper"] .skeleton-icon,
html[data-theme="paper"] .skeleton-line {
  background: var(--color-paper-elevated);
}

html[data-theme="paper"] .skeleton-shimmer {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.5) 50%,
    transparent 100%
  );
}

html[data-theme="paper"] .project-meta {
  border-top-color: var(--color-paper-edge);
}

html[data-theme="paper"] .hero-compact {
  border-bottom-color: var(--color-paper-edge);
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-shimmer {
    animation: none;
  }
}
</style>
