<template>
  <div class="ad-page">
    <!-- 顶栏 -->
    <div class="ad-topbar">
      <button class="btn-back" @click="router.push('/agents')">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        返回
      </button>
      <span class="ad-divider"></span>
      <span class="ad-name">{{ form.name || '未命名智能体' }}</span>
      <span class="ad-badge" :class="current?.status === 'published' ? 'badge--green' : 'badge--gray'">
        {{ current?.status === 'published' ? '已发布' : '草稿' }}
      </span>
      <div class="ad-topbar-right">
        <button class="hbtn" :disabled="saving" @click="saveAgent">{{ saving ? '保存中...' : '保存' }}</button>
        <button class="hbtn hbtn--outline" :disabled="publishing" @click="publishAgent" v-if="current?.status === 'draft'">发布</button>
        <button class="hbtn hbtn--primary" :disabled="executing" @click="executeAgent">
          {{ executing ? '执行中...' : '执行' }}
        </button>
      </div>
    </div>

    <!-- 主体 -->
    <div class="ad-body" v-if="current">
      <!-- 左侧配置面板 -->
      <div class="ad-left">
        <!-- 节点库 -->
        <div class="ad-section ad-section--nodes">
          <div class="ad-section-header">
            <span class="ad-section-title">节点库</span>
            <span class="ad-section-hint">拖入或点击</span>
          </div>
          <div class="ad-node-lib">
            <template v-for="group in nodeGroups" :key="group.label">
              <div class="ad-node-group-label">{{ group.label }}</div>
              <div v-for="nt in group.nodes" :key="nt.type"
                class="ad-node-item"
                draggable="true"
                @dragstart="onDragStart($event, nt.type)"
                @click="addNodeToCenter(nt.type)">
                <span class="ad-node-icon" :style="{ color: nt.color }" v-html="nt.icon"></span>
                <span class="ad-node-label">{{ nt.label }}</span>
              </div>
            </template>
          </div>
        </div>

        <!-- 智能体设置 -->
        <div class="ad-section">
          <div class="ad-section-header">
            <span class="ad-section-title">智能体设置</span>
          </div>
          <div class="ad-settings">
            <div class="ad-tabs">
              <button v-for="t in tabs" :key="t.key" class="ad-tab" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">{{ t.label }}</button>
            </div>

            <!-- 基础 -->
            <div v-show="activeTab === 'basic'" class="ad-tab-content">
              <div class="sf"><label>名称</label><input v-model="form.name" class="si" /></div>
              <div class="sf"><label>描述</label><textarea v-model="form.description" class="si si--ta" rows="3"></textarea></div>
              <div class="sf">
                <label>标签</label>
                <div class="tags-wrap">
                  <span v-for="(t,i) in form.tags" :key="i" class="stag">{{ t }}<button @click="form.tags.splice(i,1)">×</button></span>
                  <input v-model="tagInput" class="tag-in" placeholder="回车添加" @keydown.enter.prevent="addTag" />
                </div>
              </div>
            </div>

            <!-- 模型 -->
            <div v-show="activeTab === 'model'" class="ad-tab-content">
              <div class="sf"><label>模型</label>
                <select v-model="form.model_id" class="si">
                  <option :value="null">默认模型</option>
                  <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }}</option>
                </select>
              </div>
              <div class="sf"><label>温度 {{ form.tools_config.temperature }}</label>
                <input type="range" v-model.number="form.tools_config.temperature" min="0" max="2" step="0.1" class="slider" />
              </div>
              <div class="sf"><label>Max Tokens</label>
                <input type="number" v-model.number="form.tools_config.max_tokens" class="si" style="width:120px" min="1" max="32768" step="256" />
              </div>
            </div>

            <!-- 提示词 -->
            <div v-show="activeTab === 'prompt'" class="ad-tab-content">
              <div class="prompt-btns">
                <button class="hbtn hbtn--xs" @click="applyTemplate('customer')">客服</button>
                <button class="hbtn hbtn--xs" @click="applyTemplate('analysis')">分析</button>
                <button class="hbtn hbtn--xs" @click="applyTemplate('ontology')">本体</button>
              </div>
              <textarea v-model="form.system_prompt" class="si si--ta si--mono" rows="10" placeholder="系统提示词..."></textarea>
            </div>
          </div>
        </div>
      </div>

      <!-- 画布 -->
      <div class="ad-canvas-wrap" ref="canvasWrap"
        @drop="onDrop" @dragover.prevent>
        <VueFlow
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          :node-types="nodeTypes_"
          :default-edge-options="defaultEdgeOptions"
          :snap-to-grid="true"
          :snap-grid="[16,16]"
          fit-view-on-init
          class="ad-flow"
          @node-click="onNodeClick"
          @pane-click="selectedNodeId = null">
          <Background variant="lines" pattern-color="#e8edf2" :gap="24" :size="1" />
          <Controls />
          <MiniMap :node-color="nodeColor" node-stroke-color="transparent" mask-color="rgba(15,23,42,0.6)" />
        </VueFlow>
        <div v-if="flowNodes.length === 0" class="ad-canvas-hint">从左侧节点库拖入节点开始编排</div>
      </div>

      <!-- 右侧节点属性 -->
      <div class="ad-right" v-if="selectedNodeId && selectedNode">
        <div class="ad-right-header">
          <span>节点属性</span>
          <button class="ad-icon-btn" @click="selectedNodeId = null">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
        <div class="ad-right-body">
          <div class="sf"><label>节点名称</label><input class="si" v-model="selectedNode.data.label" /></div>
          <div class="sf"><label>说明</label><textarea class="si si--ta" v-model="selectedNode.data.description" rows="2"></textarea></div>
          <div class="sf" v-if="selectedNode.type === 'llm-inference'">
            <label>Prompt</label>
            <textarea class="si si--ta si--mono" v-model="selectedNode.data.prompt" rows="5" placeholder="输入 Prompt 模板"></textarea>
          </div>
          <button class="hbtn hbtn--danger hbtn--sm" @click="deleteNode(selectedNodeId)">删除节点</button>
        </div>
      </div>
    </div>

    <div v-else class="ad-loading">
      <div class="spinner"></div><span>加载中...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import WorkflowNode from '../../components/harness/nodes/WorkflowNode.vue'
