<template>
  <div class="step1">
    <!-- 左侧：Copilot 对话栏 -->
    <aside class="step1-chat">
      <div class="copilot-header">
        <div class="copilot-avatar">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="url(#cop-grad)" />
            <path d="M8 10s.6 1 2 1 2-1 2-1M14 10s.6 1 2 1 2-1 2-1" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M8 15s1 2 4 2 4-2 4-2" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
            <defs>
              <linearGradient id="cop-grad" x1="0" y1="0" x2="24" y2="24">
                <stop offset="0%" stop-color="#6366f1"/>
                <stop offset="100%" stop-color="#8b5cf6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div class="copilot-meta">
          <div class="copilot-name">场景 Copilot</div>
          <div class="copilot-sub">场景识别 · 资产匹配 · 本体构建</div>
        </div>
      </div>

      <div class="step1-messages" ref="msgsRef">
        <div
          v-for="m in messages"
          :key="m.id"
          class="msg-row"
          :class="`msg-row--${m.role}`"
        >
          <div class="msg-avatar">{{ m.role === 'user' ? 'U' : 'AI' }}</div>
          <div class="msg-bubble">
            <div v-if="m.thinkingSeconds != null" class="msg-thinking-badge">
              ✓ 已思考完成（{{ m.thinkingSeconds }} 秒）
            </div>
            <div class="msg-content" v-text="m.content"></div>
            <div v-if="m.note" class="msg-note">💡 {{ m.note }}</div>
          </div>
        </div>

        <!-- 思考中 -->
        <div v-if="phase === 'scene_analyzing'" class="msg-row msg-row--assistant">
          <div class="msg-avatar">AI</div>
          <div class="msg-bubble">
            <div class="thinking-dots"><span /><span /><span /></div>
            <div class="msg-thinking-text">正在分析你的业务场景（{{ elapsedSec }}秒）...</div>
          </div>
        </div>

        <!-- 用户故事面板 -->
        <UserStoriesPanel
          v-if="phase === 'story_split' || phase === 'asset_scanning' || phase === 'assets_ready' || phase === 'graph_building' || phase === 'graph_done'"
          :stories="userStories"
          :readonly="phase !== 'story_split'"
          @toggle="onToggleStory"
          @confirm="onConfirmStories"
        />

        <!-- 资产扫描进度 -->
        <AssetScanProgress
          v-if="phase === 'asset_scanning'"
          :active-step="scanActiveStep"
        />

        <!-- 网络构建动画 -->
        <div v-if="phase === 'graph_building'" class="msg-row msg-row--assistant">
          <div class="msg-avatar">AI</div>
          <div class="msg-bubble">
            <div class="msg-thinking-text">{{ graphPhaseLabel }}</div>
            <div class="thinking-dots"><span /><span /><span /></div>
          </div>
        </div>
      </div>

      <div class="step1-input-bar">
        <div v-if="attachments.length" class="step1-attachment-strip">
          <div v-for="a in attachments" :key="a.id" class="step1-attachment-card">
            <span class="att-icon">{{ a.fileType.charAt(0) }}</span>
            <div class="att-info">
              <div class="att-name">{{ a.fileName }}</div>
              <div class="att-meta">{{ a.fileType }} · {{ a.fileSize }} · {{ attStatus(a.status) }}</div>
            </div>
            <button class="att-close" @click="removeAttachment(a.id)">×</button>
          </div>
        </div>

        <div class="step1-input-row">
          <button class="step1-attach-btn" @click="fileInput?.click()">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 3v12M3 9h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </button>
          <input ref="fileInput" type="file" class="hidden-file" multiple @change="onFiles" />
          <a-textarea
            v-model:value="currentInput"
            class="chat-input"
            :placeholder="placeholder"
            :auto-size="{ minRows: 1, maxRows: 4 }"
            :bordered="false"
            @keydown.enter.exact.prevent="onSend"
          />
          <button class="send-btn" :disabled="!currentInput.trim()" @click="onSend">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M2 9l14-6-6 14-2-6-6-2z" fill="currentColor"/>
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- 中间：资产面板 -->
    <section class="step1-assets" v-if="phase === 'assets_ready' || phase === 'graph_building' || phase === 'graph_done'">
      <AssetsPanel
        :assets="assets"
        @toggle-subscribe="onToggleSubscribe"
        @start-graph="startGraphBuilding"
        :graph-ready="phase !== 'assets_ready'"
        :selected-count="subscribedAssets.length"
      />
    </section>

    <!-- 右侧：语义网络画布 -->
    <section class="step1-graph">
      <SemanticCanvas
        :objects="draftObjects"
        :relations="draftRelations"
        :phase="phase"
        :graph-phase-label="graphPhaseLabel"
        :placeholder-message="canvasPlaceholder"
        @add="addObject"
        @delete="deleteObject"
      />

      <div class="step1-graph-actions">
        <a-button
          v-if="phase === 'graph_done' || draftObjects.length > 0"
          type="primary"
          size="large"
          @click="confirmAll"
        >
          确认本体并进入走测 →
        </a-button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore, buildPresetClasses, buildPresetRelations } from '../../../store/builder'
