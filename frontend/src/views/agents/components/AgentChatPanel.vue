<template>
  <aside class="aw-chat" :aria-label="text('智能体对话调试')">
    <div class="aw-row aw-between">
      <h2>{{ text("对话调试") }}</h2>
      <button class="aw-link" :disabled="!agentId || busy || loading" @click="newConversation">
        {{ text("新会话") }}
      </button>
    </div>
    <p class="aw-muted aw-small">
      {{
        actionMode === 'simulation'
          ? text('模拟执行：业务写操作不会写入业务系统')
          : text('授权确认：写操作等待当前用户明确授权')
      }}
    </p>
    <div v-if="conversations.length" class="aw-row aw-conversations">
      <select
        v-model="activeConversationId"
        :aria-label="text('历史会话')"
        :disabled="busy"
        @change="selectConversation(activeConversationId)"
      >
        <option v-for="c in conversations" :key="c.id" :value="c.id">{{ c.title }}</option>
      </select>
      <button class="aw-link" :disabled="busy || !activeConversationId" @click="removeConversation">
        {{ text("删除") }}
      </button>
    </div>
    <div v-if="error" class="aw-alert aw-error" role="alert">{{ error }}</div>
    <div v-if="loading" class="aw-empty">{{ text("正在加载会话…") }}</div>
    <div ref="messagesRef" class="aw-chat-messages" aria-live="polite">
      <div v-if="!messages.length && !loading" class="aw-chat-empty">
        <strong>{{ agentId ? text('用业务问题验证配置') : text('保存智能体后开始调试') }}</strong>
        <p>{{ text("查看技能选择、业务依据与工具调用过程。") }}</p>
      </div>
      <article
        v-for="(message, index) in messages"
        :key="index"
        class="aw-message"
        :class="{ 'aw-message-user': message.role === 'user' }"
      >
        <div v-if="message.role === 'user'" class="aw-bubble">{{ message.content }}</div>
        <div v-else class="aw-bubble aw-bubble-assistant">
          <p v-if="message.status && !message.content" class="aw-muted">{{ message.status }}</p>
          <div
            v-if="message.content"
            class="aw-markdown"
            v-html="renderMarkdownSafe(message.content)"
          ></div>
          <section
            v-for="pending in message.pendingActions || []"
            :key="pending.pending_id"
            class="aw-action-proposal"
          >
            <strong>{{ pending.action_name }}</strong>
            <p>{{ pending.summary }}</p>
            <pre>{{ JSON.stringify(pending.params, null, 2) }}</pre>
            <template v-if="!pending.status || pending.status === 'pending'">
              <p>{{ text("授权后将执行真实业务操作。请核对参数和影响。") }}</p>
              <small v-if="pending.expires_at"
                >授权截止：{{ formatTime(pending.expires_at) }}</small
              >
              <div class="aw-row">
                <button
                  class="aw-button aw-primary"
                  :disabled="!!deciding || !(canConfirmActions ?? canAuthorize)"
                  @click="decide(pending, true)"
                >
                  {{ deciding === pending.pending_id ? text('处理中…') : text('授权并执行') }}</button
                ><button
                  class="aw-button"
                  :disabled="!!deciding || !(canConfirmActions ?? canAuthorize)"
                  @click="decide(pending, false)"
                >
                  {{ text("拒绝执行") }}
                </button>
              </div>
            </template>
            <p v-else>
              {{ decisionLabel(pending.status)
              }}<span v-if="pending.result"> · {{ resultSummary(pending.result) }}</span>
            </p>
            <div v-if="pending.status === 'unknown' || pending.status === 'committed_unrecorded'" class="aw-reconciliation">
              <p>{{ text("结果未知。核对业务源或回执后记录人工声明，系统不会重发原动作。") }}</p>
              <label>{{ text("核查结果") }}<select v-model="reconcileForm(pending.pending_id).resolution"><option value="succeeded">{{ text("已确认业务成功") }}</option><option value="failed">{{ text("已确认未成功") }}</option></select></label>
              <label>{{ text("回执编号（可选）") }}<input v-model="reconcileForm(pending.pending_id).receipt_id" /></label>
              <label>{{ text("核查依据") }}<textarea v-model="reconcileForm(pending.pending_id).evidence" rows="3" :placeholder="text('源数据回读或外部回执证据，至少10字')" /></label>
              <label><input type="checkbox" v-model="reconcileForm(pending.pending_id).acknowledged" /> {{ text("我已核对业务源或回执，确认人工声明") }}</label>
              <button class="aw-button" :disabled="!!deciding || !(canConfirmActions ?? canAuthorize) || !reconcileForm(pending.pending_id).acknowledged || reconcileForm(pending.pending_id).evidence.trim().length < 10" @click="recoverAction(pending,false)">{{ text("记录人工核查结果") }}</button>
            </div>
            <button v-if="awaitingResume(pending.result)" class="aw-button" :disabled="!!deciding || !canAuthorize || dirty" @click="recoverAction(pending,true)">{{ text("继续未执行的图节点（不重发已核查动作）") }}</button>
          </section>
          <details
            v-if="message.steps?.length"
            class="aw-trace"
            :open="busy && index === messages.length - 1"
          >
            <summary>本体调用过程 · {{ displaySteps(message).length }} 步</summary>
            <div
              v-for="(step, stepIndex) in displaySteps(message)"
              :key="stepIndex"
              class="aw-trace-step"
            >
              <span
                class="aw-pill"
                :class="
                  step.category === 'action'
                    ? 'aw-amber'
                    : step.category === 'skill'
                      ? 'aw-blue'
                      : ''
                "
                >{{ stageLabel(step.category) }}</span
              >
              <div>
                <strong>{{ step.label || step.tool }}</strong
                ><span v-if="step.repeat && step.repeat > 1"> ×{{ step.repeat }}</span>
                <p>{{ step.summary ?? text('进行中…') }}</p>
                <small v-if="step.resultCount != null">返回 {{ step.resultCount }} 项</small>
                <details v-if="step.arguments || step.detail">
                  <summary>{{ text("参数与结果") }}</summary>
                  <pre>{{
                    JSON.stringify({ arguments: step.arguments, detail: step.detail }, null, 2)
                  }}</pre>
                </details>
              </div>
            </div>
          </details>
          <div v-if="message.content" class="aw-row aw-message-actions">
            <button class="aw-link" @click="copyMessage(message.content)">{{ text("复制") }}</button
            ><button
              v-if="looksLikeMarkdown(message.content)"
              class="aw-link"
              @click="downloadHtml(message.content, agentName || '智能体报告')"
            >
              {{ text("下载报告") }}
            </button>
            <button v-if="message.runId" class="aw-link" @click="emit('inspect', message.runId)">
              {{ text("查看运行记录") }}
            </button>
          </div>
        </div>
      </article>
    </div>
    <div class="aw-chat-compose">
      <p v-if="dirty" class="aw-alert">{{ text("草稿已修改，请保存后验证最新配置。") }}</p>
      <textarea
        v-model="question"
        rows="3"
        :aria-label="text('调试问题')"
        :placeholder="text('输入业务问题…')"
        :disabled="busy || loading || !agentId || !canAuthorize"
        @keydown.enter.exact.prevent="sendMessage"
      ></textarea>
      <div class="aw-row aw-between">
        <small class="aw-muted">{{ text("测试已保存的草稿配置") }}</small
        ><button
          class="aw-button aw-primary"
          :disabled="!question.trim() || busy || loading || dirty || !agentId || !canAuthorize"
          @click="sendMessage"
        >
          {{ busy ? text('运行中…') : text('发送') }}
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useProductText } from '../../../composables/useProductText'
const { text } = useProductText()

