<template>
  <div class="copilot">
    <!-- 左侧对话面板 -->
    <div class="copilot__chat">
      <div class="copilot__chat-header">
        <div class="copilot__chat-title">
          <div class="copilot__ai-avatar">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 2a6 6 0 100 12A6 6 0 008 2z" stroke="#fff" stroke-width="1.5"/>
              <path d="M5.5 9.5s.5 1.5 2.5 1.5 2.5-1.5 2.5-1.5" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
              <circle cx="6" cy="7" r="0.75" fill="#fff"/>
              <circle cx="10" cy="7" r="0.75" fill="#fff"/>
            </svg>
          </div>
          <div>
            <p class="text-body-medium">{{ appTitle }}</p>
            <p class="text-caption">本体驱动 · 实时推理</p>
          </div>
        </div>
        <div class="copilot__agent-select">
          <select v-model="selectedAgentId" class="copilot__agent-dropdown">
            <option value="">默认智能问答</option>
            <option v-for="a in publishedAgents" :key="a.id" :value="a.id">{{ a.name }}</option>
          </select>
        </div>
        <button class="copilot__new-chat" @click="clearChat">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新对话
        </button>
      </div>
      <div v-if="selectedAgent" class="copilot__agent-banner">
        <span>智能体：{{ selectedAgent.name }}</span>
        <span v-if="selectedAgent.entity_ids?.length" class="copilot__agent-tag">实体 ×{{ selectedAgent.entity_ids.length }}</span>
      </div>

      <!-- 消息列表 -->
      <div class="copilot__messages" ref="messagesEl">
        <TransitionGroup name="message">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="message"
            :class="`message--${msg.role}`"
          >
            <div v-if="msg.role === 'ai'" class="message__avatar">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M6 1a5 5 0 100 10A5 5 0 006 1z" stroke="#fff" stroke-width="1.2"/>
                <circle cx="4.5" cy="5.5" r="0.6" fill="#fff"/>
                <circle cx="7.5" cy="5.5" r="0.6" fill="#fff"/>
                <path d="M4 8s.5 1 2 1 2-1 2-1" stroke="#fff" stroke-width="1.2" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="message__bubble">
              <div v-if="msg.role === 'ai'" class="text-body markdown-body" v-html="renderMarkdown(msg.content)"></div>
              <p v-else class="text-body" style="white-space: pre-wrap;">{{ msg.content }}</p>
              <!-- AI 回复后的建议问题 -->
              <div v-if="msg.role === 'ai' && msg.suggestions && msg.suggestions.length > 0" class="message__suggestions">
                <button
                  v-for="s in msg.suggestions"
                  :key="s"
                  class="suggestion-chip suggestion-chip--inline"
                  @click="sendMessage(s)"
                >{{ s }}</button>
              </div>
              <!-- 可执行动作按钮 -->
              <div v-if="msg.role === 'ai' && msg.actions && msg.actions.length > 0" class="message__actions">
                <button
                  v-for="act in msg.actions"
                  :key="act.action_name"
                  class="action-btn"
                  :disabled="executingAction === act.action_name"
                  @click="executeAction(act)"
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M5 2l5 4-5 4V2z" fill="currentColor"/>
                  </svg>
                  {{ act.name }}
                  <span v-if="executingAction === act.action_name" class="action-btn__loading">执行中...</span>
                </button>
              </div>
              <span class="message__time text-caption">{{ msg.time }}</span>
            </div>
          </div>
        </TransitionGroup>

        <!-- 打字中 -->
        <div v-if="isTyping" class="message message--ai">
          <div class="message__avatar">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 1a5 5 0 100 10A5 5 0 006 1z" stroke="#fff" stroke-width="1.2"/>
            </svg>
          </div>
          <div class="message__bubble message__bubble--typing">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>

      <!-- 快捷提示 -->
      <div v-if="messages.length === 0" class="copilot__suggestions">
        <p class="text-caption-upper" style="margin-bottom: 8px;">快速提问</p>
        <button
          v-for="s in suggestions"
          :key="s"
          class="suggestion-chip"
          @click="sendMessage(s)"
        >{{ s }}</button>
      </div>

      <!-- 输入区 -->
      <div class="copilot__input-area">
        <textarea
          v-model="inputText"
          class="copilot__input"
          placeholder="向智能对话提问，例如：哪些客户有续约风险？"
          rows="1"
          @keydown.enter.exact.prevent="sendMessage()"
          @input="autoResize"
          ref="inputEl"
        ></textarea>
        <button
          class="copilot__send"
          :disabled="!inputText.trim()"
          @click="sendMessage()"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 8l12-6-5 6 5 6-12-6z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 右侧上下文面板 -->
    <div class="copilot__context">
      <div class="copilot__context-header">
        <h3 class="text-h3">推理上下文</h3>
      </div>

      <!-- 推理链 -->
      <div v-if="reasoningSteps.length > 0" class="reasoning-chain">
        <template v-for="(step, i) in reasoningSteps" :key="i">
          <div class="reasoning-step" :style="{ animationDelay: `${i * 200}ms` }">
            <div class="reasoning-step__index" :class="`reasoning-step__index--${step.type}`">{{ i + 1 }}</div>
            <div class="reasoning-step__body">
              <div class="reasoning-step__type" :class="`reasoning-step__type--${step.type}`">{{ step.typeLabel }}</div>
              <div class="reasoning-step__result text-body">{{ step.result }}</div>
              <code class="reasoning-step__source">{{ step.source }}</code>
              <div v-if="step.details && step.details.length > 0" class="reasoning-step__details">
                <div v-for="(d, di) in step.details" :key="di" class="reasoning-step__detail-item">{{ d }}</div>
              </div>
            </div>
          </div>
          <div v-if="i < reasoningSteps.length - 1" class="reasoning-chain__connector"></div>
        </template>
      </div>

      <div v-else class="copilot__context-empty">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="16" r="12" stroke="var(--neutral-300)" stroke-width="1.5"/>
          <path d="M10 16h12M16 10v12" stroke="var(--neutral-300)" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <p class="text-caption" style="margin-top: 8px;">发送消息后显示推理过程</p>
      </div>

      <!-- 关联本体对象 -->
      <div v-if="relatedObjects.length > 0" class="copilot__related">
        <p class="text-caption-upper" style="margin-bottom: 8px;">关联本体对象</p>
        <div class="related-tags">
          <span v-for="obj in relatedObjects" :key="obj.name" class="related-tag" :class="`related-tag--tier${obj.tier}`">{{ obj.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { agentsApi, type AgentItem } from '../../api/agents'

// marked 配置：同步解析，禁用异步
marked.setOptions({ async: false })

function renderMarkdown(content: string): string {
  if (!content) return ''
  return marked.parse(content) as string
}

interface ActionButton {
  name: string
  action_name: string
  params: Record<string, unknown>
  description: string
}

interface Message {
  id: number
  role: 'user' | 'ai'
  content: string
  time: string
  suggestions?: string[]
  actions?: ActionButton[]
}

interface ReasoningStep {
  type: 'ontology' | 'ml' | 'rule' | 'output'
  typeLabel: string
  result: string
  source: string
  details?: string[]
}

const TOOL_TYPE_MAP: Record<string, { type: ReasoningStep['type']; label: string }> = {
  describe_ontology_model: { type: 'ontology', label: '本体模型' },
  get_entity_detail: { type: 'ontology', label: '实体详情' },
  query_entity_data: { type: 'ontology', label: '本体数据查询' },
  list_datasources: { type: 'ml', label: '数据源列表' },
  get_table_schema: { type: 'ml', label: '表结构' },
  query_datasource: { type: 'ml', label: '数据查询' },
  get_business_rules: { type: 'rule', label: '业务规则' },
  evaluate_rule: { type: 'rule', label: '规则评估' },
  evaluate_all_rules: { type: 'rule', label: '全量规则评估' },
  screen_users_by_rule: { type: 'rule', label: '规则筛选用户' },
  execute_action: { type: 'output', label: '执行动作' },
  '[感知·数据采集]': { type: 'ontology', label: '感知·数据采集' },
  '[识别·证据提取]': { type: 'rule', label: '识别·证据提取' },
  '[推理·逻辑命中]': { type: 'rule', label: '推理·逻辑命中' },
  '[归因·结论输出]': { type: 'output', label: '归因·结论输出' },
  '[动作·推荐生成]': { type: 'output', label: '动作·推荐生成' },
  '[意图识别]': { type: 'ontology', label: '意图识别' },
  '[结果输出]': { type: 'output', label: '结果输出' },
}

const messages = ref<Message[]>([])
const inputText = ref('')
const isTyping = ref(false)
const executingAction = ref<string | null>(null)
const messagesEl = ref<HTMLElement>()
const inputEl = ref<HTMLTextAreaElement>()
let msgId = 0

const allAgents = ref<AgentItem[]>([])
const selectedAgentId = ref('')
const publishedAgents = computed(() => allAgents.value.filter(a => a.status === 'published'))
const selectedAgent = computed(() => publishedAgents.value.find(a => a.id === selectedAgentId.value) || null)

onMounted(async () => {
  try { allAgents.value = await agentsApi.list() } catch {}
})

const appTitle = computed(() => '智能对话')

const suggestions = [
  '携号转网场景有哪些预警规则？',
  '用户 U00001 的携转风险等级是什么？',
  '在网不到12个月且有携转查询记录的用户有哪些？',
  '最近有哪些维系挽留未成功的用户？',
  '宽带退单的主要根因分布是什么？',
  '施工原因导致的宽带退单有哪些共性特征？',
]

const reasoningSteps = ref<ReasoningStep[]>([])
const relatedObjects = ref<{ name: string; tier: 1 | 2 | 3 }[]>([])

function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function sendMessage(text?: string) {
  const content = (text ?? inputText.value).trim()
  if (!content || isTyping.value) return

  messages.value.push({ id: ++msgId, role: 'user', content, time: now() })
  inputText.value = ''
  if (inputEl.value) inputEl.value.style.height = 'auto'

  await scrollToBottom()
  isTyping.value = true
  reasoningSteps.value = []
  relatedObjects.value = []

  const aiMsg: Message = { id: ++msgId, role: 'ai', content: '', time: now() }
  messages.value.push(aiMsg)
  // 获取响应式引用，确保修改能触发视图更新
  const aiMsgRef = messages.value[messages.value.length - 1]

  try {
    // Route to agent chat if an agent is selected
    const url = selectedAgentId.value
      ? `/api/v1/agents/${selectedAgentId.value}/chat`
      : '/api/v1/copilot/agent-chat'
    const body = JSON.stringify({ question: content })

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })

    if (!response.ok) {
    aiMsgRef.content = `请求失败: ${response.status}`
      isTyping.value = false
      return
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    if (reader) {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') break
          try {
            const event = JSON.parse(data)
            handleSSEEvent(event, aiMsgRef)
            await scrollToBottom()
          } catch {
            // 非 JSON，忽略
          }
        }
      }
    }
  } catch (e) {
    aiMsgRef.content = `连接失败: ${(e as Error).message}`
  } finally {
    isTyping.value = false
    await scrollToBottom()
  }
}

