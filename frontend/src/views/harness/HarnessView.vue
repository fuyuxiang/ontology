<template>
  <div class="harness">
    <!-- 顶栏 -->
    <div class="harness__topbar">
      <div class="harness__topbar-left">
        <template v-if="store.current">
          <span class="harness__divider"></span>
          <span class="harness__scene-name">{{ store.current.name }}</span>
          <span class="harness__status-tag" :class="`harness__status-tag--${store.current.status}`">
            {{ store.statusLabel }}
          </span>
          <span class="harness__dirty" v-if="store.isDirty">
            <svg width="6" height="6" viewBox="0 0 6 6"><circle cx="3" cy="3" r="3" fill="#f59e0b"/></svg>
            未保存
          </span>
        </template>
      </div>
      <div class="harness__topbar-right" v-if="store.current">
        <button class="harness__btn" @click="handleSave" :disabled="!store.isDirty">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 2h8l3 3v9H3V2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6 2v4h5V2M5 9h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          保存
        </button>
        <button class="harness__btn harness__btn--outline" @click="handlePublish" v-if="store.current.status === 'draft'">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 4v4l-6 4-6-4V6l6-4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
          发布
        </button>
        <button class="harness__btn harness__btn--primary" @click="handleExecute" :disabled="store.executing">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M5 3l9 5-9 5V3z" fill="currentColor"/></svg>
          {{ store.executing ? '执行中...' : '执行' }}
        </button>
        <button class="harness__btn harness__btn--ghost" @click="logExpanded = !logExpanded">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          日志
          <span v-if="store.executionLog.length" class="harness__log-badge">{{ store.executionLog.length }}</span>
        </button>
      </div>
    </div>

    <!-- 主体 -->
    <div class="harness__body">
      <!-- 左侧面板 -->
      <div class="harness__left">
        <!-- 节点库 -->
        <div class="harness__section harness__section--nodes">
          <div class="harness__section-header">
            <span class="harness__section-title">节点库</span>
            <span class="harness__section-hint">拖入或点击添加</span>
          </div>
          <div class="harness__node-lib">
            <template v-for="group in nodeGroups" :key="group.label">
              <div class="harness__node-group-label">{{ group.label }}</div>
              <div v-for="nt in group.nodes" :key="nt.type"
                class="harness__node-item"
                draggable="true"
                @dragstart="onDragStart($event, nt.type)"
                @click="addNodeToCenter(nt.type)"
                :title="`点击添加 ${nt.label}`">
                <span class="harness__node-item-icon" :style="{ color: nt.color }" v-html="nt.icon"></span>
                <span class="harness__node-item-label">{{ nt.label }}</span>
                <svg class="harness__node-item-add" width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- 画布 -->
      <div class="harness__canvas-wrap" ref="canvasWrap">
        <div v-if="!store.current" class="harness__canvas-empty">
          <div class="harness__canvas-empty-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <path d="M24 6L42 16v16L24 42 6 32V16L24 6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
              <path d="M24 16v16M16 20l8 4 8-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <p class="harness__canvas-empty-title">选择场景开始编排</p>
          <p class="harness__canvas-empty-sub">从左侧节点库拖入节点，连接节点构建工作流</p>
        </div>

        <VueFlow v-else
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          :node-types="nodeTypes_"
          :default-edge-options="defaultEdgeOptions"
          :snap-to-grid="true"
          :snap-grid="[16, 16]"
          fit-view-on-init
          class="harness__flow"
          @node-click="onNodeClick"
          @pane-click="onPaneClick"
          @drop="onDrop"
          @dragover.prevent>
          <Background variant="lines" pattern-color="#e8edf2" :gap="24" :size="1" />
          <Controls />
          <MiniMap :node-color="miniMapColor" node-stroke-color="transparent" mask-color="rgba(15,23,42,0.6)" />
        </VueFlow>

        <!-- 节点数量提示 -->
        <div class="harness__canvas-hint" v-if="store.current && flowNodes.length === 0">
          从左侧节点库拖入节点，或点击节点旁的 + 按钮添加
        </div>
      </div>

      <!-- 右侧配置面板 -->
      <transition name="panel-slide">
        <div class="harness__right" v-if="store.selectedNodeId && selectedNode">
          <div class="harness__panel-header">
            <div class="harness__panel-header-left">
              <span class="harness__panel-type-dot" :style="{ background: nodeTypeColor(selectedNode.type) }"></span>
              <span>节点配置</span>
            </div>
            <button class="harness__icon-btn" @click="store.selectNode(null)">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
          </div>
          <div class="harness__panel-body">
            <div class="harness__panel-type-badge" :style="{ color: nodeTypeColor(selectedNode.type), borderColor: nodeTypeColor(selectedNode.type) + '40', background: nodeTypeColor(selectedNode.type) + '12' }">
              <span v-html="nodeTypeIcon(selectedNode.type)"></span>
              {{ nodeTypeLabel(selectedNode.type) }}
            </div>

            <div class="harness__field">
              <label>节点名称</label>
              <input class="harness__input" v-model="selectedNode.data.label" @input="store.markDirty()" placeholder="输入节点名称" />
            </div>
            <div class="harness__field">
              <label>描述</label>
              <textarea class="harness__input harness__input--ta" v-model="selectedNode.data.description" @input="store.markDirty()" placeholder="节点说明" rows="2"></textarea>
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'ontology-query'">
              <label>本体对象</label>
              <input class="harness__input" v-model="selectedNode.data.ontology_type" @input="store.markDirty()" placeholder="如 InstallOrder" />
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'llm-inference'">
              <label>Prompt 模板</label>
              <textarea class="harness__input harness__input--ta" v-model="selectedNode.data.prompt" @input="store.markDirty()" placeholder="输入 Prompt 模板，支持 {变量} 占位符" rows="5"></textarea>
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'datasource'">
              <label>SQL 查询</label>
              <textarea class="harness__input harness__input--ta harness__input--mono" v-model="selectedNode.data.sql" @input="store.markDirty()" placeholder="SELECT * FROM table WHERE ..." rows="4"></textarea>
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'rule-engine'">
              <label>规则表达式</label>
              <textarea class="harness__input harness__input--ta harness__input--mono" v-model="selectedNode.data.rule_expr" @input="store.markDirty()" placeholder="如 risk_score > 80 AND churn_days < 30" rows="3"></textarea>
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'notification'">
              <label>通知方式</label>
              <select class="harness__input" v-model="selectedNode.data.notify_type" @change="store.markDirty()">
                <option value="sms">短信</option>
                <option value="workorder">工单</option>
                <option value="email">邮件</option>
              </select>
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'human-approval'">
              <label>审批角色</label>
              <input class="harness__input" v-model="selectedNode.data.approver_role" @input="store.markDirty()" placeholder="如 运营主管" />
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'condition'">
              <label>判断条件</label>
              <input class="harness__input" v-model="selectedNode.data.condition_expr" @input="store.markDirty()" placeholder="如 risk_score > 80" />
            </div>
            <div class="harness__field" v-if="selectedNode.type === 'ml-model'">
              <label>模型名称</label>
              <input class="harness__input" v-model="selectedNode.data.model_name" @input="store.markDirty()" placeholder="如 churn_predict_v2" />
            </div>

            <div class="harness__exec-result" v-if="selectedNode.data.result">
              <div class="harness__exec-result-label">
                <svg width="10" height="10" viewBox="0 0 16 16" fill="none"><path d="M3 8l4 4 6-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                执行结果
              </div>
              <div class="harness__exec-result-text">{{ selectedNode.data.result }}</div>
            </div>

            <div class="harness__panel-actions">
              <button class="harness__btn harness__btn--danger harness__btn--sm" @click="deleteNode(store.selectedNodeId!)">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V2h4v2M5 4v9h6V4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                删除节点
              </button>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- 执行日志抽屉 -->
    <transition name="log-slide">
      <div class="harness__log-drawer" v-if="logExpanded">
        <div class="harness__log-header">
          <div class="harness__log-header-left">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
            执行日志
            <span class="harness__log-count" v-if="store.executionLog.length">{{ store.executionLog.length }} 条</span>
          </div>
          <button class="harness__icon-btn" @click="logExpanded = false">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
        </div>
        <div class="harness__log-body">
          <div v-if="!store.executionLog.length" class="harness__log-empty">点击「执行」按钮开始执行工作流</div>
          <div v-for="(entry, i) in store.executionLog" :key="i"
            class="harness__log-entry" :class="`harness__log-entry--${entry.event}`">
            <span class="harness__log-dot"></span>
            <span class="harness__log-event">{{ eventLabel(entry.event) }}</span>
            <span class="harness__log-msg">{{ logMsg(entry) }}</span>
            <span class="harness__log-time">{{ new Date(entry.ts).toLocaleTimeString() }}</span>
          </div>
        </div>
      </div>
    </transition>

    <!-- 新建场景向导 -->
    <SceneWizard v-if="showNewDialog" @close="showNewDialog = false" @created="handleWizardCreate" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import WorkflowNode from '../../components/harness/nodes/WorkflowNode.vue'