import { authenticatedFetch } from '../../../api/authenticatedFetch'
import { formatPlatformDateTime } from '../../../utils/platformTime'
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import {
  agentsApi,
  type ConversationSummary,
  type ConversationThinkStep,
  type PendingAgentAction,
} from '../../../api/agents'
import { readJsonSse } from '../../../api/sse'
import { authHeaders } from '../../../utils/authHeaders'
import { renderMarkdownSafe } from '../../../utils/sanitize'
import { copyText, downloadHtml, looksLikeMarkdown } from '../../../utils/markdownExport'

const props = defineProps<{
  agentId: string | null
  agentName: string
  dirty: boolean
  actionMode: 'simulation' | 'confirm'
  canAuthorize: boolean
  canConfirmActions?: boolean
}>()
const emit = defineEmits<{ activity: []; busy: [value: boolean]; inspect: [runId: string] }>()
type Step = ConversationThinkStep & { repeat?: number }
interface Message {
  role: 'user' | 'assistant'
  content: string
  status?: string
  steps?: Step[]
  pendingActions?: PendingAgentAction[]
  runId?: string
}
const conversations = ref<ConversationSummary[]>([])
const activeConversationId = ref('')
const messages = ref<Message[]>([])
const question = ref('')
const error = ref('')
const busy = ref(false)
const loading = ref(false)
const deciding = ref('')
const reconciliation = ref<Record<string,{resolution:'succeeded'|'failed';evidence:string;receipt_id:string;acknowledged:boolean}>>({})
function reconcileForm(id:string) { return reconciliation.value[id] ||= {resolution:'succeeded',evidence:'',receipt_id:'',acknowledged:false} }
function awaitingResume(result:unknown) {return !!result && typeof result==='object' && (result as any).continuation_status==='awaiting_resume'}
async function recoverAction(pending:PendingAgentAction,resume:boolean) {
  const aid=props.agentId, epoch=generation,form=reconcileForm(pending.pending_id)
  if (!aid || deciding.value || (resume ? !props.canAuthorize : !(props.canConfirmActions ?? props.canAuthorize)) || (resume && props.dirty)) return
  if (!resume && (!form.acknowledged || form.evidence.trim().length<10)) {error.value=text('请核对并提供至少10字的实际核查依据');return}
  deciding.value=pending.pending_id;error.value=''
  try {
    const result=resume ? await agentsApi.resumeAction(aid,pending.pending_id) : await agentsApi.reconcileAction(aid,pending.pending_id,{resolution:form.resolution,evidence:form.evidence.trim(),receipt_id:form.receipt_id.trim() || undefined})
    if (epoch!==generation || aid!==props.agentId) return
    pending.status=result.status;pending.result=result.result;pending.summary=result.summary || pending.summary;emit('activity')
    if (resume && activeConversationId.value) await selectConversation(activeConversationId.value)
  } catch(e) {if(epoch===generation)error.value=messageOf(e)} finally {if(epoch===generation)deciding.value=''}
}

