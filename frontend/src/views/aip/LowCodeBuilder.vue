<template>
  <div class="wf">
    <header class="wf__toolbar">
      <div class="wf__toolbar-left">
        <input v-model="appName" class="wf__app-name" placeholder="未命名应用" />
        <input v-model="appCode" class="wf__app-code" placeholder="app_code" />
        <input v-model="sceneCode" class="wf__app-code" placeholder="scene_code" />
        <span class="wf__toolbar-badge">{{ nodes.length }} 节点</span>
        <span v-if="currentAppId" class="wf__toolbar-badge wf__toolbar-badge--id">{{ currentApp?.status === 'published' ? '已发布 v' + currentApp.published_version : '草稿' }}</span>
      </div>
      <div class="wf__toolbar-center">
        <button class="wf__tb-btn" :disabled="historyIdx <= 0" @click="undo" title="撤销">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 8h8a3 3 0 010 6H8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M6 5L3 8l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <button class="wf__tb-btn" :disabled="historyIdx >= history.length - 1" @click="redo" title="重做">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M13 8H5a3 3 0 000 6h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 5l3 3-3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      </div>
      <div class="wf__toolbar-right">
        <button class="wf__tb-btn" @click="handleSave" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        <button class="wf__tb-btn wf__tb-btn--primary" @click="handlePublish" :disabled="publishing || !currentAppId">{{ publishing ? '发布中...' : '发布' }}</button>
      </div>
    </header>

    <div class="wf__body">
      <aside class="wf__panel wf__panel--left">
        <div class="wf__panel-title">节点</div>
        <div v-for="group in nodeGroups" :key="group.label" class="wf__node-group">
          <div class="wf__node-group-label">{{ group.label }}</div>
          <div v-for="def in group.items" :key="def.type" class="wf__node-item" draggable="true" @dragstart="onDragStart($event, def)">
            <div class="wf__node-item-icon" :style="{ background: def.color }"><span v-html="def.icon"></span></div>
            <div class="wf__node-item-info">
              <div class="wf__node-item-name">{{ def.label }}</div>
              <div class="wf__node-item-desc">{{ def.desc }}</div>
            </div>
          </div>
        </div>
      </aside>
      <div class="wf__canvas" @drop="onDrop" @dragover.prevent>
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :default-edge-options="defaultEdgeOpts"
          :snap-to-grid="true"
          :snap-grid="[20, 20]"
          :fit-view-on-init="true"
          @node-click="onNodeClick"
          @pane-click="onPaneClick"
          @connect="onConnect"
        >
          <Background :gap="20" pattern-color="var(--neutral-200)" :size="1" />
          <Controls position="bottom-left" />
          <MiniMap position="bottom-right" :node-color="miniMapColor" />

          <template #node-copilotWidget="props"><CopilotWidgetNode v-bind="props" :selected="selectedNodeId === props.id" /></template>
          <template #node-agentNode="props"><AgentNodeComp v-bind="props" :selected="selectedNodeId === props.id" /></template>
          <template #node-approvalNode="props"><ApprovalNodeComp v-bind="props" :selected="selectedNodeId === props.id" /></template>
          <template #node-hitlInbox="props"><HITLInboxNode v-bind="props" :selected="selectedNodeId === props.id" /></template>
          <template #node-buttonNode="props"><ButtonNode v-bind="props" :selected="selectedNodeId === props.id" /></template>
          <template #node-tableNode="props"><TableNode v-bind="props" :selected="selectedNodeId === props.id" /></template>
          <template #node-workflow="{ data, id }">
            <div class="wfnode" :class="[`wfnode--${data.nodeType}`, { 'wfnode--selected': selectedNodeId === id }]">
              <div class="wfnode__header">
                <div class="wfnode__icon" :style="{ background: data.color }"><span v-html="data.icon"></span></div>
                <span class="wfnode__title">{{ data.label }}</span>
              </div>
              <div class="wfnode__body"><div class="wfnode__desc">{{ data.description || getNodeDesc(data.nodeType) }}</div></div>
              <Handle v-if="data.nodeType !== 'start'" type="target" :position="Position.Left" />
              <Handle v-if="data.nodeType !== 'end'" type="source" :position="Position.Right" />
            </div>
          </template>
        </VueFlow>
      </div>

      <aside v-if="selectedNode" class="wf__panel wf__panel--right">
        <div class="wf__config-header">
          <div class="wf__config-icon" :style="{ background: selectedNode.data.color }"><span v-html="selectedNode.data.icon"></span></div>
          <input v-model="selectedNode.data.label" class="wf__config-title" />
          <button class="wf__config-del" @click="deleteNode" title="删除节点">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
        <div class="wf__config-body">
          <AgentConfigPanel v-if="selectedNode.data.nodeType === 'agent'" :config="selectedNode.data.config" @update="v => selectedNode!.data.config = v" />
          <CopilotConfigPanel v-else-if="selectedNode.data.nodeType === 'copilot'" :config="selectedNode.data.config" :agent-nodes="agentNodeList" @update="v => selectedNode!.data.config = v" />
          <ApprovalConfigPanel v-else-if="selectedNode.data.nodeType === 'approval'" :config="selectedNode.data.config" @update="v => selectedNode!.data.config = v" />
          <template v-else-if="selectedNode.data.nodeType === 'button'">
            <label class="wf__field"><span>按钮文字</span>
              <input v-model="selectedNode.data.config.text" class="wf__input" placeholder="点击执行" />
            </label>
            <label class="wf__field"><span>触发动作</span>
              <input v-model="selectedNode.data.config.action" class="wf__input" placeholder="action_name" />
            </label>
          </template>
          <template v-else-if="selectedNode.data.nodeType === 'table'">
            <label class="wf__field"><span>数据源实体</span>
              <input v-model="selectedNode.data.config.entityName" class="wf__input" placeholder="实体名称" />
            </label>
            <label class="wf__field"><span>显示列</span>
              <textarea v-model="selectedNode.data.config.columns" class="wf__textarea" rows="3" placeholder="每行一个列名"></textarea>
            </label>
          </template>
          <template v-else-if="selectedNode.data.nodeType === 'hitl_inbox'">
            <label class="wf__field"><span>关联审批节点</span>
              <select v-model="selectedNode.data.config.linkedApprovalNodeId" class="wf__input">
                <option value="">-- 选择审批节点 --</option>
                <option v-for="a in approvalNodeList" :key="a.id" :value="a.id">{{ a.label }}</option>
              </select>
            </label>
          </template>
          <template v-else-if="selectedNode.data.nodeType === 'llm'">
            <label class="wf__field"><span>模型</span>
              <select v-model="selectedNode.data.config.model" class="wf__input">
                <option value="gpt-4o">GPT-4o</option><option value="gpt-4o-mini">GPT-4o-mini</option>
                <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option><option value="deepseek-v3">DeepSeek-V3</option>
              </select>
            </label>
            <label class="wf__field"><span>系统提示词</span>
              <textarea v-model="selectedNode.data.config.systemPrompt" class="wf__textarea" rows="4" placeholder="设定AI角色和行为..."></textarea>
            </label>
            <label class="wf__field"><span>用户提示词</span>
              <textarea v-model="selectedNode.data.config.userPrompt" class="wf__textarea" rows="4" placeholder="使用 {{变量名}} 引用上游输出"></textarea>
            </label>
            <label class="wf__field"><span>温度 {{ selectedNode.data.config.temperature }}</span>
              <input type="range" v-model.number="selectedNode.data.config.temperature" min="0" max="1" step="0.1" class="wf__range" />
            </label>
          </template>
          <template v-else-if="selectedNode.data.nodeType === 'http'">
            <label class="wf__field"><span>方法</span>
              <select v-model="selectedNode.data.config.method" class="wf__input">
                <option value="GET">GET</option><option value="POST">POST</option>
                <option value="PUT">PUT</option><option value="DELETE">DELETE</option>
              </select>
            </label>
            <label class="wf__field"><span>URL</span>
              <input v-model="selectedNode.data.config.url" class="wf__input" placeholder="https://api.example.com/..." />
            </label>
            <label class="wf__field"><span>请求头</span>
              <textarea v-model="selectedNode.data.config.headers" class="wf__textarea" rows="3" placeholder='{"Content-Type": "application/json"}'></textarea>
            </label>
            <label class="wf__field"><span>请求体</span>
              <textarea v-model="selectedNode.data.config.body" class="wf__textarea" rows="4" placeholder="JSON 请求体"></textarea>
            </label>
          </template>
          <template v-else-if="selectedNode.data.nodeType === 'ontology'">
            <label class="wf__field"><span>本体实体</span>
              <input v-model="selectedNode.data.config.entityName" class="wf__input" placeholder="输入实体名称" />
            </label>
            <label class="wf__field"><span>查询方式</span>
              <select v-model="selectedNode.data.config.queryType" class="wf__input">
                <option value="attributes">属性查询</option><option value="relations">关系查询</option>
                <option value="rules">规则执行</option>
              </select>
            </label>
          </template>
          <template v-else-if="selectedNode.data.nodeType === 'start'">
            <label class="wf__field"><span>输入变量</span>
              <textarea v-model="selectedNode.data.config.variables" class="wf__textarea" rows="4" placeholder="每行一个变量名"></textarea>
            </label>
          </template>
          <template v-else-if="selectedNode.data.nodeType === 'end'">
            <label class="wf__field"><span>输出变量</span>
              <input v-model="selectedNode.data.config.outputKey" class="wf__input" placeholder="result" />
            </label>
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, markRaw, onMounted } from 'vue'
import { VueFlow, useVueFlow, Position, Handle } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import type { Node, Edge, Connection } from '@vue-flow/core'
import { useRoute } from 'vue-router'
import { workflowApi } from '../../api/workflow'
import CopilotWidgetNode from '../../components/lowcode/nodes/CopilotWidgetNode.vue'
import AgentNodeComp from '../../components/lowcode/nodes/AgentNode.vue'
import ApprovalNodeComp from '../../components/lowcode/nodes/ApprovalNode.vue'
import HITLInboxNode from '../../components/lowcode/nodes/HITLInboxNode.vue'
import ButtonNode from '../../components/lowcode/nodes/ButtonNode.vue'
import TableNode from '../../components/lowcode/nodes/TableNode.vue'
import AgentConfigPanel from '../../components/lowcode/panels/AgentConfigPanel.vue'
import CopilotConfigPanel from '../../components/lowcode/panels/CopilotConfigPanel.vue'
import ApprovalConfigPanel from '../../components/lowcode/panels/ApprovalConfigPanel.vue'
import type { WorkflowApp } from '../../types/workflow'

