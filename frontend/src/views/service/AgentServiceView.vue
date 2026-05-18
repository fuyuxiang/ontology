<template>
  <div class="agent-service">
    <div class="agent-service__header">
      <h1 class="page-title">Agent 交互</h1>
      <p class="page-desc">本体感知的智能体，通过自然语言查询实体、遍历关系、执行规则</p>
    </div>

    <div class="agent-service__body">
      <!-- 左侧：Agent 列表 -->
      <div class="agent-sidebar">
        <div class="agent-sidebar__head">
          <input v-model="searchText" class="search-input" placeholder="搜索智能体..." />
          <button class="btn-sm" @click="$router.push('/service/agent/new')">+ 新建</button>
        </div>
        <div class="agent-list">
          <div
            v-for="agent in filteredAgents"
            :key="agent.id"
            class="agent-card"
            :class="{ 'agent-card--active': selectedAgent?.id === agent.id }"
            @click="selectAgent(agent)"
          >
            <div class="agent-card__name">{{ agent.name }}</div>
            <div class="agent-card__desc">{{ agent.description || '暂无描述' }}</div>
            <div class="agent-card__meta">
              <span class="agent-card__status" :class="`agent-card__status--${agent.status}`">{{ agent.status === 'published' ? '已发布' : '草稿' }}</span>
              <span class="agent-card__tags" v-if="agent.tags">{{ agent.tags }}</span>
            </div>
          </div>
          <div v-if="filteredAgents.length === 0" class="agent-list__empty">暂无智能体</div>
        </div>
      </div>

      <!-- 右侧：对话区 -->
      <div class="chat-area">
        <template v-if="selectedAgent">
          <div class="chat-header">
            <span class="chat-header__name">{{ selectedAgent.name }}</span>
            <button class="btn-sm" @click="$router.push(`/service/agent/${selectedAgent.id}`)">编辑</button>
          </div>
          <div class="chat-messages" ref="messagesRef">
            <div v-for="(msg, i) in messages" :key="i" class="chat-msg" :class="`chat-msg--${msg.role}`">
              <div class="chat-msg__bubble">{{ msg.content }}</div>
            </div>
            <div v-if="streaming" class="chat-msg chat-msg--assistant">
              <div class="chat-msg__bubble chat-msg__typing">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
            </div>
          </div>
          <div class="chat-input">
            <textarea v-model="userInput" class="chat-textarea" placeholder="输入消息..." rows="2" @keydown.enter.exact.prevent="sendMessage" :disabled="streaming"></textarea>
            <button class="btn-send" @click="sendMessage" :disabled="streaming || !userInput.trim()">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 8l12-5-4 5 4 5-12-5z" fill="currentColor"/></svg>
            </button>
          </div>
        </template>
        <div v-else class="chat-empty">
          <p>选择左侧智能体开始对话</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { get } from '../../api/client'

interface Agent { id: string; name: string; description: string; status: string; tags: string }
interface ChatMsg { role: 'user' | 'assistant'; content: string }

const searchText = ref('')
const agents = ref<Agent[]>([])
const selectedAgent = ref<Agent | null>(null)
const messages = ref<ChatMsg[]>([])
const userInput = ref('')
const streaming = ref(false)
const messagesRef = ref<HTMLElement | null>(null)

const filteredAgents = computed(() => {
  if (!searchText.value) return agents.value
  const q = searchText.value.toLowerCase()
  return agents.value.filter(a => a.name.toLowerCase().includes(q) || a.description?.toLowerCase().includes(q))
})

function selectAgent(agent: Agent) {
  selectedAgent.value = agent
  messages.value = [{ role: 'assistant', content: `你好！我是「${agent.name}」，有什么可以帮你的？` }]
}

