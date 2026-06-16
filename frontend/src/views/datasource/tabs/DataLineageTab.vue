<template>
  <div class="ln-tab">
    <div class="ln-header">
      <div>
        <div class="ln-title">
          <span class="ln-title__dot"></span>
          数据血缘追踪
        </div>
        <div class="ln-subtitle">数据资产 → 本体类型 → 动作；边由本体映射 (Binding) 与执行日志自动写入</div>
      </div>
      <div class="ln-stats" v-if="!loading && stats.total > 0">
        <span><b>{{ stats.assets }}</b> 资产</span>
        <span><b>{{ stats.objectTypes }}</b> 本体</span>
        <span><b>{{ stats.actions }}</b> 动作</span>
        <span><b>{{ stats.bindsTo }}</b> 绑定</span>
        <span><b>{{ stats.reads }}</b> 读取</span>
      </div>
    </div>

    <div class="ln-canvas-wrapper">
      <VueFlow
        v-if="flowNodes.length > 0"
        v-model:nodes="flowNodes"
        v-model:edges="flowEdges"
        :node-types="nodeTypes"
        :default-edge-options="defaultEdgeOptions"
        :fit-view-on-init="true"
        :fit-view-options="{ padding: 0.12 }"
        :nodes-draggable="true"
        :nodes-connectable="false"
        :pan-on-drag="true"
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

      <div v-else-if="flowNodes.length === 0" class="ln-empty">
        <div class="ln-empty__icon">↯</div>
        <div class="ln-empty__title">暂无血缘记录</div>
        <div class="ln-empty__desc">
          血缘边由 <b>本体映射 (ObjectBinding)</b> 与 <b>执行日志</b> 自动写入。
          <br />
          请先在「数据接入」注册资产，并在「本体管理」为对象类型建立映射。
        </div>
      </div>
    </div>

    <a-drawer
      v-model:open="detailOpen"
      :title="detailTitle"
      width="560"
      placement="right"
      :body-style="{ paddingBottom: '24px' }"
    >
      <div v-if="detailNode">
        <div class="ln-detail__row">
          <span class="ln-detail__label">类型</span>
          <a-tag :color="kindTagColor(detailNode.kind)">{{ kindLabel(detailNode.kind) }}</a-tag>
        </div>
        <div class="ln-detail__row" v-for="[k, v] in detailExtraEntries" :key="k">
          <span class="ln-detail__label">{{ extraLabel(k) }}</span>
          <span class="ln-detail__value">{{ v ?? '-' }}</span>
        </div>

        <a-divider />
        <div class="ln-detail__section-title">相关边 ({{ detailEdges.length }})</div>
        <div v-if="detailEdges.length === 0" class="ln-detail__empty">无</div>
        <div v-else>
          <div v-for="(edge, ei) in detailEdges" :key="ei" class="ln-edge-card">
            <div class="ln-edge-card__main">
              <span class="ln-edge-card__node">{{ nodeLabel(edge.source) }}</span>
              <span class="ln-edge-card__arrow">{{ relationLabel(edge.relation) }} →</span>
              <span class="ln-edge-card__node">{{ nodeLabel(edge.target) }}</span>
            </div>
            <div class="ln-edge-card__meta">
              <span v-if="edge.via_module">via {{ edge.via_module }}</span>
              <span v-if="edge.via_purpose">· purpose: <code>{{ edge.via_purpose }}</code></span>
              <span>· weight: {{ edge.weight }}</span>
            </div>
          </div>
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
import LineageOntologyNode from '../../../components/lineage/LineageOntologyNode.vue'
import LineageAppNode from '../../../components/lineage/LineageAppNode.vue'

import { lineageApi, type LineageGraph, type LineageNode as LNode, type LineageNodeKind } from '../../../api/lineage'
import { getErrorMessage } from '../../../utils/error'

const nodeTypes = {
  lineageLayer: markRaw(LineageLayerNode),
  lineageAsset: markRaw(LineageSourceNode),
  lineageOntology: markRaw(LineageOntologyNode),
  lineageAction: markRaw(LineageAppNode),
} as any

