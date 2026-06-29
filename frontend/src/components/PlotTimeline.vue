<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { BookOpen, GripVertical, Plus, Pencil, Trash2, List } from 'lucide-vue-next'
import Sortable from 'sortablejs'
import type { PlotOutline, SceneSpec } from '../types/api'
import { useI18n } from '../i18n'

const { t } = useI18n()

const props = defineProps<{
  outline: PlotOutline | null
}>()

const emit = defineEmits<{
  selectScene: [scene: SceneSpec]
  reorder: [actId: string, sceneIds: string[]]
  addScene: [actId: string]
  editScene: [scene: SceneSpec]
  deleteScene: [id: string]
}>()

const sortableInstances = new Map<string, Sortable>()
const actContainerRefs = ref<Record<string, HTMLElement | null>>({})

function setActContainerRef(actId: string, el: HTMLElement | null): void {
  actContainerRefs.value[actId] = el
}

function initSortable(actId: string, el: HTMLElement): void {
  const existing = sortableInstances.get(actId)
  if (existing) {
    existing.destroy()
    sortableInstances.delete(actId)
  }

  const instance = Sortable.create(el, {
    handle: '.drag-handle',
    animation: 150,
    ghostClass: 'opacity-50',
    chosenClass: 'sortable-chosen',
    onEnd(_evt) {
      const items = Array.from(el.querySelectorAll('[data-scene-id]'))
      const sceneIds = items.map((item) => (item as HTMLElement).dataset.sceneId!)
      emit('reorder', actId, sceneIds)
    },
  })

  sortableInstances.set(actId, instance)
}

function initAllSortables(): void {
  if (!props.outline) return
  nextTick(() => {
    for (const act of props.outline!.acts) {
      const el = actContainerRefs.value[act.id]
      if (el) {
        initSortable(act.id, el)
      }
    }
  })
}

watch(() => props.outline, () => {
  initAllSortables()
}, { immediate: true })

onBeforeUnmount(() => {
  for (const instance of sortableInstances.values()) {
    instance.destroy()
  }
  sortableInstances.clear()
})
</script>

<template>
  <div v-if="outline" class="space-y-6 stagger-children">
    <div class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-full bg-gold-soft flex items-center justify-center border border-gold/30">
            <BookOpen :size="18" class="text-gold-light" />
          </div>
          <div>
            <h2 class="text-xl font-display font-semibold text-parchment">{{ outline.title }}</h2>
            <p class="text-xs text-parchment-dim mt-0.5">{{ outline.description }}</p>
          </div>
        </div>
        <span class="badge badge-gold">
          <List :size="11" />
          {{ outline.structure }}
        </span>
      </div>
    </div>

    <div v-for="act in outline.acts" :key="act.id" class="relative">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-9 h-9 rounded-full bg-gradient-chop flex items-center justify-center text-sm font-bold text-white shadow-md seal-glow flex-shrink-0">
          {{ act.number }}
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="text-base font-display font-semibold text-parchment">{{ act.title }}</h3>
          <p v-if="act.summary" class="text-xs text-muted">{{ act.summary }}</p>
        </div>
        <button
          @click="emit('addScene', act.id)"
          class="btn btn-ghost btn-sm text-chop"
        >
          <Plus :size="13" />
          Add Scene
        </button>
      </div>
      <div
        class="ml-4 pl-6 border-l-2 border-ink-edge space-y-3 relative"
        :ref="(el) => setActContainerRef(act.id, el as HTMLElement | null)"
      >
        <div class="absolute left-0 top-0 bottom-0 w-px bg-gradient-to-b from-chop/30 via-chop/10 to-transparent -translate-x-[2px]" />

        <div
          v-for="scene in act.scenes"
          :key="scene.id"
          :data-scene-id="scene.id"
          class="card p-3.5 cursor-pointer [&.sortable-chosen]:cursor-grabbing hover:border-chop-border group"
          @click="emit('selectScene', scene)"
        >
          <div class="flex items-start gap-2.5">
            <div
              class="drag-handle flex-shrink-0 flex flex-col gap-0.5 pt-1 cursor-grab text-muted hover:text-parchment-dim transition-colors select-none opacity-0 group-hover:opacity-100"
              @click.stop
              :title="t('plot.drag_hint')"
            >
              <GripVertical :size="14" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1.5">
                <span class="text-[10px] text-muted font-mono bg-ink-bg-deep px-1.5 py-0.5 rounded">#{{ scene.order }}</span>
                <h4 class="text-sm font-display font-medium text-parchment truncate">{{ scene.title }}</h4>
              </div>
              <p class="text-xs text-muted line-clamp-2 leading-relaxed">{{ scene.description }}</p>
              <div class="mt-2.5 flex flex-wrap gap-1">
                <span
                  v-for="char in scene.characters?.slice(0, 3)"
                  :key="char"
                  class="badge badge-accent text-[10px] py-0"
                >
                  {{ char }}
                </span>
                <span
                  v-if="scene.characters && scene.characters.length > 3"
                  class="badge badge-muted text-[10px] py-0"
                >
                  +{{ scene.characters.length - 3 }}
                </span>
              </div>
            </div>
            <div class="flex items-center gap-0.5 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                @click.stop="emit('editScene', scene)"
                class="btn btn-ghost p-1.5 text-muted hover:text-chop"
                title="Edit"
              >
                <Pencil :size="12" />
              </button>
              <button
                @click.stop="emit('deleteScene', scene.id)"
                class="btn btn-ghost p-1.5 text-muted hover:text-danger"
                title="Delete"
              >
                <Trash2 :size="12" />
              </button>
            </div>
          </div>
        </div>
        <div v-if="act.scenes.length === 0" class="empty-state py-8">
          <p class="empty-state-text">No scenes yet. Click "+ Add Scene" to create one.</p>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="empty-state h-64">
    <p class="empty-state-text">Select or create a plot outline to view the timeline</p>
  </div>
</template>

<style scoped>
.bg-gradient-chop {
  background: var(--gradient-chop-seal);
}
</style>
