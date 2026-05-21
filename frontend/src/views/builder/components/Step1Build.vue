<template>
  <div class="step1-root">
    <!-- 左侧：Copilot 对话栏 -->
    <aside class="step1-chat">
      <div class="step1-chat-header">
        <div class="copilot-avatar">
          <div style="width:36px;height:36px;border-radius:8px;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:14px">CP</div>
        </div>
        <div>
          <div class="copilot-name">场景 Copilot</div>
          <div class="copilot-sub">场景识别 · 资产匹配 · 本体构建</div>
        </div>
      </div>

      <div class="step1-messages" ref="msgsRef">
        <div
          v-for="m in messages"
          :key="m.id"
          :class="['msg-row', m.role]"
        >
          <div v-if="m.role === 'assistant'" class="msg-avatar">
            <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#06b6d4);display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;font-weight:700">AI</div>
          </div>
          <div class="msg-content">
            <div v-if="m.thinkingSeconds != null" class="msg-thinking-badge">
              <span style="color:#10b981">✓</span>
              已思考完成（{{ m.thinkingSeconds }}秒）
            </div>
            <div class="msg-bubble">
              <div v-if="m.note" class="msg-note">
                <span class="msg-note-icon">💡</span>
                {{ m.note }}
              </div>
              <span v-for="(line, i) in m.content.split('\n')" :key="i">{{ line }}<br v-if="i < m.content.split('\n').length - 1" /></span>
            </div>
          </div>
        </div>

        <!-- 思考中 -->
        <div v-if="phase === 'scene_analyzing' || phase === 'scene_confirm'" class="msg-row assistant">
          <div class="msg-avatar">
            <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#06b6d4);display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;font-weight:700">AI</div>
          </div>
          <div class="msg-content">
            <div class="msg-thinking">
              <span style="color:#6366f1">⟳</span>
              <span>{{ phase === 'scene_confirm' ? `正在拆解用户故事（${elapsedSec}秒）...` : `正在分析你的业务场景（${elapsedSec}秒）...` }}</span>
              <div class="thinking-dots"><span/><span/><span/></div>
            </div>
          </div>
        </div>

        <!-- 用户故事面板 -->
        <UserStoriesPanel
          v-if="userStories.length && (phase === 'story_split' || phase === 'asset_scanning' || phase === 'assets_ready' || phase === 'graph_building' || phase === 'graph_done')"
          :stories="userStories"
          :readonly="phase !== 'story_split'"
          @toggle="onToggleStory"
          @confirm="onConfirmStories"
        />

        <!-- 资产扫描进度 + 雷达 -->
        <AssetScanProgress
          v-if="phase === 'asset_scanning'"
          :active-step="scanActiveStep"
          :keywords="scenarioKeywords"
        />

        <!-- 资产清单（沿用左侧消息流） -->
        <AssetsPanel
          v-if="(phase === 'assets_ready' || phase === 'graph_building' || phase === 'graph_done') && assets.length"
          :assets="assets"
          :selected-count="subscribedAssets.length"
          :graph-ready="phase === 'graph_building' || phase === 'graph_done'"
          @toggle-subscribe="onToggleSubscribe"
          @start-graph="startGraphBuilding"
        />

        <!-- 网络构建动画 -->
        <div v-if="phase === 'graph_building'" class="msg-row assistant">
          <div class="msg-avatar">
            <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#06b6d4);display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;font-weight:700">AI</div>
          </div>
          <div class="msg-content">
            <div class="msg-thinking">
              <span style="color:#6366f1">⟳</span>
              <span>{{ graphPhaseLabel }}</span>
              <div class="thinking-dots"><span/><span/><span/></div>
            </div>
          </div>
        </div>

        <div ref="bottomRef"></div>
      </div>

      <!-- composer -->
      <div :class="['step1-composer', { 'has-attachments': attachments.length }]">
        <div v-if="attachments.length" class="step1-attachment-strip" aria-label="待发送素材">
          <div
            v-for="a in attachments"
            :key="a.id"
            :class="['step1-attachment-card', categoryTone(a.mimeCategory)]"
          >
            <div class="step1-attachment-thumb">
              <span>{{ thumbAbbr(a.fileType) }}</span>
            </div>
            <div class="step1-attachment-info">
              <div class="step1-attachment-name" :title="a.fileName">{{ a.fileName }}</div>
              <div class="step1-attachment-meta">
                {{ a.fileType }} · {{ a.fileSize }}
                <span :class="['step1-attachment-status', a.status === 'parsed' ? 'completed' : a.status === 'parsing' ? 'pending' : '']">
                  {{ attStatus(a.status) }}
                </span>
              </div>
            </div>
            <button class="step1-attachment-remove" @click="removeAttachment(a.id)">×</button>
          </div>
        </div>

        <div class="step1-input-bar">
          <button class="step1-upload-trigger" :disabled="phase !== 'idle'" @click="fileInput?.click()" title="上传素材">＋</button>
          <input ref="fileInput" type="file" multiple style="display:none" @change="onFiles" />
          <textarea
            class="chat-input"
            v-model="currentInput"
            :placeholder="placeholder"
            rows="2"
            @keydown.enter.exact.prevent="onSend"
          />
          <button class="send-btn" :disabled="!currentInput.trim()" @click="onSend">▶</button>
        </div>
      </div>
    </aside>

    <!-- 右侧：语义网络画布 -->
    <section class="step1-graph">
      <div class="graph-header">
        <span style="font-size:15px">🗺️</span>
        <span>语义网络画布</span>
        <span v-if="phase === 'graph_building'" class="graph-building-phase">
          <span style="margin-right:5px;color:#6366f1">⟳</span>
          {{ graphPhaseLabel }}
        </span>
        <span v-else-if="draftObjects.length > 0" class="graph-stats">
          已有 {{ draftObjects.length }} 个对象 · {{ draftRelations.length }} 条关系
        </span>
      </div>

      <div
        v-if="draftObjects.length === 0 && phase !== 'graph_building'"
        class="graph-empty"
        :style="{ border: dragOver ? '2px dashed #6366f1' : '2px dashed transparent', transition: 'border .2s' }"
        @drop.prevent="onDrop"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
      >
        <div class="graph-empty-icon">🗺️</div>
        <div>将左侧资产拖入此处</div>
        <div style="font-size:12px;color:#cbd5e1;margin-top:4px">AI 将根据场景×资产组合动态构建本体</div>
        <button
          v-if="subscribedAssets.length > 0 && userStoriesConfirmed"
          class="build-ontology-btn"
          style="width:auto;margin-top:12px;padding:10px 24px"
          @click="startGraphBuilding"
        >⚡ 一键生成画布</button>
      </div>

      <div v-else style="flex:1;min-height:0;display:flex;flex-direction:column">
        <SemanticCanvas
          :objects="draftObjects"
          :relations="draftRelations"
          :phase="phase"
          :graph-phase-label="graphPhaseLabel"
          @add="addObject"
          @delete="deleteObject"
          @drop="onDrop"
        />

        <button
          v-if="phase === 'graph_done'"
          class="next-step-btn"
          @click="confirmAll"
        >确认本体并进入走测 →</button>
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
  AssetCategory,
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
const bottomRef = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)

