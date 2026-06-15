<template>
  <div class="guided-builder">
    <!-- 进度条 -->
    <div class="guided-progress">
      <div v-for="(p, i) in phases" :key="p.key" class="guided-progress__item" :class="{ 'guided-progress__item--active': phaseIndex >= i, 'guided-progress__item--current': phaseIndex === i }">
        <span class="guided-progress__dot">{{ phaseIndex > i ? '✓' : i + 1 }}</span>
        <span class="guided-progress__label">{{ p.label }}</span>
      </div>
      <div class="guided-progress__bar">
        <div class="guided-progress__fill" :style="{ width: `${(phaseIndex / (phases.length - 1)) * 100}%` }"></div>
      </div>
    </div>

    <div class="guided-body">
      <!-- 左侧：对话区 -->
      <div class="guided-chat">
        <div class="guided-chat__messages" ref="messagesRef">
          <div v-for="(msg, i) in messages" :key="i" class="chat-msg" :class="`chat-msg--${msg.role}`">
            <div class="chat-msg__avatar">
              <span v-if="msg.role === 'ai'">🤖</span>
              <span v-else>👤</span>
            </div>
            <div class="chat-msg__body">
              <div class="chat-msg__content" v-html="renderMarkdown(msg.content)"></div>
              <!-- 文件标签 -->
              <div v-if="msg.files && msg.files.length" class="chat-msg__files">
                <span v-for="f in msg.files" :key="f" class="file-tag">📎 {{ f }}</span>
              </div>
            </div>
          </div>

          <!-- 加载指示 -->
          <div v-if="loading" class="chat-msg chat-msg--ai">
            <div class="chat-msg__avatar"><span>🤖</span></div>
            <div class="chat-msg__body">
              <div class="chat-msg__typing">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
            </div>
          </div>

          <!-- 构建进度 -->
          <div v-if="buildProgress" class="build-progress-card">
            <div class="build-progress-card__step">{{ buildProgress.step }}</div>
            <div class="build-progress-card__bar">
              <div class="build-progress-card__fill" :style="{ width: `${buildProgress.progress}%` }"></div>
            </div>
          </div>
        </div>

        <!-- 快捷建议按钮 -->
        <div v-if="suggestions.length && !loading" class="guided-suggestions">
          <button v-for="s in suggestions" :key="s.value" class="suggestion-btn" :class="{ 'suggestion-btn--required': s.required }" @click="handleSuggestion(s)">
            {{ s.label }}
          </button>
        </div>

        <!-- 输入区 -->
        <div class="guided-input">
          <div class="guided-input__row">
            <textarea v-model="userInput" class="guided-input__text" :placeholder="inputPlaceholder" rows="2" @keydown.enter.exact.prevent="handleSend" :disabled="loading || currentPhase === 'building'"></textarea>
            <button class="guided-input__upload" @click="fileInputRef?.click()" :disabled="loading" title="上传文件">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M9 3v9M6 6l3-3 3 3M3 13v2a1 1 0 001 1h10a1 1 0 001-1v-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <button class="guided-input__send" @click="handleSend" :disabled="loading || (!userInput.trim() && !pendingFiles.length)">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M3 9l12-6-4 6 4 6-12-6z" fill="currentColor"/></svg>
            </button>
          </div>
          <!-- 待上传文件列表 -->
          <div v-if="pendingFiles.length" class="guided-input__files">
            <span v-for="(f, i) in pendingFiles" :key="i" class="file-tag file-tag--pending">
              📎 {{ f.name }}
              <button class="file-tag__remove" @click="pendingFiles.splice(i, 1)">×</button>
            </span>
          </div>
          <input ref="fileInputRef" type="file" multiple accept=".txt,.md,.csv,.json,.doc,.docx,.pdf,.xls,.xlsx,.sql" class="hidden-input" @change="onFileSelect" />
        </div>
      </div>

      <!-- 右侧：预览区 -->
      <div class="guided-preview">
        <div class="guided-preview__header">
          <span class="panel-title">构建预览</span>
        </div>

        <!-- 收集信息摘要 -->
        <div class="preview-section" v-if="currentPhase !== 'done'">
          <div class="preview-item" v-if="sessionData.scenario">
            <span class="preview-item__label">场景</span>
            <span class="preview-item__value">{{ sessionData.scenario }}</span>
          </div>
          <div class="preview-item" v-if="sessionData.materials_count > 0">
            <span class="preview-item__label">材料</span>
            <span class="preview-item__value">{{ sessionData.materials_count }} 份已提供</span>
          </div>
          <div class="preview-item" v-if="sessionData.clarify_count > 0">
            <span class="preview-item__label">补充</span>
            <span class="preview-item__value">{{ sessionData.clarify_count }} 个问题已回答</span>
          </div>
        </div>

        <!-- 构建结果预览 -->
        <div class="preview-section" v-if="buildResult">
          <div class="preview-stats">
            <span class="stat-badge stat-badge--blue">{{ buildResult.entities.length }} 个实体</span>
            <span class="stat-badge stat-badge--green">{{ totalAttrs }} 个属性</span>
            <span class="stat-badge stat-badge--amber">{{ buildResult.relations.length }} 个关系</span>
          </div>
          <div class="preview-entity-list">
            <div v-for="entity in buildResult.entities" :key="entity.name" class="preview-entity">
              <span class="tier-dot" :class="`tier-dot--t${entity.tier}`">T{{ entity.tier }}</span>
              <span class="preview-entity__name">{{ entity.name_cn }}</span>
              <span class="preview-entity__en">{{ entity.name }}</span>
              <span class="preview-entity__attrs">{{ entity.attributes?.length || 0 }} 属性</span>
            </div>
          </div>
        </div>

        <!-- 冲突警告 -->
        <div class="preview-section" v-if="conflicts.length">
          <div class="conflict-title">⚠️ 冲突检测</div>
          <div v-for="c in conflicts" :key="c.entity_name" class="conflict-item">
            <span>{{ c.entity_name_cn }}（{{ c.entity_name }}）</span>
            <span class="conflict-msg">{{ c.message }}</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="preview-actions" v-if="buildResult">
          <button class="btn-primary" @click="$emit('complete', buildResult)">确认，进入编辑 →</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import { renderMarkdownSafe } from '@/utils/sanitize'