function extractDetailLines(detail: Record<string, unknown>): string[] {
  const lines: string[] = []
  const t = detail.type as string

  if (t === 'rules') {
    const rules = detail.rules as Array<Record<string, unknown>> || []
    for (const r of rules) {
      const cond = r.has_conditions ? '可评估' : '仅描述'
      lines.push(`规则: ${r.name} [${cond}] → 关联实体: ${r.entity}`)
    }
  } else if (t === 'screen') {
    const risk = detail.risk_level as string
    const mode = detail.match_mode as string
    const condCount = detail.conditions_count as number
    const matched = detail.matched_users as number
    lines.push(`风险等级: ${risk} | 匹配模式: ${mode} | 条件数: ${condCount} | 命中: ${matched}人`)
    const entities = detail.entities_involved as Array<Record<string, string>> || []
    if (entities.length > 0) {
      lines.push('涉及本体实体 → 数据源:')
      for (const e of entities) {
        lines.push(`  ${e.entity_cn}(${e.entity}) → ${e.datasource}`)
      }
    }
    const conditions = detail.conditions as string[] || []
    if (conditions.length > 0) {
      lines.push('规则条件:')
      for (const c of conditions) {
        lines.push(`  · ${c}`)
      }
    }
  } else if (t === 'evaluate') {
    lines.push(`用户: ${detail.user_id} | 综合风险: ${detail.overall_risk}`)
    lines.push(`评估 ${detail.evaluated_count} 条规则，${detail.triggered_count} 条触发`)
  } else if (t === 'evaluate_single') {
    const triggered = detail.triggered ? '触发' : '未触发'
    lines.push(`规则: ${detail.rule_name} → ${triggered} (${detail.matched_count}/${detail.total_count})`)
    lines.push(`风险等级: ${detail.risk_level}`)
  } else if (t === 'entity_query') {
    lines.push(`本体实体: ${detail.entity_cn}(${detail.entity})`)
    lines.push(`数据源: ${detail.datasource} → 表: ${detail.table}`)
    lines.push(`查询结果: ${detail.row_count} 条记录`)
  } else if (t === 'entity_detail') {
    lines.push(`实体: ${detail.entity_cn}(${detail.entity})`)
    lines.push(`属性: ${detail.attr_count}个 | 关系: ${detail.relation_count}个 | 规则: ${detail.rule_count}条`)
  } else if (t === 'action') {
    const success = detail.success ? '成功' : '失败'
    lines.push(`动作: ${detail.action_name} → ${success}`)
    const effects = detail.effects as Array<Record<string, unknown>> || []
    for (const e of effects) {
      lines.push(`  效果: ${e.operation} ${e.target}`)
    }
  } else if (t === 'broadband_perception') {
    const sources = detail.source_types as Record<string, number> || {}
    lines.push(`数据源采集: 共 ${detail.total_sources} 条`)
    for (const [src, cnt] of Object.entries(sources)) {
      lines.push(`  ${src}: ${cnt}`)
    }
  } else if (t === 'broadband_recognition') {
    lines.push(`NLP证据: ${detail.nlp_count} 条 | 规则证据: ${detail.rule_count} 条`)
    lines.push(`命中: ${detail.hit_count} / ${detail.total} 条`)
    const codes = detail.hit_codes as string[] || []
    if (codes.length > 0) {
      lines.push(`命中编码: ${codes.join(', ')}`)
    }
  } else if (t === 'broadband_reasoning') {
    lines.push(`逻辑规则命中: ${detail.hit_count} 条`)
    const fns = detail.logic_functions as string[] || []
    if (fns.length > 0) {
      lines.push(`逻辑函数: ${fns.join(', ')}`)
    }
  } else if (t === 'broadband_attribution') {
    lines.push(`根因类别: ${detail.root_cause_level_one || '未知'}`)
    lines.push(`根因细类: ${detail.root_cause_level_two || '-'}`)
    lines.push(`置信度: ${((detail.confidence as number || 0) * 100).toFixed(1)}%`)
    lines.push(`稽核状态: ${detail.audit_status || '-'}`)
  } else if (t === 'broadband_todo') {
    lines.push(`推荐动作: ${detail.action_count} 个`)
    const acts = detail.actions as string[] || []
    for (const a of acts) {
      lines.push(`  · ${a}`)
    }
  }

  return lines
}

