<script setup lang="ts">
import { ref, onBeforeUnmount, nextTick, watch } from 'vue'
import { createSseDecoder } from './sseDecoder'
import { skillError } from '../../api/skills'
import { useToast } from '../../composables/useToast'
import { aiCodeApi } from '../../api/aiCode'
import { entityApi } from '../../api/ontology'
import type { ConversationMessage } from '../../api/aiCode'
import type { EntityListItem } from '../../types'

const props = defineProps<{
  visible: boolean
  targetType: 'function' | 'action'
  targetId: string
  contextEntityIds: string[]
  ontologyId?: string | null
  executionMode?: 'expression' | 'sql' | 'python' | 'custom_script'
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
const historyLoading = ref(false)
const applying = ref(false)
const toast = useToast()

let sessionGeneration = 0
let activeRequest: AbortController | null = null
watch(
  () => [props.visible, props.targetType, props.targetId, props.executionMode, props.ontologyId] as const,
  async ([visible]) => {
    const generation = ++sessionGeneration
    activeRequest?.abort()
    activeRequest = null
    generating.value = false
    currentResponse.value = ''
    messages.value = []
    extraEntityIds.value = []
    historyLoading.value = false
    if (!visible || !props.targetId) return
    historyLoading.value = true
    try {
      const [objects, conversation] = await Promise.all([
        entityApi.list({ontology_id:props.ontologyId || undefined}),
        aiCodeApi.getConversation(props.targetType, props.targetId),
      ])
      if (generation !== sessionGeneration) return
      entities.value = objects
      const mode = props.executionMode || (props.targetType === 'action' ? 'custom_script' : 'python')
      messages.value = (conversation?.messages || []).filter(message => !message.execution_mode || message.execution_mode === mode)
      await nextTick()
      scrollToBottom()
    } catch (e) {
      if (generation === sessionGeneration)
        messages.value.push({
          role: 'assistant',
          content: `请求失败：${skillError(e, '历史与上下文加载失败，请关闭后重试')}`,
          timestamp: new Date().toISOString(),
        })
    } finally {
      if (generation === sessionGeneration) historyLoading.value = false
    }
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  sessionGeneration++
  activeRequest?.abort()
})

async function send() {
  const text = inputText.value.trim()
  if (!text || generating.value || historyLoading.value) return

  messages.value.push({ role: 'user', content: text, timestamp: new Date().toISOString() })
  inputText.value = ''
  generating.value = true
  currentResponse.value = ''
  const generation = sessionGeneration
  const controller = new AbortController()
  activeRequest = controller

  try {
    const resp = await aiCodeApi.generatePost(
      {
        target_type: props.targetType,
        target_id: props.targetId,
        execution_mode: props.executionMode,
        message: text,
        extra_entity_ids: [...props.contextEntityIds, ...extraEntityIds.value],
      },
      controller.signal,
    )
    if (generation !== sessionGeneration) return
    if (!resp.ok) throw new Error(`生成请求失败（HTTP ${resp.status}），请重试`)
    const reader = resp.body?.getReader()
    if (!reader) throw new Error('生成响应没有内容，请重试')
    let completed = false
    const stream = createSseDecoder((payload) => {
      if (generation !== sessionGeneration) return
      const parsed = JSON.parse(payload)
      if (parsed.event === 'chunk') currentResponse.value += parsed.content
      else if (parsed.event === 'done') {
        if (typeof parsed.full_code !== 'string' || !parsed.full_code.trim()) throw new Error('模型未生成有效代码，请重试')
        messages.value.push({
          role: 'assistant',
          content: parsed.full_code,
          execution_mode: props.executionMode || (props.targetType === 'action' ? 'custom_script' : 'python'),
          timestamp: new Date().toISOString(),
        })
        currentResponse.value = ''
        completed = true
      } else if (parsed.event === 'error') throw new Error(parsed.message || '生成失败')
    })
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (generation !== sessionGeneration) return
        if (done) break
        stream.push(value)
        await nextTick()
        scrollToBottom()
      }
      stream.finish()
      if (!completed) throw new Error('响应已中断，代码尚未生成完成，请重试')
    } finally {
      reader.releaseLock()
    }
  } catch (e: any) {
    if (e?.name === 'AbortError' || generation !== sessionGeneration) return
    messages.value.push({
      role: 'assistant',
      content: `请求失败：${e.message || '未知错误'}`,
      timestamp: new Date().toISOString(),
    })
    currentResponse.value = ''
  } finally {
    if (activeRequest === controller && generation === sessionGeneration) {
      generating.value = false
      activeRequest = null
    }
  }
}

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function applyCode(code: string) {
  if (applying.value) return
  const generation = sessionGeneration
  applying.value = true
  try {
    const result = await aiCodeApi.validate(code, props.executionMode || (props.targetType === 'action' ? 'custom_script' : 'python'))
    if (generation !== sessionGeneration) return
    if (!result.safe) {
      const reasons = result.violations.map((v) => `行${v.line}: ${v.reason}`).join('\n')
      toast.error(`代码安全检查未通过：${reasons}`)
      return
    }
    emit('apply', code)
  } catch (e) {
    if (generation === sessionGeneration) toast.error(skillError(e, '代码校验失败，请重试'))
  } finally {
    applying.value = false
  }
}
</script>