import { aiOntologyApi, type AiOntologyEvent } from '../../api/aiOntology'

const emit = defineEmits<{ complete: [result: { entities: any[]; relations: any[] }] }>()

interface ChatMessage {
  role: 'ai' | 'user'
  content: string
  files?: string[]
}

const phases = [
  { key: 'scenario', label: '场景识别' },
  { key: 'materials', label: '素材收集' },
  { key: 'clarify', label: '业务确认' },
  { key: 'building', label: '自动构建' },
]

const messages = ref<ChatMessage[]>([])
const userInput = ref('')
const loading = ref(false)
const pendingFiles = ref<File[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)
const messagesRef = ref<HTMLElement | null>(null)
const suggestions = ref<Array<{ label: string; value: string; required?: boolean }>>([])
const buildProgress = ref<{ step: string; progress: number } | null>(null)
const buildResult = ref<{ entities: any[]; relations: any[] } | null>(null)
const conflicts = ref<Array<{ entity_name: string; entity_name_cn: string; type: string; message: string }>>([])

const sessionId = ref('')
const currentPhase = ref<string>('scenario')
const sessionData = ref({ scenario: '', materials_count: 0, clarify_count: 0 })

const phaseIndex = computed(() => {
  const idx = phases.findIndex(p => p.key === currentPhase.value)
  return idx >= 0 ? idx : 0
})

const totalAttrs = computed(() =>
  buildResult.value?.entities.reduce((s, e) => s + (e.attributes?.length || 0), 0) ?? 0
)

const inputPlaceholder = computed(() => {
  switch (currentPhase.value) {
    case 'scenario': return '描述您要构建的业务场景...'
    case 'materials': return '补充描述业务情况，或上传文件...'
    case 'clarify': return '回答业务问题...'
    default: return '输入消息...'
  }
})

