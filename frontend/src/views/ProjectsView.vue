<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '../i18n'
import { useProjects } from '../composables/useProjects'
import { useAssistant } from '../composables/useAssistant'
import { FolderPlus, Trash2, Clock, Calendar, Orbit } from 'lucide-vue-next'

const { t } = useI18n()
const router = useRouter()
const { projects, loading, error, fetchProjects, createProject, deleteProject } = useProjects()
const assistant = useAssistant()

const showCreateDialog = ref(false)
const newName = ref('')
const newSeedIdea = ref('')
const creating = ref(false)
const createError = ref('')

const hasProjects = computed(() => !loading.value && projects.value.length > 0)

let unregisterActions: Array<() => void> = []

onMounted(() => {
  fetchProjects()
  unregisterActions.push(
    assistant.registerPageAction({
      id: 'create-project',
      label: '新建项目',
      description: '创建一个新的故事项目',
      primary: true,
      handler: () => {
        openCreateDialog()
      },
    }),
    assistant.registerPageSuggestion({
      text: '直接开始一键生成',
      action: () => router.push('/pipeline'),
    }),
    assistant.registerPageSuggestion({
      text: '开始互动创作引导',
      action: () => router.push('/interactive'),
    }),
  )
})

onUnmounted(() => {
  unregisterActions.forEach((fn) => fn())
  unregisterActions = []
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
    world: 'badge-blue',
    characters: 'badge-purple',
    plot: 'badge-gold',
    scenes: 'badge-cyan',
    writing: 'badge-gold',
  }
  return classMap[stage] || 'badge-offline'
}
</script>

