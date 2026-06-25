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
          <label class="agent-detail__label">标签</label>
          <input class="agent-detail__input" v-model="form.tagsStr" placeholder="多个标签用逗号分隔" />
        </div>
        <div class="agent-detail__form-group agent-detail__form-group--grow">
          <label class="agent-detail__label">系统提示词</label>
          <textarea class="agent-detail__textarea agent-detail__textarea--tall" v-model="form.system_prompt" placeholder="系统提示词"></textarea>
        </div>
        <div class="agent-detail__form-group">
          <label class="agent-detail__label">实体绑定</label>
          <select class="agent-detail__select" v-model="form.entity_ids" multiple>
            <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name_cn || e.name }}</option>
          </select>
        </div>
      </div>

      <!-- Right: Chat test -->
      <div class="agent-detail__right">
        <div class="agent-detail__chat-header">
          <span class="agent-detail__chat-title">对话测试</span>
          <button class="agent-detail__btn agent-detail__btn--ghost" @click="resetChat" :disabled="!current || isNew">重置对话</button>
        </div>
        <div class="agent-detail__chat-body" v-if="!current || isNew">
          <div class="agent-detail__chat-placeholder">请先保存智能体后测试</div>
        </div>
        <div class="agent-detail__chat-body" v-else>
          <div class="agent-detail__messages" ref="messagesRef">
            <div v-for="(msg, i) in messages" :key="i" class="agent-detail__message" :class="`agent-detail__message--${msg.role}`">
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
              <div
                v-if="msg.role === 'assistant' && !streaming && msg.content"
                class="agent-detail__msg-actions"
              >
                <button class="agent-detail__download-btn" @click="copyMessage(msg.content, i)">
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><rect x="5" y="5" width="8" height="9" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5" stroke="currentColor" stroke-width="1.3"/></svg>
                  {{ copiedIdx === i ? '已复制' : '复制' }}
                </button>
                <button
                  v-if="looksLikeMarkdown(msg.content)"
                  class="agent-detail__download-btn"
                  @click="downloadHtml(msg.content, form.name || '智能体分析报告')"
                >
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2v8m0 0L5 7m3 3l3-3M3 13h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
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
import { agentsApi, type AgentItem } from '../../api/agents'
import { entityApi } from '../../api/ontology'
import { authHeaders } from '../../utils/authHeaders'
import { renderMarkdownSafe } from '@/utils/sanitize'
import { looksLikeMarkdown, downloadHtml, copyText } from '@/utils/markdownExport'

const route = useRoute()
const router = useRouter()

const isNew = computed(() => route.params.id === 'new')

const entities = ref<{ id: string; name: string; name_cn?: string }[]>([])
const current = ref<AgentItem | null>(null)
const saving = ref(false)
const streaming = ref(false)
const showStaleDetail = ref(false)

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
const messages = ref<{ role: 'user' | 'assistant'; content: string; status?: string }[]>([])

const copiedIdx = ref(-1)
let copiedTimer: ReturnType<typeof setTimeout> | undefined
async function copyMessage(content: string, idx: number) {
  const ok = await copyText(content)
  if (!ok) return
  copiedIdx.value = idx
  clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => { copiedIdx.value = -1 }, 1500)
}

// 工具英文名 → 中文提示，未命中则回退显示原始名
const TOOL_LABELS: Record<string, string> = {
  describe_ontology_model: '读取本体模型',
  list_datasources: '查询数据源列表',
  get_table_schema: '读取表结构',
  query_datasource: '查询数据源',
  get_entity_detail: '读取实体详情',
  query_entity_data: '查询实体数据',
  get_business_rules: '读取业务规则',
  evaluate_rule: '评估规则',
  evaluate_all_rules: '评估全部规则',
  screen_users_by_rule: '按规则筛选用户',
  execute_action: '执行动作',
  list_business_datasources: '查询业务数据源',
  list_business_documents: '查询业务文档',
  analyze_assets_for_ontology: '分析资产生成本体',
}
function toolLabel(tool: string): string {
  // 画布节点工具名形如 "[节点标签]"，直接展示
  if (tool.startsWith('[')) return tool.replace(/^\[|\]$/g, '')
  return TOOL_LABELS[tool] || tool
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

function resetChat() {
  messages.value = []
  chatInput.value = ''
}

async function sendMessage() {
  const text = chatInput.value.trim()
  if (!text || !current.value || streaming.value) return
  chatInput.value = ''
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '', status: '思考中…' })
  streaming.value = true

  await nextTick()
  scrollToBottom()

  try {
    const response = await fetch(`/api/v1/agents/${current.value.id}/chat`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ question: text }),
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
          if (evt.type === 'content') {
            // 正文分块（orchestrator / graph_engine 均以 content 事件流式输出）
            cur.status = undefined  // 正文开始，清除阶段提示
            cur.content += evt.content
          } else if (evt.type === 'answer') {
            // 出错兜底：后端直接返回完整答复
            cur.status = undefined
            cur.content = evt.content
          } else if (evt.type === 'tool_start') {
            // 工具调用开始：在气泡里提示正在做什么
            if (!cur.content) cur.status = `正在${toolLabel(evt.tool)}…`
          } else if (evt.type === 'tool_result') {
            // 工具返回：展示该步骤的结果摘要
            if (!cur.content && evt.summary) cur.status = evt.summary
          }
        } catch { /* skip non-json lines */ }
      }
      await nextTick()
      scrollToBottom()
    }
  } finally {
    streaming.value = false
    // 流结束后若气泡仍无正文，清掉阶段提示并给出兜底文案，避免卡在“思考中”
    const cur = messages.value[messages.value.length - 1]
    if (cur && cur.role === 'assistant' && !cur.content) {
      cur.status = undefined
      cur.content = '（未返回内容）'
    }
  }
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

onMounted(async () => {
  const entityList = await entityApi.list()
  entities.value = entityList as any

  if (!isNew.value) {
    const agent = await agentsApi.get(route.params.id as string)
    loadFormFromAgent(agent)
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
.agent-detail__msg-actions {
  margin-top: 6px;
  display: flex;
  gap: 8px;
}
.agent-detail__download-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 6px;
  background: #fff;
  color: var(--neutral-600, #4b5563);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
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
</style>
