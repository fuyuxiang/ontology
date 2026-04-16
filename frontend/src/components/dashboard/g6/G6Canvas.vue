<template>
  <div class="g6-dashboard">
    <div ref="containerRef" class="g6-container" />

    <StatsPanel :stats="stats" />
    <TierPanel :stats="stats" />
    <ActivityPanel :stats="stats" />
    <ControlBar @layout="changeLayout" @zoom-in="zoomIn" @zoom-out="zoomOut" @fit="fitView" />
    <ProbeCard v-if="probeNode" :node="probeNode" :x="probePos.x" :y="probePos.y" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { Graph } from '@antv/g6'
import { useRouter } from 'vue-router'
import { registerCustomNodes } from './registerNodes'
import { registerCustomEdges } from './registerEdges'
import { DARK_BG, COLORS, tierColor } from './darkTheme'
import { mapEntities, mapRelations, type G6NodeData } from './mapData'
import StatsPanel from '../panels/StatsPanel.vue'
import TierPanel from '../panels/TierPanel.vue'
import ActivityPanel from '../panels/ActivityPanel.vue'
import ControlBar from '../panels/ControlBar.vue'
import ProbeCard from '../panels/ProbeCard.vue'
import type { EntityListItem } from '../../../types'
import type { RelationData } from '../../../api/relations'
import type { DashboardStatsEx } from '../../../api/dashboard'

const props = defineProps<{
  entities: EntityListItem[]
  relations: RelationData[]
  stats: DashboardStatsEx | null
}>()

const router = useRouter()
const containerRef = ref<HTMLElement | null>(null)
const probeNode = ref<G6NodeData | null>(null)
const probePos = ref({ x: 0, y: 0 })

let graph: Graph | null = null
let registered = false
let ro: ResizeObserver | null = null

function nodeTypeMap(t: string) {
  if (t === 'datasource') return 'datasource-node'
  if (t === 'operator') return 'operator-node'
  return 'model-node'
}

function initGraph() {
  if (!containerRef.value || graph) return

  if (!registered) {
    registerCustomNodes()
    registerCustomEdges()
    registered = true
  }

  const rect = containerRef.value.getBoundingClientRect()

  graph = new Graph({
    container: containerRef.value,
    width: rect.width,
    height: rect.height,
    background: DARK_BG,
    node: {
      type: (d: any) => nodeTypeMap(d.data?.nodeType || 'datasource'),
      style: (d: any) => ({
        label: true,
        labelText: d.data?.label || '',
        icon: true,
        badges: true,
        tier: d.data?.tier ?? 1,
        status: d.data?.status ?? 'active',
        fill: COLORS.nodeFill,
        stroke: tierColor(d.data?.tier ?? 1),
        strokeOpacity: 0.6,
        lineWidth: 1.5,
      }),
      state: {
        highlight: { strokeOpacity: 1, lineWidth: 2.5, shadowColor: 'rgba(16,185,129,.35)', shadowBlur: 16 },
        dim: { opacity: 0.15 },
      },
    },
    edge: {
      type: 'flow-edge',
      style: {
        stroke: COLORS.edgeDefault,
        lineWidth: 1,
        endArrow: true,
        endArrowSize: 6,
        labelFontSize: 9,
        labelFill: COLORS.labelSecondary,
      },
      state: {
        highlight: { stroke: COLORS.edgeHighlight, lineWidth: 2, lineDash: [6, 4], strokeOpacity: 1 },
        dim: { strokeOpacity: 0.08 },
      },
    },
    layout: {
      type: 'd3-force',
      preventOverlap: true,
      nodeSize: 80,
      linkDistance: 180,
      chargeStrength: -600,
      collideRadius: 60,
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    animation: true,
  })

  graph.on('node:mouseenter', (e: any) => {
    const id = e.target?.id
    if (!id || !graph) return
    highlightNeighbors(id)
    const nodeData = graph.getNodeData(id)
    if (nodeData) {
      probeNode.value = { id, data: nodeData.data } as any
      probePos.value = { x: e.client?.x ?? e.x ?? 0, y: e.client?.y ?? e.y ?? 0 }
    }
  })

  graph.on('node:mouseleave', () => {
    if (!graph) return
    clearHighlight()
    probeNode.value = null
  })

  graph.on('node:click', (e: any) => {
    const id = e.target?.id
    if (id) router.push(`/ontology/${id}`)
  })

  graph.on('canvas:click', () => {
    if (!graph) return
    clearHighlight()
    probeNode.value = null
  })
}

function highlightNeighbors(nodeId: string) {
  if (!graph) return
  const allNodes = graph.getNodeData()
  const allEdges = graph.getEdgeData()
  const neighborIds = new Set<string>([nodeId])

  for (const edge of allEdges) {
    if (edge.source === nodeId) neighborIds.add(edge.target as string)
    if (edge.target === nodeId) neighborIds.add(edge.source as string)
  }

  for (const n of allNodes) {
    graph.setElementState(n.id as string, neighborIds.has(n.id as string) ? 'highlight' : 'dim')
  }
  for (const e of allEdges) {
    const connected = e.source === nodeId || e.target === nodeId
    graph.setElementState(e.id as string, connected ? 'highlight' : 'dim')
  }
}

function clearHighlight() {
  if (!graph) return
  const allNodes = graph.getNodeData()
  const allEdges = graph.getEdgeData()
  for (const n of allNodes) graph.setElementState(n.id as string, [])
  for (const e of allEdges) graph.setElementState(e.id as string, [])
}

function updateData() {
  if (!graph) return
  const nodes = mapEntities(props.entities)
  const nodeIds = new Set(nodes.map(n => n.id))
  const edges = mapRelations(props.relations, nodeIds)
  graph.setData({ nodes, edges })
  graph.render()
}

function changeLayout(type: string) {
  if (!graph) return
  const layouts: Record<string, any> = {
    force: { type: 'd3-force', preventOverlap: true, nodeSize: 80, linkDistance: 180, chargeStrength: -600 },
    dagre: { type: 'dagre', rankdir: 'TB', nodesep: 40, ranksep: 80 },
    radial: { type: 'radial', unitRadius: 120, linkDistance: 180, preventOverlap: true, nodeSize: 80 },
  }
  graph.setLayout(layouts[type] || layouts.force)
  graph.layout()
}

function zoomIn() { graph?.zoomBy(1.2) }
function zoomOut() { graph?.zoomBy(0.8) }
function fitView() { graph?.fitView() }

watch(() => [props.entities, props.relations], () => {
  nextTick(updateData)
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    initGraph()
    if (props.entities.length) updateData()

    if (containerRef.value) {
      ro = new ResizeObserver(entries => {
        const { width, height } = entries[0].contentRect
        graph?.resize(width, height)
      })
      ro.observe(containerRef.value)
    }
  })
})

onBeforeUnmount(() => {
  ro?.disconnect()
  graph?.destroy()
  graph = null
})
</script>

<style scoped>
.g6-dashboard {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0F172A;
}
.g6-container {
  width: 100%;
  height: 100%;
}
</style>