function scrollToBottom() {
  nextTick(() => { if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight })
}

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || !selectedAgent.value) return
  messages.value.push({ role: 'user', content: text })
  userInput.value = ''
  streaming.value = true
  scrollToBottom()

  try {
    const token = localStorage.getItem('token')
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const res = await fetch(`/api/v1/agents/${selectedAgent.value.id}/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message: text }),
    })

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let assistantMsg = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n')
      buffer = parts.pop() ?? ''
      for (const line of parts) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') continue
          try {
            const event = JSON.parse(data)
            if (event.type === 'token' && event.content) {
              assistantMsg += event.content
            } else if (event.type === 'message' && event.content) {
              assistantMsg = event.content
            }
          } catch { /* skip */ }
        }
      }
    }
    if (assistantMsg) messages.value.push({ role: 'assistant', content: assistantMsg })
  } catch (e: any) {
    messages.value.push({ role: 'assistant', content: `错误: ${e.message}` })
  } finally {
    streaming.value = false
    scrollToBottom()
  }
}

async function loadAgents() {
  try {
    const data = await get<Agent[]>('/agents')
    agents.value = data
  } catch { /* empty */ }
}

onMounted(loadAgents)
</script>

<style scoped>
.agent-service { display: flex; flex-direction: column; height: 100%; }
.agent-service__header { padding: 20px 24px 12px; flex-shrink: 0; }
.page-title { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0 0 4px; }
.page-desc { font-size: 13px; color: var(--neutral-500); margin: 0; }
.agent-service__body { display: flex; flex: 1; overflow: hidden; border-top: 1px solid var(--neutral-200); }

.agent-sidebar { width: 280px; flex-shrink: 0; border-right: 1px solid var(--neutral-200); display: flex; flex-direction: column; }
.agent-sidebar__head { display: flex; gap: 8px; padding: 12px; border-bottom: 1px solid var(--neutral-100); }
.search-input { flex: 1; padding: 6px 10px; border: 1px solid var(--neutral-200); border-radius: 6px; font-size: 12px; outline: none; }
.search-input:focus { border-color: var(--semantic-500); }
.btn-sm { padding: 4px 10px; border: 1px solid var(--neutral-200); border-radius: 5px; background: var(--neutral-0); font-size: 11px; cursor: pointer; color: var(--neutral-600); white-space: nowrap; }
.btn-sm:hover { background: var(--neutral-50); }

.agent-list { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.agent-card { padding: 10px 12px; border-radius: 8px; cursor: pointer; border: 1px solid transparent; transition: all 0.15s; }
.agent-card:hover { background: var(--neutral-50); }
.agent-card--active { background: var(--semantic-50); border-color: var(--semantic-200); }
.agent-card__name { font-size: 13px; font-weight: 600; color: var(--neutral-800); }
.agent-card__desc { font-size: 11px; color: var(--neutral-500); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-card__meta { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.agent-card__status { font-size: 10px; padding: 1px 6px; border-radius: 4px; font-weight: 500; }
.agent-card__status--published { background: #d1fae5; color: #059669; }
.agent-card__status--draft { background: var(--neutral-100); color: var(--neutral-500); }
.agent-card__tags { font-size: 10px; color: var(--neutral-400); }
.agent-list__empty { padding: 20px; text-align: center; color: var(--neutral-400); font-size: 12px; }

.chat-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.chat-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; border-bottom: 1px solid var(--neutral-100); }
.chat-header__name { font-size: 14px; font-weight: 600; color: var(--neutral-800); }
.chat-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--neutral-400); font-size: 13px; }

.chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.chat-msg { display: flex; }
.chat-msg--user { justify-content: flex-end; }
.chat-msg--assistant { justify-content: flex-start; }
.chat-msg__bubble { max-width: 70%; padding: 8px 12px; border-radius: 10px; font-size: 13px; line-height: 1.5; white-space: pre-wrap; }
.chat-msg--user .chat-msg__bubble { background: var(--semantic-600); color: #fff; border-bottom-right-radius: 3px; }
.chat-msg--assistant .chat-msg__bubble { background: var(--neutral-100); color: var(--neutral-800); border-bottom-left-radius: 3px; }

.chat-msg__typing { display: flex; gap: 4px; padding: 10px 14px; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--neutral-400); animation: bounce 1.2s infinite; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100% { transform: translateY(0); } 40% { transform: translateY(-4px); } }

.chat-input { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--neutral-100); }
.chat-textarea { flex: 1; padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: 8px; font-size: 13px; resize: none; outline: none; font-family: inherit; }
.chat-textarea:focus { border-color: var(--semantic-500); }
.btn-send { width: 36px; height: 36px; border-radius: 8px; border: none; background: var(--semantic-600); color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; align-self: flex-end; }
.btn-send:hover:not(:disabled) { background: var(--semantic-700); }
.btn-send:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