const route = useRoute()
const { screenToFlowCoordinate } = useVueFlow()

interface NodeDef { type: string; label: string; desc: string; color: string; icon: string; vueFlowType: string; defaultConfig: Record<string, any> }

const appName = ref('未命名应用')
const appCode = ref('')
const sceneCode = ref('')
const currentAppId = ref<string | null>(null)
const currentApp = ref<WorkflowApp | null>(null)
const saving = ref(false)
const publishing = ref(false)
const selectedNodeId = ref<string | null>(null)
const history = ref<string[]>([])
const historyIdx = ref(-1)
let idCounter = 0
let draggingDef: NodeDef | null = null

const defaultEdgeOpts = { type: 'smoothstep', animated: true, style: { stroke: 'var(--color-primary)', strokeWidth: 2 } }

// ── Icons ──
const llmIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2a6 6 0 100 12A6 6 0 008 2z" stroke="#fff" stroke-width="1.5"/><path d="M5.5 9.5s.5 1.5 2.5 1.5 2.5-1.5 2.5-1.5" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/><circle cx="6" cy="7" r="0.75" fill="#fff"/><circle cx="10" cy="7" r="0.75" fill="#fff"/></svg>`
const httpIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="#fff" stroke-width="1.5"/><path d="M2 8h12M8 2c-2 2-2 10 0 12M8 2c2 2 2 10 0 12" stroke="#fff" stroke-width="1.2"/></svg>`
const ontologyIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="4" r="2" stroke="#fff" stroke-width="1.5"/><circle cx="4" cy="12" r="2" stroke="#fff" stroke-width="1.5"/><circle cx="12" cy="12" r="2" stroke="#fff" stroke-width="1.5"/><path d="M8 6v2M8 8l-4 2M8 8l4 2" stroke="#fff" stroke-width="1.2"/></svg>`
const startIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 3l9 5-9 5V3z" fill="#fff"/></svg>`
const endIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="3" y="3" width="10" height="10" rx="2" fill="#fff"/></svg>`
const copilotIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V4z" stroke="#fff" stroke-width="1.5"/><path d="M5 7h6M5 10h3" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>`
const agentIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="#fff" stroke-width="1.5"/><path d="M6 8h4M8 6v4" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>`
const approvalIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 4v4l-6 4-6-4V6l6-4z" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>`
const inboxIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="2" stroke="#fff" stroke-width="1.5"/><path d="M5 7h6M5 10h4" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>`
const buttonIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="3" y="5" width="10" height="6" rx="2" stroke="#fff" stroke-width="1.5"/></svg>`
const tableIcon = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="1" stroke="#fff" stroke-width="1.5"/><path d="M2 6h12M6 6v7M10 6v7" stroke="#fff" stroke-width="1" opacity="0.6"/></svg>`

// ── Node groups ──
const nodeGroups: { label: string; items: NodeDef[] }[] = [
  {
    label: 'UI Widgets',
    items: [
      { type: 'copilot', label: 'Copilot Chat', desc: '聊天对话组件', color: '#3b82f6', icon: copilotIcon, vueFlowType: 'copilotWidget', defaultConfig: { title: '', boundAgentNodeId: '', welcomeMessage: '' } },
      { type: 'button', label: 'Button', desc: '按钮触发器', color: '#2563eb', icon: buttonIcon, vueFlowType: 'buttonNode', defaultConfig: { text: '点击执行', action: '' } },
      { type: 'table', label: 'Table', desc: '数据表格', color: '#1d4ed8', icon: tableIcon, vueFlowType: 'tableNode', defaultConfig: { entityName: '', columns: '' } },
      { type: 'hitl_inbox', label: 'HITL Inbox', desc: '人工审批收件箱', color: '#1e40af', icon: inboxIcon, vueFlowType: 'hitlInbox', defaultConfig: { linkedApprovalNodeId: '' } },
    ]
  },
  {
    label: 'Logic Nodes',
    items: [
      { type: 'agent', label: 'Agent', desc: 'AI Agent 推理节点', color: '#8b5cf6', icon: agentIcon, vueFlowType: 'agentNode', defaultConfig: { persona: '', objective: '', maxSteps: 8, boundTools: [] } },
      { type: 'approval', label: '审批节点', desc: '敏感操作审批', color: '#7c3aed', icon: approvalIcon, vueFlowType: 'approvalNode', defaultConfig: { sensitiveTools: [] } },
      { type: 'llm', label: 'LLM', desc: '大语言模型调用', color: '#6d28d9', icon: llmIcon, vueFlowType: 'workflow', defaultConfig: { model: 'gpt-4o', systemPrompt: '', userPrompt: '', temperature: 0.7 } },
      { type: 'http', label: 'HTTP 请求', desc: '调用外部 API', color: '#5b21b6', icon: httpIcon, vueFlowType: 'workflow', defaultConfig: { method: 'GET', url: '', headers: '', body: '' } },
      { type: 'ontology', label: '本体查询', desc: '查询本体实体/关系', color: '#4c1d95', icon: ontologyIcon, vueFlowType: 'workflow', defaultConfig: { entityName: '', queryType: 'attributes', filter: '' } },
    ]
  },
  {
    label: '流程控制',
    items: [
      { type: 'start', label: '开始', desc: '工作流入口', color: '#20c997', icon: startIcon, vueFlowType: 'workflow', defaultConfig: { variables: '' } },
      { type: 'end', label: '结束', desc: '工作流出口', color: '#868e96', icon: endIcon, vueFlowType: 'workflow', defaultConfig: { outputKey: 'result' } },
    ]
  }
]

const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])
const selectedNode = computed(() => nodes.value.find(n => n.id === selectedNodeId.value) || null)
const agentNodeList = computed(() => nodes.value.filter(n => n.data?.nodeType === 'agent').map(n => ({ id: n.id, label: n.data.label })))
const approvalNodeList = computed(() => nodes.value.filter(n => n.data?.nodeType === 'approval').map(n => ({ id: n.id, label: n.data.label })))

// ── Lifecycle ──
onMounted(async () => {
  const qid = route.query.id as string | undefined
  if (qid) {
    await loadApp(qid)
  } else {
    await loadOrCreateApp()
  }
  pushHistory()
})

async function loadApp(id: string) {
  try {
    const app = await workflowApi.getApp(id)
    currentAppId.value = app.id
    currentApp.value = app
    appName.value = app.name
    appCode.value = app.code
    sceneCode.value = app.scene_code || ''
    if (app.canvas_json) {
      nodes.value = app.canvas_json.nodes || []
      edges.value = app.canvas_json.edges || []
    }
  } catch { /* new app */ }
}

async function loadOrCreateApp() {
  try {
    const list = await workflowApi.listApps()
    if (list.length > 0) {
      await loadApp(list[0].id)
    }
  } catch { /* ignore */ }
}

// ── Canvas helpers ──
function miniMapColor(node: Node) { return node.data?.color || '#adb5bd' }
function getNodeDesc(type: string) {
  const map: Record<string, string> = { start: '工作流入口', end: '工作流出口', llm: '调用大语言模型', ontology: '查询本体数据', http: 'HTTP 请求' }
  return map[type] || ''
}

function pushHistory() {
  const snap = JSON.stringify({ nodes: nodes.value, edges: edges.value })
  history.value = history.value.slice(0, historyIdx.value + 1)
  history.value.push(snap)
  historyIdx.value = history.value.length - 1
}
function undo() { if (historyIdx.value <= 0) return; historyIdx.value--; const s = JSON.parse(history.value[historyIdx.value]); nodes.value = s.nodes; edges.value = s.edges; selectedNodeId.value = null }
function redo() { if (historyIdx.value >= history.value.length - 1) return; historyIdx.value++; const s = JSON.parse(history.value[historyIdx.value]); nodes.value = s.nodes; edges.value = s.edges; selectedNodeId.value = null }

function onDragStart(e: DragEvent, def: NodeDef) { draggingDef = def; e.dataTransfer!.effectAllowed = 'copy' }
function onDrop(e: DragEvent) {
  if (!draggingDef) return
  const pos = screenToFlowCoordinate({ x: e.clientX, y: e.clientY })
  const id = `${draggingDef.type}_${++idCounter}_${Date.now()}`
  nodes.value.push({
    id, type: draggingDef.vueFlowType,
    position: { x: pos.x - 80, y: pos.y - 30 },
    data: { nodeType: draggingDef.type, label: draggingDef.label, color: draggingDef.color, icon: draggingDef.icon, config: { ...draggingDef.defaultConfig }, description: '' }
  })
  pushHistory()
  draggingDef = null
}
function onNodeClick(event: { node: Node }) { selectedNodeId.value = event.node.id }
function onPaneClick() { selectedNodeId.value = null }
function onConnect(conn: Connection) {
  edges.value.push({ id: `e_${conn.source}_${conn.target}`, source: conn.source!, target: conn.target!, sourceHandle: conn.sourceHandle ?? undefined, targetHandle: conn.targetHandle ?? undefined, type: 'smoothstep', animated: true, style: { stroke: 'var(--color-primary)', strokeWidth: 2 } })
  pushHistory()
}
function deleteNode() {
  if (!selectedNodeId.value) return
  const id = selectedNodeId.value
  nodes.value = nodes.value.filter(n => n.id !== id)
  edges.value = edges.value.filter(e => e.source !== id && e.target !== id)
  selectedNodeId.value = null
  pushHistory()
}

// ── Save / Publish ──
async function handleSave() {
  saving.value = true
  try {
    const canvas = { nodes: nodes.value, edges: edges.value }
    if (!currentAppId.value) {
      const code = appCode.value || `app_${Date.now()}`
      const app = await workflowApi.createApp({ code, name: appName.value || '未命名应用', scene_code: sceneCode.value || undefined, canvas_json: canvas })
      currentAppId.value = app.id
      currentApp.value = await workflowApi.getApp(app.id)
      appCode.value = app.code
    } else {
      await workflowApi.updateApp(currentAppId.value, { name: appName.value, scene_code: sceneCode.value || undefined, canvas_json: canvas })
      currentApp.value = await workflowApi.getApp(currentAppId.value)
    }
  } catch (e: any) {
    alert('保存失败: ' + (e?.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function handlePublish() {
  if (!currentAppId.value) { alert('请先保存'); return }
  publishing.value = true
  try {
    await handleSave()
    const result = await workflowApi.publish(currentAppId.value!)
    currentApp.value = await workflowApi.getApp(currentAppId.value!)
    alert(`发布成功! 版本: v${result.version}\n可在智能问答页通过 appId 加载此配置`)
  } catch (e: any) {
    alert('发布失败: ' + (e?.response?.data?.detail || e.message))
  } finally {
    publishing.value = false
  }
}
</script>

<style scoped>
.wf { display: flex; flex-direction: column; height: 100vh; background: var(--bg-primary); color: var(--text-primary); }
.wf__toolbar { display: flex; align-items: center; justify-content: space-between; height: 48px; padding: 0 16px; border-bottom: 1px solid var(--border-primary); background: var(--bg-secondary); flex-shrink: 0; }
.wf__app-name { background: transparent; border: 1px solid transparent; color: var(--text-primary); font-size: 14px; font-weight: 600; padding: 4px 8px; border-radius: 4px; width: 160px; }
.wf__app-name:focus { border-color: var(--color-primary); outline: none; }
.wf__app-code { background: transparent; border: 1px solid transparent; color: var(--text-muted); font-size: 12px; padding: 4px 8px; border-radius: 4px; width: 100px; }
.wf__app-code:focus { border-color: var(--color-primary); outline: none; }
.wf__toolbar-badge { font-size: 11px; color: var(--text-muted); margin-left: 8px; }
.wf__toolbar-badge--id { background: var(--neutral-100); padding: 2px 8px; border-radius: 4px; }
.wf__toolbar-left { display: flex; align-items: center; gap: 4px; }
.wf__toolbar-center { display: flex; align-items: center; gap: 4px; }
.wf__toolbar-right { display: flex; gap: 6px; }
.wf__tb-btn { background: transparent; border: 1px solid var(--border-primary); color: var(--text-secondary); padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; display: flex; align-items: center; gap: 4px; transition: all 0.15s; }
.wf__tb-btn:hover:not(:disabled) { background: var(--bg-hover); color: var(--text-primary); }
.wf__tb-btn:disabled { opacity: 0.35; cursor: default; }
.wf__tb-btn--primary { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.wf__tb-sep { width: 1px; height: 20px; background: var(--border-primary); margin: 0 4px; }
.wf__body { display: flex; flex: 1; overflow: hidden; }
.wf__panel { background: var(--bg-secondary); overflow-y: auto; flex-shrink: 0; border-right: 1px solid var(--border-primary); }
.wf__panel--left { width: 220px; padding: 16px 12px; }
.wf__panel--right { width: 320px; border-right: none; border-left: 1px solid var(--border-primary); padding: 0; }
.wf__panel-title { font-size: 13px; font-weight: 700; margin-bottom: 12px; color: var(--text-primary); }
.wf__node-group { margin-bottom: 16px; }
.wf__node-group-label { font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
.wf__node-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border: 1px solid var(--border-primary); border-radius: 8px; cursor: grab; transition: all 0.15s; margin-bottom: 6px; }
.wf__node-item:hover { border-color: var(--color-primary); background: var(--bg-hover); }
.wf__node-item-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.wf__node-item-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.wf__node-item-desc { font-size: 11px; color: var(--text-muted); margin-top: 1px; }
.wf__canvas { flex: 1; position: relative; }
.wfnode { background: var(--bg-secondary); border: 2px solid var(--border-primary); border-radius: 12px; min-width: 180px; max-width: 240px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); transition: border-color 0.15s, box-shadow 0.15s; }
.wfnode--selected { border-color: var(--color-primary); box-shadow: 0 0 0 3px rgba(76,110,245,0.15); }
.wfnode:hover { border-color: var(--color-primary); }
.wfnode__header { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-bottom: 1px solid var(--border-primary); }
.wfnode__icon { width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.wfnode__title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.wfnode__body { padding: 8px 14px; }
.wfnode__desc { font-size: 11px; color: var(--text-muted); line-height: 1.4; }
.wf__config-header { display: flex; align-items: center; gap: 10px; padding: 14px 16px; border-bottom: 1px solid var(--border-primary); }
.wf__config-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.wf__config-title { flex: 1; background: transparent; border: none; color: var(--text-primary); font-size: 14px; font-weight: 600; padding: 0; }
.wf__config-title:focus { outline: none; }
.wf__config-del { background: transparent; border: none; color: var(--text-muted); cursor: pointer; padding: 4px; border-radius: 4px; }
.wf__config-del:hover { color: #e53935; background: var(--bg-hover); }
.wf__config-body { padding: 16px; }
.wf__field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 14px; font-size: 12px; }
.wf__field > span { font-weight: 600; color: var(--text-secondary); }
.wf__input { padding: 6px 10px; border: 1px solid var(--border-primary); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 13px; }
.wf__input:focus { border-color: var(--color-primary); outline: none; }
.wf__textarea { padding: 8px 10px; border: 1px solid var(--border-primary); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 13px; resize: vertical; font-family: inherit; line-height: 1.5; }
.wf__textarea:focus { border-color: var(--color-primary); outline: none; }
.wf__range { width: 100%; accent-color: var(--color-primary); }
</style>