const placeholder = computed(() => SCENARIO_PLACEHOLDERS[props.session.scenarioId] || '描述你的业务场景，AI 将辅助构建本体...')
const subscribedAssets = computed(() => assets.value.filter(a => a.subscribed))
const userStoriesConfirmed = computed(() => userStories.value.length > 0 && userStories.value.every(s => s.confirmed))
const scenarioKeywords = computed(() => {
  if (props.session.scenarioId === 'refund-root-cause') return ['退单', '根因归因', '装机工单', '外呼回访', '装维履约']
  if (props.session.scenarioId === 'enterprise-qa') return ['政企', 'KPI', '智能问数', '指标血缘', '要客明细']
  return userStories.value.flatMap(s => s.keywords).filter((v, i, a) => a.indexOf(v) === i).slice(0, 5)
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
    role: 'assistant', content,
    thinkingSeconds: opts.thinkingSeconds, note: opts.note,
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
    bottomRef.value?.scrollIntoView({ behavior: 'smooth' })
    if (msgsRef.value) msgsRef.value.scrollTop = msgsRef.value.scrollHeight
  })
}

function attStatus(s: string) {
  return s === 'pending' ? '待发送' : s === 'parsing' ? 'AI 解析中...' : '已解析'
}
function categoryTone(c: AssetCategory) {
  if (c === 'image') return 'image'
  if (c === 'structured') return 'sheet'
  return 'doc'
}
function thumbAbbr(t: string) {
  return (t || 'FILE').slice(0, 3).toUpperCase()
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
      fileName: file.name, fileType: ext || 'FILE',
      fileSize: (file.size / 1024).toFixed(0) + ' KB',
      sourceOntology: props.session.ontologyName,
      scenarioName: props.session.scenarioName,
      status: 'parsing', statusText: 'AI 解析中...',
      extractedSummary: '正在抽取规则与字段',
      extractedRules: 0, extractedFields: 0,
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
    asRole: s.asRole, iWant: s.iWant, soThat: s.soThat,
    keywords: s.keywords, confirmed: false,
  }))
  userStories.value = stories
  addAssistantMessage(
    `好的，我已理解你的需求。基于场景分析，我为你拆解了 ${stories.length} 个用户故事，请逐个确认后开始查找匹配资产。`,
    { thinkingSeconds: elapsedSec.value, note: '点击下方故事卡进行确认，全部确认后即可开启资产扫描' },
  )
  phase.value = 'story_split'
}