const messagesRef = ref<HTMLElement | null>(null)
let controller: AbortController | undefined
let generation = 0
watch(busy, (value) => emit('busy', value))
function messageOf(e: any) {
  if (e?.response?.status === 403) return text('当前账号没有执行此操作的权限，请联系管理员配置相应权限。')
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : d ? JSON.stringify(d) : e?.message || text('请求失败，请重试')
}
function stageLabel(category: string) {
  return text(
    (
      {
        intent: '理解问题',
        ontology: '本体查询',
        logic: '逻辑计算',
        action: '执行动作',
        skill: '加载技能',
        answer: '生成回答',
        data: '数据查询',
      } as Record<string, string>
    )[category] || category
  )
}
function formatTime(value: string) {
  return formatPlatformDateTime(value)
}
function decisionLabel(status: string) {
  return text(
    (
      {
        approved: '已授权执行',
        rejected: '已拒绝执行',
        expired: '授权已过期',
        failed: '行动执行失败',
        executing: '行动正在执行',
        unknown: '行动结果未知，待人工核查',
        committed_unrecorded: '业务已提交但记录不完整，待核查',
        partial_committed: '部分写入已提交，已完成写入保留；请核查回执，原行动不可重试',
      } as Record<string, string>
    )[status] || status
  )
}
function resultSummary(result: unknown) {
  return typeof result === 'string' ? result : JSON.stringify(result)
}
function displaySteps(message: Message) {
  const output: Step[] = []
  for (const step of message.steps || []) {
    const previous = output[output.length - 1]
    if (
      previous &&
      previous.tool === step.tool &&
      previous.summary === step.summary &&
      JSON.stringify(previous.arguments) === JSON.stringify(step.arguments)
    )
      previous.repeat = (previous.repeat || 1) + 1
    else output.push({ ...step, repeat: 1 })
  }
  return output
}
function toolStage(tool: string): ConversationThinkStep['category'] {
  if (/action/.test(tool)) return 'action'
  if (/logic|function|rule/.test(tool)) return 'logic'
  if (/skill/.test(tool)) return 'skill'
  return 'ontology'
}
const toolLabels: Record<string, string> = {
  describe_ontology_model: '读取本体模型',
  get_entity_detail: '读取对象详情',
  query_entity_data: '查询对象数据',
  ontology_query_instances: '查询对象实例',
  ontology_run_logic: '执行逻辑函数',
  ontology_run_action: '执行动作函数',
  execute_action: '执行动作',
  ontology_complex_sql: '执行复杂查询',
  ontology_list_capabilities: '列出本体能力',
  load_skill: '加载业务技能',
  run_function: '执行逻辑函数',
  run_action: '执行业务动作',
}
async function scrollToBottom() {
  await nextTick()
  if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
}
async function copyMessage(content: string) {
  if (!(await copyText(content))) error.value = text('复制失败，请手动选择内容复制。')
}
let conversationRequest=0
async function loadConversations() {
  const aid=props.agentId,epoch=generation
  if (!aid) return
  const rows=await agentsApi.listConversations(aid)
  if(epoch===generation && aid===props.agentId)conversations.value=rows
}
async function selectConversation(id: string) {
  const aid=props.agentId,epoch=generation,request=++conversationRequest
  if (!aid || !id || busy.value) return
  activeConversationId.value=id;loading.value=true;error.value=''
  try {
    const detail=await agentsApi.getConversation(aid,id)
    if(epoch!==generation || request!==conversationRequest || aid!==props.agentId) return
    messages.value=detail.messages.map(m=>({...m,pendingActions:m.pending_actions}))
  } catch(e) {if(epoch===generation && request===conversationRequest)error.value=messageOf(e)}
  finally {if(epoch===generation && request===conversationRequest)loading.value=false}
  if(epoch===generation)await scrollToBottom()
}
async function newConversation() {
  const aid=props.agentId,epoch=generation
  if(!aid || busy.value || loading.value)return
  error.value='';loading.value=true
  try {
    const c=await agentsApi.createConversation(aid)
    if(epoch!==generation || aid!==props.agentId)return
    activeConversationId.value=c.id;messages.value=[];question.value=''
    await loadConversations()
  } catch(e) {if(epoch===generation)error.value=messageOf(e)}
  finally {if(epoch===generation)loading.value=false}
}
async function removeConversation() {
  const aid=props.agentId,id=activeConversationId.value,epoch=generation
  if(!aid || !id || busy.value || loading.value || !window.confirm(text('删除当前会话及其记录？')))return
  loading.value=true
  try {
    await agentsApi.deleteConversation(aid,id)
    if(epoch!==generation || aid!==props.agentId || id!==activeConversationId.value)return
    activeConversationId.value='';messages.value=[];await loadConversations()
  } catch(e) {if(epoch===generation)error.value=messageOf(e)}
  finally {if(epoch===generation)loading.value=false}
}
async function decide(pending: PendingAgentAction, approve: boolean) {
  if (!props.agentId || deciding.value || !(props.canConfirmActions ?? props.canAuthorize)) return
  const aid=props.agentId,epoch=generation
  deciding.value = pending.pending_id
  error.value = ''
  try {
    const result = await agentsApi.confirmAction(aid, pending.pending_id, approve)
    if (epoch!==generation || aid!==props.agentId) return
    pending.status = result.status
    pending.result = result.result
    pending.summary = result.summary || pending.summary
    emit('activity')
  } catch (e) {
    if (epoch===generation) {
      const detail=(e as any)?.response?.data?.detail
      if (detail?.status==='unknown' || detail?.status==='committed_unrecorded') {pending.status=detail.status;pending.result=detail.result;pending.summary=detail.summary || pending.summary;emit('activity')}
      error.value = messageOf(e)
    }
  } finally {
    if (epoch===generation) deciding.value = ''
  }
}
async function sendMessage() {
  if (!props.canAuthorize) return
  const questionText = question.value.trim()
  const aid = props.agentId
  if (!questionText || !aid || busy.value || loading.value || props.dirty) return
  error.value = ''
  busy.value = true
  const activeGeneration = generation
  let responseMessage: Message | undefined
  try {
    if (!activeConversationId.value)
      activeConversationId.value = (await agentsApi.createConversation(aid)).id
    if (activeGeneration !== generation) return
    messages.value.push({ role: 'user', content: questionText })
    messages.value.push({
      role: 'assistant',
      content: '',
      status: text('正在理解业务问题…'),
      steps: [],
      pendingActions: [],
    })
    responseMessage = messages.value[messages.value.length - 1]!
    question.value = ''
    controller = new AbortController()
    await scrollToBottom()
    const response = await authenticatedFetch(agentsApi.chatUrl(aid), {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ question: questionText, conversation_id: activeConversationId.value }),
      signal: controller.signal,
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(
        typeof data.detail === 'string'
          ? data.detail
          : data.detail
            ? JSON.stringify(data.detail)
            : `请求失败（${response.status}）`,
      )
    }
    if (!response.body) throw new Error(text('服务未返回响应流'))
    let streamComplete = false
    function processEvent(event: any) {
      if (activeGeneration !== generation) return
      const m = responseMessage!
      const steps = m.steps!
      if (event.type === 'run_started') {
        m.runId = event.run_id || event.id
      } else if (event.type === 'content') {
        m.content += event.content || ''
        m.status = undefined
      } else if (event.type === 'answer') {
        m.content = event.content || ''
        m.status = undefined
      } else if (event.type === 'error') {
        error.value = event.message || event.content || '智能体执行失败'
        m.status = undefined
      } else if (event.type === 'skill_load') {
        steps.push({
          category: 'skill',
          tool: `skill_${event.skill_id}`,
          label: `${event.name || '业务技能'} v${event.version}`,
          summary: event.summary || text('已加载固定版本技能'),
          detail: { skill_id: event.skill_id, version: event.version },
        })
        m.status = text('已加载业务技能，正在查询业务依据…')
      } else if (event.type === 'tool_start') {
        steps.push({
          category: toolStage(event.tool),
          tool: event.tool,
          label: text(toolLabels[event.tool] || event.tool),
          arguments: event.arguments,
        })
        if (!m.content) m.status = text('正在执行{tool}…', {tool:text(toolLabels[event.tool] || event.tool)})
      } else if (event.type === 'tool_result') {
        const step = [...steps].reverse().find((s) => s.tool === event.tool && s.summary == null)
        if (step) {
          step.summary = event.summary
          step.resultCount = event.resultCount
          step.detail = event.detail
        }
      } else if (event.type === 'action_pending') {
        m.pendingActions!.push({ ...event, status: 'pending' })
        m.status = text('业务动作等待授权确认')
      } else if (event.type === 'done') {
        streamComplete = true
        m.status = undefined
        if (event.error) error.value = String(event.error)
      }
    }
    await readJsonSse(response, event => { processEvent(event); void scrollToBottom() })
    if (!streamComplete) throw new Error(text('响应流提前结束，请查看运行记录后重试。'))
    if (!responseMessage.content && !responseMessage.pendingActions?.length && !error.value)
      error.value = text('服务未返回答复，请查看运行记录。')
    await loadConversations()
  } catch (e: any) {
    if (e?.name !== 'AbortError' && activeGeneration === generation) error.value = messageOf(e)
  } finally {
    if (activeGeneration === generation) {
      busy.value = false
      if (responseMessage) {
        responseMessage.status = undefined
        emit('activity')
      }
    }
  }
}
watch(
  () => props.agentId,
  async (aid) => {
    generation++
    const activeGeneration = generation
    controller?.abort()
    busy.value = false
    error.value = ''
    messages.value = []
    conversations.value = []
    activeConversationId.value = ''
    question.value = ''
    deciding.value = ''
    reconciliation.value = {}
    if (!aid) return
    loading.value = true
    try {
      const rows = await agentsApi.listConversations(aid)
      if (generation !== activeGeneration) return
      conversations.value = rows
      if (rows[0]) {
        activeConversationId.value = rows[0].id
        await selectConversation(rows[0].id)
      }
    } catch (e) {
      if (generation === activeGeneration) error.value = messageOf(e)
    } finally {
      if (generation === activeGeneration) loading.value = false
    }
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  generation++
  controller?.abort()
})
</script>
