<template>
  <div class="ln-tab">
    <div class="ln-header">
      <div>
        <div class="ln-title">
          <span class="ln-title__dot"></span>
          数据血缘追踪
        </div>
        <div class="ln-subtitle">按行对齐 数据源 → ETL → 本体 → 应用；点击本体节点查看字段级血缘</div>
      </div>
    </div>

    <div class="ln-canvas-wrapper">
      <VueFlow
        v-model:nodes="flowNodes"
        v-model:edges="flowEdges"
        :node-types="nodeTypes"
        :default-edge-options="defaultEdgeOptions"
        :fit-view-on-init="true"
        :fit-view-options="{ padding: 0.08 }"
        :nodes-draggable="true"
        :nodes-connectable="false"
        :pan-on-drag="false"
        :zoom-on-double-click="false"
        :pro-options="{ hideAttribution: true }"
        @node-click="onNodeClick"
      >
        <Background variant="dots" :gap="20" :size="1" pattern-color="#e5e7eb" />
        <Controls position="bottom-left" :show-interactive="false" />
      </VueFlow>

      <div v-if="loading" class="ln-loading">
        <div class="ln-loading__spinner"></div>
        <span>加载血缘数据...</span>
      </div>
    </div>

    <a-drawer
      v-model:open="detailOpen"
      :title="detailTitle"
      width="640"
      placement="right"
      :body-style="{ paddingBottom: '24px' }"
    >
      <div v-if="detailLoading" class="ln-drawer__loading">
        <a-spin />
      </div>
      <div v-else-if="detailData">
        <div v-if="detailData.groups.length === 0" class="ln-drawer__empty">
          暂无字段级血缘记录
        </div>
        <div v-for="(group, gi) in detailData.groups" :key="gi" class="ln-detail__group">
          <div class="ln-detail__src">
            <span class="ln-detail__src-tag">来源</span>
            <span class="ln-detail__src-text">{{ group.source }}</span>
          </div>
          <table class="ln-detail__table">
            <thead>
              <tr>
                <th>源字段</th>
                <th>本体属性（中文名）</th>
                <th>API 名称</th>
                <th>类型</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(f, fi) in group.fields" :key="fi">
                <td><span class="ln-mono">{{ f.from }}</span></td>
                <td>{{ f.to }}</td>
                <td><span class="ln-mono">{{ f.apiName }}</span></td>
                <td>
                  <span class="ln-tag" :class="`ln-tag--${f.type.toLowerCase()}`">{{ f.type }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw } from 'vue'
import { VueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import type { Node, Edge } from '@vue-flow/core'
import { message } from 'ant-design-vue'

import LineageLayerNode from '../../../components/lineage/LineageLayerNode.vue'
import LineageSourceNode from '../../../components/lineage/LineageSourceNode.vue'
import LineageETLNode from '../../../components/lineage/LineageETLNode.vue'
import LineageOntologyNode from '../../../components/lineage/LineageOntologyNode.vue'
import LineageAppNode from '../../../components/lineage/LineageAppNode.vue'

import { lineageApi, type LineageRow, type LineageCrossEdge, type FieldLineageResponse } from '../../../api/lineage'

const nodeTypes = {
  lineageLayer: markRaw(LineageLayerNode),
  lineageSource: markRaw(LineageSourceNode),
  lineageETL: markRaw(LineageETLNode),
  lineageOntology: markRaw(LineageOntologyNode),
  lineageApp: markRaw(LineageAppNode),
}

const defaultEdgeOptions = {
  type: 'default',
  markerEnd: MarkerType.ArrowClosed,
}

// X 坐标参考原版 bn / Sn / xn
const COL_X = { source: 0, etl: 290, ontology: 580, app: 870 }
const ROW_GAP = 52
const HEADER_Y = -62

const flowNodes = ref<Node[]>([])
const flowEdges = ref<Edge[]>([])
const loading = ref(false)

const rowsCache = ref<LineageRow[]>([])

const detailOpen = ref(false)
const detailLoading = ref(false)
const detailData = ref<FieldLineageResponse | null>(null)
const detailTitle = computed(() =>
  detailData.value
    ? `${detailData.value.ontologyLabel} (${detailData.value.objectName}) — 字段级血缘`
    : '字段级血缘',
)

onMounted(loadGraph)

async function loadGraph() {
  loading.value = true
  try {
    const data = await lineageApi.workshop()
    rowsCache.value = data.rows
    buildGraph(data.rows, data.crossEdges)
  } catch (e: unknown) {
    message.error(`加载血缘数据失败：${getErrorMessage(e)}`)
  } finally {
    loading.value = false
  }
}

function buildGraph(rows: LineageRow[], crossEdges: LineageCrossEdge[]) {
  const headerNodes: Node[] = [
    { id: 'lh-source', type: 'lineageLayer', position: { x: COL_X.source + 19, y: HEADER_Y },
      data: { label: '数据源层', tone: 'source' }, draggable: false, selectable: false },
    { id: 'lh-etl', type: 'lineageLayer', position: { x: COL_X.etl + 7, y: HEADER_Y },
      data: { label: 'ETL层', tone: 'etl' }, draggable: false, selectable: false },
    { id: 'lh-ontology', type: 'lineageLayer', position: { x: COL_X.ontology + 1, y: HEADER_Y },
      data: { label: '本体层', tone: 'ontology' }, draggable: false, selectable: false },
    { id: 'lh-app', type: 'lineageLayer', position: { x: COL_X.app, y: HEADER_Y },
      data: { label: '应用层', tone: 'app' }, draggable: false, selectable: false },
  ]

  const rowNodes: Node[] = rows.flatMap((r, i) => {
    const y = i * ROW_GAP
    return [
      { id: `ls-${r.key}`, type: 'lineageSource', position: { x: COL_X.source, y },
        data: { label: r.source } },
      { id: `le-${r.key}`, type: 'lineageETL', position: { x: COL_X.etl, y: y + 2 },
        data: { label: r.etl } },
      { id: r.ontologyId, type: 'lineageOntology', position: { x: COL_X.ontology, y: y - 4 },
        data: { label: r.ontologyLabel, objectName: r.objectName, tier: r.tier } },
      { id: `la-${r.key}`, type: 'lineageApp', position: { x: COL_X.app, y: y + 2 },
        data: { label: r.app } },
    ]
  })

  const linkEdges: Edge[] = rows.flatMap((r) => [
    { id: `l-${r.key}-source-etl`, source: `ls-${r.key}`, target: `le-${r.key}`,
      style: { stroke: '#94a3b8' } },
    { id: `l-${r.key}-etl-ontology`, source: `le-${r.key}`, target: r.ontologyId,
      style: { stroke: '#8B5CF6' } },
    { id: `l-${r.key}-ontology-app`, source: r.ontologyId, target: `la-${r.key}`,
      style: { stroke: '#f59e0b' } },
  ])

  const ontologyEdges: Edge[] = crossEdges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    style: { stroke: '#8B5CF6', strokeDasharray: '5 3' },
  }))

  flowNodes.value = [...headerNodes, ...rowNodes]
  flowEdges.value = [...linkEdges, ...ontologyEdges]
}

