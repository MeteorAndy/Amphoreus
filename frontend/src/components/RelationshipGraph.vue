<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { Network } from 'lucide-vue-next'
import * as d3Force from 'd3-force'
import * as d3Selection from 'd3-selection'
import * as d3Drag from 'd3-drag'
import type { CharacterProfile, Relationship } from '../types/api'

const props = defineProps<{
  characters: CharacterProfile[]
  relationships: Relationship[]
}>()

const emit = defineEmits<{
  'select-character': [characterId: string]
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const svgRef = ref<SVGSVGElement | null>(null)

const tooltip = ref<{ visible: boolean; x: number; y: number; text: string }>({
  visible: false, x: 0, y: 0, text: '',
})

let simulation: d3Force.Simulation<SimNode, SimLink> | null = null

interface SimNode extends d3Force.SimulationNodeDatum {
  id: string
  name: string
  role: string
}

interface SimLink extends d3Force.SimulationLinkDatum<SimNode> {
  rel_type: string
  strength: number
  description: string
}

const nodePositions = ref<Map<string, { x: number; y: number }>>(new Map())
const linkPositions = ref<Array<{ x1: number; y1: number; x2: number; y2: number; strength: number; rel_type: string; description: string }>>([])

const WIDTH = ref(600)
const HEIGHT = 400

const ROLE_COLORS: Record<string, string> = {
  protagonist: 'var(--color-chop)',
  antagonist:  'var(--color-danger)',
  supporting:  'var(--color-editor)',
  minor:       'var(--color-gold)',
}
function roleColor(role: string): string {
  return ROLE_COLORS[role?.toLowerCase()] ?? 'var(--color-muted)'
}

function nodeLabel(name: string): string {
  return name.length > 12 ? name.slice(0, 11) + '…' : name
}

function buildSimulation() {
  if (!svgRef.value) return

  const w = WIDTH.value
  const h = HEIGHT

  const simNodes: SimNode[] = props.characters.map((c) => ({
    id: c.id,
    name: c.name,
    role: c.role,
  }))

  const idSet = new Set(simNodes.map((n) => n.id))
  const simLinks: SimLink[] = props.relationships
    .filter((r) => idSet.has(r.from_id) && idSet.has(r.to_id))
    .map((r) => ({
      source: r.from_id,
      target: r.to_id,
      rel_type: r.rel_type,
      strength: r.strength,
      description: r.description,
    }))

  if (simulation) simulation.stop()

  simulation = d3Force.forceSimulation<SimNode>(simNodes)
    .force('link', d3Force.forceLink<SimNode, SimLink>(simLinks)
      .id((d) => d.id)
      .distance(120)
      .strength(0.5))
    .force('charge', d3Force.forceManyBody().strength(-300))
    .force('center', d3Force.forceCenter(w / 2, h / 2))
    .force('collision', d3Force.forceCollide(30))
    .on('tick', () => {
      for (const n of simNodes) {
        n.x = Math.max(24, Math.min(w - 24, n.x ?? w / 2))
        n.y = Math.max(24, Math.min(h - 24, n.y ?? h / 2))
      }
      const posMap = new Map<string, { x: number; y: number }>()
      for (const n of simNodes) posMap.set(n.id, { x: n.x!, y: n.y! })
      nodePositions.value = posMap

      linkPositions.value = simLinks.map((l) => {
        const s = l.source as SimNode
        const t = l.target as SimNode
        return {
          x1: s.x ?? 0, y1: s.y ?? 0,
          x2: t.x ?? 0, y2: t.y ?? 0,
          strength: l.strength,
          rel_type: l.rel_type,
          description: l.description,
        }
      })
    })

  attachDrag(simNodes)
}

function attachDrag(simNodes: SimNode[]) {
  if (!svgRef.value) return
  const svg = d3Selection.select(svgRef.value)
  svg.selectAll<SVGGElement, SimNode>('.node-group')
    .data(simNodes, (d) => d.id)
    .call(
      d3Drag.drag<SVGGElement, SimNode>()
        .on('start', (event, d) => {
          if (!event.active) simulation?.alphaTarget(0.3).restart()
          d.fx = d.x; d.fy = d.y
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
        .on('end', (event, d) => {
          if (!event.active) simulation?.alphaTarget(0)
          d.fx = null; d.fy = null
        })
    )
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  if (containerRef.value) {
    WIDTH.value = containerRef.value.clientWidth || 600
    resizeObserver = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width
      if (w && Math.abs(w - WIDTH.value) > 10) {
        WIDTH.value = w
        buildSimulation()
      }
    })
    resizeObserver.observe(containerRef.value)
  }
  buildSimulation()
})

