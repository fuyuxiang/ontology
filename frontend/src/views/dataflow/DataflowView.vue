<template>
  <div class="canvas-page">
    <CanvasToolbar
      :direction="direction"
      :node-count="flowNodes.length"
      :edge-count="flowEdges.length"
      @layout="doLayout"
      @fit="fitView"
      @direction="onDirection"
    />
    <div class="canvas-page__body">
      <CanvasNodePalette :grouped="store.grouped" />

      <div class="canvas-page__canvas" @drop="onDrop" @dragover.prevent>
        <VueFlow
          ref="vueFlowRef"
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          :node-types="nodeTypes"
          :edge-types="edgeTypes"
          :default-edge-options="defaultEdgeOptions"
          :fit-view-on-init="true"
          :snap-to-grid="true"
          :snap-grid="[20, 20]"
          @node-click="onNodeClick"
          @pane-click="onPaneClick"
        >
          <Background :gap="20" pattern-color="#dee2e6" :size="1" />
          <Controls position="bottom-left" />
          <MiniMap position="bottom-right" :node-color="miniMapNodeColor" />
        </VueFlow>

        <div v-if="loading" class="canvas-loading">
          <div class="canvas-loading__spinner"></div>
          <span>加载图谱数据...</span>
        </div>
      </div>

      <CanvasConfigPanel
        :node="selectedNodeData"
        :in-edges="selectedInEdges"
        :out-edges="selectedOutEdges"
        @detail="goDetail"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, markRaw } from 'vue'
import { VueFlow, useVueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { useRouter } from 'vue-router'
import { useOntologyStore } from '../../store/ontology'
import { useGraphLayout } from '../../composables/useGraphLayout'
import CanvasToolbar from '../../components/canvas/CanvasToolbar.vue'
import CanvasNodePalette from '../../components/canvas/CanvasNodePalette.vue'
import CanvasConfigPanel from '../../components/canvas/CanvasConfigPanel.vue'
import OntologyNode from '../../components/canvas/OntologyNode.vue'
import CanvasEdgeLabel from '../../components/canvas/CanvasEdgeLabel.vue'
import type { Node, Edge } from '@vue-flow/core'

const store = useOntologyStore()
const router = useRouter()
const { transformGraphData } = useGraphLayout()
const { fitView: doFitView, screenToFlowCoordinate } = useVueFlow()

const flowNodes = ref<Node[]>([])
const flowEdges = ref<Edge[]>([])
const direction = ref<'LR' | 'TB'>('LR')
const selectedNodeId = ref<string | null>(null)
const loading = ref(false)

const nodeTypes = { ontologyNode: markRaw(OntologyNode) }
const edgeTypes = { ontologyEdge: markRaw(CanvasEdgeLabel) }
const defaultEdgeOptions = { markerEnd: MarkerType.ArrowClosed, animated: false }

const tierMiniColors: Record<number, string> = { 1: '#4c6ef5', 2: '#7950f2', 3: '#20c997' }
function miniMapNodeColor(node: Node) {
  return tierMiniColors[node.data?.tier] || '#adb5bd'
}

onMounted(async () => {
  loading.value = true
  if (store.entities.length === 0) await store.fetchEntities()
  await store.fetchGraph()
  loading.value = false
  doLayout()
})

watch(() => store.graphData, () => { if (store.graphData) doLayout() })

function doLayout() {
  if (!store.graphData) return
  const { nodes, edges } = transformGraphData(store.graphData, direction.value)
  flowNodes.value = nodes
  flowEdges.value = edges
  setTimeout(() => doFitView({ padding: 0.15 }), 50)
}

function fitView() { doFitView({ padding: 0.15 }) }

function onDirection(d: 'LR' | 'TB') {
  direction.value = d
  doLayout()
}

function onNodeClick(event: { node: Node }) {
  selectedNodeId.value = event.node.id
}

function onPaneClick() {
  selectedNodeId.value = null
}

const selectedNodeData = computed(() => {
  if (!selectedNodeId.value) return null
  const n = flowNodes.value.find(n => n.id === selectedNodeId.value)
  if (!n) return null
  return { id: n.id, ...n.data }
})

const selectedInEdges = computed(() => {
  if (!selectedNodeId.value) return []
  return flowEdges.value
    .filter(e => e.target === selectedNodeId.value)
    .map(e => {
      const src = flowNodes.value.find(n => n.id === e.source)
      return { id: e.id, sourceName: src?.data?.name || e.source, targetName: '', label: e.data?.label || '', cardinality: e.data?.cardinality || '' }
    })
})

const selectedOutEdges = computed(() => {
  if (!selectedNodeId.value) return []
  return flowEdges.value
    .filter(e => e.source === selectedNodeId.value)
    .map(e => {
      const tgt = flowNodes.value.find(n => n.id === e.target)
      return { id: e.id, sourceName: '', targetName: tgt?.data?.name || e.target, label: e.data?.label || '', cardinality: e.data?.cardinality || '' }
    })
})

function onDrop(event: DragEvent) {
  const data = event.dataTransfer?.getData('application/vueflow')
  if (!data) return
  const parsed = JSON.parse(data)
  const pos = screenToFlowCoordinate({ x: event.clientX, y: event.clientY })
  const newNode: Node = {
    id: `${parsed.id}-${Date.now()}`,
    type: 'ontologyNode',
    position: pos,
    data: { name: parsed.name, nameCn: parsed.nameCn, tier: parsed.tier, status: 'active', relCount: 0 },
  }
  flowNodes.value = [...flowNodes.value, newNode]
}

function goDetail(id: string) { router.push(`/ontology/${id}`) }
</script>

<style scoped>
.canvas-page { display: flex; flex-direction: column; height: 100%; background: #f8f9fa; }
.canvas-page__body { display: flex; flex: 1; overflow: hidden; }
.canvas-page__canvas { flex: 1; position: relative; }
.canvas-loading {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 12px;
  background: rgba(248,249,250,0.85); z-index: 10; color: #868e96; font-size: 13px;
}
.canvas-loading__spinner {
  width: 28px; height: 28px; border: 2.5px solid #e9ecef;
  border-top-color: #4c6ef5; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
