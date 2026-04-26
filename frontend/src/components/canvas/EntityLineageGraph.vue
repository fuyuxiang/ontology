<template>
  <div class="lineage-graph">
    <div class="lineage-graph__toolbar">
      <span class="lineage-label">血缘深度</span>
      <select v-model.number="depth" class="lineage-select" @change="loadLineage">
        <option :value="1">1 跳</option>
        <option :value="2">2 跳</option>
        <option :value="3">3 跳</option>
      </select>
      <button class="lineage-btn" @click="doFitView({ padding: 0.2 })">适应画布</button>
      <span class="lineage-stats" v-if="!loading">{{ flowNodes.length }} 对象 · {{ flowEdges.length }} 关系</span>
    </div>

    <div class="lineage-graph__canvas" v-if="!loading && flowNodes.length > 0">
      <VueFlow
        v-model:nodes="flowNodes"
        v-model:edges="flowEdges"
        :node-types="nodeTypes"
        :edge-types="edgeTypes"
        :fit-view-on-init="true"
        :nodes-draggable="true"
        :nodes-connectable="false"
        :edges-updatable="false"
      >
        <Background :gap="20" pattern-color="#dee2e6" :size="1" />
        <Controls position="bottom-left" />
      </VueFlow>
    </div>

    <div class="lineage-graph__loading" v-else-if="loading">
      <div class="lineage-spinner"></div>
      <span>加载血缘数据...</span>
    </div>

    <div class="lineage-graph__empty" v-else>
      <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
        <circle cx="20" cy="20" r="18" stroke="#dee2e6" stroke-width="1.5" stroke-dasharray="4 3"/>
        <path d="M14 20h12M20 14v12" stroke="#ced4da" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <p>该实体暂无关联血缘</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, markRaw, watch } from 'vue'
import { VueFlow, useVueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { entityApi } from '../../api/ontology'
import { useGraphLayout } from '../../composables/useGraphLayout'
import OntologyNode from './OntologyNode.vue'
import CanvasEdgeLabel from './CanvasEdgeLabel.vue'
import type { Node, Edge } from '@vue-flow/core'

const props = defineProps<{ entityId: string }>()

const { transformGraphData } = useGraphLayout()
const { fitView: doFitView } = useVueFlow()

const flowNodes = ref<Node[]>([])
const flowEdges = ref<Edge[]>([])
const depth = ref(2)
const loading = ref(false)

const nodeTypes = { ontologyNode: markRaw(OntologyNode) }
const edgeTypes = { ontologyEdge: markRaw(CanvasEdgeLabel) }

async function loadLineage() {
  loading.value = true
  try {
    const data = await entityApi.lineage(props.entityId, depth.value)
    const { nodes, edges } = transformGraphData(data, 'LR')
    // Highlight the current entity
    nodes.forEach(n => {
      if (n.id === props.entityId) {
        n.data = { ...n.data, _highlight: true }
        n.class = 'lineage-highlight'
      }
    })
    flowNodes.value = nodes
    flowEdges.value = edges
    setTimeout(() => doFitView({ padding: 0.2 }), 50)
  } catch {
    flowNodes.value = []
    flowEdges.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadLineage)
watch(() => props.entityId, loadLineage)
</script>

<style scoped>
.lineage-graph { display: flex; flex-direction: column; height: 420px; }
.lineage-graph__toolbar {
  display: flex; align-items: center; gap: 10px; padding: 10px 0; flex-shrink: 0;
}
.lineage-label { font-size: var(--text-code-size); color: var(--neutral-600); }
.lineage-select {
  padding: 4px 8px; border: 1px solid var(--neutral-300); border-radius: 6px;
  font-size: var(--text-code-size); background: var(--neutral-0); outline: none;
}
.lineage-btn {
  padding: 4px 12px; border: 1px solid var(--neutral-300); border-radius: 6px;
  font-size: var(--text-code-size); background: var(--neutral-50); cursor: pointer; color: var(--neutral-700);
}
.lineage-btn:hover { background: var(--neutral-200); }
.lineage-stats { margin-left: auto; font-size: var(--text-caption-size); color: var(--neutral-500); }
.lineage-graph__canvas {
  flex: 1; border: 1px solid var(--neutral-200); border-radius: 8px; overflow: hidden; background: var(--neutral-50);
}
.lineage-graph__loading, .lineage-graph__empty {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 12px; color: var(--neutral-500); font-size: var(--text-body-size);
}
.lineage-spinner {
  width: 24px; height: 24px; border: 2.5px solid var(--neutral-200);
  border-top-color: var(--semantic-600); border-radius: 50%;
  animation: lspin 0.8s linear infinite;
}
@keyframes lspin { to { transform: rotate(360deg); } }
:deep(.lineage-highlight .ontology-node) {
  border-color: var(--semantic-600); box-shadow: 0 0 0 3px rgba(76,110,245,0.2);
}
</style>
