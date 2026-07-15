<template>
  <div class="agent-detail">
    <!-- Top bar -->
    <div class="agent-detail__topbar">
      <div class="agent-detail__topbar-left">
        <button class="agent-detail__btn agent-detail__btn--ghost" @click="router.push('/agent/manage')">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          返回
        </button>
        <span class="agent-detail__divider"></span>
        <input
          class="agent-detail__name-input"
          v-model="form.name"
          placeholder="未命名智能体"
        />
        <span class="agent-detail__status-tag" :class="statusClass">
          {{ current?.status === 'published' ? '已发布' : '草稿' }}
        </span>
        <span class="agent-detail__dirty" v-if="isDirty">
          <svg width="6" height="6" viewBox="0 0 6 6"><circle cx="3" cy="3" r="3" fill="#f59e0b"/></svg>
          未保存
        </span>
      </div>
      <div class="agent-detail__topbar-right">
        <button class="agent-detail__btn" @click="saveAgent" :disabled="saving">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button class="agent-detail__btn agent-detail__btn--primary" @click="publishAgent" v-if="current && current.status === 'draft'">
          发布
        </button>
        <button class="agent-detail__btn agent-detail__btn--danger" @click="unpublishAgent" v-if="current && current.status === 'published'">
          下线
        </button>
      </div>
    </div>

    <!-- Ontology stale banner -->
    <div v-if="current?.ontology_stale" class="agent-detail__stale-banner">
      <span class="agent-detail__stale-icon">⚠</span>
      <span class="agent-detail__stale-text">该 Agent 依赖的本体实体已发生变更</span>
      <button class="agent-detail__stale-btn" @click="showStaleDetail = !showStaleDetail">查看变更</button>
      <button class="agent-detail__stale-btn agent-detail__stale-btn--ack" @click="ackStale">确认已知</button>
    </div>
    <div v-if="showStaleDetail && current?.ontology_stale_detail" class="agent-detail__stale-detail">
      <ul>
        <li v-for="c in current.ontology_stale_detail.breaking_changes" :key="c.entity_name">
          <strong>{{ c.entity_name }}</strong> —
          <span v-if="c.change_type === 'deleted'">已删除</span>
          <span v-else>改名为 {{ c.new_name }}</span>
        </li>
      </ul>
    </div>

    <!-- Body: left form + right chat -->
    <div class="agent-detail__body">
      <!-- Left: Config form -->
      <div class="agent-detail__left">
        <div class="agent-detail__form-group">
          <label class="agent-detail__label">描述</label>
          <textarea class="agent-detail__textarea" v-model="form.description" rows="2" placeholder="智能体描述"></textarea>
        </div>
        <div class="agent-detail__form-group">
          <label class="agent-detail__label">关联本体</label>
          <select class="agent-detail__select" v-model="selectedOntologyId" @change="onOntologyChange">
            <option value="">请选择本体</option>
            <option v-for="s in scenarioStore.scenarios" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="agent-detail__form-group agent-detail__form-group--grow">
          <label class="agent-detail__label">系统提示词</label>
          <textarea class="agent-detail__textarea agent-detail__textarea--tall" v-model="form.system_prompt" placeholder="系统提示词"></textarea>
        </div>
      </div>

      <!-- Right: Chat test -->
      <div class="agent-detail__right">
        <div class="agent-detail__chat-header">
          <span class="agent-detail__chat-title">对话测试</span>
          <select
            class="agent-detail__conv-select"
            v-if="!isNew && current"
            :value="activeConversationId || ''"
            :disabled="streaming"
            @change="selectConversation(($event.target as HTMLSelectElement).value)"
          >
            <option value="" disabled>选择会话</option>
            <option v-for="c in conversations" :key="c.id" :value="c.id">{{ c.title }}</option>
          </select>
          <button
            class="agent-detail__btn agent-detail__btn--ghost"
            @click="newConversation"
            :disabled="!current || isNew || streaming"
          >+ 新会话</button>
          <button
            class="agent-detail__btn agent-detail__btn--ghost"
            v-if="activeConversationId"
            :disabled="streaming"
            @click="removeConversation(activeConversationId)"
          >删除会话</button>
        </div>
        <div class="agent-detail__chat-body" v-if="!current || isNew">
          <div class="agent-detail__chat-placeholder">请先保存智能体后测试</div>
        </div>
        <div class="agent-detail__chat-body" v-else>
          <div class="agent-detail__messages" ref="messagesRef">
            <div v-for="(msg, i) in messages" :key="i" class="agent-detail__message" :class="`agent-detail__message--${msg.role}`">
              <!-- 思考过程：意图识别 → 本体查询 → 逻辑计算 → 执行动作 → 生成回答 -->
              <div
                v-if="msg.role === 'assistant' && msg.steps && msg.steps.length"
                class="agent-detail__think"
              >
                <button class="agent-detail__think-head" @click="msg.stepsOpen = !msg.stepsOpen">
                  <svg
                    class="agent-detail__think-caret"
                    :class="{ 'is-open': msg.stepsOpen }"
                    viewBox="0 0 16 16" fill="none"
                  ><path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  <span class="agent-detail__think-title">思考过程</span>
                  <span class="agent-detail__think-count">{{ displaySteps(msg).length }} 步</span>
                </button>
                <div v-show="msg.stepsOpen" class="agent-detail__think-steps">
                  <div
                    v-for="(step, si) in displaySteps(msg)"
                    :key="si"
                    class="agent-detail__step"
                  >
                    <span class="agent-detail__step-dot" :class="`agent-detail__step-dot--${step.stage}`"></span>
                    <div class="agent-detail__step-body">
                      <div class="agent-detail__step-line">
                        <span class="agent-detail__step-tag" :class="`agent-detail__step-tag--${step.stage}`">{{ STAGE_LABELS[step.stage] }}</span>
                        <span class="agent-detail__step-label">{{ step.label }}</span>
                        <span v-if="stepTarget(step)" class="agent-detail__step-target" :class="`agent-detail__step-target--${step.stage}`">{{ stepTarget(step) }}</span>
                        <span v-if="(step.repeat || 1) > 1" class="agent-detail__step-repeat">×{{ step.repeat }}</span>
                        <span
                          v-if="step.summary == null && streaming && i === messages.length - 1"
                          class="agent-detail__step-running"
                        >进行中…</span>
                      </div>
                      <div v-if="step.summary" class="agent-detail__step-summary">{{ step.summary }}</div>
                      <div v-if="stepFacts(step).length" class="agent-detail__step-facts">
                        <span v-for="(f, fi) in stepFacts(step)" :key="fi" class="agent-detail__fact">
                          <span class="agent-detail__fact-k">{{ f.label }}</span>
                          <span class="agent-detail__fact-v">{{ f.value }}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="agent-detail__bubble" :class="`agent-detail__bubble--${msg.role}`">
                <span v-if="msg.status && !msg.content" class="agent-detail__thinking">
                  <span class="agent-detail__thinking-dots"><i></i><i></i><i></i></span>
                  <span class="agent-detail__thinking-text">{{ msg.status }}</span>
                </span>
                <div
                  v-else-if="msg.role === 'assistant'"
                  class="agent-detail__markdown"
                  v-html="renderMarkdownSafe(msg.content)"
                ></div>
                <template v-else>{{ msg.content }}</template>
              </div>
              <!-- 本体调用链：把本轮命中的本体对象/逻辑函数/动作串成一条思维链 -->
              <div
                v-if="msg.role === 'assistant' && !streaming && msg.content && messageChain(msg).length"
                class="agent-detail__chain"
              >
                <span class="agent-detail__chain-title">本体调用链</span>
                <template v-for="(node, ni) in messageChain(msg)" :key="ni">
                  <span class="agent-detail__chain-node" :class="`agent-detail__chain-node--${node.stage}`">
                    <span class="agent-detail__chain-stage">{{ node.label }}</span>
                    <span v-if="node.target" class="agent-detail__chain-target">{{ node.target }}</span>
                  </span>
                  <span v-if="ni < messageChain(msg).length - 1" class="agent-detail__chain-arrow">→</span>
                </template>
              </div>
              <div
                v-if="msg.role === 'assistant' && !streaming && msg.content"
                class="agent-detail__msg-actions"
              >
                <button class="agent-detail__download-btn" @click="copyMessage(msg.content, i)">
                  <svg viewBox="0 0 16 16" fill="none"><rect x="5" y="5" width="8" height="9" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5" stroke="currentColor" stroke-width="1.3"/></svg>
                  {{ copiedIdx === i ? '已复制' : '复制' }}
                </button>
                <button
                  v-if="looksLikeMarkdown(msg.content)"
                  class="agent-detail__download-btn"
                  @click="downloadHtml(msg.content, form.name || '智能体分析报告')"
                >
                  <svg viewBox="0 0 16 16" fill="none"><path d="M8 2v8m0 0L5 7m3 3l3-3M3 13h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  下载 HTML
                </button>
              </div>
            </div>
          </div>
          <div class="agent-detail__dirty-hint" v-if="isDirty">配置已修改，保存后测试最新配置</div>
          <div class="agent-detail__chat-input">
            <textarea class="agent-detail__textarea" v-model="chatInput" rows="2" placeholder="输入消息...（回车发送，Shift+Enter 换行）" @keydown.enter.exact.prevent="sendMessage"></textarea>
            <button class="agent-detail__btn agent-detail__btn--primary" @click="sendMessage" :disabled="!chatInput.trim() || streaming">发送</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { agentsApi, type AgentItem, type ConversationSummary } from '../../api/agents'
