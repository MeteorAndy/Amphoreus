<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
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

// Map of actId → Sortable instance
const sortableInstances = new Map<string, Sortable>()
// Map of actId → container element ref
const actContainerRefs = ref<Record<string, HTMLElement | null>>({})

function setActContainerRef(actId: string, el: HTMLElement | null): void {
  actContainerRefs.value[actId] = el
}

function initSortable(actId: string, el: HTMLElement): void {
  // Destroy existing instance if any
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
  <div v-if="outline" class="space-y-6">
    <div class="bg-ink-panel rounded-lg border border-ink-edge p-4">
      <div class="flex items-center justify-between mb-2">
        <h2 class="text-lg font-semibold text-parchment">{{ outline.title }}</h2>
        <span class="text-xs text-muted bg-ink-elevated px-2 py-1 rounded-full">
          {{ outline.structure }}
        </span>
      </div>
      <p class="text-sm text-parchment-dim">{{ outline.description }}</p>
    </div>
    <div v-for="act in outline.acts" :key="act.id" class="relative">
      <div class="flex items-center gap-3 mb-3">
        <div class="w-8 h-8 rounded-full bg-chop flex items-center justify-center text-sm font-bold text-white">
          {{ act.number }}
        </div>
        <div>
          <h3 class="text-sm font-semibold text-parchment">{{ act.title }}</h3>
          <p v-if="act.summary" class="text-xs text-muted">{{ act.summary }}</p>
        </div>
        <button
          @click="emit('addScene', act.id)"
          class="ml-auto text-xs text-chop hover:text-chop transition-colors"
        >
          + Add Scene
        </button>
      </div>
      <div
        class="ml-4 pl-6 border-l-2 border-ink-edge space-y-3"
        :ref="(el) => setActContainerRef(act.id, el as HTMLElement | null)"
      >
        <div
          v-for="scene in act.scenes"
          :key="scene.id"
          :data-scene-id="scene.id"
          class="bg-ink-panel border border-ink-edge rounded-lg p-3 hover:border-ink-edge transition-colors cursor-pointer [&.sortable-chosen]:cursor-grabbing"
          @click="emit('selectScene', scene)"
        >
          <div class="flex items-start gap-2">
            <!-- Drag handle -->
            <div
              class="drag-handle flex-shrink-0 flex flex-col gap-0.5 pt-1 cursor-grab text-muted hover:text-parchment-dim transition-colors select-none"
              @click.stop
              :title="t('plot.drag_hint')"
            >
              <span class="block w-3.5 h-0.5 bg-current rounded-full"></span>
              <span class="block w-3.5 h-0.5 bg-current rounded-full"></span>
              <span class="block w-3.5 h-0.5 bg-current rounded-full"></span>
              <span class="block w-3.5 h-0.5 bg-current rounded-full"></span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-xs text-muted">#{{ scene.order }}</span>
                <h4 class="text-sm font-medium text-parchment truncate">{{ scene.title }}</h4>
              </div>
              <p class="text-xs text-muted line-clamp-2">{{ scene.description }}</p>
              <div class="mt-2 flex flex-wrap gap-1">
                <span
                  v-for="char in scene.characters?.slice(0, 3)"
                  :key="char"
                  class="text-xs text-chop bg-chop/20/30 px-1.5 py-0.5 rounded"
                >
                  {{ char }}
                </span>
                <span
                  v-if="scene.characters && scene.characters.length > 3"
                  class="text-xs text-muted"
                >
                  +{{ scene.characters.length - 3 }}
                </span>
              </div>
            </div>
            <div class="flex items-center gap-1 flex-shrink-0">
              <button
                @click.stop="emit('editScene', scene)"
                class="text-xs text-muted hover:text-chop transition-colors px-1"
              >
                Edit
              </button>
              <button
                @click.stop="emit('deleteScene', scene.id)"
                class="text-xs text-red-400 hover:text-red-300 transition-colors px-1"
              >
                Del
              </button>
            </div>
          </div>
        </div>
        <div v-if="act.scenes.length === 0" class="text-center py-6 text-muted text-sm">
          No scenes yet. Click "+ Add Scene" to create one.
        </div>
      </div>
    </div>
  </div>
  <div v-else class="flex items-center justify-center h-64 text-muted text-sm">
    Select or create a plot outline to view the timeline
  </div>
</template>