<template>
  <div class="projects-view">
    <section
      class="hero-section-hsr"
      :class="{ 'hero-compact-hsr': hasProjects }"
    >
      <div class="hero-content-hsr">
        <div v-if="!hasProjects" class="hero-icon-wrapper-hsr">
          <div class="hero-icon-hsr animate-float">
            <Orbit :size="40" />
          </div>
        </div>
        <div v-else class="hero-icon-wrapper-hsr hero-icon-small-hsr">
          <div class="hero-icon-hsr hero-icon-seal-hsr">
            <Orbit :size="22" />
          </div>
        </div>
        <h1 class="hero-title-hsr text-gold-gradient text-glow-gold" :class="{ 'hero-title-compact-hsr': hasProjects }">
          {{ t('projects.title') }}
        </h1>
        <div v-if="!hasProjects" class="divider-hsr hero-divider-hsr">
          <span class="hero-subtitle-hsr">{{ t('app.title') }}</span>
        </div>
        <p v-if="!hasProjects" class="hero-tagline-hsr">{{ t('projects.empty') }}</p>
        <button v-if="!hasProjects" @click="openCreateDialog" class="btn-hsr-primary hero-cta-hsr">
          <FolderPlus :size="18" />
          {{ t('projects.new') }}
        </button>
        <button v-else @click="openCreateDialog" class="btn-hsr-primary hero-cta-compact-hsr">
          <FolderPlus :size="16" />
          {{ t('projects.new') }}
        </button>
      </div>
    </section>

    <div v-if="error" class="error-banner-hsr">
      {{ error }}
    </div>

    <div v-if="loading" class="projects-grid-hsr">
      <div v-for="n in 6" :key="n" class="skeleton-card-hsr">
        <div class="skeleton-shimmer-hsr"></div>
        <div class="skeleton-icon-hsr"></div>
        <div class="skeleton-line-hsr w-3/4"></div>
        <div class="skeleton-line-hsr w-1/2"></div>
        <div class="skeleton-line-hsr w-1/3"></div>
      </div>
    </div>

    <div v-else-if="projects.length === 0" class="empty-hsr">
      <Orbit :size="64" class="empty-hsr-icon" />
      <p class="empty-hsr-title">{{ t('projects.title') }}</p>
      <p class="empty-hsr-desc">{{ t('projects.empty') }}</p>
    </div>

    <div v-else class="projects-grid-hsr">
      <div
        v-for="project in projects"
        :key="project.id"
        class="glass-card project-card-hsr"
        @click="openProject(project.id)"
      >
        <button
          class="delete-btn-hsr"
          @click="handleDelete(project.id, project.name, $event)"
          :title="t('general.delete')"
        >
          <Trash2 :size="14" />
        </button>

        <div class="project-card-header-hsr">
          <div class="project-icon-hsr">
            <Orbit :size="18" />
          </div>
          <div class="project-info-hsr">
            <h3 class="project-name-hsr">{{ project.name }}</h3>
            <p v-if="project.seed_idea" class="project-seed-hsr">{{ project.seed_idea }}</p>
          </div>
        </div>

        <div v-if="project.last_stage && project.last_stage !== 'idle'" class="project-badge-hsr">
          <span :class="['badge-hsr', stageBadgeClass(project.last_stage)]">
            {{ stageLabel(project.last_stage) }}
          </span>
        </div>

        <div class="project-meta-hsr">
          <div v-if="project.updated_at" class="meta-item-hsr">
            <Clock :size="12" class="meta-icon-hsr" />
            <span>{{ formatDate(project.updated_at) }}</span>
          </div>
          <div v-if="project.created_at" class="meta-item-hsr">
            <Calendar :size="12" class="meta-icon-hsr" />
            <span>{{ formatDate(project.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showCreateDialog" class="modal-overlay-hsr" @click.self="closeCreateDialog">
        <div class="modal-panel-hsr modal-content-hsr">
          <div class="modal-header-hsr">
            <div class="modal-icon-hsr">
              <FolderPlus :size="20" />
            </div>
            <h2 class="modal-title-hsr">{{ t('projects.new') }}</h2>
          </div>

          <div class="modal-body-hsr">
            <div class="field-group-hsr">
              <label class="field-label-hsr">{{ t('projects.name') }}</label>
              <input
                v-model="newName"
                type="text"
                :placeholder="t('projects.name_placeholder')"
                class="input"
                @keydown.enter="handleCreate"
                autofocus
              />
            </div>

            <div class="field-group-hsr">
              <label class="field-label-hsr">{{ t('projects.seed_idea') }}</label>
              <textarea
                v-model="newSeedIdea"
                :placeholder="t('projects.seed_idea_placeholder')"
                rows="3"
                class="input"
              />
            </div>

            <div v-if="createError" class="error-banner-hsr">{{ createError }}</div>
          </div>

          <div class="modal-footer-hsr">
            <button @click="closeCreateDialog" class="btn-hsr-secondary">
              {{ t('general.cancel') }}
            </button>
            <button @click="handleCreate" :disabled="creating || !newName.trim()" class="btn-hsr-primary">
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
  padding: 2rem 1.5rem;
  position: relative;
  z-index: 1;
}

.hero-section-hsr {
  text-align: center;
  padding: 3rem 1.5rem 2.5rem;
  margin-bottom: 2.5rem;
  position: relative;
}

.hero-section-hsr.hero-compact-hsr {
  text-align: left;
  padding: 0 0 1.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid rgba(212, 168, 67, 0.15);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hero-section-hsr.hero-compact-hsr .hero-content-hsr {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  width: 100%;
}

.hero-icon-wrapper-hsr {
  margin-bottom: 1.25rem;
}

.hero-icon-hsr {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(212, 168, 67, 0.15), rgba(240, 208, 120, 0.08));
  color: #d4a843;
  border: 1px solid rgba(212, 168, 67, 0.3);
  box-shadow: 0 0 30px rgba(212, 168, 67, 0.2),
              inset 0 1px 0 rgba(255,255,255,0.1);
  position: relative;
}

.hero-icon-hsr::before {
  content: '';
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  border: 1px solid rgba(212, 168, 67, 0.15);
  animation: ringPulse 3s ease-in-out infinite;
}

@keyframes ringPulse {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.05); }
}