function renderMarkdown(text: string): string {
  return renderMarkdownSafe(text)
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    pendingFiles.value.push(...Array.from(input.files))
  }
  input.value = ''
}

async function initSession() {
  try {
    const session = await aiOntologyApi.createSession()
    sessionId.value = session.id
    messages.value.push({
      role: 'ai',
      content: '您好！我是本体建模助手。请问您要构建哪个业务场景的本体？\n\n可以选择下方常见场景，或直接描述您的业务需求。',
    })
    suggestions.value = [
      { label: '宽带退单稽核', value: '宽带退单稽核' },
      { label: '携号转网预警', value: '携号转网预警' },
      { label: '政企故障分析', value: '政企故障分析' },
      { label: '客户价值分析', value: '客户价值分析' },
      { label: '网络质量优化', value: '网络质量优化' },
    ]
  } catch (err) {
    messages.value.push({ role: 'ai', content: '会话初始化失败，请刷新重试。' })
  }
}

function handleSuggestion(s: { label: string; value: string }) {
  if (s.value === '__skip__') {
    userInput.value = '不确定，跳过'
    handleSend()
  } else if (s.value === '__build__') {
    triggerBuild()
  } else {
    userInput.value = s.value
    handleSend()
  }
}

async function handleSend() {
  const text = userInput.value.trim()
  const files = [...pendingFiles.value]
  if (!text && !files.length) return

  messages.value.push({
    role: 'user',
    content: text || `上传了 ${files.length} 个文件`,
    files: files.map(f => f.name),
  })
  userInput.value = ''
  pendingFiles.value = []
  suggestions.value = []
  loading.value = true
  scrollToBottom()

  aiOntologyApi.sendMessage(sessionId.value, text, files, handleEvent, handleError)
}

function triggerBuild() {
  suggestions.value = []
  loading.value = true
  messages.value.push({ role: 'user', content: '材料够了，直接构建' })
  scrollToBottom()
  aiOntologyApi.triggerBuild(sessionId.value, handleEvent, handleError)
}

function handleEvent(event: AiOntologyEvent) {
  switch (event.type) {
    case 'message':
      if (messages.value.length && messages.value[messages.value.length - 1].content.startsWith('⏳')) {
        messages.value.pop()
      }
      if (event.content) {
        messages.value.push({ role: 'ai', content: event.content })
        scrollToBottom()
      }
      if (event.done) loading.value = false
      break
    case 'phase_change':
      if (event.phase) {
        currentPhase.value = event.phase
        if (event.phase === 'materials') sessionData.value.scenario = messages.value.filter(m => m.role === 'user')[0]?.content || ''
      }
      break
    case 'thinking':
      loading.value = true
      messages.value.push({ role: 'ai', content: `⏳ ${event.content || '思考中...'}` })
      scrollToBottom()
      break
    case 'suggestion':
      if (event.suggestions) suggestions.value = event.suggestions
      loading.value = false
      break
    case 'build_progress':
      buildProgress.value = { step: event.step || '', progress: event.progress || 0 }
      scrollToBottom()
      break
    case 'build_result':
      buildProgress.value = null
      loading.value = false
      if (event.result) buildResult.value = event.result
      if (event.conflicts) conflicts.value = event.conflicts
      if (event.summary) {
        sessionData.value.materials_count = sessionData.value.materials_count || 0
      }
      currentPhase.value = 'done'
      messages.value.push({
        role: 'ai',
        content: `本体构建完成！共生成 **${event.summary?.entity_count || 0}** 个实体、**${event.summary?.attr_count || 0}** 个属性、**${event.summary?.relation_count || 0}** 个关系。\n\n请在右侧预览确认，点击"确认，进入编辑"进行微调。`,
      })
      scrollToBottom()
      break
    case 'error':
      loading.value = false
      messages.value.push({ role: 'ai', content: `❌ ${event.content || '发生错误，请重试'}` })
      scrollToBottom()
      break
  }
}