function handleSSEEvent(event: Record<string, unknown>, aiMsg: Message) {
  const type = event.type as string

  if (type === 'tool_start') {
    const toolName = event.tool as string
    const mapping = TOOL_TYPE_MAP[toolName] || { type: 'ml' as const, label: toolName }
    const args = event.arguments as Record<string, unknown> | undefined
    const argStr = args ? Object.values(args).filter(Boolean).join(', ') : ''
    reasoningSteps.value.push({
      type: mapping.type,
      typeLabel: mapping.label,
      result: '执行中...',
      source: argStr || toolName,
    })
  } else if (type === 'tool_result') {
    const lastStep = reasoningSteps.value[reasoningSteps.value.length - 1]
    if (lastStep) {
      lastStep.result = (event.summary as string) || '完成'
      // 提取本体上下文详情
      const detail = event.detail as Record<string, unknown> | undefined
      if (detail) {
        lastStep.details = extractDetailLines(detail)
      }
    }
  } else if (type === 'content') {
    // 流式内容追加到对话气泡
    aiMsg.content += (event.content as string) || ''
  } else if (type === 'done') {
    // 完成，设置建议问题和动作按钮
    const sug = event.suggestions as string[] | undefined
    if (sug && sug.length > 0) {
      aiMsg.suggestions = sug
    }
    const acts = event.actions as ActionButton[] | undefined
    if (acts && acts.length > 0) {
      aiMsg.actions = acts
    }
    // 添加最终输出步骤到推理链
    reasoningSteps.value.push({
      type: 'output',
      typeLabel: '最终回答',
      result: '推理完成',
      source: 'AI',
    })
  } else if (type === 'tool_summary') {
    // 工具链汇总（可选展示）
  } else if (type === 'answer') {
    // 兼容旧格式
    aiMsg.content = (event.content as string) || ''
    const sug = event.suggestions as string[] | undefined
    if (sug && sug.length > 0) {
      aiMsg.suggestions = sug
    }
  }
}

