<template>
  <div class="step-chat">
    <div class="step-chat__main">
      <div class="step-chat__messages" ref="messagesEl">
        <div v-for="(msg, i) in messages" :key="i" class="step-chat__msg" :class="`step-chat__msg--${msg.role}`">
          <div class="step-chat__msg-avatar">{{ msg.role === 'assistant' ? '🤖' : '👤' }}</div>
          <div class="step-chat__msg-body">
            <div class="step-chat__msg-text" v-html="renderMarkdown(msg.text)"></div>
            <div v-if="msg.ontology" class="step-chat__ontology-card">
              <div class="step-chat__ontology-header" @click="msg.expanded = !msg.expanded">
                <span>📋 本体草稿：{{ msg.ontology.entities.length }} 实体 · {{ msg.ontology.relations.length }} 关系</span>
                <span class="step-chat__toggle">{{ msg.expanded ? '▼' : '▶' }}</span>
              </div>
              <div v-if="msg.expanded" class="step-chat__ontology-body">
                <div v-for="e in msg.ontology.entities" :key="e.name" class="step-chat__entity">
                  <strong>{{ e.displayName }}</strong> <code>{{ e.name }}</code>
                  <div class="step-chat__props">
                    <span v-for="p in e.properties" :key="p.name" class="step-chat__prop">{{ p.displayName || p.name }}({{ p.type }})</span>
                  </div>
                </div>
                <div v-if="msg.ontology.relations.length" class="step-chat__relations">
                  <div v-for="r in msg.ontology.relations" :key="r.name" class="step-chat__rel">
                    {{ r.source }} →<strong>{{ r.displayName }}</strong>→ {{ r.target }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-if="streaming" class="step-chat__msg step-chat__msg--assistant">
          <div class="step-chat__msg-avatar">🤖</div>
          <div class="step-chat__msg-body">
            <div class="step-chat__msg-text step-chat__streaming" v-html="renderMarkdown(streamingText)"></div>
          </div>
        </div>
      </div>

      <div class="step-chat__input-area">
        <textarea class="step-chat__input" v-model="userInput" placeholder="输入修正指令，如：把客户实体拆分为个人客户和企业客户..." rows="2" @keydown.enter.ctrl="sendMessage" :disabled="streaming"></textarea>
        <div class="step-chat__actions">
          <button class="step-chat__btn" :disabled="!userInput.trim() || streaming" @click="sendMessage">发送</button>
          <button class="step-chat__btn step-chat__btn--confirm" :disabled="!latestOntology || streaming" @click="emit('next', latestOntology!)">
            确认本体，进入审核 →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { marked } from 'marked'
import { docBuilderChat } from '../../../../api/docBuilder'

interface OntologyData {
  entities: Array<{ name: string; displayName: string; description?: string; properties: Array<{ name: string; displayName?: string; type: string }> }>
  relations: Array<{ name: string; displayName: string; source: string; target: string; cardinality: string }>
}

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  ontology?: OntologyData
  expanded?: boolean
}

const props = defineProps<{ sessionId: string; businessDesc: string }>()
const emit = defineEmits<{ (e: 'next', ontology: OntologyData): void }>()

const messages = ref<ChatMessage[]>([])
const userInput = ref('')
const streaming = ref(false)
const streamingText = ref('')
const latestOntology = ref<OntologyData | null>(null)
const messagesEl = ref<HTMLElement>()