import { agentsApi, modelsApi } from '../../api/agents'

const route = useRoute()
const router = useRouter()

const current = ref<any>(null)
const models = ref<any[]>([])
const saving = ref(false)
const publishing = ref(false)
const executing = ref(false)
const activeTab = ref('basic')
const tagInput = ref('')
const selectedNodeId = ref<string | null>(null)
const canvasWrap = ref<HTMLElement>()
const flowNodes = ref<any[]>([])
const flowEdges = ref<any[]>([])

const form = ref({
  name: '', description: '', model_id: null as string | null,
  system_prompt: '', kb_ids: [] as string[], entity_ids: [] as string[],
  tags: [] as string[], tools_config: { temperature: 0.7, max_tokens: 2048 }
})

const tabs = [
  { key: 'basic', label: '基础' },
  { key: 'model', label: '模型' },
  { key: 'prompt', label: '提示词' },
]

const TEMPLATES: Record<string, string> = {
  customer: '你是一名专业的客服助手，负责解答用户的问题。\n请保持礼貌、耐心，用简洁清晰的语言回答。',
  analysis: '你是一名数据分析专家，擅长解读数据、发现规律和提供洞察。\n请根据用户提供的数据或问题，给出专业的分析结论和建议。',
  ontology: '你是一名本体知识图谱问答助手，基于结构化知识库回答问题。\n请优先从知识库中检索相关实体和关系，给出准确的答案。'
}