import {
  SCENARIO_PLACEHOLDERS,
  SCENARIO_WELCOME,
  SCENARIO_STORIES,
  SCENARIO_ASSETS,
  SCAN_STEPS,
  GRAPH_BUILDING_STEPS,
} from '../../../data/builderPresets'
import type {
  BuilderSession,
  CopilotMessage,
  CopilotAttachment,
  UserStory,
  DataAsset,
  Step1Phase,
  OntologyClassDraft,
  OntologyRelationDraft,
} from '../../../types/builder'
import UserStoriesPanel from './copilot/UserStoriesPanel.vue'
import AssetScanProgress from './copilot/AssetScanProgress.vue'
import AssetsPanel from './copilot/AssetsPanel.vue'
import SemanticCanvas from './graph/SemanticCanvas.vue'

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'next'): void }>()
const store = useBuilderStore()

const phase = ref<Step1Phase>('idle')
const messages = ref<CopilotMessage[]>([])
const currentInput = ref('')
const attachments = ref<CopilotAttachment[]>([])
const userStories = ref<UserStory[]>([])
const assets = ref<DataAsset[]>([])
const scanActiveStep = ref(0)
const draftObjects = ref<OntologyClassDraft[]>([])
const draftRelations = ref<OntologyRelationDraft[]>([])
const graphPhaseLabel = ref(GRAPH_BUILDING_STEPS[0])
const elapsedSec = ref(0)
const msgsRef = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const placeholder = computed(() => SCENARIO_PLACEHOLDERS[props.session.scenarioId] || '描述你的业务场景，AI 将辅助构建本体...')
const subscribedAssets = computed(() => assets.value.filter(a => a.subscribed))
const canvasPlaceholder = computed(() => {
  if (phase.value === 'idle' || phase.value === 'scene_analyzing' || phase.value === 'scene_confirm') return '等待场景识别完成'
  if (phase.value === 'story_split') return '请确认用户故事，再开始资产扫描'
  if (phase.value === 'asset_scanning') return '资产扫描中，请稍候...'
  if (phase.value === 'assets_ready') return '已识别 ' + subscribedAssets.value.length + ' 个资产 · 点击下方"一键生成画布"进行本体构建'
  if (phase.value === 'graph_building') return graphPhaseLabel.value
  return ''
})

onMounted(() => {
  if (props.session.ontologyClasses.length > 0) {
    draftObjects.value = [...props.session.ontologyClasses]
    draftRelations.value = [...props.session.ontologyRelations]
    phase.value = 'graph_done'
  } else {
    addAssistantMessage(SCENARIO_WELCOME[props.session.scenarioId] || SCENARIO_WELCOME['refund-root-cause'])
  }
})