import SceneWizard from '../../components/harness/SceneWizard.vue'
import { useHarnessStore } from '../../store/harness'

const store = useHarnessStore()
const route = useRoute()
const router = useRouter()
const canvasWrap = ref<HTMLElement>()
const logExpanded = ref(false)
const showNewDialog = ref(false)
const newForm = ref({ name: '', description: '', namespace: '' })
const flowNodes = ref<any[]>([])
const flowEdges = ref<any[]>([])

const nodeTypes_: Record<string, any> = {
  'ontology-query': markRaw(WorkflowNode), 'ontology-relation': markRaw(WorkflowNode),
  'rule-evaluate': markRaw(WorkflowNode), 'datasource': markRaw(WorkflowNode),
  'variable-assign': markRaw(WorkflowNode), 'parallel': markRaw(WorkflowNode),
  'llm-inference': markRaw(WorkflowNode), 'ml-model': markRaw(WorkflowNode),
  'voice-audit': markRaw(WorkflowNode),
  'condition': markRaw(WorkflowNode), 'loop': markRaw(WorkflowNode),
  'merge': markRaw(WorkflowNode), 'rule-engine': markRaw(WorkflowNode),
  'notification': markRaw(WorkflowNode), 'human-approval': markRaw(WorkflowNode),
  'write-back': markRaw(WorkflowNode), 'api-response': markRaw(WorkflowNode),
}

