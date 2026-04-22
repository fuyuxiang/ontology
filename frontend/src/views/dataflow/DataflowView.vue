<template>
  <div class="graph-workbench">
    <section class="graph-stage">
      <CanvasToolbar
        v-model:search-query="searchQuery"
        :direction="direction"
        :node-count="visibleNodeCount"
        :edge-count="visibleEdgeCount"
        :total-node-count="graphStats.totalNodes"
        :has-filters="hasActiveFilters"
        :active-tier="activeTier"
        :tier-cards="tierCards"
        @layout="doLayout"
        @fit="fitView"
        @direction="onDirection"
        @clear="clearFilters"
        @tier-filter="setTierFilter"
      />

      <div class="graph-stage__canvas" @drop="onDrop" @dragover.prevent>
          <VueFlow
            v-model:nodes="flowNodes"
            v-model:edges="flowEdges"
            :node-types="nodeTypes"
            :edge-types="edgeTypes"
            :default-edge-options="defaultEdgeOptions"
            :fit-view-on-init="true"
            :nodes-draggable="true"
            :nodes-connectable="false"
            :edges-updatable="false"
            :min-zoom="0.35"
            :max-zoom="1.6"
            @node-click="onNodeClick"
            @node-double-click="onNodeDblClick"
            @pane-click="onPaneClick"
            @node-mouse-enter="onNodeMouseEnter"
            @node-mouse-leave="onNodeMouseLeave"
          >
            <Background :gap="24" pattern-color="rgba(133, 147, 173, 0.10)" :size="0.8" />

            <template #node-ontologyNode="nodeProps">
              <OntologyNode v-bind="nodeProps" />
            </template>

            <Controls position="bottom-left" />
            <MiniMap position="bottom-right" :node-color="miniMapNodeColor" />
          </VueFlow>

          <!-- Tooltip -->
          <Teleport to="body">
            <div
              v-if="tooltip.visible"
              class="graph-tooltip"
              :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
            >
              <div class="graph-tooltip__head">
                <span class="graph-tooltip__icon">{{ tooltip.icon }}</span>
                <span class="graph-tooltip__tier" :style="{ color: tooltip.tierColor }">T{{ tooltip.tier }}</span>
                <span class="graph-tooltip__status" :class="`graph-tooltip__status--${tooltip.status}`"></span>
              </div>
              <div class="graph-tooltip__name">{{ tooltip.nameCn }}</div>
              <div class="graph-tooltip__sub">{{ tooltip.name }}</div>
              <div class="graph-tooltip__stats">
                <span>🔗 {{ tooltip.relCount }} 关系</span>
                <span>📋 {{ tooltip.attrCount }} 属性</span>
                <span>⚡ {{ tooltip.ruleCount }} 规则</span>
              </div>
              <div v-if="tooltip.datasource" class="graph-tooltip__ds">📦 {{ tooltip.datasource }}</div>
            </div>
          </Teleport>

          <div v-if="loading" class="canvas-loading">
            <div class="canvas-loading__spinner"></div>
            <span>加载图谱数据...</span>
          </div>

          <div v-else-if="!visibleNodeCount" class="canvas-empty">
            <div class="canvas-empty__icon">
              <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
                <circle cx="17" cy="10.5" r="4.5" stroke="currentColor" stroke-width="1.6"/>
                <circle cx="9" cy="24.5" r="4.5" stroke="currentColor" stroke-width="1.6"/>
                <circle cx="25" cy="24.5" r="4.5" stroke="currentColor" stroke-width="1.6"/>
                <path d="M17 15v3.5M17 18.5L9.5 20.5M17 18.5l7.5 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
              </svg>
            </div>
            <h3>当前条件下没有图谱结果</h3>
            <p>尝试清空搜索词或切换 Tier，再重新查看全量关系网络。</p>
            <button class="canvas-empty__btn" @click="clearFilters">清空筛选</button>
          </div>
        </div>
    </section>

    <CanvasConfigPanel
      :node="selectedNodeData"
      :in-edges="selectedInEdges"
      :out-edges="selectedOutEdges"
      :visible-node-count="visibleNodeCount"
      :total-node-count="graphStats.totalNodes"
      :total-edge-count="graphStats.totalEdges"
      :busiest-entity="busiestEntity"
      @detail="goDetail"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { VueFlow, useVueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { useRouter } from 'vue-router'
import { useOntologyStore } from '../../store/ontology'
import { useGraphLayout } from '../../composables/useGraphLayout'
import CanvasToolbar from '../../components/canvas/CanvasToolbar.vue'
import CanvasConfigPanel from '../../components/canvas/CanvasConfigPanel.vue'
import OntologyNode from '../../components/canvas/OntologyNode.vue'
import CanvasEdgeLabel from '../../components/canvas/CanvasEdgeLabel.vue'
import type { GraphData, Tier } from '../../types'

interface VisibleEntity {
  id: string
  name: string
  nameCn: string
  tier: Tier
  status: string
  relationCount: number
  attrCount: number
  ruleCount: number
  datasource: string | null
}

const store = useOntologyStore()
const router = useRouter()
const { transformGraphData } = useGraphLayout()
const { fitView: doFitView, screenToFlowCoordinate } = useVueFlow()

const flowNodes = ref<any[]>([])
const flowEdges = ref<any[]>([])
const direction = ref<'LR' | 'TB'>('LR')
const selectedNodeId = ref<string | null>(null)
const hoveredNodeId = ref<string | null>(null)
const loading = ref(false)
const searchQuery = ref('')
const activeTier = ref<Tier | null>(null)

const tierIcons: Record<number, string> = { 1: '🏛️', 2: '🔗', 3: '📊' }
const tierColorsMap: Record<number, string> = { 1: '#4c6ef5', 2: '#7950f2', 3: '#20c997' }

const tooltip = reactive({
  visible: false,
  x: 0,
  y: 0,
  nameCn: '',
  name: '',
  tier: 1 as number,
  tierColor: '#4c6ef5',
  icon: '🏛️',
  status: 'active',
  relCount: 0,
  attrCount: 0,
  ruleCount: 0,
  datasource: null as string | null,
})

const nodeTypes = { ontologyNode: markRaw(OntologyNode) } as any
const edgeTypes = { ontologyEdge: markRaw(CanvasEdgeLabel) } as any
const defaultEdgeOptions = { markerEnd: MarkerType.ArrowClosed, animated: false }

const tierMiniColors: Record<number, string> = { 1: '#4c6ef5', 2: '#7950f2', 3: '#20c997' }

function miniMapNodeColor(node: any) {
  return tierMiniColors[node.data?.tier] || '#adb5bd'
}

const entityMetaMap = computed(() => new Map(store.entities.map(entity => [entity.id, entity])))
const baseGraph = computed<GraphData>(() => store.graphData ?? { nodes: [], edges: [] })

const graphStats = computed(() => ({
  totalNodes: baseGraph.value.nodes.length,
  totalEdges: baseGraph.value.edges.length,
}))

const tierCards = computed(() =>
  ([1, 2, 3] as Tier[]).map(tier => ({
    tier,
    count: baseGraph.value.nodes.filter(node => node.tier === tier).length,
  }))
)

const filteredGraphData = computed<GraphData>(() => {
  const q = searchQuery.value.trim().toLowerCase()

  const nodes = baseGraph.value.nodes.filter(node => {
    const meta = entityMetaMap.value.get(node.id)
    const name = (meta?.name ?? node.name ?? '').toLowerCase()
    const nameCn = (meta?.name_cn ?? node.name_cn ?? '').toLowerCase()
    const tierMatched = activeTier.value === null || node.tier === activeTier.value
    const searchMatched = !q || name.includes(q) || nameCn.includes(q)
    return tierMatched && searchMatched
  })

  const ids = new Set(nodes.map(node => node.id))
  const edges = baseGraph.value.edges.filter(edge => ids.has(edge.from_id) && ids.has(edge.to_id))

  return { nodes, edges }
})

const visibleNodeCount = computed(() => filteredGraphData.value.nodes.length)
const visibleEdgeCount = computed(() => filteredGraphData.value.edges.length)
const hasActiveFilters = computed(() => activeTier.value !== null || searchQuery.value.trim().length > 0)

const visibleEntities = computed<VisibleEntity[]>(() =>
  filteredGraphData.value.nodes
    .map(node => {
      const meta = entityMetaMap.value.get(node.id)
      return {
        id: node.id,
        name: meta?.name ?? node.name,
        nameCn: meta?.name_cn ?? node.name_cn,
        tier: node.tier,
        status: meta?.status ?? node.status,
        relationCount: node.relation_count,
        attrCount: meta?.attr_count ?? 0,
        ruleCount: meta?.rule_count ?? 0,
        datasource: meta?.datasource_name ?? null,
      }
    })
    .sort((a, b) => {
      if (a.tier !== b.tier) return a.tier - b.tier
      if (a.relationCount !== b.relationCount) return b.relationCount - a.relationCount
      return a.nameCn.localeCompare(b.nameCn, 'zh-CN')
    })
)

const busiestEntity = computed(() =>
  [...visibleEntities.value].sort((a, b) => b.relationCount - a.relationCount)[0] ?? null
)

const selectedNodeData = computed(() => {
  if (!selectedNodeId.value) return null
  const node = flowNodes.value.find(item => item.id === selectedNodeId.value)
  if (!node) return null
  return { id: node.id, ...node.data }
})

const selectedInEdges = computed(() => {
  if (!selectedNodeId.value) return []

  return flowEdges.value
    .filter(edge => edge.target === selectedNodeId.value)
    .map(edge => {
      const sourceNode = flowNodes.value.find(item => item.id === edge.source)
      return {
        id: edge.id,
        sourceName: sourceNode?.data?.nameCn || sourceNode?.data?.name || edge.source,
        sourceTier: (sourceNode?.data?.tier || 1) as Tier,
        targetName: '',
        targetTier: selectedNodeData.value?.tier ?? 1,
        label: edge.data?.label || '',
        cardinality: edge.data?.cardinality || '',
      }
    })
})

const selectedOutEdges = computed(() => {
  if (!selectedNodeId.value) return []

  return flowEdges.value
    .filter(edge => edge.source === selectedNodeId.value)
    .map(edge => {
      const targetNode = flowNodes.value.find(item => item.id === edge.target)
      return {
        id: edge.id,
        sourceName: '',
        sourceTier: selectedNodeData.value?.tier ?? 1,
        targetName: targetNode?.data?.nameCn || targetNode?.data?.name || edge.target,
        targetTier: (targetNode?.data?.tier || 1) as Tier,
        label: edge.data?.label || '',
        cardinality: edge.data?.cardinality || '',
      }
    })
})

async function loadGraph() {
  loading.value = true
  try {
    if (store.entities.length === 0) await store.fetchEntities()
    await store.fetchGraph()
    await nextTick()
    doLayout()
  } finally {
    loading.value = false
  }
}

onMounted(loadGraph)

watch(
  [() => store.graphData, () => store.entities, direction, activeTier, searchQuery],
  async () => {
    if (!store.graphData) return
    await nextTick()
    doLayout()
  },
  { deep: true },
)

watch(filteredGraphData, graph => {
  if (selectedNodeId.value && !graph.nodes.some(node => node.id === selectedNodeId.value)) {
    selectedNodeId.value = null
  }
}, { deep: true })

function doLayout() {
  if (!store.graphData) {
    flowNodes.value = []
    flowEdges.value = []
    return
  }

  const { nodes, edges } = transformGraphData(filteredGraphData.value, direction.value, entityMetaMap.value)
  const nodeTierMap = new Map(nodes.map(n => [n.id, n.data?.tier ?? 1]))

  flowNodes.value = nodes
  flowEdges.value = edges.map(edge => ({
    ...edge,
    data: {
      ...edge.data,
      sourceTier: nodeTierMap.get(edge.source) ?? 1,
      targetTier: nodeTierMap.get(edge.target) ?? 1,
      highlighted: false,
      dimmed: false,
    },
  }))
  setTimeout(() => doFitView({ padding: 0.18 }), 40)
}

function fitView() {
  doFitView({ padding: 0.18 })
}

function onDirection(nextDirection: 'LR' | 'TB') {
  direction.value = nextDirection
}

function onNodeClick(event: { node: { id: string } }) {
  selectedNodeId.value = event.node.id
  applyHighlight(event.node.id)
}

function onPaneClick() {
  selectedNodeId.value = null
  hoveredNodeId.value = null
  clearHighlight()
}

function onNodeDblClick(event: { node: { id: string } }) {
  router.push(`/ontology/${event.node.id}`)
}

function onNodeMouseEnter(event: { node: { id: string }; event: MouseEvent }) {
  hoveredNodeId.value = event.node.id
  if (!selectedNodeId.value) {
    applyHighlight(event.node.id)
  }
  const nodeData = flowNodes.value.find(n => n.id === event.node.id)?.data
  if (nodeData) {
    tooltip.visible = true
    tooltip.x = event.event.clientX + 14
    tooltip.y = event.event.clientY + 14
    tooltip.nameCn = nodeData.nameCn
    tooltip.name = nodeData.name
    tooltip.tier = nodeData.tier
    tooltip.tierColor = tierColorsMap[nodeData.tier] || '#4c6ef5'
    tooltip.icon = tierIcons[nodeData.tier] || '🏛️'
    tooltip.status = nodeData.status
    tooltip.relCount = nodeData.relCount
    tooltip.attrCount = nodeData.attrCount
    tooltip.ruleCount = nodeData.ruleCount
    tooltip.datasource = nodeData.datasource
  }
}

function onNodeMouseLeave() {
  hoveredNodeId.value = null
  tooltip.visible = false
  if (!selectedNodeId.value) {
    clearHighlight()
  }
}

function getNeighborIds(nodeId: string) {
  const neighbors = new Set<string>([nodeId])
  flowEdges.value.forEach(edge => {
    if (edge.source === nodeId) neighbors.add(edge.target)
    if (edge.target === nodeId) neighbors.add(edge.source)
  })
  return neighbors
}

function applyHighlight(focusId: string) {
  const neighbors = getNeighborIds(focusId)
  const nodeTierMap = new Map(flowNodes.value.map(n => [n.id, n.data?.tier ?? 1]))

  flowNodes.value = flowNodes.value.map(node => ({
    ...node,
    zIndex: node.id === focusId ? 1001 : neighbors.has(node.id) ? 1000 : 0,
    data: { ...node.data, dimmed: !neighbors.has(node.id) },
  }))

  flowEdges.value = flowEdges.value.map(edge => {
    const connected = edge.source === focusId || edge.target === focusId
    return {
      ...edge,
      zIndex: connected ? 1000 : 0,
      data: {
        ...edge.data,
        highlighted: connected,
        dimmed: !connected,
        sourceTier: nodeTierMap.get(edge.source) ?? 1,
        targetTier: nodeTierMap.get(edge.target) ?? 1,
      },
    }
  })
}

function clearHighlight() {
  const nodeTierMap = new Map(flowNodes.value.map(n => [n.id, n.data?.tier ?? 1]))

  flowNodes.value = flowNodes.value.map(node => ({
    ...node,
    zIndex: 0,
    data: { ...node.data, dimmed: false },
  }))

  flowEdges.value = flowEdges.value.map(edge => ({
    ...edge,
    zIndex: 0,
    data: {
      ...edge.data,
      highlighted: false,
      dimmed: false,
      sourceTier: nodeTierMap.get(edge.source) ?? 1,
      targetTier: nodeTierMap.get(edge.target) ?? 1,
    },
  }))
}

function setTierFilter(tier: Tier | null) {
  activeTier.value = activeTier.value === tier ? null : tier
}

function clearFilters() {
  searchQuery.value = ''
  activeTier.value = null
}

function onDrop(event: DragEvent) {
  const raw = event.dataTransfer?.getData('application/vueflow')
  if (!raw) return

  const parsed = JSON.parse(raw)
  const position = screenToFlowCoordinate({ x: event.clientX, y: event.clientY })

  const newNode = {
    id: `${parsed.id}-${Date.now()}`,
    type: 'ontologyNode',
    position,
    data: {
      name: parsed.name,
      nameCn: parsed.nameCn,
      tier: parsed.tier,
      status: 'active',
      relCount: 0,
      attrCount: 0,
      ruleCount: 0,
      datasource: null,
    },
  }

  flowNodes.value = [...flowNodes.value, newNode]
}

function goDetail(id: string) {
  router.push(`/ontology/${id}`)
}
</script>

<style scoped>
.graph-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 0;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(76, 110, 245, 0.06), transparent 30%),
    radial-gradient(circle at right 10% top 16%, rgba(32, 201, 151, 0.06), transparent 26%),
    linear-gradient(180deg, #f8fafe 0%, #f0f4fa 100%);
}