function addAssistantMessage(content: string, opts: { thinkingSeconds?: number; note?: string } = {}) {
  messages.value.push({
    id: 'msg-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
    role: 'assistant',
    content,
    thinkingSeconds: opts.thinkingSeconds,
    note: opts.note,
    createdAt: new Date().toISOString(),
  })
  scrollBottom()
}
function addUserMessage(content: string) {
  messages.value.push({
    id: 'msg-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
    role: 'user', content, createdAt: new Date().toISOString(),
  })
  scrollBottom()
}
function scrollBottom() {
  nextTick(() => {
    if (msgsRef.value) msgsRef.value.scrollTop = msgsRef.value.scrollHeight
  })
}

function attStatus(s: string) {
  return s === 'pending' ? '待发送' : s === 'parsing' ? 'AI 解析中...' : '已解析'
}

function onSend() {
  if (!currentInput.value.trim()) return
  const text = currentInput.value.trim()
  addUserMessage(text)
  currentInput.value = ''
  if (phase.value === 'idle') startSceneAnalysis()
}

function onFiles(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  for (const file of Array.from(input.files)) {
    const ext = (file.name.split('.').pop() || '').toUpperCase()
    const att: CopilotAttachment = {
      id: 'att-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
      fileName: file.name,
      fileType: ext || 'FILE',
      fileSize: (file.size / 1024 / 1024).toFixed(2) + ' MB',
      status: 'pending',
      mimeCategory: file.type.startsWith('image') ? 'image' :
        ['xls', 'xlsx', 'csv', 'json'].includes(ext.toLowerCase()) ? 'structured' : 'unstructured',
    }
    attachments.value.push(att)
    setTimeout(() => updateAttachmentStatus(att.id, 'parsing'), 300)
    setTimeout(() => updateAttachmentStatus(att.id, 'parsed'), 1800)
    store.addUploadRecord({
      fileName: file.name,
      fileType: ext || 'FILE',
      fileSize: (file.size / 1024).toFixed(0) + ' KB',
      sourceOntology: props.session.ontologyName,
      scenarioName: props.session.scenarioName,
      status: 'parsing',
      statusText: 'AI 解析中...',
      extractedSummary: '正在抽取规则与字段',
      extractedRules: 0,
      extractedFields: 0,
      mimeCategory: att.mimeCategory,
    })
  }
  input.value = ''
}
function updateAttachmentStatus(id: string, status: 'pending' | 'parsing' | 'parsed') {
  const a = attachments.value.find(x => x.id === id)
  if (a) a.status = status
}
function removeAttachment(id: string) {
  attachments.value = attachments.value.filter(a => a.id !== id)
}

async function startSceneAnalysis() {
  phase.value = 'scene_analyzing'
  elapsedSec.value = 0
  const t = setInterval(() => elapsedSec.value++, 1000)
  await new Promise(r => setTimeout(r, 2400))
  clearInterval(t)
  phase.value = 'scene_confirm'

  const stories = (SCENARIO_STORIES[props.session.scenarioId] || SCENARIO_STORIES['refund-root-cause']).map((s, i) => ({
    id: 'story-' + i,
    asRole: s.asRole,
    iWant: s.iWant,
    soThat: s.soThat,
    keywords: s.keywords,
    confirmed: false,
  }))
  userStories.value = stories
  addAssistantMessage(
    `好的，我已理解你的需求。基于场景分析，我为你拆解了 ${stories.length} 个用户故事，请逐个确认后开始查找匹配资产。`,
    { thinkingSeconds: elapsedSec.value, note: '点击下方故事卡进行确认，全部确认后即可开启资产扫描' },
  )
  phase.value = 'story_split'
}

