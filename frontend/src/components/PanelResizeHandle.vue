<script setup lang="ts">
import { ref, onUnmounted } from 'vue'

const emit = defineEmits<{
  resize: [deltaPx: number]
  reset: []
}>()

const isDragging = ref(false)
const indicatorX = ref(0)
const showIndicator = ref(false)
const isHovered = ref(false)

let startX = 0

function onPointerDown(e: PointerEvent): void {
  if (e.button !== 0) return
  e.preventDefault()
  isDragging.value = true
  showIndicator.value = true
  indicatorX.value = e.clientX
  startX = e.clientX
  document.body.classList.add('dragging-resize')
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp, { once: true })
}

function onPointerMove(e: PointerEvent): void {
  if (!isDragging.value) return
  const delta = startX - e.clientX
  emit('resize', delta)
  startX = e.clientX
  indicatorX.value = e.clientX
}

function onPointerUp(): void {
  if (!isDragging.value) return
  isDragging.value = false
  showIndicator.value = false
  document.body.classList.remove('dragging-resize')
  window.removeEventListener('pointermove', onPointerMove)
}

function onDoubleClick(): void {
  emit('reset')
}

onUnmounted(() => {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  document.body.classList.remove('dragging-resize')
})
</script>

<template>
  <div
    class="resize-handle"
    :class="{ 'is-dragging': isDragging, 'is-hovered': isHovered }"
    @pointerdown="onPointerDown"
    @pointerenter="isHovered = true"
    @pointerleave="isHovered = false"
    @dblclick="onDoubleClick"
    role="separator"
    aria-orientation="vertical"
    title="拖拽调整宽度，双击重置"
  >
    <div class="handle-grip" />
  </div>
  <div
    v-if="showIndicator"
    class="resize-indicator"
    :style="{ left: `${indicatorX}px` }"
  />
</template>

<style scoped>
.resize-handle {
  width: 4px;
  flex-shrink: 0;
  cursor: col-resize;
  position: relative;
  background: transparent;
  transition: background var(--duration-fast) var(--ease-editorial),
              width var(--duration-fast) var(--ease-editorial);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='4' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  z-index: 10;
}

.resize-handle:hover,
.resize-handle.is-hovered,
.resize-handle.is-dragging {
  width: 8px;
  background: var(--color-chop);
  background-image: linear-gradient(180deg,
    transparent 0%,
    rgba(200, 66, 59, 0.3) 10%,
    var(--color-chop) 50%,
    rgba(200, 66, 59, 0.3) 90%,
    transparent 100%
  );
}

.handle-grip {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 1px;
  height: 40px;
  background: var(--color-ink-edge);
  border-radius: 1px;
  opacity: 0.5;
  transition: opacity var(--duration-fast), background var(--duration-fast);
}

.resize-handle:hover .handle-grip,
.resize-handle.is-dragging .handle-grip {
  background: var(--color-parchment-bright);
  opacity: 0.9;
  box-shadow: 0 0 6px var(--color-chop-glow);
}

.resize-indicator {
  position: fixed;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--color-chop);
  box-shadow: 0 0 8px var(--color-chop-glow), 0 0 16px rgba(200, 66, 59, 0.3);
  z-index: 9999;
  pointer-events: none;
}

html[data-theme="paper"] .resize-handle:hover,
html[data-theme="paper"] .resize-handle.is-hovered,
html[data-theme="paper"] .resize-handle.is-dragging {
  background: var(--color-chop);
  background-image: linear-gradient(180deg,
    transparent 0%,
    rgba(168, 54, 47, 0.25) 10%,
    var(--color-chop) 50%,
    rgba(168, 54, 47, 0.25) 90%,
    transparent 100%
  );
}
</style>