.graph-stage {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 14px;
  gap: 12px;
}

.graph-stage__canvas {
  position: relative;
  flex: 1;
  min-height: 0;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(212, 220, 232, 0.7);
  background:
    radial-gradient(circle at 20% 16%, rgba(76, 110, 245, 0.04), transparent 24%),
    radial-gradient(circle at 80% 12%, rgba(32, 201, 151, 0.05), transparent 22%),
    linear-gradient(180deg, #fafbfe 0%, #f3f6fb 100%);
}

.canvas-loading,
.canvas-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
}

.canvas-loading {
  background: rgba(248, 250, 252, 0.78);
  color: var(--neutral-600);
  z-index: 10;
}

.canvas-loading__spinner {
  width: 30px;
  height: 30px;
  border: 2.5px solid rgba(203, 213, 225, 0.65);
  border-top-color: var(--semantic-600);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.canvas-empty {
  color: var(--neutral-500);
}

.canvas-empty__icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.95);
  color: rgba(134, 142, 150, 0.85);
  border: 1px solid rgba(220, 227, 237, 0.95);
  box-shadow: var(--shadow-sm);
}

.canvas-empty h3 {
  margin: 6px 0 0;
  font-size: var(--text-h2-size);
  color: #172033;
}

.canvas-empty p {
  margin: 0;
  max-width: 320px;
  line-height: 1.7;
}