function onToggleStory(id: string) {
  const s = userStories.value.find(s => s.id === id)
  if (s) s.confirmed = !s.confirmed
}
async function onConfirmStories() {
  const confirmed = userStories.value.filter(s => s.confirmed).length
  if (confirmed === 0) {
    message.warning('请至少确认 1 个用户故事')
    return
  }
  userStories.value.forEach(s => (s.confirmed = true))
  phase.value = 'asset_scanning'
  scanActiveStep.value = 0
  for (let i = 0; i < SCAN_STEPS.length; i++) {
    scanActiveStep.value = i
    await new Promise(r => setTimeout(r, 700))
  }
  assets.value = (SCENARIO_ASSETS[props.session.scenarioId] || SCENARIO_ASSETS['refund-root-cause']).map(a => ({ ...a }))
  const sCount = assets.value.filter(a => a.category === 'structured').length
  const uCount = assets.value.length - sCount
  addAssistantMessage(
    `资产清单组装完成，共 ${assets.value.length} 个资产（${sCount} 结构化 + ${uCount} 非结构化）。请勾选要纳入本体的资产，然后点击右侧"⚡ 一键生成画布"。`,
    { note: '资产将映射到本体的 T-box / R-box / A-box 三盒结构' },
  )
  phase.value = 'assets_ready'
  // 默认订阅前 4 个
  assets.value.slice(0, 4).forEach(a => (a.subscribed = true))
}

function onToggleSubscribe(id: string) {
  const a = assets.value.find(x => x.id === id)
  if (a) a.subscribed = !a.subscribed
}

async function startGraphBuilding() {
  if (subscribedAssets.value.length === 0) {
    message.warning('请至少订阅 1 个资产再生成画布')
    return
  }
  phase.value = 'graph_building'
  for (let i = 0; i < GRAPH_BUILDING_STEPS.length; i++) {
    graphPhaseLabel.value = GRAPH_BUILDING_STEPS[i]
    await new Promise(r => setTimeout(r, 800))
  }
  // 生成预设的对象与关系
  const classes = buildPresetClasses(props.session.scenarioId)
  const relations = buildPresetRelations(props.session.scenarioId, classes)
  draftObjects.value = classes
  draftRelations.value = relations
  store.patchActive({
    ontologyClasses: classes,
    ontologyRelations: relations,
    selectedAssetIds: subscribedAssets.value.map(a => a.id),
  })
  phase.value = 'graph_done'
  addAssistantMessage(
    `本体画布构建完成 — 共 ${classes.length} 个对象、${relations.length} 条关系，已自动关联订阅资产。请确认后进入"专家走测审批"。`,
    { note: '若对结构有调整，可直接在画布上新增/删除节点；走测阶段也可继续编辑属性' },
  )
}

function addObject() {
  const cls: OntologyClassDraft = {
    id: 'cls-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6),
    name: 'NewClass' + (draftObjects.value.length + 1),
    displayName: '新对象',
    tier: 2,
    description: '',
    primaryKey: 'id',
    icon: '🆕',
    instanceCount: 0,
    properties: [
      { id: 'p-' + Date.now(), name: 'id', displayName: '主键', type: 'string', required: true },
    ],
    rules: [], actions: [], approved: false,
  }
  draftObjects.value.push(cls)
  store.patchActive({ ontologyClasses: draftObjects.value })
}

function deleteObject(id: string) {
  draftObjects.value = draftObjects.value.filter(c => c.id !== id)
  draftRelations.value = draftRelations.value.filter(r => r.source !== id && r.target !== id)
  store.patchActive({ ontologyClasses: draftObjects.value, ontologyRelations: draftRelations.value })
}

function confirmAll() {
  if (draftObjects.value.length === 0) {
    message.warning('请先生成本体画布')
    return
  }
  store.patchActive({
    ontologyClasses: draftObjects.value,
    ontologyRelations: draftRelations.value,
    status: 'pending_review',
  })
  emit('next')
}

watch(() => phase.value, () => scrollBottom())
</script>

<style scoped>
.step1 {
  display: flex;
  height: calc(100vh - 64px - 56px - 76px);
  min-height: 600px;
  gap: 16px;
  padding: 16px;
  background: #f8fafc;
}