function renderMarkdown(text: string): string {
  const cleaned = text.replace(/```json[\s\S]*?```/g, '')
  return marked.parse(cleaned, { async: false }) as string
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

function doChat(message: string) {
  streaming.value = true
  streamingText.value = ''

  docBuilderChat(
    props.sessionId,
    message,
    props.businessDesc,
    (ev) => {
      if (ev.event === 'token') {
        streamingText.value += ev.content
        scrollToBottom()
      } else if (ev.event === 'ontology') {
        latestOntology.value = ev.data
      } else if (ev.event === 'thinking') {
        streamingText.value += `_${ev.message}_\n\n`
      }
    },
    () => {
      const msg: ChatMessage = {
        role: 'assistant',
        text: streamingText.value,
        ontology: latestOntology.value || undefined,
        expanded: true,
      }
      messages.value.push(msg)
      streaming.value = false
      streamingText.value = ''
      scrollToBottom()
    },
    () => {
      streaming.value = false
      streamingText.value = '请求失败，请重试'
    },
  )
}

function sendMessage() {
  if (!userInput.value.trim() || streaming.value) return
  const text = userInput.value.trim()
  messages.value.push({ role: 'user', text })
  userInput.value = ''
  scrollToBottom()
  doChat(text)
}

onMounted(() => {
  doChat('')
})
</script>

<style scoped>
.step-chat { height: 100%; display: flex; flex-direction: column; }
.step-chat__main { flex: 1; display: flex; flex-direction: column; max-width: 900px; margin: 0 auto; width: 100%; padding: 16px; }
.step-chat__messages { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; padding: 16px 0; }
.step-chat__msg { display: flex; gap: 10px; }
.step-chat__msg--user { flex-direction: row-reverse; }
.step-chat__msg-avatar { width: 32px; height: 32px; border-radius: 50%; background: #f0f0f0; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
.step-chat__msg-body { max-width: 75%; }
.step-chat__msg-text { font-size: 13px; line-height: 1.6; padding: 10px 14px; border-radius: 12px; }
.step-chat__msg--assistant .step-chat__msg-text { background: #f8f9fa; border: 1px solid #e2e8f0; border-radius: 4px 12px 12px; color: #334155; }
.step-chat__msg--assistant .step-chat__msg-text :deep(h2) { font-size: 15px; font-weight: 600; margin: 12px 0 6px; padding-bottom: 4px; border-bottom: 1px solid #e2e8f0; }
.step-chat__msg--assistant .step-chat__msg-text :deep(h3) { font-size: 14px; font-weight: 600; margin: 10px 0 4px; }
.step-chat__msg--assistant .step-chat__msg-text :deep(blockquote) { margin: 8px 0; padding: 6px 12px; border-left: 3px solid #94a3b8; background: #f1f5f9; color: #475569; font-size: 12px; border-radius: 0 4px 4px 0; }
.step-chat__msg--assistant .step-chat__msg-text :deep(code) { font-size: 12px; background: #e2e8f0; padding: 1px 4px; border-radius: 3px; }
.step-chat__msg--assistant .step-chat__msg-text :deep(hr) { border: none; border-top: 1px solid #e2e8f0; margin: 12px 0; }
.step-chat__msg--assistant .step-chat__msg-text :deep(ul), .step-chat__msg--assistant .step-chat__msg-text :deep(ol) { padding-left: 18px; margin: 6px 0; }
.step-chat__msg--assistant .step-chat__msg-text :deep(li) { margin: 3px 0; }
.step-chat__msg--assistant .step-chat__msg-text :deep(p) { margin: 6px 0; }
.step-chat__msg--assistant .step-chat__msg-text :deep(strong) { font-weight: 600; }
.step-chat__msg--user .step-chat__msg-text { background: linear-gradient(135deg, #4a6fa5, #6366f1); color: #fff; border-radius: 12px 4px 12px 12px; }
.step-chat__streaming { animation: pulse 1.2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
.step-chat__ontology-card { margin-top: 8px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
.step-chat__ontology-header { padding: 8px 12px; background: #f8f9fa; cursor: pointer; font-size: 12px; font-weight: 500; display: flex; justify-content: space-between; align-items: center; }
.step-chat__ontology-header:hover { background: #eef2f7; }
.step-chat__toggle { font-size: 10px; color: #999; }
.step-chat__ontology-body { padding: 12px; font-size: 12px; }
.step-chat__entity { margin-bottom: 8px; }
.step-chat__entity code { font-size: 11px; color: #888; margin-left: 4px; }
.step-chat__props { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.step-chat__prop { font-size: 11px; background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }
.step-chat__relations { margin-top: 12px; padding-top: 8px; border-top: 1px solid #eee; }
.step-chat__rel { font-size: 12px; color: #555; padding: 2px 0; }
.step-chat__input-area { border-top: 1px solid #e0e0e0; padding-top: 12px; }
.step-chat__input { width: 100%; padding: 10px 12px; border: 1px solid #d0d0d0; border-radius: 8px; font-size: 13px; resize: none; font-family: inherit; }
.step-chat__input:focus { outline: none; border-color: #4a6fa5; }
.step-chat__actions { display: flex; gap: 8px; margin-top: 8px; justify-content: flex-end; }
.step-chat__btn { padding: 8px 16px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; }
.step-chat__btn:disabled { opacity: 0.5; cursor: default; }
.step-chat__btn:hover:not(:disabled) { background: #3d5f8c; }
.step-chat__btn--confirm { background: #2e7d32; }
.step-chat__btn--confirm:hover:not(:disabled) { background: #1b5e20; }
</style>