.canvas-empty__btn {
  margin-top: 4px;
  padding: 9px 16px;
  border-radius: 999px;
  border: 1px solid rgba(76, 110, 245, 0.28);
  background: rgba(238, 242, 255, 0.9);
  color: var(--semantic-700);
  font-size: var(--text-code-size);
  font-weight: 700;
  cursor: pointer;
}

/* Tooltip */
.graph-tooltip {
  position: fixed;
  z-index: 9999;
  min-width: 180px;
  max-width: 240px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(228, 233, 241, 0.9);
  box-shadow: 0 12px 32px -8px rgba(30, 41, 59, 0.22);
  backdrop-filter: blur(16px);
  pointer-events: none;
  animation: tooltip-in 0.18s ease-out;
}

@keyframes tooltip-in {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

.graph-tooltip__head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.graph-tooltip__icon { font-size: 16px; }

.graph-tooltip__tier {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.4px;
}

.graph-tooltip__status {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #cbd5e1;
  margin-left: auto;
}
.graph-tooltip__status--active { background: var(--status-success, #12b886); }
.graph-tooltip__status--warning { background: var(--status-warning, #f59f00); }
.graph-tooltip__status--error { background: var(--status-error, #fa5252); }

.graph-tooltip__name {
  font-size: 13px;
  font-weight: 700;
  color: #172033;
  line-height: 1.3;
}

.graph-tooltip__sub {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.graph-tooltip__stats {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  font-size: 10px;
  color: #64748b;
  font-weight: 600;
}

.graph-tooltip__ds {
  margin-top: 6px;
  padding: 3px 6px;
  border-radius: 4px;
  background: #f1f5f9;
  font-size: 9px;
  color: #64748b;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

:deep(.vue-flow__controls) {
  overflow: hidden;
  border-radius: 14px;
  border: 1px solid rgba(200, 210, 225, 0.92);
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
    0 4px 12px -4px rgba(30, 41, 59, 0.12),
    0 8px 24px -8px rgba(30, 41, 59, 0.16);
  backdrop-filter: blur(16px);
}

:deep(.vue-flow__controls-button) {
  width: 34px;
  height: 34px;
  background: transparent;
  border: none;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  color: #475569;
  transition: background 0.15s ease, color 0.15s ease;
}

:deep(.vue-flow__controls-button:last-child) {
  border-bottom: none;
}

:deep(.vue-flow__controls-button:hover) {
  background: rgba(76, 110, 245, 0.08);
  color: #4c6ef5;
}

:deep(.vue-flow__minimap) {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(200, 210, 225, 0.92);
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
    0 4px 12px -4px rgba(30, 41, 59, 0.12),
    0 8px 24px -8px rgba(30, 41, 59, 0.16);
  backdrop-filter: blur(16px);
}

:deep(.vue-flow__minimap svg) {
  background: rgba(248, 250, 253, 0.9);
}

@media (max-width: 1100px) {
  .graph-workbench {
    grid-template-columns: minmax(0, 1fr) 320px;
  }
}

@media (max-width: 860px) {
  .graph-workbench {
    grid-template-columns: 1fr;
    height: auto;
    overflow: auto;
  }

  :deep(.config-panel) {
    border-left: none;
    border-top: 1px solid rgba(208, 217, 229, 0.74);
    min-height: 320px;
  }
}
</style>
