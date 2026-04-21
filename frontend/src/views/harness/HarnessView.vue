<template>
  <div class="harness">
    <!-- 顶栏 -->
    <div class="harness__topbar">
      <div class="harness__topbar-left">
        <span class="harness__logo-icon">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M9 2L16 6v6l-7 4-7-4V6l7-4z" stroke="#4c6ef5" stroke-width="1.5" stroke-linejoin="round"/>
            <path d="M9 6l4 2.5v3L9 14l-4-2.5v-3L9 6z" fill="#4c6ef5" opacity=".3"/>
          </svg>
        </span>
        <span class="harness__title">智能编排中心</span>
        <span class="harness__divider">|</span>
        <span class="harness__scene-name" v-if="store.current">{{ store.current.name }}</span>
        <span class="harness__status-tag" v-if="store.current" :class="`harness__status-tag--${store.current.status}`">
          {{ store.statusLabel }}
        </span>
        <span class="harness__dirty" v-if="store.isDirty">● 未保存</span>
      </div>
      <div class="harness__topbar-right" v-if="store.current">
        <button class="harness__btn" @click="handleSave" :disabled="!store.isDirty">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 2h8l3 3v9H3V2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6 2v4h5V2M5 9h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          保存
        </button>
        <button class="harness__btn harness__btn--outline" @click="handlePublish" v-if="store.current.status === 'draft'">
          发布
        </button>
        <button class="harness__btn harness__btn--primary" @click="handleExecute" :disabled="store.executing">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M5 3l9 5-9 5V3z" fill="currentColor"/></svg>
          {{ store.executing ? '执行中...' : '执行' }}
        </button>
      </div>
    </div>

    <!-- 主体 -->
    <div class="harness__body">
      <!-- 左侧：场景列表 + 节点库 -->
      <div class="harness__left">
        <!-- 场景列表 -->
        <div class="harness__section">
          <div class="harness__section-header">
            <span>场景列表</span>
            <button class="harness__icon-btn" @click="showNewDialog = true" title="新建场景">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
          </div>
          <div class="harness__scene-list">
            <div
              v-for="w in store.workflows" :key="w.id"
              class="harness__scene-item"
              :class="{ 'harness__scene-item--active': store.current?.id === w.id }"
              @click="loadScene(w.id)"
            >
              <div class="harness__scene-item-name">{{ w.name }}</div>
              <div class="harness__scene-item-meta">
                <span class="harness__scene-status" :class="`harness__scene-status--${w.status}`">{{ { draft:'草稿', published:'已发布', disabled:'停用' }[w.status] }}</span>
                <span>{{ w.node_count }} 节点</span>
              </div>
            </div>
            <div v-if="!store.workflows.length" class="harness__empty">暂无场景</div>
          </div>
        </div>

        <!-- 节点库 -->
        <div class="harness__section harness__section--nodes">
          <div class="harness__section-header"><span>节点库</span></div>
          <div class="harness__node-lib">
            <div
              v-for="nt in nodeTypes" :key="nt.type"
              class="harness__node-item"
              draggable="true"
              @dragstart="onDragStart($event, nt.type)"
            >
              <span class="harness__node-item-icon" :style="{ color: nt.color }" v-html="nt.icon"></span>
              <span class="harness__node-item-label">{{ nt.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间：画布 -->
      <div class="harness__canvas-wrap" ref="canvasWrap">
        <div v-if="!store.current" class="harness__canvas-empty">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none" opacity=".2">
            <path d="M32 8L56 22v20L32 56 8 42V22L32 8z" stroke="currentColor" stroke-width="2"/>
            <path d="M32 20v24M20 26l12 6 12-6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <p>选择左侧场景或新建场景开始编排</p>
          <button class="harness__btn harness__btn--primary" @click="showNewDialog = true">新建场景</button>
        </div>

        <VueFlow
          v-else
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          :node-types="nodeTypes_"
          :default-edge-options="defaultEdgeOptions"
          :snap-to-grid="true"
          :snap-grid="[20, 20]"
          fit-view-on-init
          class="harness__flow"
          @node-click="onNodeClick"
          @pane-click="onPaneClick"
          @drop="onDrop"
          @dragover.prevent
        >
          <Background pattern-color="#e2e8f0" :gap="20" />
          <Controls />
          <MiniMap :node-color="miniMapColor" />
        </VueFlow>
      </div>

      <!-- 右侧：节点配置面板 -->
      <div class="harness__right" v-if="store.selectedNodeId && selectedNode">
        <div class="harness__panel-header">
          <span>节点配置</span>
          <button class="harness__icon-btn" @click="store.selectNode(null)">✕</button>
        </div>
        <div class="harness__panel-body">
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
            <textarea class="harness__input harness__input--ta" v-model="selectedNode.data.prompt" @input="store.markDirty()" placeholder="输入 Prompt 模板，支持 {变量} 占位符" rows="4"></textarea>
          </div>
          <div class="harness__field" v-if="selectedNode.type === 'datasource'">
            <label>SQL 查询</label>
            <textarea class="harness__input harness__input--ta harness__input--mono" v-model="selectedNode.data.sql" @input="store.markDirty()" placeholder="SELECT * FROM table WHERE ..." rows="3"></textarea>
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
          <div class="harness__exec-result" v-if="selectedNode.data.result">
            <div class="harness__exec-result-label">执行结果</div>
            <div class="harness__exec-result-text">{{ selectedNode.data.result }}</div>
          </div>
          <button class="harness__btn harness__btn--danger harness__btn--sm" @click="deleteNode(store.selectedNodeId!)">删除节点</button>
        </div>
      </div>
    </div>

    <!-- 底部执行日志 -->
    <div class="harness__log" :class="{ 'harness__log--expanded': logExpanded }">
      <div class="harness__log-header" @click="logExpanded = !logExpanded">
        <span>执行日志</span>
        <span class="harness__log-count" v-if="store.executionLog.length">{{ store.executionLog.length }} 条</span>
        <span class="harness__log-toggle">{{ logExpanded ? '▼' : '▲' }}</span>
      </div>
      <div class="harness__log-body" v-if="logExpanded">
        <div v-if="!store.executionLog.length" class="harness__log-empty">点击「执行」按钮开始执行工作流</div>
        <div v-for="(entry, i) in store.executionLog" :key="i" class="harness__log-entry" :class="`harness__log-entry--${entry.event}`">
          <span class="harness__log-event">{{ eventLabel(entry.event) }}</span>
          <span class="harness__log-msg">{{ logMsg(entry) }}</span>
          <span class="harness__log-time">{{ new Date(entry.ts).toLocaleTimeString() }}</span>
        </div>
      </div>
    </div>

    <!-- 新建场景对话框 -->
    <div class="harness__dialog-mask" v-if="showNewDialog" @click.self="showNewDialog = false">
      <div class="harness__dialog">
        <div class="harness__dialog-title">新建场景</div>
        <div class="harness__field">
          <label>场景名称 *</label>
          <input class="harness__input" v-model="newForm.name" placeholder="如：续约智能策划" autofocus />
        </div>
        <div class="harness__field">
          <label>描述</label>
          <input class="harness__input" v-model="newForm.description" placeholder="场景目标和说明" />
        </div>
        <div class="harness__field">
          <label>本体命名空间</label>
          <input class="harness__input" v-model="newForm.namespace" placeholder="如 s1" />
        </div>
        <div class="harness__dialog-footer">
          <button class="harness__btn" @click="showNewDialog = false">取消</button>
          <button class="harness__btn harness__btn--primary" @click="handleCreate" :disabled="!newForm.name">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw, watch } from 'vue'
import { VueFlow, useVueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import WorkflowNode from '../../components/harness/nodes/WorkflowNode.vue'
import { useHarnessStore } from '../../store/harness'

const store = useHarnessStore()
const canvasWrap = ref<HTMLElement>()
const logExpanded = ref(false)
const showNewDialog = ref(false)
const newForm = ref({ name: '', description: '', namespace: '' })

const flowNodes = ref<any[]>([])
const flowEdges = ref<any[]>([])

const nodeTypes_ = { 'ontology-query': markRaw(WorkflowNode), 'datasource': markRaw(WorkflowNode), 'rule-engine': markRaw(WorkflowNode), 'llm-inference': markRaw(WorkflowNode), 'ml-model': markRaw(WorkflowNode), 'write-back': markRaw(WorkflowNode), 'notification': markRaw(WorkflowNode), 'human-approval': markRaw(WorkflowNode), 'condition': markRaw(WorkflowNode), 'loop': markRaw(WorkflowNode), 'merge': markRaw(WorkflowNode) }

const defaultEdgeOptions = { type: 'smoothstep', markerEnd: MarkerType.ArrowClosed, style: { stroke: '#94a3b8', strokeWidth: 1.5 } }

const nodeTypes = [
  { type: 'ontology-query', label: '本体查询', color: '#3b82f6', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'datasource', label: '数据源连接', color: '#8b5cf6', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="currentColor" stroke-width="1.5"/><path d="M3 8v4c0 1.1 2.24 2 5 2s5-.9 5-2V8" stroke="currentColor" stroke-width="1.5"/></svg>` },
  { type: 'rule-engine', label: '规则引擎', color: '#f59e0b', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'llm-inference', label: '大模型推理', color: '#10b981', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 3.5L13 7l-3.5 1.5L8 12l-1.5-3.5L3 7l3.5-1.5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'ml-model', label: '预测模型', color: '#06b6d4', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 7l3 3 2-4 3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
  { type: 'write-back', label: '结果写回', color: '#64748b', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 3v8M5 8l3 3 3-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
  { type: 'notification', label: '通知触达', color: '#ec4899', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2a5 5 0 015 5v2l1 2H2l1-2V7a5 5 0 015-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'human-approval', label: '人工审批', color: '#f97316', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="2.5" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'condition', label: '条件判断', color: '#a855f7', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 6-6 6-6-6 6-6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'loop', label: '遍历列表', color: '#0ea5e9', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 8a5 5 0 019.9-1M13 8a5 5 0 01-9.9 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'merge', label: '合并分支', color: '#84cc16', icon: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 3v4l4 3 4-3V3M8 10v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
]

const selectedNode = computed(() => flowNodes.value.find(n => n.id === store.selectedNodeId) ?? null)

watch(() => store.current, (w) => {
  if (w) {
    flowNodes.value = (w.nodes_json || []).map((n: any) => ({ ...n }))
    flowEdges.value = (w.edges_json || []).map((e: any) => ({ ...e }))
  } else {
    flowNodes.value = []
    flowEdges.value = []
  }
})

// Update node exec states from execution log
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

onMounted(() => store.loadList())

async function loadScene(id: string) {
  await store.loadWorkflow(id)
}

async function handleCreate() {
  if (!newForm.value.name) return
  await store.createWorkflow(newForm.value.name, newForm.value.description, newForm.value.namespace)
  showNewDialog.value = false
  newForm.value = { name: '', description: '', namespace: '' }
}

async function handleSave() {
  await store.saveCanvas(flowNodes.value, flowEdges.value)
}

async function handlePublish() {
  await store.publishWorkflow()
}

function handleExecute() {
  if (!store.current) return
  // Reset exec states
  flowNodes.value.forEach(n => { n.data = { ...n.data, execState: 'pending', result: undefined } })
  store.startExecution(store.current.id)
}

function onNodeClick({ node }: { node: any }) {
  store.selectNode(node.id)
}

function onPaneClick() {
  store.selectNode(null)
}

let dragType = ''
function onDragStart(e: DragEvent, type: string) {
  dragType = type
  e.dataTransfer!.effectAllowed = 'move'
}

function onDrop(e: DragEvent) {
  if (!dragType || !canvasWrap.value) return
  const rect = canvasWrap.value.getBoundingClientRect()
  const x = e.clientX - rect.left - 80
  const y = e.clientY - rect.top - 30
  const id = `node-${Date.now()}`
  const meta = nodeTypes.find(n => n.type === dragType)
  flowNodes.value.push({
    id, type: dragType,
    position: { x, y },
    data: { label: meta?.label || dragType, execState: 'pending' },
  })
  store.markDirty()
  dragType = ''
}

function deleteNode(id: string) {
  flowNodes.value = flowNodes.value.filter(n => n.id !== id)
  flowEdges.value = flowEdges.value.filter(e => e.source !== id && e.target !== id)
  store.selectNode(null)
  store.markDirty()
}

function miniMapColor(node: any) {
  const colors: Record<string, string> = { 'ontology-query': '#3b82f6', 'llm-inference': '#10b981', 'rule-engine': '#f59e0b', 'datasource': '#8b5cf6', 'notification': '#ec4899', 'human-approval': '#f97316', 'condition': '#a855f7' }
  return colors[node.type] || '#94a3b8'
}

function eventLabel(e: string) {
  return { workflow_start: '开始', node_start: '节点启动', node_result: '节点完成', node_error: '节点错误', workflow_done: '完成' }[e] || e
}

function logMsg(entry: any) {
  if (entry.event === 'node_start') return `${entry.data.label} 开始执行`
  if (entry.event === 'node_result') return `${entry.data.label}: ${entry.data.result?.message || '完成'}`
  if (entry.event === 'node_error') return `${entry.data.label} 执行失败: ${entry.data.error}`
  if (entry.event === 'workflow_done') return `工作流执行完成，共 ${entry.data.node_count} 个节点`
  if (entry.event === 'workflow_start') return `开始执行「${entry.data.workflow_name}」，共 ${entry.data.total_nodes} 个节点`
  return JSON.stringify(entry.data)
}
</script>

<style scoped>
.harness {
  display: flex; flex-direction: column; height: 100vh;
  background: var(--neutral-50, #f8fafc); font-family: inherit;
}

/* Topbar */
.harness__topbar {
  display: flex; align-items: center; justify-content: space-between;
  height: 48px; padding: 0 16px;
  background: #fff; border-bottom: 1px solid var(--neutral-200, #e2e8f0);
  flex-shrink: 0; gap: 8px;
}
.harness__topbar-left { display: flex; align-items: center; gap: 8px; }
.harness__logo-icon { display: flex; align-items: center; }
.harness__title { font-size: 14px; font-weight: 700; color: var(--neutral-900, #0f172a); }
.harness__divider { color: var(--neutral-300, #cbd5e1); }
.harness__scene-name { font-size: 13px; color: var(--neutral-700, #334155); font-weight: 500; }
.harness__dirty { font-size: 11px; color: #f59e0b; }
.harness__status-tag {
  font-size: 10px; padding: 2px 7px; border-radius: 10px; font-weight: 600;
  background: #f1f5f9; color: #64748b;
}
.harness__status-tag--draft { background: #fef9c3; color: #a16207; }
.harness__status-tag--published { background: #dcfce7; color: #15803d; }
.harness__status-tag--disabled { background: #fee2e2; color: #b91c1c; }

.harness__topbar-right { display: flex; align-items: center; gap: 8px; }

/* Buttons */
.harness__btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 500;
  border: 1px solid var(--neutral-200, #e2e8f0);
  background: #fff; color: var(--neutral-700, #334155);
  cursor: pointer; transition: background .15s, border-color .15s;
}
.harness__btn:hover:not(:disabled) { background: #f8fafc; border-color: #cbd5e1; }
.harness__btn:disabled { opacity: .45; cursor: not-allowed; }
.harness__btn--primary { background: #3b82f6; border-color: #3b82f6; color: #fff; }
.harness__btn--primary:hover:not(:disabled) { background: #2563eb; border-color: #2563eb; }
.harness__btn--outline { border-color: #3b82f6; color: #3b82f6; }
.harness__btn--outline:hover:not(:disabled) { background: #eff6ff; }
.harness__btn--danger { background: #fee2e2; border-color: #fca5a5; color: #b91c1c; }
.harness__btn--danger:hover:not(:disabled) { background: #fecaca; }
.harness__btn--sm { padding: 3px 8px; font-size: 11px; }
.harness__icon-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: 5px; border: none;
  background: transparent; color: var(--neutral-500, #64748b); cursor: pointer;
}
.harness__icon-btn:hover { background: var(--neutral-100, #f1f5f9); }

/* Body layout */
.harness__body {
  display: flex; flex: 1; overflow: hidden;
}

/* Left panel */
.harness__left {
  width: 220px; flex-shrink: 0;
  display: flex; flex-direction: column;
  background: #fff; border-right: 1px solid var(--neutral-200, #e2e8f0);
  overflow: hidden;
}
.harness__section { display: flex; flex-direction: column; overflow: hidden; }
.harness__section--nodes { flex: 1; overflow: hidden; }
.harness__section-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; font-size: 11px; font-weight: 600;
  color: var(--neutral-500, #64748b); text-transform: uppercase; letter-spacing: .04em;
  border-bottom: 1px solid var(--neutral-100, #f1f5f9); flex-shrink: 0;
}

/* Scene list */
.harness__scene-list { overflow-y: auto; flex: 1; padding: 4px 0; }
.harness__scene-item {
  padding: 8px 12px; cursor: pointer;
  border-left: 3px solid transparent;
  transition: background .12s;
}
.harness__scene-item:hover { background: #f8fafc; }
.harness__scene-item--active { background: #eff6ff; border-left-color: #3b82f6; }
.harness__scene-item-name { font-size: 12px; font-weight: 500; color: var(--neutral-800, #1e293b); }
.harness__scene-item-meta { display: flex; align-items: center; gap: 6px; margin-top: 2px; font-size: 10px; color: var(--neutral-400, #94a3b8); }
.harness__scene-status { padding: 1px 5px; border-radius: 4px; font-size: 9px; font-weight: 600; }
.harness__scene-status--draft { background: #fef9c3; color: #a16207; }
.harness__scene-status--published { background: #dcfce7; color: #15803d; }
.harness__scene-status--disabled { background: #f1f5f9; color: #64748b; }
.harness__empty { padding: 16px 12px; font-size: 11px; color: var(--neutral-400, #94a3b8); text-align: center; }

/* Node library */
.harness__node-lib { overflow-y: auto; flex: 1; padding: 6px 8px; display: flex; flex-direction: column; gap: 2px; }
.harness__node-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px; border-radius: 6px; cursor: grab;
  border: 1px solid transparent; transition: background .12s, border-color .12s;
  font-size: 11px;
}
.harness__node-item:hover { background: #f8fafc; border-color: #e2e8f0; }
.harness__node-item:active { cursor: grabbing; }
.harness__node-item-icon { display: flex; flex-shrink: 0; }
.harness__node-item-label { color: var(--neutral-700, #334155); font-weight: 500; }

/* Canvas */
.harness__canvas-wrap {
  flex: 1; position: relative; overflow: hidden;
  background: #f8fafc;
}
.harness__canvas-empty {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; color: var(--neutral-400, #94a3b8);
}
.harness__canvas-empty p { font-size: 13px; margin: 0; }
.harness__flow { width: 100%; height: 100%; }

/* Right panel */
.harness__right {
  width: 280px; flex-shrink: 0;
  background: #fff; border-left: 1px solid var(--neutral-200, #e2e8f0);
  display: flex; flex-direction: column; overflow: hidden;
}
.harness__panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; font-size: 12px; font-weight: 600;
  color: var(--neutral-700, #334155);
  border-bottom: 1px solid var(--neutral-100, #f1f5f9); flex-shrink: 0;
}
.harness__panel-body { flex: 1; overflow-y: auto; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
.harness__field { display: flex; flex-direction: column; gap: 4px; }
.harness__field label { font-size: 11px; font-weight: 600; color: var(--neutral-500, #64748b); }
.harness__input {
  padding: 6px 8px; border-radius: 6px; font-size: 12px;
  border: 1px solid var(--neutral-200, #e2e8f0);
  background: #fff; color: var(--neutral-900, #0f172a);
  outline: none; transition: border-color .15s; width: 100%; box-sizing: border-box;
  font-family: inherit;
}
.harness__input:focus { border-color: #3b82f6; }
.harness__input--ta { resize: vertical; min-height: 60px; }
.harness__input--mono { font-family: 'Consolas', monospace; font-size: 11px; }

.harness__exec-result { background: #f0fdf4; border-radius: 6px; padding: 8px 10px; }
.harness__exec-result-label { font-size: 10px; font-weight: 600; color: #15803d; margin-bottom: 4px; }
.harness__exec-result-text { font-size: 11px; color: #166534; }

/* Log panel */
.harness__log {
  flex-shrink: 0; background: #1e293b;
  border-top: 1px solid #334155;
  transition: height .2s;
  height: 36px; overflow: hidden;
}
.harness__log--expanded { height: 180px; }
.harness__log-header {
  display: flex; align-items: center; gap: 8px;
  padding: 0 14px; height: 36px; cursor: pointer;
  font-size: 11px; font-weight: 600; color: #94a3b8;
  user-select: none;
}
.harness__log-count { background: #334155; color: #94a3b8; padding: 1px 6px; border-radius: 8px; font-size: 10px; }
.harness__log-toggle { margin-left: auto; font-size: 10px; }
.harness__log-body { height: calc(180px - 36px); overflow-y: auto; padding: 4px 0; }
.harness__log-empty { padding: 12px 14px; font-size: 11px; color: #475569; }
.harness__log-entry {
  display: flex; align-items: baseline; gap: 8px;
  padding: 3px 14px; font-size: 11px;
}
.harness__log-entry--node_start .harness__log-event { color: #60a5fa; }
.harness__log-entry--node_result .harness__log-event { color: #34d399; }
.harness__log-entry--node_error .harness__log-event { color: #f87171; }
.harness__log-entry--workflow_start .harness__log-event { color: #a78bfa; }
.harness__log-entry--workflow_done .harness__log-event { color: #34d399; }
.harness__log-event { font-weight: 600; flex-shrink: 0; min-width: 60px; }
.harness__log-msg { color: #cbd5e1; flex: 1; }
.harness__log-time { color: #475569; font-size: 10px; flex-shrink: 0; }

/* Dialog */
.harness__dialog-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.harness__dialog {
  background: #fff; border-radius: 12px; padding: 24px;
  width: 380px; display: flex; flex-direction: column; gap: 14px;
  box-shadow: 0 20px 60px rgba(0,0,0,.2);
}
.harness__dialog-title { font-size: 15px; font-weight: 700; color: var(--neutral-900, #0f172a); }
.harness__dialog-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
</style>