const defaultEdgeOptions = {
  type: 'default',
  markerEnd: MarkerType.ArrowClosed,
}

const COL_X = { asset: 0, ontology: 360, action: 720 }
const ROW_GAP = 64
const HEADER_Y = -62

const flowNodes = ref<Node[]>([])
const flowEdges = ref<Edge[]>([])
const loading = ref(false)
const graphCache = ref<LineageGraph | null>(null)
const nodeIndex = ref<Record<string, LNode>>({})

const stats = computed(() => {
  const g = graphCache.value
  if (!g) return { total: 0, assets: 0, objectTypes: 0, actions: 0, bindsTo: 0, reads: 0 }
  return {
    total: g.nodes.length,
    assets: g.nodes.filter(n => n.kind === 'asset').length,
    objectTypes: g.nodes.filter(n => n.kind === 'object_type').length,
    actions: g.nodes.filter(n => n.kind === 'action').length,
    bindsTo: g.edges.filter(e => e.relation === 'binds_to').length,
    reads: g.edges.filter(e => e.relation === 'reads').length,
  }
})

const detailOpen = ref(false)
const detailNode = ref<LNode | null>(null)
const detailTitle = computed(() => {
  if (!detailNode.value) return '节点详情'
  return `${detailNode.value.label || detailNode.value.id.slice(0, 8)} — ${kindLabel(detailNode.value.kind)}`
})
const detailExtraEntries = computed<[string, unknown][]>(() => {
  const extra = detailNode.value?.extra
  if (!extra) return []
  return Object.entries(extra).filter(([, v]) => v !== null && v !== undefined && v !== '')
})
const detailEdges = computed(() => {
  if (!detailNode.value || !graphCache.value) return []
  const key = `${detailNode.value.kind}:${detailNode.value.id}`
  return graphCache.value.edges.filter(
    e => `${e.source.kind}:${e.source.id}` === key || `${e.target.kind}:${e.target.id}` === key,
  )
})

onMounted(loadGraph)

async function loadGraph() {
  loading.value = true
  try {
    const data = await lineageApi.overview()
    graphCache.value = data
    nodeIndex.value = Object.fromEntries(data.nodes.map(n => [`${n.kind}:${n.id}`, n]))
    buildGraph(data)
  } catch (e: unknown) {
    message.error(`加载血缘数据失败：${getErrorMessage(e)}`)
  } finally {
    loading.value = false
  }
}

function buildGraph(g: LineageGraph) {
  if (g.nodes.length === 0) {
    flowNodes.value = []
    flowEdges.value = []
    return
  }

  const groups: Record<LineageNodeKind, LNode[]> = {
    asset: [],
    object_type: [],
    action: [],
    rule: [],
  }
  for (const n of g.nodes) groups[n.kind].push(n)

  const headerNodes: Node[] = [
    { id: 'lh-asset', type: 'lineageLayer', position: { x: COL_X.asset + 40, y: HEADER_Y },
      data: { label: '数据资产', tone: 'source' }, draggable: false, selectable: false },
    { id: 'lh-ontology', type: 'lineageLayer', position: { x: COL_X.ontology + 40, y: HEADER_Y },
      data: { label: '本体类型', tone: 'ontology' }, draggable: false, selectable: false },
    { id: 'lh-action', type: 'lineageLayer', position: { x: COL_X.action + 40, y: HEADER_Y },
      data: { label: '动作', tone: 'app' }, draggable: false, selectable: false },
  ]

  const flowNs: Node[] = [...headerNodes]
  for (const [kind, list] of Object.entries(groups) as [LineageNodeKind, LNode[]][]) {
    const x = kind === 'asset' ? COL_X.asset : kind === 'object_type' ? COL_X.ontology : COL_X.action
    const type = kind === 'asset' ? 'lineageAsset' : kind === 'object_type' ? 'lineageOntology' : 'lineageAction'
    list.forEach((n, i) => {
      flowNs.push({
        id: `${kind}:${n.id}`,
        type,
        position: { x, y: i * ROW_GAP },
        data: {
          label: n.label || n.id.slice(0, 8),
          objectName: n.sub_label || '',
          tier: (n.extra?.tier as number) || undefined,
        },
      })
    })
  }

  const edgeColor = (rel: string) => {
    if (rel === 'binds_to') return '#8B5CF6'
    if (rel === 'reads') return '#3b82f6'
    if (rel === 'writes') return '#f59e0b'
    return '#94a3b8'
  }
  const flowEs: Edge[] = g.edges.map((e, i) => ({
    id: `e-${i}`,
    source: `${e.source.kind}:${e.source.id}`,
    target: `${e.target.kind}:${e.target.id}`,
    label: e.weight > 1 ? `×${e.weight}` : undefined,
    style: { stroke: edgeColor(e.relation), strokeWidth: Math.min(3, 1 + Math.log2(e.weight || 1)) },
    labelStyle: { fontSize: '10px', fill: '#6b7280' },
  }))

  flowNodes.value = flowNs
  flowEdges.value = flowEs
}