import { entityApi } from '../../api/ontology'
import { useScenarioStore } from '../../store/scenarios'
import { authHeaders } from '../../utils/authHeaders'
import { renderMarkdownSafe } from '@/utils/sanitize'
import { looksLikeMarkdown, downloadHtml, copyText } from '@/utils/markdownExport'

const route = useRoute()
const router = useRouter()

const isNew = computed(() => route.name === 'agent-new')

const entities = ref<{ id: string; name: string; name_cn?: string; ontology_id?: string }[]>([])
const current = ref<AgentItem | null>(null)
const saving = ref(false)
const streaming = ref(false)
const showStaleDetail = ref(false)
const scenarioStore = useScenarioStore()
const selectedOntologyId = ref('')

const form = reactive({
  name: '',
  description: '',
  tagsStr: '',
  system_prompt: '',
  entity_ids: [] as string[],
})

let savedSnapshot = ''

const messagesRef = ref<HTMLElement | null>(null)
const chatInput = ref('')

// 思考过程阶段：意图识别 → 本体查询 → 逻辑计算 → 执行动作 → 生成回答
// intent / answer 为前端合成阶段；ontology / logic / action 来自工具调用
type ThinkStage = 'intent' | 'ontology' | 'logic' | 'action' | 'answer'
interface ThinkStep {
  stage: ThinkStage
  tool?: string          // 工具类步骤才有；合成步骤为空
  label: string
  arguments?: any
  summary?: string | null
  resultCount?: number | null
  detail?: any
  repeat?: number         // 相邻重复步骤折叠后的次数，>1 时以 ×N 展示
}
interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  status?: string
  steps?: ThinkStep[]
  stepsOpen?: boolean  // 思考过程时间线是否展开
}
const messages = ref<ChatMessage[]>([])

