<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { aiCodeApi } from '../../api/aiCode'
import { entityApi } from '../../api/ontology'
import type { ConversationMessage } from '../../api/aiCode'
import type { EntityListItem } from '../../types'

const props = defineProps<{
  visible: boolean
  targetType: 'function' | 'action'
  targetId: string
  contextEntityIds: string[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'apply', code: string): void
}>()

const messages = ref<ConversationMessage[]>([])
const inputText = ref('')
const generating = ref(false)
const currentResponse = ref('')
const chatContainer = ref<HTMLElement | null>(null)
const entities = ref<EntityListItem[]>([])
const extraEntityIds = ref<string[]>([])

watch(() => props.visible, async (v) => {
  if (v) {
    entities.value = await entityApi.list()
    await loadHistory()
  }
})

onMounted(async () => {
  if (props.visible) {
    entities.value = await entityApi.list()
    await loadHistory()
  }
})

async function loadHistory() {
  if (!props.targetId) return
  const conv = await aiCodeApi.getConversation(props.targetType, props.targetId)
  if (conv && conv.messages) {
    messages.value = conv.messages
  }
}

async function send() {
  const text = inputText.value.trim()
  if (!text || generating.value) return

  messages.value.push({ role: 'user', content: text, timestamp: new Date().toISOString() })
  inputText.value = ''
  generating.value = true
  currentResponse.value = ''

  try {
    const resp = await aiCodeApi.generatePost({
      target_type: props.targetType,
      target_id: props.targetId,
      message: text,
      extra_entity_ids: [...props.contextEntityIds, ...extraEntityIds.value],
    })

    const reader = resp.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) return

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6)
        try {
          const parsed = JSON.parse(payload)
          if (parsed.event === 'chunk') {
            currentResponse.value += parsed.content
          } else if (parsed.event === 'done') {
            messages.value.push({
              role: 'assistant',
              content: parsed.full_code,
              timestamp: new Date().toISOString(),
            })
            currentResponse.value = ''
          } else if (parsed.event === 'error') {
            messages.value.push({
              role: 'assistant',
              content: `错误：${parsed.message}`,
              timestamp: new Date().toISOString(),
            })
          }
        } catch (e) { console.warn('AI 响应解析失败,已跳过', e) }
      }
      await nextTick()
      scrollToBottom()
    }
  } catch (e: any) {
    messages.value.push({
      role: 'assistant',
      content: `请求失败：${e.message || '未知错误'}`,
      timestamp: new Date().toISOString(),
    })
  } finally {
    generating.value = false
  }
}

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function applyCode(code: string) {
  const result = await aiCodeApi.validate(code)
  if (!result.safe) {
    const reasons = result.violations.map(v => `行${v.line}: ${v.reason}`).join('\n')
    alert(`代码安全检查未通过：\n${reasons}`)
    return
  }
  emit('apply', code)
}
</script>

<template>
  <div v-if="visible" class="ai-code-panel">
    <div class="panel-header">
      <h3>AI 代码生成</h3>
      <button class="close-btn" @click="emit('close')">×</button>
    </div>

    <div class="context-bar">
      <span class="label">上下文实体：</span>
      <select multiple v-model="extraEntityIds" class="entity-select">
        <option v-for="e in entities" :key="e.id" :value="e.id">
          {{ e.name_cn || e.name }}
        </option>
      </select>
    </div>

    <div class="chat-history" ref="chatContainer">
      <div v-for="(msg, i) in messages" :key="i" :class="['message', msg.role]">
        <div class="message-content">
          <pre v-if="msg.role === 'assistant'"><code>{{ msg.content }}</code></pre>
          <p v-else>{{ msg.content }}</p>
        </div>
        <button
          v-if="msg.role === 'assistant' && !msg.content.startsWith('错误') && !msg.content.startsWith('请求失败')"
          class="apply-btn"
          @click="applyCode(msg.content)"
        >
          应用到编辑器
        </button>
      </div>

      <div v-if="currentResponse" class="message assistant streaming">
        <pre><code>{{ currentResponse }}</code></pre>
      </div>

      <div v-if="messages.length === 0 && !generating" class="placeholder">
        描述你想要的逻辑，例如：「根据订单列表计算最近30天的总消费金额」
      </div>
    </div>

    <div class="chat-input">
      <textarea
        v-model="inputText"
        placeholder="描述你的需求..."
        @keydown.enter.ctrl="send"
        :disabled="generating"
      />
      <button @click="send" :disabled="generating || !inputText.trim()">
        {{ generating ? '生成中...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.ai-code-panel {
  position: fixed;
  right: 0;
  top: 0;
  width: 480px;
  height: 100vh;
  background: var(--bg-color, #fff);
  border-left: 1px solid var(--border-color, #e0e0e0);
  display: flex;
  flex-direction: column;
  z-index: 1000;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.1);
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}
.panel-header h3 { margin: 0; font-size: 16px; }
.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}
.context-bar {
  padding: 8px 16px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  display: flex;
  align-items: center;
  gap: 8px;
}
.entity-select { flex: 1; min-height: 32px; }
.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.message { margin-bottom: 12px; }
.message.user p {
  background: var(--primary-light, #e3f2fd);
  padding: 8px 12px;
  border-radius: 8px;
  display: inline-block;
}
.message.assistant pre {
  background: var(--code-bg, #f5f5f5);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
}
.message.streaming pre { border: 1px solid var(--primary, #1976d2); }
.apply-btn {
  margin-top: 4px;
  font-size: 12px;
  padding: 4px 8px;
  background: var(--primary, #1976d2);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.placeholder {
  color: var(--text-secondary, #666);
  text-align: center;
  padding: 40px 20px;
}
.chat-input {
  border-top: 1px solid var(--border-color, #e0e0e0);
  padding: 12px 16px;
  display: flex;
  gap: 8px;
}
.chat-input textarea {
  flex: 1;
  resize: none;
  height: 60px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  padding: 8px;
}
.chat-input button {
  padding: 8px 16px;
  background: var(--primary, #1976d2);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  align-self: flex-end;
}
.chat-input button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