function onNodeClick(event: { node: Node }) {
  const id = event.node.id
  if (id.startsWith('lh-')) return
  const n = nodeIndex.value[id]
  if (!n) return
  detailNode.value = n
  detailOpen.value = true
}

function nodeLabel(ref: { kind: LineageNodeKind; id: string }) {
  const n = nodeIndex.value[`${ref.kind}:${ref.id}`]
  return n?.label || ref.id.slice(0, 8)
}

function kindLabel(k: LineageNodeKind) {
  return ({ asset: '数据资产', object_type: '本体类型', action: '动作', rule: '规则' })[k] || k
}

function kindTagColor(k: LineageNodeKind) {
  return ({ asset: 'blue', object_type: 'purple', action: 'orange', rule: 'green' })[k] || 'default'
}

function relationLabel(r: string) {
  return ({ binds_to: '映射 (binds_to)', reads: '读取 (reads)', writes: '写入 (writes)', derives_from: '派生 (derives_from)' } as Record<string, string>)[r] || r
}

function extraLabel(k: string) {
  return ({
    name: '名称', alias: '别名', kind: '类型',
    connection_id: '连接 ID', connection_name: '所属连接', status: '状态',
    name_cn: '中文名', tier: '层级', entity_id: '所属实体', type: '类型',
  } as Record<string, string>)[k] || k
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
.ln-stats {
  display: flex; gap: 16px; font-size: 12px; color: var(--neutral-600);
}
.ln-stats b { color: var(--neutral-900); font-weight: 600; margin-right: 2px; }

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

.ln-empty {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 40px; text-align: center; color: var(--neutral-500);
}
.ln-empty__icon {
  font-size: 36px; color: #c4b5fd; line-height: 1;
}
.ln-empty__title { font-size: 14px; font-weight: 600; color: var(--neutral-700); }
.ln-empty__desc { font-size: 12px; line-height: 1.7; max-width: 480px; }
.ln-empty__desc b { color: var(--neutral-700); font-weight: 600; }

.ln-detail__row {
  display: flex; gap: 16px; padding: 6px 0;
  font-size: 13px;
}
.ln-detail__label { width: 96px; color: var(--neutral-500); flex-shrink: 0; }
.ln-detail__value { color: var(--neutral-800); word-break: break-all; }
.ln-detail__section-title {
  font-size: 12px; font-weight: 600; color: var(--neutral-700); margin-bottom: 8px;
}
.ln-detail__empty { color: var(--neutral-400); font-size: 12px; padding: 8px 0; }

.ln-edge-card {
  border: 1px solid var(--neutral-200);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 8px;
  background: var(--neutral-50);
}
.ln-edge-card__main {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  font-size: 12px;
}
.ln-edge-card__node {
  font-weight: 600; color: var(--neutral-800);
  background: #fff; padding: 2px 8px; border-radius: 4px;
  border: 1px solid var(--neutral-200);
}
.ln-edge-card__arrow { color: #8B5CF6; font-size: 11px; }
.ln-edge-card__meta {
  margin-top: 4px; font-size: 11px; color: var(--neutral-500);
}
.ln-edge-card__meta code {
  background: var(--neutral-100); padding: 1px 4px; border-radius: 3px;
  font-size: 10px;
}

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