/* Copilot 对话栏 */
.step1-chat {
  width: 480px; flex-shrink: 0;
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.copilot-header {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid #f1f5f9;
}
.copilot-avatar {
  width: 38px; height: 38px; border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex; align-items: center; justify-content: center;
}
.copilot-name { font-size: 14px; font-weight: 600; color: #0f172a; }
.copilot-sub { font-size: 11px; color: #94a3b8; margin-top: 2px; }

.step1-messages {
  flex: 1; overflow-y: auto;
  padding: 16px 18px;
  display: flex; flex-direction: column; gap: 14px;
}
.msg-row {
  display: flex; gap: 10px; align-items: flex-start;
}
.msg-row--user { flex-direction: row-reverse; }
.msg-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: #fff;
  flex-shrink: 0;
}
.msg-row--user .msg-avatar { background: linear-gradient(135deg, #8b5cf6, #6366f1); }
.msg-row--assistant .msg-avatar { background: linear-gradient(135deg, #6366f1, #06b6d4); }
.msg-bubble {
  padding: 10px 14px; border-radius: 12px;
  max-width: 86%;
  line-height: 1.7; font-size: 13px;
  white-space: pre-wrap; word-break: break-word;
}
.msg-row--user .msg-bubble {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
}
.msg-row--assistant .msg-bubble {
  background: #f8fafc; color: #1e293b;
  border: 1px solid #e2e8f0;
}
.msg-thinking-badge {
  display: inline-block;
  padding: 2px 8px; border-radius: 999px;
  font-size: 10px; font-weight: 500;
  background: rgba(99, 102, 241, 0.1); color: #4f46e5;
  margin-bottom: 6px;
}
.msg-content { white-space: pre-wrap; }
.msg-note {
  margin-top: 8px; padding: 6px 10px; border-radius: 8px;
  background: rgba(245, 158, 11, 0.08); color: #b45309;
  font-size: 12px; border-left: 3px solid #f59e0b;
}
.msg-thinking-text { font-size: 12px; color: #64748b; margin-top: 6px; }

.thinking-dots { display: inline-flex; gap: 4px; align-items: center; }
.thinking-dots span {
  width: 6px; height: 6px; border-radius: 50%;
  background: #6366f1;
  animation: dotPulse 1.2s ease-in-out infinite;
}
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

.step1-input-bar {
  border-top: 1px solid #f1f5f9;
  padding: 12px 14px;
  background: #fff;
}
.step1-attachment-strip {
  display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;
}
.step1-attachment-card {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px; border-radius: 8px;
  background: #f8fafc; border: 1px solid #e2e8f0;
  font-size: 11px;
}
.att-icon {
  width: 24px; height: 24px; border-radius: 6px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.att-info { line-height: 1.3; }
.att-name { color: #0f172a; font-weight: 500; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.att-meta { color: #94a3b8; font-size: 10px; }
.att-close { width: 16px; height: 16px; border-radius: 50%; background: #e2e8f0; border: 0; cursor: pointer; color: #64748b; line-height: 1; }

.step1-input-row {
  display: flex; gap: 8px; align-items: flex-end;
  background: #f8fafc; border-radius: 12px;
  padding: 6px 8px;
}
.step1-attach-btn, .send-btn {
  width: 32px; height: 32px; border-radius: 50%;
  border: 0; cursor: pointer; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  transition: transform 150ms ease;
}
.step1-attach-btn { background: #fff; color: #64748b; border: 1px solid #e2e8f0; }
.step1-attach-btn:hover { color: #4f46e5; border-color: #4f46e5; }
.send-btn { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; }
.send-btn:hover:not(:disabled) { transform: scale(1.05); }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.hidden-file { display: none; }
.chat-input { flex: 1; background: transparent !important; padding: 6px 4px !important; resize: none; }
.chat-input :deep(textarea) { background: transparent !important; box-shadow: none !important; }

/* 资产面板 */
.step1-assets {
  width: 380px; flex-shrink: 0;
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  display: flex; flex-direction: column;
}

/* 画布 */
.step1-graph {
  flex: 1; min-width: 0;
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.step1-graph-actions {
  padding: 12px 16px;
  border-top: 1px solid #f1f5f9;
  display: flex; justify-content: flex-end;
}
</style>