const nodeTypes_ = {
  'ontology-query': markRaw(WorkflowNode), 'ontology-relation': markRaw(WorkflowNode),
  'rule-evaluate': markRaw(WorkflowNode), 'datasource': markRaw(WorkflowNode),
  'variable-assign': markRaw(WorkflowNode), 'parallel': markRaw(WorkflowNode),
  'llm-inference': markRaw(WorkflowNode), 'ml-model': markRaw(WorkflowNode),
  'voice-audit': markRaw(WorkflowNode), 'condition': markRaw(WorkflowNode),
  'loop': markRaw(WorkflowNode), 'merge': markRaw(WorkflowNode),
  'rule-engine': markRaw(WorkflowNode), 'notification': markRaw(WorkflowNode),
  'human-approval': markRaw(WorkflowNode), 'write-back': markRaw(WorkflowNode),
  'api-response': markRaw(WorkflowNode),
}

const defaultEdgeOptions = {
  type: 'smoothstep', markerEnd: MarkerType.ArrowClosed,
  style: { stroke: '#94a3b8', strokeWidth: 1.5 },
}

const nodeTypesMeta = [
  { type: 'ontology-query', label: '本体实体查询', color: '#3b82f6', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'ontology-relation', label: '关系图遍历', color: '#6366f1', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="3" cy="8" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M5 8h3l3-4M5 8h3l3 4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>` },
  { type: 'rule-evaluate', label: '规则评估', color: '#f59e0b', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'datasource', label: '数据源连接', color: '#8b5cf6', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="currentColor" stroke-width="1.5"/></svg>` },
  { type: 'llm-inference', label: '大模型推理', color: '#10b981', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 3.5L13 7l-3.5 1.5L8 12l-1.5-3.5L3 7l3.5-1.5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'ml-model', label: '预测模型', color: '#06b6d4', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M2 12L6 7l3 3 2-4 3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>` },
  { type: 'voice-audit', label: '语音质检', color: '#7c3aed', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><rect x="5" y="2" width="6" height="8" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 9a5 5 0 0010 0M8 14v-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
  { type: 'condition', label: '条件判断', color: '#a855f7', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 6-6 6-6-6 6-6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'notification', label: '通知触达', color: '#ec4899', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2a5 5 0 015 5v2l1 2H2l1-2V7a5 5 0 015-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>` },
  { type: 'api-response', label: 'API 响应', color: '#2e5bff', icon: `<svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M5 4L2 8l3 4M11 4l3 4-3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 3L7 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` },
]

const nodeGroups = [
  { label: '本体推理', nodes: nodeTypesMeta.filter(n => ['ontology-query','ontology-relation','rule-evaluate'].includes(n.type)) },
  { label: 'AI 能力', nodes: nodeTypesMeta.filter(n => ['llm-inference','ml-model','voice-audit'].includes(n.type)) },
  { label: '数据/流程', nodes: nodeTypesMeta.filter(n => ['datasource','condition','notification','api-response'].includes(n.type)) },
]

const selectedNode = computed(() => flowNodes.value.find(n => n.id === selectedNodeId.value) ?? null)
function nodeColor(node: any) { return nodeTypesMeta.find(n => n.type === node.type)?.color ?? '#94a3b8' }

function addTag() {
  const t = tagInput.value.trim()
  if (t && !form.value.tags.includes(t)) form.value.tags.push(t)
  tagInput.value = ''
}
function applyTemplate(key: string) { form.value.system_prompt = TEMPLATES[key] || '' }