const conversations = ref<ConversationSummary[]>([])
const activeConversationId = ref<string | null>(null)

const copiedIdx = ref(-1)
let copiedTimer: ReturnType<typeof setTimeout> | undefined
async function copyMessage(content: string, idx: number) {
  const ok = await copyText(content)
  if (!ok) return
  copiedIdx.value = idx
  clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => { copiedIdx.value = -1 }, 1500)
}

// 工具英文名 → [阶段, 中文名]。阶段用于思考过程时间线分组：
// ontology 本体查询 / logic 逻辑计算 / action 执行动作
type ToolStage = 'ontology' | 'logic' | 'action'
const TOOL_META: Record<string, [ToolStage, string]> = {
  // 本体查询：读模型/结构、取数、查实例
  describe_ontology_model: ['ontology', '读取本体模型'],
  get_entity_detail: ['ontology', '读取实体详情'],
  query_entity_data: ['ontology', '查询实体数据'],
  ontology_query_instances: ['ontology', '查询实体实例'],
  ontology_get_attr_mapping: ['ontology', '读取属性映射'],
  ontology_complex_sql: ['ontology', '执行复杂查询'],
  ontology_list_capabilities: ['ontology', '列出本体能力'],
  query_datasource: ['ontology', '查询数据源'],
  list_datasources: ['ontology', '查询数据源列表'],
  get_table_schema: ['ontology', '读取表结构'],
  list_business_datasources: ['ontology', '查询业务数据源'],
  list_business_documents: ['ontology', '查询业务文档'],
  analyze_assets_for_ontology: ['ontology', '分析资产生成本体'],
  // 逻辑计算：执行逻辑函数、规则评估/筛查
  ontology_run_logic: ['logic', '执行逻辑函数'],
  list_rules: ['logic', '读取本体规则'],
  evaluate_rule: ['logic', '评估规则'],
  evaluate_all_rules: ['logic', '评估全部规则'],
  screen_users_by_rule: ['logic', '按规则筛查'],
  // 执行动作：有副作用的业务动作
  execute_action: ['action', '执行动作'],
  ontology_run_action: ['action', '执行动作函数'],
}
function toolMeta(tool: string): [ToolStage, string] {
  // 画布节点工具名形如 "[节点标签]"，归为执行动作并去掉方括号
  if (tool.startsWith('[') && tool.endsWith(']')) return ['action', tool.slice(1, -1)]
  return TOOL_META[tool] || ['ontology', tool]
}

// 阶段中文名与展示顺序（意图识别 → 本体查询 → 逻辑计算 → 执行动作 → 生成回答）
const STAGE_LABELS: Record<ThinkStage, string> = {
  intent: '意图识别',
  ontology: '本体查询',
  logic: '逻辑计算',
  action: '执行动作',
  answer: '生成回答',
}

// 从一步思考过程里提炼「调用了哪个本体对象/哪个逻辑函数/哪些数据」的目标标签，
// 供时间线上高亮展示，让用户看清每一步落在哪个本体资产上。
function stepTarget(step: ThinkStep): string {
  const d = step.detail || {}
  switch (d.type) {
    case 'logic_run':
    case 'action_run':
      return d.callable || ''
    case 'instance_query':
    case 'entity_query':
      return d.entity_cn || d.entity || ''
    case 'entity_detail':
      return d.entity_cn || d.entity || ''
    case 'evaluate_single':
    case 'screen':
      return d.rule_name || ''
    case 'action':
      return d.action_name || ''
    default:
      break
  }
  // 退化到入参里的实体/函数名
  const a = step.arguments || {}
  return a.callable_name || a.entity_name || a.action_name || ''
}