.hero-title-hsr {
  font-size: clamp(2rem, 5vw, 2.75rem);
  font-weight: 700;
  margin: 0 0 0.75rem;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.hero-divider-hsr {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 1rem auto;
  max-width: 300px;
}

.hero-subtitle-hsr {
  font-size: 0.8125rem;
  color: #6b6780;
  letter-spacing: 0.12em;
  padding: 0 1rem;
  white-space: nowrap;
  text-transform: uppercase;
}

.hero-tagline-hsr {
  font-size: 0.9375rem;
  color: #a09cb8;
  margin: 1rem auto 1.5rem;
  max-width: 40ch;
  line-height: 1.7;
}

.hero-cta-hsr {
  margin-top: 0.5rem;
  padding: 12px 32px;
  font-size: 0.9375rem;
}

.hero-icon-small-hsr {
  margin-bottom: 0 !important;
}

.hero-icon-seal-hsr {
  width: 40px !important;
  height: 40px !important;
  border-radius: 10px !important;
}

.hero-icon-seal-hsr::before {
  display: none;
}

.hero-title-compact-hsr {
  font-size: 1.375rem !important;
  margin: 0 !important;
  flex: 1;
  text-align: left;
}

.hero-cta-compact-hsr {
  flex-shrink: 0;
  padding: 8px 18px;
  font-size: 0.8125rem;
}

.projects-grid-hsr {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1.25rem;
}

@media (min-width: 640px) {
  .projects-grid-hsr {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .projects-grid-hsr {
    grid-template-columns: repeat(3, 1fr);
  }
}

.project-card-hsr {
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.project-card-hsr:hover {
  transform: translateY(-3px);
  border-color: rgba(212, 168, 67, 0.4);
  box-shadow: 0 8px 32px rgba(0,0,0,0.3), 0 0 20px rgba(212, 168, 67, 0.2);
}

.project-card-header-hsr {
  display: flex;
  align-items: flex-start;
  gap: 0.875rem;
  margin-bottom: 1rem;
  padding-right: 2rem;
}

.project-icon-hsr {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(212, 168, 67, 0.12), rgba(240, 208, 120, 0.06));
  border: 1px solid rgba(212, 168, 67, 0.2);
  color: #d4a843;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.3s;
}

.project-card-hsr:hover .project-icon-hsr {
  border-color: rgba(212, 168, 67, 0.4);
  box-shadow: 0 0 12px rgba(212, 168, 67, 0.2);
}

.project-info-hsr {
  min-width: 0;
  flex: 1;
}

.project-name-hsr {
  font-size: 1rem;
  font-weight: 600;
  color: #e8e6f0;
  margin: 0;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.project-seed-hsr {
  font-size: 0.75rem;
  color: #6b6780;
  margin: 0.35rem 0 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.project-badge-hsr {
  margin-bottom: 0.875rem;
}

.project-meta-hsr {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-top: 0.875rem;
  border-top: 1px solid rgba(100, 95, 128, 0.15);
}

.meta-item-hsr {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: #6b6780;
  font-variant-numeric: tabular-nums;
}

.meta-icon-hsr {
  opacity: 0.7;
}

.delete-btn-hsr {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: transparent;
  color: #6b6780;
  border: none;
  cursor: pointer;
  opacity: 0;
  transform: scale(0.9);
  transition: all 0.2s;
}

.delete-btn-hsr:hover {
  background: rgba(248, 113, 113, 0.1);
  color: #f87171;
  opacity: 1 !important;
  transform: scale(1);
}

.project-card-hsr:hover .delete-btn-hsr {
  opacity: 0.7;
  transform: scale(1);
}

.skeleton-card-hsr {
  background: rgba(20, 24, 50, 0.6);
  border: 1px solid rgba(100, 95, 128, 0.1);
  border-radius: 12px;
  padding: 1.25rem;
  position: relative;
  overflow: hidden;
}

.skeleton-shimmer-hsr {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(212, 168, 67, 0.04) 50%,
    transparent 100%
  );
  animation: skeletonShimmer 1.8s infinite;
}

.skeleton-icon-hsr {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 10px;
  background: rgba(30, 35, 70, 0.5);
  margin-bottom: 0.875rem;
}

.skeleton-line-hsr {
  height: 0.625rem;
  background: rgba(30, 35, 70, 0.5);
  border-radius: 4px;
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

.modal-content-hsr {
  padding: 1.5rem;
}

.modal-header-hsr {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.modal-icon-hsr {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(212, 168, 67, 0.15), rgba(240, 208, 120, 0.08));
  border: 1px solid rgba(212, 168, 67, 0.25);
  color: #d4a843;
}

.modal-title-hsr {
  font-size: 1.125rem;
  font-weight: 600;
  color: #e8e6f0;
  margin: 0;
}

.modal-body-hsr {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field-group-hsr {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field-label-hsr {
  font-size: 0.8125rem;
  font-weight: 500;
  color: #a09cb8;
  letter-spacing: 0.02em;
}

.modal-footer-hsr {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.error-banner-hsr {
  padding: 0.75rem 1rem;
  background: rgba(248, 113, 113, 0.08);
  border: 1px solid rgba(248, 113, 113, 0.2);
  border-radius: 8px;
  color: #f87171;
  font-size: 0.8125rem;
  margin-bottom: 1rem;
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-shimmer-hsr {
    animation: none;
  }
  .hero-icon-hsr::before {
    animation: none;
  }
  .hero-icon-hsr {
    animation: none;
  }
}
</style>