let dragType = ''
function onDragStart(e: DragEvent, type: string) { dragType = type; e.dataTransfer!.effectAllowed = 'move' }
function onDrop(e: DragEvent) {
  if (!dragType || !canvasWrap.value) return
  const rect = canvasWrap.value.getBoundingClientRect()
  addNode(dragType, { x: e.clientX - rect.left - 80, y: e.clientY - rect.top - 30 })
  dragType = ''
}
function addNodeToCenter(type: string) {
  const i = flowNodes.value.length
  addNode(type, { x: 80 + (i % 4) * 220, y: 80 + Math.floor(i / 4) * 120 })
}
function addNode(type: string, position: { x: number; y: number }) {
  const meta = nodeTypesMeta.find(n => n.type === type)
  flowNodes.value.push({ id: `node-${Date.now()}`, type, position, data: { label: meta?.label || type } })
}
function deleteNode(id: string) {
  flowNodes.value = flowNodes.value.filter(n => n.id !== id)
  flowEdges.value = flowEdges.value.filter(e => e.source !== id && e.target !== id)
  selectedNodeId.value = null
}
function onNodeClick({ node }: { node: any }) { selectedNodeId.value = node.id }

async function saveAgent() {
  saving.value = true
  try {
    const res = await agentsApi.update(current.value.id, {
      ...form.value, nodes_json: flowNodes.value, edges_json: flowEdges.value, status: current.value.status
    } as any)
    current.value = res
  } catch (e) { console.error(e) }
  finally { saving.value = false }
}

async function publishAgent() {
  publishing.value = true
  try {
    const res = await agentsApi.update(current.value.id, {
      ...form.value, nodes_json: flowNodes.value, edges_json: flowEdges.value, status: 'published'
    } as any)
    current.value = res
  } catch (e) { console.error(e) }
  finally { publishing.value = false }
}

function executeAgent() {}

onMounted(async () => {
  const id = route.params.id as string
  const [agentRes, modelRes] = await Promise.all([agentsApi.get(id), modelsApi.list()])
  current.value = agentRes
  models.value = modelRes
  form.value = {
    name: agentRes.name || '',
    description: agentRes.description || '',
    model_id: agentRes.model_id || null,
    system_prompt: agentRes.system_prompt || '',
    kb_ids: (agentRes as any).kb_ids || [],
    entity_ids: (agentRes as any).entity_ids || [],
    tags: agentRes.tags || [],
    tools_config: { temperature: 0.7, max_tokens: 2048, ...(agentRes.tools_config || {}) }
  }
  flowNodes.value = ((agentRes as any).nodes_json || []).map((n: any) => ({ ...n }))
  flowEdges.value = ((agentRes as any).edges_json || []).map((e: any) => ({ ...e }))
})
</script>

