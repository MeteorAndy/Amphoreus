<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import type { CharacterProfile, NetworkData } from '../types/api'

const props = defineProps<{
  characters: CharacterProfile[]
  networkData: NetworkData | null
}>()

const emit = defineEmits<{
  select: [characterId: string]
}>()

const svgRef = ref<SVGSVGElement | null>(null)
const dimensions = ref({ width: 600, height: 400 })

interface Node {
  id: string
  name: string
  x: number
  y: number
  label: string
}

interface Edge {
  source: string
  target: string
  strength: number
  type: string
}

const nodes = computed<Node[]>(() => {
  const count = props.characters.length
  const centerX = dimensions.value.width / 2
  const centerY = dimensions.value.height / 2
  const radius = Math.min(centerX, centerY) - 60

  return props.characters.map((char, idx) => {
    const angle = (2 * Math.PI * idx) / count - Math.PI / 2
    return {
      id: char.id,
      name: char.name,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
      label: char.name.length > 10 ? char.name.slice(0, 10) + '...' : char.name,
    }
  })
})

const edges = computed<Edge[]>(() => {
  if (!props.networkData?.edges) return []
  return props.networkData.edges.map((e: Record<string, unknown>) => ({
    source: String(e.source || e.from_id || ''),
    target: String(e.target || e.to_id || ''),
    strength: Number(e.strength || e.weight || 0.5),
    type: String(e.type || e.rel_type || ''),
  }))
})

function getNodeCenter(nodeId: string): { x: number; y: number } | null {
  const node = nodes.value.find((n) => n.id === nodeId)
  return node ? { x: node.x, y: node.y } : null
}

function getEdgeTargetEndPos(edge: Edge): { x: number; y: number } {
  // Default fallback
  const target = nodes.value.find((n) => n.id === edge.target)
  if (target) return { x: target.x, y: target.y }
  // Try partial match
  for (const node of nodes.value) {
    if (edge.target.includes(node.id) || node.id.includes(edge.target)) {
      return { x: node.x, y: node.y }
    }
  }
  return { x: 0, y: 0 }
}

onMounted(() => {
  if (svgRef.value) {
    const rect = svgRef.value.parentElement?.getBoundingClientRect()
    if (rect) {
      dimensions.value = { width: Math.max(rect.width, 300), height: 400 }
    }
  }
})
</script>

<template>
  <div class="bg-gray-900 rounded-lg border border-gray-800 p-4">
    <svg
      ref="svgRef"
      :width="dimensions.width"
      :height="dimensions.height"
      class="w-full"
    >
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#4f46e5" />
        </marker>
      </defs>
      <line
        v-for="(edge, idx) in edges"
        :key="`edge-${idx}`"
        :x1="getNodeCenter(edge.source)?.x ?? 0"
        :y1="getNodeCenter(edge.source)?.y ?? 0"
        :x2="getEdgeTargetEndPos(edge).x"
        :y2="getEdgeTargetEndPos(edge).y"
        stroke="#4f46e5"
        :stroke-width="Math.max(1, edge.strength * 3)"
        stroke-opacity="0.5"
      />
      <g
        v-for="node in nodes"
        :key="node.id"
        @click="emit('select', node.id)"
        class="cursor-pointer"
      >
        <circle
          :cx="node.x"
          :cy="node.y"
          r="24"
          class="fill-indigo-600 hover:fill-indigo-500 transition-colors"
          opacity="0.9"
        />
        <text
          :x="node.x"
          :y="node.y"
          text-anchor="middle"
          dominant-baseline="central"
          class="fill-white text-xs font-medium pointer-events-none"
          font-size="10"
        >
          {{ node.name.charAt(0) }}
        </text>
        <text
          :x="node.x"
          :y="node.y + 36"
          text-anchor="middle"
          class="fill-gray-400 text-xs pointer-events-none"
          font-size="11"
        >
          {{ node.label }}
        </text>
      </g>
    </svg>
    <div v-if="characters.length === 0" class="flex items-center justify-center h-40 text-gray-500 text-sm">
      No characters to display
    </div>
  </div>
</template>