function handleError(err: Error) {
  loading.value = false
  messages.value.push({ role: 'ai', content: `❌ 请求失败：${err.message}` })
  scrollToBottom()
}

onMounted(initSession)
</script>

<style scoped>
.guided-builder {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

/* 进度条 */
.guided-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--surface-secondary, #f8f9fa);
  border-radius: 8px;
  position: relative;
}
.guided-progress__item {
  display: flex;
  align-items: center;
  gap: 6px;
  z-index: 1;
  flex: 1;
}
.guided-progress__dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  background: var(--neutral-200, #e5e7eb);
  color: var(--neutral-500, #6b7280);
  transition: all 0.3s;
}
.guided-progress__item--active .guided-progress__dot {
  background: var(--semantic-600, #4f46e5);
  color: #fff;
}
.guided-progress__item--current .guided-progress__dot {
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2);
}
.guided-progress__label {
  font-size: 12px;
  color: var(--neutral-500, #6b7280);
}
.guided-progress__item--active .guided-progress__label {
  color: var(--neutral-800, #1f2937);
  font-weight: 500;
}
.guided-progress__bar {
  position: absolute;
  left: 40px;
  right: 40px;
  top: 50%;
  height: 2px;
  background: var(--neutral-200, #e5e7eb);
  z-index: 0;
}
.guided-progress__fill {
  height: 100%;
  background: var(--semantic-600, #4f46e5);
  transition: width 0.5s ease;
}

/* 主体布局 */
.guided-body {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* 对话区 */
.guided-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
}
.guided-chat__messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 消息气泡 */
.chat-msg {
  display: flex;
  gap: 8px;
  max-width: 85%;
}
.chat-msg--user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.chat-msg__avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  background: var(--neutral-100, #f3f4f6);
}
.chat-msg--user .chat-msg__avatar {
  background: var(--semantic-100, #eef2ff);
}
.chat-msg__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.chat-msg__content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  background: var(--neutral-100, #f3f4f6);
  color: var(--neutral-800, #1f2937);
}
.chat-msg__content :deep(p) { margin: 0 0 8px; }
.chat-msg__content :deep(p:last-child) { margin: 0; }
.chat-msg__content :deep(ul), .chat-msg__content :deep(ol) { margin: 4px 0; padding-left: 18px; }
.chat-msg__content :deep(strong) { font-weight: 600; }
.chat-msg--user .chat-msg__content {
  background: var(--semantic-600, #4f46e5);
  color: #fff;
}
.chat-msg__files {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.chat-msg__typing {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
  background: var(--neutral-100, #f3f4f6);
  border-radius: 12px;
}
.chat-msg__typing .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--neutral-400, #9ca3af);
  animation: typing 1.2s infinite;
}
.chat-msg__typing .dot:nth-child(2) { animation-delay: 0.2s; }
.chat-msg__typing .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-3px); }
}

/* 文件标签 */
.file-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  background: var(--neutral-100, #f3f4f6);
  color: var(--neutral-600, #4b5563);
}
.file-tag--pending {
  background: var(--semantic-50, #eef2ff);
  border: 1px solid var(--semantic-200, #c7d2fe);
}
.file-tag__remove {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--neutral-400);
  padding: 0 2px;
}

/* 构建进度卡片 */
.build-progress-card {
  padding: 12px 16px;
  background: var(--semantic-50, #eef2ff);
  border-radius: 8px;
  border: 1px solid var(--semantic-200, #c7d2fe);
}
.build-progress-card__step {
  font-size: 12px;
  font-weight: 500;
  color: var(--semantic-700, #4338ca);
  margin-bottom: 8px;
}
.build-progress-card__bar {
  height: 4px;
  background: var(--semantic-100, #e0e7ff);
  border-radius: 2px;
  overflow: hidden;
}
.build-progress-card__fill {
  height: 100%;
  background: var(--semantic-600, #4f46e5);
  transition: width 0.5s ease;
}

/* 快捷建议 */
.guided-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 16px;
  border-top: 1px solid var(--neutral-100, #f3f4f6);
}
.suggestion-btn {
  padding: 5px 12px;
  border-radius: 16px;
  border: 1px solid var(--neutral-200, #e5e7eb);
  background: #fff;
  font-size: 12px;
  color: var(--neutral-700, #374151);
  cursor: pointer;
  transition: all 0.15s;
}
.suggestion-btn:hover {
  border-color: var(--semantic-400, #818cf8);
  color: var(--semantic-600, #4f46e5);
  background: var(--semantic-50, #eef2ff);
}
.suggestion-btn--required {
  border-color: var(--semantic-300, #a5b4fc);
  background: var(--semantic-50, #eef2ff);
}

/* 输入区 */
.guided-input {
  padding: 10px 12px;
  border-top: 1px solid var(--neutral-200, #e5e7eb);
  background: #fff;
}
.guided-input__row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.guided-input__text {
  flex: 1;
  resize: none;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1.5;
  outline: none;
  transition: border-color 0.15s;
}
.guided-input__text:focus {
  border-color: var(--semantic-400, #818cf8);
}
.guided-input__upload,
.guided-input__send {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--neutral-200, #e5e7eb);
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--neutral-500, #6b7280);
  transition: all 0.15s;
}
.guided-input__upload:hover,
.guided-input__send:hover {
  border-color: var(--semantic-400, #818cf8);
  color: var(--semantic-600, #4f46e5);
}
.guided-input__send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.guided-input__files {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}
.hidden-input {
  display: none;
}

/* 预览区 */
.guided-preview {
  width: 280px;
  flex-shrink: 0;
  border: 1px solid var(--neutral-200, #e5e7eb);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.guided-preview__header {
  padding: 12px 14px;
  border-bottom: 1px solid var(--neutral-100, #f3f4f6);
}
.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-800, #1f2937);
}
.preview-section {
  padding: 12px 14px;
  border-bottom: 1px solid var(--neutral-50, #f9fafb);
}
.preview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}
.preview-item__label {
  font-size: 12px;
  color: var(--neutral-500, #6b7280);
}
.preview-item__value {
  font-size: 12px;
  font-weight: 500;
  color: var(--neutral-800, #1f2937);
}

/* 构建结果预览 */
.preview-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.stat-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.stat-badge--blue { background: #dbeafe; color: #1d4ed8; }
.stat-badge--green { background: #dcfce7; color: #15803d; }
.stat-badge--amber { background: #fef3c7; color: #b45309; }

.preview-entity-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 300px;
  overflow-y: auto;
}
.preview-entity {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.preview-entity:hover { background: var(--neutral-50, #f9fafb); }
.preview-entity__name { font-weight: 500; color: var(--neutral-800); }
.preview-entity__en { color: var(--neutral-400); font-size: 11px; }
.preview-entity__attrs { margin-left: auto; color: var(--neutral-400); font-size: 11px; }

.tier-dot {
  width: 20px;
  height: 16px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
}
.tier-dot--t1 { background: var(--tier1-bg, #fef3c7); color: var(--tier1-text, #b45309); }
.tier-dot--t2 { background: var(--tier2-bg, #dbeafe); color: var(--tier2-text, #1d4ed8); }
.tier-dot--t3 { background: var(--tier3-bg, #dcfce7); color: var(--tier3-text, #15803d); }

/* 冲突警告 */
.conflict-title {
  font-size: 12px;
  font-weight: 600;
  color: #b45309;
  margin-bottom: 6px;
}
.conflict-item {
  font-size: 11px;
  padding: 4px 0;
  color: var(--neutral-600);
  border-bottom: 1px dashed var(--neutral-100);
}
.conflict-msg {
  display: block;
  color: #b45309;
  font-size: 11px;
}

/* 操作按钮 */
.preview-actions {
  padding: 12px 14px;
  margin-top: auto;
}
.btn-primary {
  width: 100%;
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  background: var(--semantic-600, #4f46e5);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover { background: var(--semantic-700, #4338ca); }
</style>