const defaultEdgeOptions = {
  type: 'smoothstep', markerEnd: MarkerType.ArrowClosed,
  style: { stroke: '#94a3b8', strokeWidth: 1.5 },
}

const nodeTypes = [
  { type: 'ontology-query', label: '本体实体查询', color: '#3b82f6', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'ontology-relation', label: '关系图遍历', color: '#6366f1', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="3" cy="8" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M5 8h3l3-4M5 8h3l3 4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>` },
  { type: 'rule-evaluate', label: '规则评估', color: '#f59e0b', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="13" cy="10" r="2" stroke="currentColor" stroke-width="1.5"/></svg>` },
  { type: 'datasource', label: '数据源连接', color: '#8b5cf6', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="currentColor" stroke-width="1.5"/><path d="M3 8v4c0 1.1 2.24 2 5 2s5-.9 5-2V8" stroke="currentColor" stroke-width="1.5"/></svg>` },
  { type: 'variable-assign', label: '变量赋值', color: '#64748b', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M4 5h8M4 8h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M10 10l3 2-3 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
  { type: 'parallel', label: '并行分支', color: '#0ea5e9', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 8h3M10 5h3M10 11h3M6 8l4-3M6 8l4 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'llm-inference', label: '大模型推理', color: '#10b981', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 3.5L13 7l-3.5 1.5L8 12l-1.5-3.5L3 7l3.5-1.5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'ml-model', label: '预测模型', color: '#06b6d4', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 7l3 3 2-4 3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
  { type: 'voice-audit', label: '语音质检', color: '#7c3aed', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><rect x="5" y="2" width="6" height="8" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 9a5 5 0 0010 0M8 14v-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'condition', label: '条件判断', color: '#a855f7', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 6-6 6-6-6 6-6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'loop', label: '遍历列表', color: '#0ea5e9', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 8a5 5 0 019.9-1M13 8a5 5 0 01-9.9 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'merge', label: '合并分支', color: '#84cc16', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M4 3v4l4 3 4-3V3M8 10v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
  { type: 'rule-engine', label: '规则引擎', color: '#f59e0b', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'notification', label: '通知触达', color: '#ec4899', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2a5 5 0 015 5v2l1 2H2l1-2V7a5 5 0 015-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'human-approval', label: '人工审批', color: '#f97316', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="2.5" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'write-back', label: '结果写回', color: '#64748b', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 3v8M5 8l3 3 3-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
  { type: 'api-response', label: 'API 响应', color: '#2e5bff', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M5 4L2 8l3 4M11 4l3 4-3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 3L7 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
]

const nodeGroups = [
  { label: '本体推理', nodes: nodeTypes.filter(n => ['ontology-query','ontology-relation','rule-evaluate'].includes(n.type)) },
  { label: '数据处理', nodes: nodeTypes.filter(n => ['datasource','variable-assign','parallel'].includes(n.type)) },
  { label: 'AI 能力', nodes: nodeTypes.filter(n => ['llm-inference','ml-model','voice-audit'].includes(n.type)) },
  { label: '流程控制', nodes: nodeTypes.filter(n => ['condition','loop','merge','rule-engine'].includes(n.type)) },
  { label: '触达输出', nodes: nodeTypes.filter(n => ['notification','human-approval','write-back','api-response'].includes(n.type)) },
]

const selectedNode = computed(() => flowNodes.value.find(n => n.id === store.selectedNodeId) ?? null)
function nodeTypeColor(type: string) { return nodeTypes.find(n => n.type === type)?.color ?? '#94a3b8' }
function nodeTypeLabel(type: string) { return nodeTypes.find(n => n.type === type)?.label ?? type }
function nodeTypeIcon(type: string) { return nodeTypes.find(n => n.type === type)?.icon ?? '' }

watch(() => store.current, (w) => {
  if (w) {
    flowNodes.value = (w.nodes_json || []).map((n: any) => ({ ...n }))
    flowEdges.value = (w.edges_json || []).map((e: any) => ({ ...e }))
  } else { flowNodes.value = []; flowEdges.value = [] }
})

watch(() => store.executionLog, (log) => {
  for (const entry of log) {
    if (entry.event === 'node_start') {
      const n = flowNodes.value.find(n => n.id === entry.data.node_id)
      if (n) n.data = { ...n.data, execState: 'running' }
    } else if (entry.event === 'node_result') {
      const n = flowNodes.value.find(n => n.id === entry.data.node_id)
      if (n) n.data = { ...n.data, execState: 'done', result: entry.data.result?.message }
    } else if (entry.event === 'node_error') {
      const n = flowNodes.value.find(n => n.id === entry.data.node_id)
      if (n) n.data = { ...n.data, execState: 'error' }
    }
  }
  if (log.length > 0) logExpanded.value = true
}, { deep: true })

onMounted(async () => {
  await store.loadList()
  const id = route.query.id as string
  if (id) await store.loadWorkflow(id)
})

async function loadScene(id: string) { await store.loadWorkflow(id) }
async function handleCreate() {
  if (!newForm.value.name) return
  await store.createWorkflow(newForm.value.name, newForm.value.description, newForm.value.namespace)
  showNewDialog.value = false
  newForm.value = { name: '', description: '', namespace: '' }
}
async function handleSave() { await store.saveCanvas(flowNodes.value, flowEdges.value) }
async function handlePublish() { await store.publishWorkflow() }
function handleExecute() {
  if (!store.current) return
  flowNodes.value.forEach(n => { n.data = { ...n.data, execState: 'pending', result: undefined } })
  store.startExecution(store.current.id)
}
function onNodeClick({ node }: { node: any }) { store.selectNode(node.id) }
function onPaneClick() { store.selectNode(null) }

let dragType = ''
function onDragStart(e: DragEvent, type: string) { dragType = type; e.dataTransfer!.effectAllowed = 'move' }
function onDrop(e: DragEvent) {
  if (!dragType || !canvasWrap.value) return
  const rect = canvasWrap.value.getBoundingClientRect()
  addNode(dragType, { x: e.clientX - rect.left - 80, y: e.clientY - rect.top - 30 })
  dragType = ''
}
function addNodeToCenter(type: string) {
  if (!store.current) return
  const i = flowNodes.value.length
  addNode(type, { x: 80 + (i % 4) * 220, y: 80 + Math.floor(i / 4) * 120 })
}
function addNode(type: string, position: { x: number; y: number }) {
  const id = `node-${Date.now()}`
  const meta = nodeTypes.find(n => n.type === type)
  flowNodes.value.push({ id, type, position, data: { label: meta?.label || type, execState: 'pending' } })
  store.markDirty()
}
function deleteNode(id: string) {
  flowNodes.value = flowNodes.value.filter(n => n.id !== id)
  flowEdges.value = flowEdges.value.filter(e => e.source !== id && e.target !== id)
  store.selectNode(null); store.markDirty()
}
function miniMapColor(node: any) { return nodeTypeColor(node.type) }

async function handleWizardCreate(name: string, description: string, namespace: string, entityIds: string[], dsIds: string[], agentId: string) {
  await store.createWorkflow(name, description, namespace)
  showNewDialog.value = false

  // 预置本体查询节点
  let x = 60
  for (const eid of entityIds) {
    const entity = (await import('../../store/ontology')).useOntologyStore().entities.find(e => e.id === eid)
    if (entity) {
      flowNodes.value.push({ id: `node-${Date.now()}-${eid}`, type: 'ontology-query', position: { x, y: 80 }, data: { label: `查询${entity.name_cn}`, execState: 'pending', ontology_type: entity.name } })
      x += 220
    }
  }

  // 预置数据源节点
  for (const dsId of dsIds) {
    flowNodes.value.push({ id: `node-ds-${Date.now()}-${dsId}`, type: 'datasource', position: { x, y: 80 }, data: { label: '数据源查询', execState: 'pending' } })
    x += 220
  }

  if (flowNodes.value.length > 0) store.markDirty()
}

function eventLabel(e: string) {
  return { workflow_start: '开始', node_start: '启动', node_result: '完成', node_error: '错误', workflow_done: '结束' }[e] || e
}
function logMsg(entry: any) {
  if (entry.event === 'node_start') return `${entry.data.label} 开始执行`
  if (entry.event === 'node_result') return `${entry.data.label}: ${entry.data.result?.message || '完成'}`
  if (entry.event === 'node_error') return `${entry.data.label} 执行失败: ${entry.data.error}`
  if (entry.event === 'workflow_done') return `工作流执行完成，共 ${entry.data.node_count} 个节点`
  if (entry.event === 'workflow_start') return `开始执行「${entry.data.workflow_name}」`
  return JSON.stringify(entry.data)
}
</script>

<style scoped>
/* ── Theme variables ── */
.harness {
  --h-bg: #f8fafc;
  --h-bg-2: #fff;
  --h-bg-3: #f1f5f9;
  --h-border: #e2e8f0;
  --h-border-2: #cbd5e1;
  --h-text: #0f172a;
  --h-text-2: #334155;
  --h-text-3: #64748b;
  --h-text-4: #94a3b8;
  --h-input-bg: #fff;
  --h-node-bg: #fff;
  --h-node-border: #e2e8f0;
  --h-accent: #4f46e5;
  --h-accent-hover: #4338ca;
  --h-canvas-bg: #ffffff;
  --h-canvas-dot: #e2e8f0;
  --h-log-bg: #1e293b;
}
:global([data-theme='dark']) .harness {
  --h-bg: #0f172a;
  --h-bg-2: #1e293b;
  --h-bg-3: #0a0f1a;
  --h-border: #1e293b;
  --h-border-2: #334155;
  --h-text: #f1f5f9;
  --h-text-2: #cbd5e1;
  --h-text-3: #64748b;
  --h-text-4: #475569;
  --h-input-bg: #0a0f1a;
  --h-node-bg: #1e293b;
  --h-node-border: #334155;
  --h-accent: #6366f1;
  --h-accent-hover: #4f46e5;
  --h-canvas-bg: #0f172a;
  --h-canvas-dot: #334155;
  --h-log-bg: #0a0f1a;
}

.harness {
  display: flex; flex-direction: column; height: 100vh;
  background: var(--h-bg); font-family: inherit; color: var(--h-text);
}
.harness__topbar {
  display: flex; align-items: center; justify-content: space-between;
  height: 48px; padding: 0 16px; flex-shrink: 0;
  background: var(--h-bg); border-bottom: 1px solid var(--h-border); gap: 8px;

}
.harness__topbar-left { display: flex; align-items: center; gap: 8px; }
.harness__logo-icon { display: flex; align-items: center; }
.harness__title { font-size: var(--text-body-size); font-weight: 700; color: var(--h-text); letter-spacing: .02em; }
.harness__divider { width: 1px; height: 14px; background: var(--h-border-2); }
.harness__scene-name { font-size: var(--text-code-size); color: var(--h-text-2); }
.harness__dirty { display: flex; align-items: center; gap: 4px; font-size: var(--text-caption-size); color: var(--kinetic-500); }
.harness__status-tag { font-size: var(--text-caption-upper-size); padding: 2px 7px; border-radius: 10px; font-weight: 600; background: var(--h-bg-2); color: var(--h-text-3); }
.harness__status-tag--draft { background: var(--kinetic-900); color: var(--kinetic-600); }
.harness__status-tag--published { background: var(--dynamic-900); color: var(--dynamic-300); }
.harness__topbar-right { display: flex; align-items: center; gap: 6px; }
.harness__btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 11px; border-radius: 6px; font-size: var(--text-code-size); font-weight: 500;
  border: 1px solid var(--h-border-2); background: var(--h-bg-2); color: var(--h-text-2);
  cursor: pointer; transition: all .15s; white-space: nowrap;
}
.harness__btn:hover:not(:disabled) { background: var(--h-bg-2); border-color: var(--h-border-2); color: var(--h-text); }
.harness__btn:disabled { opacity: .4; cursor: not-allowed; }
.harness__btn--primary { background: var(--semantic-600); border-color: var(--semantic-600); color: var(--neutral-0); }
.harness__btn--primary:hover:not(:disabled) { background: var(--semantic-800); border-color: var(--semantic-800); }
.harness__btn--outline { border-color: var(--semantic-600); color: var(--semantic-400); background: transparent; }
.harness__btn--outline:hover:not(:disabled) { background: var(--semantic-900); }
.harness__btn--ghost { border-color: transparent; background: transparent; color: var(--neutral-700); }
.harness__btn--ghost:hover:not(:disabled) { background: var(--h-bg-2); color: var(--h-text-2); }
.harness__btn--danger { background: var(--kinetic-900); border-color: var(--kinetic-900); color: var(--status-error); }
.harness__btn--danger:hover:not(:disabled) { background: var(--kinetic-900); }
.harness__btn--sm { padding: 3px 8px; font-size: var(--text-caption-size); }
.harness__log-badge { background: var(--semantic-600); color: var(--neutral-0); font-size: var(--text-caption-upper-size); font-weight: 700; padding: 1px 5px; border-radius: 8px; }
.harness__icon-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: 5px; border: none;
  background: transparent; color: var(--neutral-700); cursor: pointer; transition: all .15s;
}
.harness__icon-btn:hover { background: var(--h-bg-2); color: var(--h-text-2); }
.harness__body { display: flex; flex: 1; overflow: hidden; }
.harness__left {
  width: 216px; flex-shrink: 0; display: flex; flex-direction: column;
  background: var(--h-bg); border-right: 1px solid var(--h-border); overflow: hidden;
}
.harness__section { display: flex; flex-direction: column; overflow: hidden; }
.harness__section--nodes { flex: 1; overflow: hidden; border-top: 1px solid var(--h-border); }
.harness__section-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; flex-shrink: 0;
}
.harness__section-title { font-size: var(--text-caption-upper-size); font-weight: 600; color: var(--h-text-4); text-transform: uppercase; letter-spacing: .06em; }
.harness__section-hint { font-size: var(--text-caption-upper-size); color: var(--h-border-2); }
.harness__scene-list { overflow-y: auto; flex: 1; max-height: 220px; padding: 2px 0; }
.harness__scene-item { padding: 8px 12px; cursor: pointer; border-left: 2px solid transparent; transition: all .12s; }
.harness__scene-item:hover { background: var(--h-bg-2); }
.harness__scene-item--active { background: var(--semantic-900); border-left-color: var(--semantic-600); }
.harness__scene-item-row { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.harness__scene-item-name { font-size: var(--text-code-size); font-weight: 500; color: var(--h-text-2); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.harness__scene-item-meta { display: flex; align-items: center; gap: 4px; margin-top: 3px; font-size: var(--text-caption-upper-size); color: var(--h-text-4); }
.harness__scene-status { font-size: var(--text-caption-upper-size); font-weight: 600; padding: 1px 5px; border-radius: 4px; flex-shrink: 0; }
.harness__scene-status--draft { background: var(--kinetic-900); color: var(--kinetic-600); }
.harness__scene-status--published { background: var(--dynamic-900); color: var(--dynamic-300); }
.harness__scene-status--disabled { background: var(--neutral-900); color: var(--neutral-800); }
.harness__empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 20px 12px; color: var(--h-border-2); font-size: var(--text-caption-size); }
.harness__node-lib { overflow-y: auto; flex: 1; padding: 4px 8px; display: flex; flex-direction: column; gap: 1px; }
.harness__node-group-label { font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.6px; padding: 8px 4px 4px; margin-top: 4px; border-top: 1px solid #f1f5f9; }
.harness__node-group-label:first-child { border-top: none; margin-top: 0; }
.harness__node-item {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px;
  cursor: pointer; border: 1px solid transparent; transition: all .12s; position: relative;
}
.harness__node-item:hover { background: var(--h-bg-2); border-color: var(--h-border-2); }
.harness__node-item:hover .harness__node-item-add { opacity: 1; }
.harness__node-item-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
.harness__node-item-icon { display: flex; flex-shrink: 0; }
.harness__node-item-label { font-size: var(--text-caption-size); color: var(--h-text-2); font-weight: 500; flex: 1; }
.harness__node-item-add { opacity: 0; color: var(--h-text-4); transition: opacity .15s; flex-shrink: 0; }
.harness__canvas-wrap { flex: 1; position: relative; overflow: hidden; background: var(--h-bg); }
.harness__flow { width: 100%; height: 100%; }
.harness__canvas-empty {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 10px; color: var(--h-border-2);
}
.harness__canvas-empty-icon { color: var(--h-bg-2); }
.harness__canvas-empty-title { font-size: var(--text-body-size); font-weight: 600; color: var(--h-text-4); margin: 0; }
.harness__canvas-empty-sub { font-size: var(--text-code-size); color: var(--h-border-2); margin: 0; }
.harness__canvas-hint {
  position: absolute; bottom: 60px; left: 50%; transform: translateX(-50%);
  font-size: var(--text-caption-size); color: var(--h-text-4); background: var(--h-bg-2); border: 1px solid var(--h-border-2);
  padding: 5px 12px; border-radius: 20px; pointer-events: none; white-space: nowrap;
}
.harness__right {
  width: 272px; flex-shrink: 0; background: var(--h-bg);
  border-left: 1px solid var(--h-border); display: flex; flex-direction: column; overflow: hidden;
}
.harness__panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border-bottom: 1px solid var(--h-border); flex-shrink: 0;
}
.harness__panel-header-left { display: flex; align-items: center; gap: 7px; font-size: var(--text-code-size); font-weight: 600; color: var(--h-text-2); }
.harness__panel-type-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.harness__panel-body { flex: 1; overflow-y: auto; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
.harness__panel-type-badge {
  display: inline-flex; align-items: center; gap: 6px; font-size: var(--text-caption-size); font-weight: 600;
  padding: 4px 10px; border-radius: 6px; border: 1px solid; align-self: flex-start;
}
.harness__panel-actions { margin-top: 4px; }
.harness__field { display: flex; flex-direction: column; gap: 5px; }
.harness__field label { font-size: var(--text-caption-size); font-weight: 600; color: var(--h-text-4); }
.harness__required { color: var(--status-error); }
.harness__input {
  padding: 6px 9px; border-radius: 6px; font-size: var(--text-code-size);
  border: 1px solid var(--h-border); background: var(--h-input-bg); color: var(--h-text);
  outline: none; transition: border-color .15s; width: 100%; box-sizing: border-box; font-family: inherit;
}
.harness__input:focus { border-color: var(--semantic-600); }
.harness__input--ta { resize: vertical; min-height: 60px; }
.harness__input--mono { font-family: var(--font-mono); font-size: var(--text-caption-size); }
.harness__exec-result { background: var(--dynamic-900); border: 1px solid var(--dynamic-900); border-radius: 6px; padding: 8px 10px; }
.harness__exec-result-label { font-size: var(--text-caption-upper-size); font-weight: 600; color: var(--dynamic-300); margin-bottom: 4px; display: flex; align-items: center; gap: 4px; }
.harness__exec-result-text { font-size: var(--text-caption-size); color: var(--dynamic-200); }
.harness__log-drawer {
  position: absolute; bottom: 0; left: 216px; right: 0;
  height: 200px; background: var(--h-log-bg); border-top: 1px solid var(--h-border);
  display: flex; flex-direction: column; z-index: 50;
}
.harness__log-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 14px; height: 36px; border-bottom: 1px solid var(--h-border); flex-shrink: 0;
  font-size: var(--text-caption-size); font-weight: 600; color: var(--h-text-4);
}
.harness__log-header-left { display: flex; align-items: center; gap: 7px; }
.harness__log-count { background: var(--h-bg-2); color: var(--h-text-3); padding: 1px 6px; border-radius: 8px; font-size: var(--text-caption-upper-size); }
.harness__log-body { flex: 1; overflow-y: auto; padding: 4px 0; }
.harness__log-empty { padding: 16px 14px; font-size: var(--text-caption-size); color: var(--h-border-2); }
.harness__log-entry { display: flex; align-items: center; gap: 8px; padding: 4px 14px; font-size: var(--text-caption-size); }
.harness__log-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--h-border-2); flex-shrink: 0; }
.harness__log-entry--node_start .harness__log-dot { background: var(--semantic-500); }
.harness__log-entry--node_result .harness__log-dot { background: var(--status-success); }
.harness__log-entry--node_error .harness__log-dot { background: var(--status-error); }
.harness__log-entry--workflow_done .harness__log-dot { background: var(--semantic-600); }
.harness__log-event { font-weight: 600; flex-shrink: 0; min-width: 36px; color: var(--h-text-4); font-size: var(--text-caption-upper-size); }
.harness__log-msg { color: var(--h-text-3); flex: 1; }
.harness__log-time { color: var(--h-border-2); font-size: var(--text-caption-upper-size); flex-shrink: 0; }
.harness__dialog-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,.6);
  display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(2px);
}
.harness__dialog {
  background: var(--h-bg); border: 1px solid var(--h-border); border-radius: 12px; padding: 24px;
  width: 400px; display: flex; flex-direction: column; gap: 14px;
  box-shadow: 0 24px 64px rgba(0,0,0,.5);
}
.harness__dialog-header { display: flex; align-items: center; justify-content: space-between; }
.harness__dialog-title { font-size: var(--text-body-size); font-weight: 700; color: var(--h-text); }
.harness__dialog-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
.panel-slide-enter-active, .panel-slide-leave-active { transition: all .2s ease; }
.panel-slide-enter-from, .panel-slide-leave-to { transform: translateX(20px); opacity: 0; }
.log-slide-enter-active, .log-slide-leave-active { transition: all .2s ease; }
.log-slide-enter-from, .log-slide-leave-to { transform: translateY(20px); opacity: 0; }
:deep(.vue-flow__background) { background: var(--h-canvas-bg); }
:deep(.vue-flow__controls) { background: var(--h-bg-2); border: 1px solid var(--h-border-2); border-radius: 8px; overflow: hidden; }
:deep(.vue-flow__controls-button) { background: var(--h-bg-2); border-color: var(--h-border-2); color: var(--h-text-3); }
:deep(.vue-flow__controls-button:hover) { background: var(--h-bg-2); color: var(--h-text-2); }
:deep(.vue-flow__minimap) { background: var(--h-bg-3); border: 1px solid var(--h-border); border-radius: 8px; }
</style>