// 把一步的关键 detail 拆成若干「键: 值」小标签，展示数据来源、筛选条件、耗时、调用链等。
function stepFacts(step: ThinkStep): { label: string; value: string }[] {
  const d = step.detail || {}
  const out: { label: string; value: string }[] = []
  const fmtObj = (o: any) => {
    if (!o || typeof o !== 'object') return String(o ?? '')
    const parts = Object.entries(o).map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`)
    return parts.join('、')
  }
  switch (d.type) {
    case 'logic_run':
    case 'action_run':
      if (d.params && Object.keys(d.params).length) out.push({ label: '入参', value: fmtObj(d.params) })
      if (Array.isArray(d.call_trace) && d.call_trace.length) out.push({ label: '调用链', value: d.call_trace.join(' → ') })
      if (d.execution_ms != null) out.push({ label: '耗时', value: `${d.execution_ms}ms` })
      if (d.error) out.push({ label: '错误', value: String(d.error) })
      break
    case 'instance_query':
    case 'entity_query':
      if (d.datasource) out.push({ label: '数据源', value: d.datasource })
      if (d.table) out.push({ label: '数据表', value: d.table })
      if (d.filters && Object.keys(d.filters).length) out.push({ label: '筛选', value: fmtObj(d.filters) })
      if (d.row_count != null) out.push({ label: '记录数', value: `${d.row_count}` })
      break
    case 'sql_query':
      if (d.sql) out.push({ label: 'SQL', value: d.sql })
      if (d.row_count != null) out.push({ label: '返回', value: `${d.row_count} 行` })
      break
    case 'attr_mapping':
      for (const m of (d.mappings || [])) out.push({ label: m.entity, value: m.table })
      break
    case 'ontology_model':
      if (d.entities?.length) out.push({ label: '本体对象', value: d.entities.join('、') })
      out.push({ label: '规模', value: `${d.entity_count} 对象 / ${d.relation_count} 关系` })
      break
    case 'capabilities':
      for (const f of (d.functions || [])) out.push({ label: f.type === 'action' ? '动作' : '逻辑', value: f.name })
      break
    case 'entity_detail':
      out.push({ label: '结构', value: `${d.attr_count ?? 0} 属性 / ${d.relation_count ?? 0} 关系` })
      break
    case 'evaluate_single':
      out.push({ label: '规则', value: d.rule_name || '' })
      out.push({ label: '结果', value: `${d.triggered ? '触发' : '未触发'}（命中 ${d.matched_count}/${d.total_count}）` })
      break
    case 'screen':
      if (d.risk_level) out.push({ label: '风险', value: d.risk_level })
      if (d.matched_users != null) out.push({ label: '命中人数', value: `${d.matched_users}` })
      break
    case 'action':
      out.push({ label: '结果', value: d.success ? '成功' : '失败' })
      break
    default:
      break
  }
  return out
}

// 把相邻的重复步骤折叠成一条：模型常对同一实体反复查询，时间线里会出现大量
// 「同阶段+同标签+同目标+同摘要+同记录数」的连续步骤，这里按签名合并并记次数，
// 使思考过程时间线保持简洁。签名不含耗时/入参细节，仅看用户可感知的展示要素。
function dedupeSteps(steps: ThinkStep[] | undefined): ThinkStep[] {
  if (!steps || !steps.length) return []
  const sig = (s: ThinkStep) =>
    [s.stage, s.label, stepTarget(s), s.summary ?? '', s.resultCount ?? ''].join('¦')
  const out: ThinkStep[] = []
  let prevSig = ''
  for (const s of steps) {
    const cur = sig(s)
    const last = out[out.length - 1]
    if (last && cur === prevSig) {
      last.repeat = (last.repeat || 1) + 1
      continue
    }
    out.push({ ...s, repeat: 1 })
    prevSig = cur
  }
  return out
}

// 去重结果按 steps 数组引用缓存，避免模板里多处（计数/时间线/调用链）重复计算。
// 流式过程中 steps 被原地 push，引用不变，故用长度参与 key 让缓存随之失效。
const _dedupeCache = new WeakMap<ThinkStep[], { len: number; out: ThinkStep[] }>()
function displaySteps(msg: ChatMessage): ThinkStep[] {
  const steps = msg.steps
  if (!steps || !steps.length) return []
  const cached = _dedupeCache.get(steps)
  if (cached && cached.len === steps.length) return cached.out
  const out = dedupeSteps(steps)
  _dedupeCache.set(steps, { len: steps.length, out })
  return out
}

// 汇总整条消息的「本体调用链」思维链：把每一步压成一个链路节点，供答复下方展示。
interface ChainNode { stage: ThinkStage; label: string; target: string }
function messageChain(msg: ChatMessage): ChainNode[] {
  const steps = displaySteps(msg)
  if (!steps.length) return []
  return steps.map(s => ({
    stage: s.stage,
    label: STAGE_LABELS[s.stage],
    target: stepTarget(s),
  }))
}

function formToPayload() {
  return {
    name: form.name || '未命名智能体',
    description: form.description,
    tags: form.tagsStr.split(',').map(t => t.trim()).filter(Boolean),
    system_prompt: form.system_prompt,
    entity_ids: form.entity_ids,
  }
}

const isDirty = computed(() => JSON.stringify(formToPayload()) !== savedSnapshot)

const statusClass = computed(() => {
  const s = current.value?.status || 'draft'
  return `agent-detail__status-tag--${s}`
})

function loadFormFromAgent(a: AgentItem) {
  form.name = a.name
  form.description = a.description
  form.tagsStr = (a.tags || []).join(', ')
  form.system_prompt = a.system_prompt
  form.entity_ids = a.entity_ids || []
  current.value = a
  savedSnapshot = JSON.stringify(formToPayload())
}
async function saveAgent() {
  saving.value = true
  try {
    const payload = formToPayload()
    let result: AgentItem
    if (isNew.value) {
      result = await agentsApi.create(payload)
      router.replace(`/agent/manage/${result.id}`)
    } else {
      result = await agentsApi.update(route.params.id as string, payload)
    }
    loadFormFromAgent(result)
  } finally {
    saving.value = false
  }
}

async function publishAgent() {
  if (!current.value) return
  const result = await agentsApi.publish(current.value.id)
  loadFormFromAgent(result)
}

async function unpublishAgent() {
  if (!current.value) return
  const result = await agentsApi.update(current.value.id, { status: 'draft' } as any)
  loadFormFromAgent(result)
}

async function ackStale() {
  if (!current.value) return
  await agentsApi.acknowledgeStale(current.value.id)
  current.value.ontology_stale = false
  current.value.ontology_stale_detail = null
  showStaleDetail.value = false
}

async function loadConversations() {
  if (!current.value || isNew.value) return
  conversations.value = await agentsApi.listConversations(current.value.id).catch(() => [])
}

// 历史会话的步骤（后端字段为 category=ontology/logic/action）还原为前端阶段模型，
// 首尾补上"意图识别""生成回答"合成阶段，与实时展示保持一致
function restoreSteps(raw: any): ThinkStep[] | undefined {
  if (!Array.isArray(raw) || raw.length === 0) return undefined
  const toolSteps: ThinkStep[] = raw.map((s: any) => ({
    stage: (['ontology', 'logic', 'action'].includes(s.category) ? s.category : 'ontology') as ThinkStage,
    tool: s.tool,
    label: s.label || s.tool || '',
    arguments: s.arguments,
    summary: s.summary,
    resultCount: s.resultCount,
    detail: s.detail,
  }))
  return [
    { stage: 'intent', label: '理解问题、规划调用', summary: '' },
    ...toolSteps,
    { stage: 'answer', label: '输出分析结论', summary: '' },
  ]
}

async function selectConversation(cid: string) {
  if (!current.value) return
  activeConversationId.value = cid
  try {
    const detail = await agentsApi.getConversation(current.value.id, cid)
    messages.value = detail.messages.map((m: any) => ({
      role: m.role,
      content: m.content,
      steps: restoreSteps(m.steps),
      stepsOpen: false,  // 历史回看默认收起，可点开
    }))
  } catch {
    messages.value = []
    await loadConversations()
  }
  await nextTick()
  scrollToBottom()
}

async function newConversation() {
  if (!current.value) return
  const conv = await agentsApi.createConversation(current.value.id)
  activeConversationId.value = conv.id
  messages.value = []
  chatInput.value = ''
  await loadConversations()
}

async function removeConversation(cid: string) {
  if (!current.value) return
  await agentsApi.deleteConversation(current.value.id, cid)
  if (activeConversationId.value === cid) {
    activeConversationId.value = null
    messages.value = []
  }
  await loadConversations()
  const first = conversations.value[0]
  if (!activeConversationId.value && first) await selectConversation(first.id)
}

// 把最近一个还在"进行中"的步骤收尾。合成阶段（意图识别/生成回答）没有
// 工具返回，用空串占位标记完成，避免一直显示"进行中…"
function finishRunningStep(msg: ChatMessage) {
  const running = [...(msg.steps || [])].reverse().find(s => s.summary == null)
  if (running && (running.stage === 'intent' || running.stage === 'answer')) {
    running.summary = ''
  }
}

async function sendMessage() {
  const text = chatInput.value.trim()
  if (!text || !current.value || streaming.value) return

  // 先确保有会话：在 push 气泡、置 streaming=true 之前创建，
  // 避免创建失败时留下卡在“思考中…”的气泡并把发送锁死。
  if (!activeConversationId.value) {
    try {
      const conv = await agentsApi.createConversation(current.value.id)
      activeConversationId.value = conv.id
    } catch (e) {
      console.error('创建会话失败', e)
      alert('创建会话失败，请稍后重试')
      return
    }
  }

  chatInput.value = ''
  messages.value.push({ role: 'user', content: text })
  messages.value.push({
    role: 'assistant',
    content: '',
    status: '思考中…',
    // 意图识别为首个合成阶段：从发问到首个工具调用/正文之间
    steps: [{ stage: 'intent', label: '理解问题、规划调用' }],
    stepsOpen: true,
  })
  streaming.value = true

  await nextTick()
  scrollToBottom()

  try {
    const response = await fetch(`/api/v1/agents/${current.value.id}/chat`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ question: text, conversation_id: activeConversationId.value }),
    })
    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const lastIdx = messages.value.length - 1

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6)
        if (data === '[DONE]') break
        try {
          const evt = JSON.parse(data)
          const cur = messages.value[lastIdx]
          if (!cur.steps) cur.steps = []
          if (evt.type === 'content') {
            // 正文分块（orchestrator / graph_engine 均以 content 事件流式输出）
            cur.status = undefined  // 正文开始，清除阶段提示
            if (!cur.content) {
              // 正文首次到达：收尾意图识别阶段，补入"生成回答"合成阶段
              finishRunningStep(cur)
              cur.steps.push({ stage: 'answer', label: '输出分析结论' })
            }
            cur.content += evt.content
          } else if (evt.type === 'answer') {
            // 出错兜底：后端直接返回完整答复
            cur.status = undefined
            cur.content = evt.content
          } else if (evt.type === 'tool_start') {
            // 工具调用开始：收尾上一阶段，累积一步思考过程 + 气泡提示
            finishRunningStep(cur)
            const [stage, label] = toolMeta(evt.tool)
            cur.steps.push({ stage, tool: evt.tool, label, arguments: evt.arguments })
            cur.stepsOpen = true  // 流式过程中自动展开时间线
            if (!cur.content) cur.status = `正在${label}…`
          } else if (evt.type === 'tool_result') {
            // 工具返回：回填该步骤的结果摘要与详情
            const step = [...cur.steps].reverse().find(
              s => s.tool === evt.tool && s.summary == null,
            )
            if (step) {
              step.summary = evt.summary
              step.resultCount = evt.resultCount
              step.detail = evt.detail
            }
            if (!cur.content && evt.summary) cur.status = evt.summary
          }
        } catch { /* skip non-json lines */ }
      }
      await nextTick()
      scrollToBottom()
    }
  } finally {
    streaming.value = false
    const cur = messages.value[messages.value.length - 1]
    if (cur && cur.role === 'assistant') {
      // 流结束后若气泡仍无正文，清掉阶段提示并给出兜底文案，避免卡在“思考中”
      if (!cur.content) {
        cur.status = undefined
        cur.content = '（未返回内容）'
      }
      finishRunningStep(cur)  // 收尾"生成回答"阶段
      // 答复已出，自动收起思考过程时间线，可手动点开回看
      if (cur.content && cur.steps && cur.steps.length) cur.stepsOpen = false
    }
  }
  await loadConversations()
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

function onOntologyChange() {
  if (!selectedOntologyId.value) {
    form.entity_ids = []
    return
  }
  const matched = entities.value.filter((e: any) => e.ontology_id === selectedOntologyId.value)
  form.entity_ids = matched.map(e => e.id)
}

onMounted(async () => {
  await scenarioStore.fetchScenarios()
  const entityList = await entityApi.list()
  entities.value = entityList as any

  if (!isNew.value) {
    const agent = await agentsApi.get(route.params.id as string)
    loadFormFromAgent(agent)
    // 反推选中的本体
    if (form.entity_ids.length > 0) {
      const firstEntity = entities.value.find(e => e.id === form.entity_ids[0])
      if (firstEntity?.ontology_id) {
        selectedOntologyId.value = firstEntity.ontology_id
      }
    }
    await loadConversations()
    if (conversations.value.length > 0) {
      await selectConversation(conversations.value[0].id)
    }
  }
})
</script>
<style scoped>
.agent-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.agent-detail__topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
  border-bottom: 1px solid var(--neutral-200, #e5e7eb);
  flex-shrink: 0;
}
.agent-detail__topbar-left,
.agent-detail__topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.agent-detail__divider {
  width: 1px;
  height: 20px;
  background: var(--neutral-200, #e5e7eb);
  margin: 0 4px;
}
.agent-detail__name-input {
  border: none;
  outline: none;
  font-size: 15px;
  font-weight: 600;
  background: transparent;
  width: 180px;
  padding: 4px 8px;
  border-radius: 4px;
}
.agent-detail__name-input:hover,
.agent-detail__name-input:focus {
  background: var(--neutral-100, #f3f4f6);
}
.agent-detail__status-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--neutral-100, #f3f4f6);
  color: var(--neutral-500, #6b7280);
}
.agent-detail__status-tag--published {
  background: #d1fae5;
  color: #059669;
}
.agent-detail__dirty {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #f59e0b;
}
.agent-detail__btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}
.agent-detail__btn:hover { background: var(--neutral-100, #f3f4f6); }
.agent-detail__btn:disabled { opacity: 0.5; cursor: not-allowed; }
.agent-detail__btn--ghost { border: none; background: transparent; }
.agent-detail__btn--primary {
  background: var(--semantic-600, #2563eb);
  color: #fff;
  border-color: var(--semantic-600, #2563eb);
}
.agent-detail__btn--primary:hover { background: var(--semantic-700, #1d4ed8); }
.agent-detail__btn--danger {
  background: #fff;
  color: #dc2626;
  border-color: #fca5a5;
}
.agent-detail__btn--danger:hover { background: #fef2f2; }
.agent-detail__body {
  display: flex;
  flex: 1;
  overflow: hidden;
}
.agent-detail__left {
  width: 420px;
  flex-shrink: 0;
  border-right: 1px solid var(--neutral-200, #e5e7eb);
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.agent-detail__right {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.agent-detail__form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.agent-detail__form-group--grow {
  flex: 1;
  min-height: 0;
}
.agent-detail__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-700, #374151);
}
.agent-detail__input,
.agent-detail__select,
.agent-detail__textarea {
  padding: 8px 10px;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.agent-detail__input:focus,
.agent-detail__select:focus,
.agent-detail__textarea:focus {
  border-color: var(--semantic-400, #60a5fa);
}
.agent-detail__textarea--tall {
  flex: 1;
  min-height: 120px;
  resize: vertical;
}
.agent-detail__select[multiple] {
  min-height: 80px;
}
.agent-detail__chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--neutral-200, #e5e7eb);
  flex-shrink: 0;
}
.agent-detail__chat-title {
  font-size: 14px;
  font-weight: 600;
}
.agent-detail__chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.agent-detail__chat-placeholder {
  margin: auto;
  font-size: 14px;
  color: var(--neutral-400, #9ca3af);
}
.agent-detail__messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.agent-detail__message {
  max-width: 88%;
  min-width: 0;
}
.agent-detail__message--user {
  align-self: flex-end;
}
.agent-detail__message--assistant {
  align-self: flex-start;
}
.agent-detail__bubble {
  width: fit-content;
  max-width: 100%;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.agent-detail__bubble--user {
  background: var(--semantic-600, #2563eb);
  color: #fff;
}
.agent-detail__bubble--assistant {
  background: var(--neutral-100, #f3f4f6);
  color: var(--neutral-800, #1f2937);
}
.agent-detail__thinking {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--neutral-500, #6b7280);
  white-space: normal;  /* 覆盖气泡的 pre-wrap，避免模板换行被当成真实换行 */
}
/* 思考过程时间线 */
.agent-detail__think {
  margin-bottom: 6px;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 8px;
  background: #fafbfc;
  overflow: hidden;
}
.agent-detail__think-head {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 6px 10px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  color: var(--neutral-600, #4b5563);
}
.agent-detail__think-head:hover {
  background: var(--neutral-100, #f3f4f6);
}
.agent-detail__think-caret {
  width: 12px;
  height: 12px;
  color: var(--neutral-400, #9ca3af);
  transition: transform 0.15s;
}
.agent-detail__think-caret.is-open {
  transform: rotate(90deg);
}
.agent-detail__think-title {
  font-weight: 500;
}
.agent-detail__think-count {
  color: var(--neutral-400, #9ca3af);
}
.agent-detail__think-steps {
  padding: 4px 10px 8px 12px;
  display: flex;
  flex-direction: column;
}
.agent-detail__step {
  position: relative;
  display: flex;
  gap: 8px;
  padding: 4px 0;
}
/* 竖向连接线 */
.agent-detail__step:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 14px;
  bottom: -4px;
  width: 1px;
  background: var(--neutral-200, #e5e7eb);
}
.agent-detail__step-dot {
  flex: none;
  width: 9px;
  height: 9px;
  margin-top: 4px;
  border-radius: 50%;
  z-index: 1;
}
.agent-detail__step-dot--intent { background: #64748b; }
.agent-detail__step-dot--ontology { background: #2563eb; }
.agent-detail__step-dot--logic { background: #7c3aed; }
.agent-detail__step-dot--action { background: #ea580c; }
.agent-detail__step-dot--answer { background: #059669; }
.agent-detail__step-body {
  flex: 1;
  min-width: 0;
}
.agent-detail__step-line {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.agent-detail__step-tag {
  flex: none;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  line-height: 18px;
}
.agent-detail__step-tag--intent { background: #f1f5f9; color: #64748b; }
.agent-detail__step-tag--ontology { background: #eff6ff; color: #2563eb; }
.agent-detail__step-tag--logic { background: #f5f3ff; color: #7c3aed; }
.agent-detail__step-tag--action { background: #fff7ed; color: #ea580c; }
.agent-detail__step-tag--answer { background: #ecfdf5; color: #059669; }
.agent-detail__step-label {
  font-size: 12px;
  color: var(--neutral-700, #374151);
}
.agent-detail__step-running {
  font-size: 11px;
  color: var(--neutral-400, #9ca3af);
}
.agent-detail__step-summary {
  margin-top: 2px;
  font-size: 11px;
  color: var(--neutral-500, #6b7280);
  line-height: 1.5;
  word-break: break-word;
}
/* 每步调用目标：本体对象名 / 逻辑函数名 / 动作名 */
.agent-detail__step-target {
  flex: none;
  max-width: 100%;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  line-height: 18px;
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
  background: var(--neutral-100, #f3f4f6);
  color: var(--neutral-700, #374151);
  word-break: break-all;
}
.agent-detail__step-target--ontology { background: #eff6ff; color: #1d4ed8; }
.agent-detail__step-target--logic { background: #f5f3ff; color: #6d28d9; }
.agent-detail__step-target--action { background: #fff7ed; color: #c2410c; }
/* 折叠重复步骤的次数角标 */
.agent-detail__step-repeat {
  flex: none;
  padding: 0 5px;
  border-radius: 8px;
  font-size: 10px;
  line-height: 16px;
  font-weight: 600;
  background: var(--neutral-200, #e5e7eb);
  color: var(--neutral-600, #4b5563);
}
/* 每步关键事实：数据源 / 数据表 / 筛选 / 调用链 / 耗时 等 */
.agent-detail__step-facts {
  margin-top: 3px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.agent-detail__fact {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  padding: 1px 6px;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 4px;
  background: #fff;
  font-size: 11px;
  line-height: 16px;
}
.agent-detail__fact-k {
  flex: none;
  color: var(--neutral-400, #9ca3af);
}
.agent-detail__fact-v {
  color: var(--neutral-700, #374151);
  word-break: break-all;
}
/* 本体调用链：答复下方的横向思维链 */
.agent-detail__chain {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
  padding: 8px 10px;
  border: 1px dashed var(--neutral-200, #e5e7eb);
  border-radius: 8px;
  background: #fafbfc;
}
.agent-detail__chain-title {
  flex: none;
  margin-right: 2px;
  font-size: 11px;
  font-weight: 500;
  color: var(--neutral-500, #6b7280);
}
.agent-detail__chain-node {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--neutral-100, #f3f4f6);
  font-size: 11px;
  line-height: 18px;
}
.agent-detail__chain-node--intent { background: #f1f5f9; color: #475569; }
.agent-detail__chain-node--ontology { background: #eff6ff; color: #1d4ed8; }
.agent-detail__chain-node--logic { background: #f5f3ff; color: #6d28d9; }
.agent-detail__chain-node--action { background: #fff7ed; color: #c2410c; }
.agent-detail__chain-node--answer { background: #ecfdf5; color: #047857; }
.agent-detail__chain-stage {
  font-weight: 500;
}
.agent-detail__chain-target {
  padding-left: 4px;
  border-left: 1px solid currentColor;
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
  opacity: 0.85;
}
.agent-detail__chain-arrow {
  color: var(--neutral-400, #9ca3af);
  font-size: 12px;
}
.agent-detail__msg-actions {
  margin-top: 4px;
  display: flex;
  gap: 4px;
}
.agent-detail__download-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 5px;
  background: #fff;
  color: var(--neutral-500, #6b7280);
  font-size: 11px;
  line-height: 1.5;
  cursor: pointer;
  transition: all 0.15s;
}
.agent-detail__download-btn svg {
  width: 11px;
  height: 11px;
}
.agent-detail__download-btn:hover {
  border-color: var(--semantic-400, #60a5fa);
  color: var(--semantic-600, #2563eb);
  background: #f0f7ff;
}
.agent-detail__thinking-dots {
  display: inline-flex;
  gap: 3px;
}
.agent-detail__thinking-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--neutral-400, #9ca3af);
  animation: agent-detail-blink 1.4s infinite both;
}
.agent-detail__thinking-dots i:nth-child(2) { animation-delay: 0.2s; }
.agent-detail__thinking-dots i:nth-child(3) { animation-delay: 0.4s; }
@keyframes agent-detail-blink {
  0%, 80%, 100% { opacity: 0.25; }
  40% { opacity: 1; }
}
.agent-detail__dirty-hint {
  padding: 6px 16px;
  font-size: 12px;
  color: #f59e0b;
  background: #fffbeb;
  text-align: center;
}
.agent-detail__chat-input {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--neutral-200, #e5e7eb);
  align-items: flex-end;
}
.agent-detail__chat-input .agent-detail__textarea {
  flex: 1;
  resize: none;
}
.agent-detail__stale-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #fef3c7;
  border-bottom: 1px solid #fde68a;
  font-size: 13px;
}
.agent-detail__stale-icon { color: #d97706; }
.agent-detail__stale-text { flex: 1; color: #92400e; }
.agent-detail__stale-btn {
  padding: 4px 10px;
  border: 1px solid #d97706;
  border-radius: 4px;
  background: transparent;
  color: #d97706;
  cursor: pointer;
  font-size: 12px;
}
.agent-detail__stale-btn--ack {
  background: #d97706;
  color: #fff;
}
.agent-detail__stale-detail {
  padding: 8px 16px;
  background: #fffbeb;
  border-bottom: 1px solid #fde68a;
  font-size: 12px;
}
.agent-detail__stale-detail ul { margin: 0; padding-left: 16px; }
.agent-detail__stale-detail li { margin: 2px 0; }
.agent-detail__conv-select {
  max-width: 160px;
  padding: 4px 8px;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 4px;
  font-size: 12px;
}
</style>