function clearChat() {
  messages.value = []
  reasoningSteps.value = []
  relatedObjects.value = []
  executingAction.value = null
}

async function executeAction(action: ActionButton) {
  executingAction.value = action.action_name
  // 将动作执行作为新的对话消息发送给 Agent
  const prompt = `请执行动作「${action.name}」，参数: ${JSON.stringify(action.params)}，动作英文名: ${action.action_name}`
  await sendMessage(prompt)
  executingAction.value = null
}

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

</script>

<style scoped>
.copilot {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* 左侧聊天面板 */
.copilot__chat {
  width: 460px;
  min-width: 460px;
  display: flex;
  flex-direction: column;
  background: var(--neutral-0);
  border-right: 1px solid var(--neutral-200);
}

.copilot__chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--neutral-100);
  flex-shrink: 0;
}
.copilot__chat-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.copilot__ai-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--semantic-600), var(--tier2-primary));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.copilot__new-chat {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--neutral-200);
  background: transparent;
  font-size: var(--text-code-size);
  color: var(--neutral-600);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.copilot__new-chat:hover {
  border-color: var(--semantic-400);
  color: var(--semantic-600);
}

/* 消息列表 */
.copilot__messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}
.message--user {
  flex-direction: row-reverse;
}

.message__avatar {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--semantic-600), var(--tier2-primary));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message__bubble {
  max-width: 320px;
  padding: 10px 14px;
  border-radius: 12px;
  position: relative;
}
.message--ai .message__bubble {
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
  border-bottom-left-radius: 4px;
}
.message--user .message__bubble {
  background: var(--semantic-50);
  border: 1px solid var(--semantic-200);
  border-bottom-right-radius: 4px;
}