function onToggleStory(id: string) {
  const s = userStories.value.find(x => x.id === id)
  if (s) s.confirmed = !s.confirmed
}
async function onConfirmStories() {
  const confirmed = userStories.value.filter(s => s.confirmed).length
  if (confirmed === 0) { message.warning('请至少确认 1 个用户故事'); return }
  userStories.value.forEach(s => (s.confirmed = true))
  phase.value = 'asset_scanning'
  scanActiveStep.value = 0
  for (let i = 0; i < SCAN_STEPS.length; i++) {
    scanActiveStep.value = i
    await new Promise(r => setTimeout(r, 700))
  }
  scanActiveStep.value = SCAN_STEPS.length
  assets.value = (SCENARIO_ASSETS[props.session.scenarioId] || SCENARIO_ASSETS['refund-root-cause']).map(a => ({ ...a }))
  const sCount = assets.value.filter(a => a.category === 'structured').length
  const uCount = assets.value.length - sCount
  addAssistantMessage(
    `资产清单组装完成，共 ${assets.value.length} 个资产（${sCount} 结构化 + ${uCount} 非结构化）。请勾选要纳入本体的资产，然后点击右侧"⚡ 一键生成画布"。`,
    { note: '资产将映射到本体的 T-box / R-box / A-box 三盒结构' },
  )
  phase.value = 'assets_ready'
  assets.value.slice(0, 4).forEach(a => (a.subscribed = true))
}

function onToggleSubscribe(id: string) {
  const a = assets.value.find(x => x.id === id)
  if (a) a.subscribed = !a.subscribed
}

async function startGraphBuilding() {
  if (subscribedAssets.value.length === 0) {
    message.warning('请至少订阅 1 个资产再生成画布'); return
  }
  phase.value = 'graph_building'
  for (let i = 0; i < GRAPH_BUILDING_STEPS.length; i++) {
    graphPhaseLabel.value = GRAPH_BUILDING_STEPS[i]
    await new Promise(r => setTimeout(r, 800))
  }
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

function onDrop(e: DragEvent) {
  dragOver.value = false
  const id = e.dataTransfer?.getData('assetId')
  if (id) {
    const a = assets.value.find(x => x.id === id)
    if (a && !a.subscribed) a.subscribed = true
  }
}

function addObject() {
  const cls: OntologyClassDraft = {
    id: 'cls-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6),
    name: 'NewClass' + (draftObjects.value.length + 1),
    displayName: '新对象', tier: 2, description: '', primaryKey: 'id',
    icon: '🆕', instanceCount: 0,
    properties: [{ id: 'p-' + Date.now(), name: 'id', displayName: '主键', type: 'string', required: true }],
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
  if (draftObjects.value.length === 0) { message.warning('请先生成本体画布'); return }
  store.patchActive({
    ontologyClasses: draftObjects.value,
    ontologyRelations: draftRelations.value,
    status: 'pending_review',
  })
  emit('next')
}

watch(() => phase.value, () => scrollBottom())
</script>