async function onNodeClick(event: { node: Node }) {
  const node = event.node
  if (node.type !== 'lineageOntology') return

  detailOpen.value = true
  detailLoading.value = true
  detailData.value = null
  try {
    detailData.value = await lineageApi.objectFields(node.id)
  } catch (e: unknown) {
    message.error(`加载字段级血缘失败：${getErrorMessage(e)}`)
    detailOpen.value = false
  } finally {
    detailLoading.value = false
  }
}

function getErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return (error as { message: string }).message
  }
  return String(error)
}
</script>

<style scoped>
.ln-tab { display: flex; flex-direction: column; gap: 16px; }
.ln-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }

.ln-title {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 14px; font-weight: 600; color: var(--neutral-900);
}
.ln-title__dot {
  width: 6px; height: 6px; border-radius: 50%; background: #8B5CF6;
}
.ln-subtitle {
  font-size: 12px; color: var(--neutral-500); margin-top: 2px;
}

.ln-canvas-wrapper {
  position: relative;
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: 12px;
  height: 650px;
  overflow: hidden;
}

.ln-loading {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 10px; background: rgba(255,255,255,0.85);
  color: var(--neutral-500); font-size: 12px;
}
.ln-loading__spinner {
  width: 22px; height: 22px;
  border: 2.5px solid var(--neutral-100);
  border-top-color: #8B5CF6;
  border-radius: 50%;
  animation: ln-spin 0.7s linear infinite;
}
@keyframes ln-spin { to { transform: rotate(360deg); } }

.ln-drawer__loading { display: flex; justify-content: center; padding: 40px; }
.ln-drawer__empty { padding: 24px; text-align: center; color: var(--neutral-500); font-size: 13px; }

.ln-detail__group { margin-bottom: 20px; }
.ln-detail__group:last-child { margin-bottom: 0; }

.ln-detail__src {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}
.ln-detail__src-tag {
  font-size: 11px; font-weight: 600;
  color: #5b21b6; background: #EDE9FE;
  padding: 2px 8px; border-radius: 4px;
  flex-shrink: 0;
}
.ln-detail__src-text { color: var(--neutral-700); word-break: break-all; }

.ln-detail__table { width: 100%; border-collapse: collapse; }
.ln-detail__table thead th {
  background: var(--neutral-50); padding: 8px 12px; text-align: left;
  font-size: 11px; font-weight: 600; color: var(--neutral-600);
  border-bottom: 1px solid var(--neutral-200);
}
.ln-detail__table tbody td {
  padding: 8px 12px; font-size: 12px; color: var(--neutral-700);
  border-bottom: 1px solid var(--neutral-100);
}
.ln-mono { font-family: var(--font-mono, monospace); font-size: 11px; color: var(--neutral-800); }

.ln-tag {
  display: inline-block; padding: 1px 8px;
  font-size: 10px; font-weight: 600; border-radius: 4px;
  background: var(--neutral-100); color: var(--neutral-600);
}
.ln-tag--string { background: #DBEAFE; color: #1d4ed8; }
.ln-tag--int, .ln-tag--decimal, .ln-tag--integer { background: #FEF3C7; color: #92400e; }
.ln-tag--fk { background: #EDE9FE; color: #5b21b6; }
.ln-tag--enum { background: #FFE4E6; color: #be123c; }
.ln-tag--timestamp, .ln-tag--date, .ln-tag--datetime { background: #ECFEFF; color: #0e7490; }
.ln-tag--json, .ln-tag--text { background: #F3F4F6; color: #374151; }
.ln-tag--boolean { background: #DCFCE7; color: #166534; }

:deep(.vue-flow__edge-path) { stroke-width: 1.5; }
:deep(.vue-flow__controls) {
  background: #fff; border: 1px solid var(--neutral-200);
  border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
:deep(.vue-flow__controls-button) {
  background: #fff; border-color: var(--neutral-200); color: var(--neutral-500);
}
:deep(.vue-flow__controls-button:hover) {
  background: var(--neutral-50); color: var(--neutral-700);
}
:deep(.vue-flow__handle) { transition: opacity 0.15s; }
</style>