.message__time {
  display: block;
  margin-top: 4px;
  text-align: right;
}

/* 打字动画 */
.message__bubble--typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 16px;
}
.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--neutral-400);
  animation: typing-bounce 1.2s ease-in-out infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

/* 快捷提示 */
.copilot__suggestions {
  padding: 0 20px 12px;
  flex-shrink: 0;
}
.suggestion-chip {
  display: inline-block;
  margin: 4px 4px 0 0;
  padding: 5px 12px;
  border-radius: var(--radius-full);
  border: 1px solid var(--neutral-200);
  background: var(--neutral-50);
  font-size: var(--text-code-size);
  color: var(--neutral-700);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.suggestion-chip:hover {
  border-color: var(--semantic-400);
  background: var(--semantic-50);
  color: var(--semantic-600);
}

/* 输入区 */
.copilot__input-area {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--neutral-100);
  flex-shrink: 0;
}
.copilot__input {
  flex: 1;
  padding: 8px 12px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--neutral-200);
  background: var(--neutral-50);
  font-size: var(--text-body-size);
  color: var(--neutral-800);
  resize: none;
  outline: none;
  font-family: var(--font-sans);
  line-height: 1.5;
  min-height: 38px;
  max-height: 120px;
  transition: border-color var(--transition-fast);
}
.copilot__input:focus {
  border-color: var(--semantic-400);
  background: var(--neutral-0);
}
.copilot__input::placeholder { color: var(--neutral-400); }