<template>
  <div v-if="visible" class="ai-code-panel">
    <div class="panel-header">
      <h3>AI 代码生成</h3>
      <button class="close-btn" aria-label="关闭 AI 代码生成" @click="emit('close')">×</button>
    </div>

    <div class="context-bar">
      <span class="label">上下文实体：</span>
      <select multiple aria-label="补充上下文实体" v-model="extraEntityIds" class="entity-select">
        <option v-for="e in entities" :key="e.id" :value="e.id">
          {{ e.name_cn || e.name }}
        </option>
      </select>
    </div>

    <div class="chat-history" ref="chatContainer" aria-live="polite">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        :class="[
          'message',
          msg.role,
          { 'message-error': msg.content.startsWith('错误') || msg.content.startsWith('请求失败') },
        ]"
      >
        <div class="message-content">
          <pre v-if="msg.role === 'assistant'"><code>{{ msg.content }}</code></pre>
          <p v-else>{{ msg.content }}</p>
        </div>
        <button
          v-if="
            msg.role === 'assistant' &&
            !msg.content.startsWith('错误') &&
            !msg.content.startsWith('请求失败')
          "
          class="apply-btn"
          :disabled="applying || generating"
          @click="applyCode(msg.content)"
        >
          应用到编辑器
        </button>
      </div>

      <div v-if="currentResponse" class="message assistant streaming">
        <pre><code>{{ currentResponse }}</code></pre>
      </div>

      <div v-if="historyLoading" class="placeholder" role="status">正在加载历史与上下文…</div>
      <div v-else-if="messages.length === 0 && !generating" class="placeholder">
        描述你想要的逻辑，例如：「根据订单列表计算最近30天的总消费金额」
      </div>
    </div>

    <div class="ai-code-compose">
      <textarea
        v-model="inputText"
        placeholder="描述你的需求..."
        aria-label="代码生成需求"
        @keydown.enter.ctrl="send"
        :disabled="generating || historyLoading"
      />
      <button @click="send" :disabled="generating || historyLoading || !inputText.trim()">
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
  max-width: 95vw;
  height: 100vh;
  background: var(--bg-color, #fff);
  border-left: 1px solid var(--border-color, #e0e0e0);
  display: flex;
  flex-direction: column;
  z-index: 1100;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.1);
}
.panel-header {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}
.panel-header h3 {
  margin: 0;
  font-size: 16px;
}
.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}
.context-bar {
  flex-shrink: 0;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  display: flex;
  align-items: center;
  gap: 8px;
}
.entity-select {
  flex: 1;
  min-width: 0;
  min-height: 32px;
  padding: 6px 8px;
  border: 1px solid var(--neutral-200);
  border-radius: 8px;
  color: var(--neutral-700);
  background: var(--neutral-50);
  font: inherit;
}
.chat-history {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.message {
  margin-bottom: 12px;
}
.message.user p {
  overflow-wrap: anywhere;
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
.message.streaming pre {
  border: 1px solid var(--primary, #1976d2);
}
.message-error pre {
  color: var(--status-error);
  background: var(--status-error-bg, #fef2f2);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
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
.ai-code-compose {
  flex: 0 0 auto;
  align-items: flex-end;
  border-top: 1px solid var(--border-color, #e0e0e0);
  padding: 12px 16px;
  display: flex;
  gap: 8px;
}
.ai-code-compose textarea {
  min-width: 0;
  flex: 1;
  resize: none;
  height: 60px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  padding: 8px;
}
.ai-code-compose button {
  padding: 8px 16px;
  background: var(--primary, #1976d2);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  align-self: flex-end;
}
.ai-code-compose button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