<style scoped>
.ad-page { display: flex; flex-direction: column; height: 100vh; background: #f0f2f5; overflow: hidden; }
.ad-topbar { display: flex; align-items: center; gap: 8px; padding: 0 16px; height: 44px; background: #1a1a2e; color: #e0e0e0; flex-shrink: 0; }
.btn-back { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #aaa; background: none; border: none; cursor: pointer; padding: 4px 8px; border-radius: 4px; }
.btn-back:hover { background: rgba(255,255,255,0.1); color: #fff; }
.ad-divider { width: 1px; height: 16px; background: rgba(255,255,255,0.15); }
.ad-name { font-size: 13px; font-weight: 600; color: #e8e8e8; flex: 1; }
.ad-badge { font-size: 11px; padding: 2px 7px; border-radius: 10px; }
.badge--green { background: rgba(22,163,74,0.2); color: #4ade80; }
.badge--gray { background: rgba(255,255,255,0.1); color: #aaa; }
.ad-topbar-right { display: flex; gap: 6px; }
.hbtn { display: inline-flex; align-items: center; gap: 4px; padding: 5px 12px; border-radius: 5px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.08); color: #e0e0e0; transition: all 0.15s; }
.hbtn:hover { background: rgba(255,255,255,0.15); }
.hbtn--primary { background: #4c6ef5; border-color: #4c6ef5; color: #fff; }
.hbtn--primary:hover { background: #3b5bdb; }
.hbtn--outline { border-color: #4c6ef5; color: #748ffc; }
.hbtn--danger { background: rgba(239,68,68,0.15); border-color: rgba(239,68,68,0.4); color: #f87171; }
.hbtn--sm { padding: 3px 8px; font-size: 11px; }
.hbtn--xs { padding: 2px 7px; font-size: 11px; }
.hbtn:disabled { opacity: 0.4; cursor: not-allowed; }
.ad-body { flex: 1; display: flex; overflow: hidden; }
.ad-left { width: 220px; min-width: 220px; background: #1e2235; display: flex; flex-direction: column; overflow: hidden; border-right: 1px solid rgba(255,255,255,0.06); }
.ad-section { display: flex; flex-direction: column; overflow: hidden; }
.ad-section--nodes { flex-shrink: 0; max-height: 40%; border-bottom: 1px solid rgba(255,255,255,0.06); }
.ad-section-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px 4px; flex-shrink: 0; }
.ad-section-title { font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }
.ad-section-hint { font-size: 10px; color: #64748b; }
.ad-node-lib { overflow-y: auto; padding: 0 8px 8px; }
.ad-node-group-label { font-size: 10px; color: #64748b; padding: 4px 4px 2px; text-transform: uppercase; letter-spacing: 0.3px; }
.ad-node-item { display: flex; align-items: center; gap: 7px; padding: 5px 8px; border-radius: 5px; cursor: pointer; color: #cbd5e1; font-size: 12px; transition: background 0.12s; }
.ad-node-item:hover { background: rgba(255,255,255,0.07); }
.ad-node-icon { width: 13px; height: 13px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.ad-settings { flex: 1; overflow-y: auto; }
.ad-tabs { display: flex; border-bottom: 1px solid rgba(255,255,255,0.06); }
.ad-tab { flex: 1; padding: 7px 4px; font-size: 11px; color: #64748b; background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; transition: all 0.12s; }
.ad-tab:hover { color: #94a3b8; }
.ad-tab.active { color: #748ffc; border-bottom-color: #748ffc; }
.ad-tab-content { padding: 10px; display: flex; flex-direction: column; gap: 10px; }
.sf { display: flex; flex-direction: column; gap: 4px; }
.sf label { font-size: 11px; color: #64748b; }
.si { padding: 5px 8px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; font-size: 12px; color: #e0e0e0; outline: none; width: 100%; box-sizing: border-box; }
.si:focus { border-color: #748ffc; }
.si--ta { resize: vertical; font-family: inherit; }
.si--mono { font-family: 'Consolas', monospace; }
.slider { width: 100%; accent-color: #748ffc; }
.tags-wrap { display: flex; flex-wrap: wrap; gap: 4px; padding: 4px 6px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; min-height: 32px; align-items: center; }
.stag { display: inline-flex; align-items: center; gap: 3px; background: rgba(116,143,252,0.2); color: #748ffc; font-size: 11px; padding: 1px 6px; border-radius: 3px; }
.stag button { background: none; border: none; cursor: pointer; color: #748ffc; font-size: 12px; line-height: 1; padding: 0; }
.tag-in { border: none; outline: none; background: transparent; font-size: 12px; color: #e0e0e0; min-width: 80px; }
.prompt-btns { display: flex; gap: 4px; flex-wrap: wrap; }
.ad-canvas-wrap { flex: 1; position: relative; overflow: hidden; }
.ad-flow { width: 100%; height: 100%; }
.ad-canvas-hint { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 13px; color: #94a3b8; pointer-events: none; }
.ad-right { width: 220px; min-width: 220px; background: #1e2235; border-left: 1px solid rgba(255,255,255,0.06); display: flex; flex-direction: column; overflow: hidden; }
.ad-right-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 12px; font-weight: 600; color: #94a3b8; flex-shrink: 0; }
.ad-icon-btn { background: none; border: none; cursor: pointer; color: #64748b; padding: 2px; border-radius: 3px; display: flex; align-items: center; }
.ad-icon-btn:hover { color: #94a3b8; background: rgba(255,255,255,0.07); }
.ad-right-body { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 10px; }
.ad-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 12px; color: #999; font-size: 14px; }
.spinner { width: 28px; height: 28px; border: 3px solid #333; border-top-color: #4c6ef5; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