.copilot__send {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  border: none;
  background: var(--semantic-600);
  color: var(--neutral-0);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: background var(--transition-fast), transform var(--transition-fast);
}
.copilot__send:hover:not(:disabled) {
  background: var(--semantic-700);
  transform: scale(1.05);
}
.copilot__send:disabled {
  background: var(--neutral-200);
  color: var(--neutral-400);
  cursor: not-allowed;
}

/* 右侧上下文面板 */
.copilot__context {
  flex: 1;
  background: var(--neutral-50);
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.copilot__context-header {
  flex-shrink: 0;
}

.copilot__context-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: var(--neutral-400);
}

/* 推理链 */
.reasoning-chain { display: flex; flex-direction: column; }
.reasoning-step {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  opacity: 0;
  transform: translateY(8px);
  animation: reasoning-step-in 400ms ease-out forwards;
}
@keyframes reasoning-step-in {
  to { opacity: 1; transform: translateY(0); }
}

.reasoning-step__index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-caption-size);
  font-weight: 700;
  color: var(--neutral-0);
  flex-shrink: 0;
}
.reasoning-step__index--ontology { background: var(--semantic-600); }
.reasoning-step__index--ml { background: var(--tier2-primary); }
.reasoning-step__index--rule { background: var(--kinetic-600); }
.reasoning-step__index--output { background: var(--dynamic-600); }

.reasoning-step__body {
  flex: 1;
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
}
.reasoning-step__type {
  font-size: var(--text-caption-upper-size);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 4px;
}
.reasoning-step__type--ontology { color: var(--semantic-600); }
.reasoning-step__type--ml { color: var(--tier2-primary); }
.reasoning-step__type--rule { color: var(--kinetic-600); }
.reasoning-step__type--output { color: var(--dynamic-600); }