onUnmounted(() => {
  simulation?.stop()
  resizeObserver?.disconnect()
})

watch(
  () => [props.characters, props.relationships] as const,
  () => buildSimulation(),
  { deep: true }
)

function showTooltip(event: MouseEvent, text: string) {
  const svgRect = svgRef.value?.getBoundingClientRect()
  if (!svgRect) return
  tooltip.value = {
    visible: true,
    x: event.clientX - svgRect.left + 8,
    y: event.clientY - svgRect.top - 24,
    text,
  }
}

function hideTooltip() {
  tooltip.value.visible = false
}

const nodeList = computed(() =>
  props.characters.map((c) => ({
    id: c.id,
    name: c.name,
    role: c.role,
    color: roleColor(c.role),
    label: nodeLabel(c.name),
    pos: nodePositions.value.get(c.id) ?? { x: WIDTH.value / 2, y: HEIGHT / 2 },
  }))
)
</script>

<template>
  <div class="card overflow-hidden">
    <div class="px-4 py-3 border-b border-ink-edge flex items-center gap-2">
      <div class="w-8 h-8 rounded-full bg-chop-soft flex items-center justify-center">
        <Network :size="15" class="text-chop-light" />
      </div>
      <h3 class="text-sm font-display font-semibold text-parchment">Relationship Graph</h3>
    </div>
    <div ref="containerRef" class="relative">
      <div
        v-if="characters.length === 0"
        class="empty-state h-48"
      >
        <p class="empty-state-text">暂无角色数据 / No characters to display</p>
      </div>

      <svg
        v-else
        ref="svgRef"
        :width="WIDTH"
        :height="HEIGHT"
        class="w-full block"
        :viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
      >
        <defs>
          <marker
            id="rg-arrow"
            markerWidth="8"
            markerHeight="6"
            refX="28"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="var(--color-muted-soft)" opacity="0.7" />
          </marker>
        </defs>

        <line
          v-for="(link, idx) in linkPositions"
          :key="`link-${idx}`"
          :x1="link.x1"
          :y1="link.y1"
          :x2="link.x2"
          :y2="link.y2"
          stroke="var(--color-muted-soft)"
          :stroke-width="Math.max(1, link.strength / 2)"
          stroke-opacity="0.5"
          marker-end="url(#rg-arrow)"
          class="cursor-pointer transition-all hover:stroke-chop-light hover:stroke-opacity-80"
          @mouseenter="showTooltip($event, link.rel_type + (link.description ? ': ' + link.description : ''))"
          @mouseleave="hideTooltip"
        />

        <g
          v-for="node in nodeList"
          :key="node.id"
          class="node-group cursor-pointer"
          @click="emit('select-character', node.id)"
        >
          <circle
            :cx="node.pos.x"
            :cy="node.pos.y"
            r="20"
            :fill="node.color"
            fill-opacity="0.85"
            stroke="var(--color-ink-bg-deep)"
            stroke-width="2"
            class="transition-all hover:fill-opacity-100 hover:r-[22]"
            :style="{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))' }"
          />
          <text
            :x="node.pos.x"
            :y="node.pos.y"
            text-anchor="middle"
            dominant-baseline="central"
            fill="white"
            font-size="12"
            font-weight="600"
            class="pointer-events-none select-none"
          >{{ node.name.charAt(0) }}</text>
          <text
            :x="node.pos.x"
            :y="node.pos.y + 32"
            text-anchor="middle"
            fill="var(--color-muted)"
            font-size="11"
            font-family="var(--font-body)"
            class="pointer-events-none select-none"
          >{{ node.label }}</text>
        </g>
      </svg>

      <div
        v-if="tooltip.visible"
        class="absolute z-10 px-2.5 py-1.5 card text-xs text-parchment pointer-events-none max-w-48 whitespace-normal"
        :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
      >
        {{ tooltip.text }}
      </div>
    </div>
  </div>
</template>
