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
            <p class="text-body-medium">智能副驾</p>
            <p class="text-caption">本体驱动 · 实时推理</p>
          </div>
        </div>
        <button class="copilot__new-chat" @click="clearChat">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新对话
        </button>
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
              <p class="text-body" style="white-space: pre-wrap;">{{ msg.content }}</p>
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
          placeholder="向智能副驾提问，例如：哪些客户有续约风险？"
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
          <span
            v-for="obj in relatedObjects"
            :key="obj.name"
            class="related-tag"
            :class="`related-tag--tier${obj.tier}`"
          >{{ obj.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'

interface Message {
  id: number
  role: 'user' | 'ai'
  content: string
  time: string
}

interface ReasoningStep {
  type: 'ontology' | 'ml' | 'rule' | 'output'
  typeLabel: string
  result: string
  source: string
}

const messages = ref<Message[]>([])
const inputText = ref('')
const isTyping = ref(false)
const messagesEl = ref<HTMLElement>()
const inputEl = ref<HTMLTextAreaElement>()
let msgId = 0

const suggestions = [
  '哪些客户有 FTTR 续约风险？',
  '本月营销活动效果如何？',
  '规则 rule_007 的触发条件是什么？',
  '客户分群的依据是什么？',
]

const reasoningSteps = ref<ReasoningStep[]>([])
const relatedObjects = ref<{ name: string; tier: 1 | 2 | 3 }[]>([])

function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function sendMessage(text?: string) {
  const content = (text ?? inputText.value).trim()
  if (!content) return

  messages.value.push({ id: ++msgId, role: 'user', content, time: now() })
  inputText.value = ''
  if (inputEl.value) inputEl.value.style.height = 'auto'

  await scrollToBottom()
  isTyping.value = true
  reasoningSteps.value = []
  relatedObjects.value = []

  // 模拟推理过程
  await delay(800)
  reasoningSteps.value.push({
    type: 'ontology', typeLabel: '本体查询',
    result: '检索 FTTRSubscription 对象，筛选 days_to_expire < 30',
    source: 'FTTRSubscription.days_to_expire'
  })

  await delay(600)
  reasoningSteps.value.push({
    type: 'ml', typeLabel: 'ML 评分',
    result: '调用流失风险模型，识别高风险客户 847 人',
    source: 'churn_risk_model_v2'
  })

  await delay(600)
  reasoningSteps.value.push({
    type: 'rule', typeLabel: '规则匹配',
    result: 'rule_007 触发：月费 > 200 且 churn_risk > 0.7',
    source: 'RuleSet.rule_007'
  })

  await delay(400)
  reasoningSteps.value.push({
    type: 'output', typeLabel: '策略输出',
    result: '推荐执行"专属优惠外呼"策略，预期转化率 4.1%',
    source: 'FTTRStrategy.exclusive_offer'
  })

  relatedObjects.value = [
    { name: 'Customer', tier: 1 },
    { name: 'FTTRSubscription', tier: 3 },
    { name: 'Campaign', tier: 2 },
    { name: 'RuleSet', tier: 2 },
  ]

  isTyping.value = false
  messages.value.push({
    id: ++msgId,
    role: 'ai',
    content: `根据本体分析，当前共有 847 名客户存在 FTTR 续约风险：\n\n• 距到期 < 30 天：312 人\n• 流失风险评分 > 0.7：535 人\n\n推荐策略：专属优惠外呼\n预期转化率：4.1%（高于短信 1.2%、APP 2.8%）\n\n是否立即执行续约策略？`,
    time: now()
  })

  await scrollToBottom()
}

function clearChat() {
  messages.value = []
  reasoningSteps.value = []
  relatedObjects.value = []
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

function delay(ms: number) {
  return new Promise(r => setTimeout(r, ms))
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
  font-size: 12px;
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
  font-size: 12px;
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
  font-size: 13px;
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
  color: #fff;
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
  font-size: 11px;
  font-weight: 700;
  color: #fff;
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
  font-size: 10px;
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
  font-size: 11px;
  color: var(--neutral-600);
  background: var(--neutral-100);
  padding: 2px 6px;
  border-radius: 3px;
  display: inline-block;
  margin-top: 4px;
}
.reasoning-step__result {
  font-size: 12px;
  color: var(--neutral-700);
  margin-top: 2px;
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
  font-size: 12px;
  font-weight: 500;
}
.related-tag--tier1 { background: var(--tier1-bg); color: var(--tier1-text); }
.related-tag--tier2 { background: var(--tier2-bg); color: var(--tier2-text); }
.related-tag--tier3 { background: var(--tier3-bg); color: var(--tier3-text); }

/* 消息过渡 */
.message-enter-active { transition: opacity 250ms ease-out, transform 250ms ease-out; }
.message-enter-from { opacity: 0; transform: translateY(12px); }
</style>