.reasoning-step__source {
  font-family: var(--font-mono);
  font-size: var(--text-caption-size);
  color: var(--neutral-600);
  background: var(--neutral-100);
  padding: 2px 6px;
  border-radius: 3px;
  display: inline-block;
  margin-top: 4px;
}
.reasoning-step__result {
  font-size: var(--text-code-size);
  color: var(--neutral-700);
  margin-top: 2px;
}
.reasoning-step__details {
  margin-top: 6px;
  padding: 6px 8px;
  background: var(--neutral-50, #fafafa);
  border-radius: 4px;
  border-left: 2px solid var(--semantic-300, #93b8e6);
}
.reasoning-step__detail-item {
  font-size: var(--text-caption-size);
  color: var(--neutral-600);
  line-height: 1.6;
  white-space: pre-wrap;
  font-family: var(--font-mono);
}

.reasoning-chain__connector {
  width: 2px;
  height: 16px;
  margin-left: 11px;
  background: var(--neutral-300);
  border-style: dashed;
}

/* 关联对象 */
.copilot__related { flex-shrink: 0; }
.related-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.related-tag {
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: var(--text-code-size);
  font-weight: 500;
}
.related-tag--tier1 { background: var(--tier1-bg); color: var(--tier1-text); }
.related-tag--tier2 { background: var(--tier2-bg); color: var(--tier2-text); }
.related-tag--tier3 { background: var(--tier3-bg); color: var(--tier3-text); }

/* 消息过渡 */
.message-enter-active { transition: opacity 250ms ease-out, transform 250ms ease-out; }
.message-enter-from { opacity: 0; transform: translateY(12px); }

/* 消息内建议 */
.message__suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

/* 可执行动作按钮 */
.message__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--neutral-200);
}
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-code-size);
  padding: 6px 14px;
  border-radius: var(--radius-md, 6px);
  border: 1px solid var(--semantic-400, #4a90d9);
  background: var(--semantic-50, #f0f7ff);
  color: var(--semantic-700, #1a56a0);
  cursor: pointer;
  font-weight: 500;
  transition: all var(--transition-fast);
}
.action-btn:hover:not(:disabled) {
  background: var(--semantic-100, #d6e8ff);
  border-color: var(--semantic-500, #3a7bd5);
  box-shadow: 0 1px 4px rgba(74, 144, 217, 0.2);
}
.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.action-btn__loading {
  font-size: var(--text-caption-size);
  color: var(--semantic-500);
  margin-left: 4px;
}
.suggestion-chip--inline {
  font-size: var(--text-caption-size);
  padding: 3px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--semantic-200);
  background: var(--semantic-50, #f0f7ff);
  color: var(--semantic-600);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.suggestion-chip--inline:hover {
  background: var(--semantic-100);
  border-color: var(--semantic-400);
}
.copilot__agent-select { flex: 1; }
.copilot__agent-dropdown { padding: 5px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--surface-1); color: var(--text); cursor: pointer; max-width: 220px; }
.copilot__agent-banner { display: flex; align-items: center; gap: 8px; padding: 6px 20px; background: var(--semantic-50, #eff6ff); border-bottom: 1px solid var(--semantic-200, #bfdbfe); font-size: 13px; color: var(--semantic-700, #1d4ed8); }
.copilot__agent-tag { background: var(--semantic-100, #dbeafe); padding: 2px 8px; border-radius: 4px; font-size: 11px; }

/* Markdown 渲染 */
.markdown-body { font-size: var(--text-body-size); line-height: 1.6; word-break: break-word; }
.markdown-body :deep(p) { margin: 4px 0; }
.markdown-body :deep(h3) { font-size: var(--text-body-size); font-weight: 600; margin: 10px 0 4px; }
.markdown-body :deep(h4) { font-size: var(--text-body-size); font-weight: 600; margin: 8px 0 4px; }
.markdown-body :deep(table) { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: var(--text-code-size); }
.markdown-body :deep(th),
.markdown-body :deep(td) { border: 1px solid var(--neutral-200); padding: 4px 8px; text-align: left; }
.markdown-body :deep(th) { background: var(--neutral-100); font-weight: 600; }
.markdown-body :deep(ul),
.markdown-body :deep(ol) { padding-left: 18px; margin: 4px 0; }
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(code) { background: var(--neutral-100); padding: 1px 4px; border-radius: 3px; font-size: var(--text-code-size); }
.markdown-body :deep(pre) { background: var(--neutral-100); padding: 8px; border-radius: 6px; overflow-x: auto; margin: 6px 0; }
.markdown-body :deep(pre code) { background: none; padding: 0; }

/* HITL Approval Cards */

/* Published App Info */
.copilot__app-info { padding: 12px 20px; border-top: 1px solid var(--neutral-200); }
</style>
