<template>
  <div class="extract-root">
    <header class="extract-topbar">
      <div class="extract-topbar-title">
        <span>文档抽取</span>
        <small>从 Word / Excel / PDF 业务文档中流式抽取对象、属性、关系</small>
      </div>
      <div class="extract-topbar-actions">
        <button class="btn btn-primary" :disabled="!canSubmit || extracting" @click="confirmAll">进入审核 →</button>
      </div>
    </header>

    <div class="extract-body">
      <!-- 左：文件队列 + 上传区 -->
      <aside class="extract-files">
        <div
          class="extract-drop"
          :class="{ 'extract-drop--active': dragOver }"
          @click="fileInput?.click()"
          @dragover.prevent="dragOver = true"
          @dragleave="dragOver = false"
          @drop.prevent="onDrop"
        >
          <div class="extract-drop-icon">📤</div>
          <div class="extract-drop-title">点击或拖拽文件到此</div>
          <div class="extract-drop-sub">支持 .xlsx / .xls / .csv / .docx / .pdf / .md / .txt</div>
          <input
            ref="fileInput"
            type="file"
            multiple
            accept=".xlsx,.xls,.csv,.docx,.pdf,.md,.txt"
            style="display:none"
            @change="onPick"
          />
        </div>

        <div class="extract-file-list">
          <div v-for="f in files" :key="f.id" class="extract-file-item">
            <span class="ef-icon">{{ extLabel(f.ext) }}</span>
            <div class="ef-meta">
              <div class="ef-name" :title="f.name">{{ f.name }}</div>
              <div class="ef-sub">{{ f.sizeText }} · <span :class="`ef-status ef-status--${f.status}`">{{ statusLabel(f.status) }}</span></div>
            </div>
            <button v-if="!extracting" class="iconbtn iconbtn-danger" @click="removeFile(f.id)">×</button>
          </div>
          <div v-if="!files.length" class="extract-empty">还没有文件</div>
        </div>

        <button class="btn btn-primary extract-start" :disabled="!files.length || extracting" @click="startExtract">
          {{ extracting ? `抽取中 (${elapsed}s)` : `🚀 开始抽取` }}
        </button>
      </aside>

      <!-- 右：抽取卡片流 -->
      <main class="extract-stream">
        <div class="extract-stream-head">
          <span>抽取结果</span>
          <span class="extract-stream-stats">
            {{ proposedObjects.length }} 对象 · {{ proposedRelations.length }} 关系
            · 建议 {{ suggestedRules.length + suggestedActions.length }}
          </span>
        </div>

        <div v-if="suggestedRules.length || suggestedActions.length" class="suggest-zone">
          <div class="suggest-title">💡 LLM 规则/动作建议（将在审核页二次决策）</div>
          <div v-for="r in suggestedRules" :key="r.id" class="suggest-card suggest-card--rule">
            <strong>{{ r.name }}</strong>
            <span>{{ r.description }}</span>
          </div>
          <div v-for="a in suggestedActions" :key="a.id" class="suggest-card suggest-card--action">
            <strong>{{ a.name }}</strong>
            <span>{{ a.description }}</span>
          </div>
        </div>

        <div class="card-stream" ref="streamRef">
          <div v-for="o in proposedObjects" :key="o.id" class="ext-card ext-card--obj">
            <div class="ext-card-head">
              <input type="checkbox" v-model="o.checked" />
              <input class="ext-card-name" v-model="o.displayName" />
              <span class="ext-card-tier">{{ o.name }}</span>
            </div>
            <div class="ext-card-en">{{ o.name }}</div>
            <div v-if="o.properties.length" class="ext-prop-list">
              <div v-for="p in o.properties" :key="p.id" class="ext-prop">
                <input v-model="p.name" />
                <select v-model="p.type">
                  <option value="string">string</option>
                  <option value="number">number</option>
                  <option value="date">date</option>
                  <option value="boolean">boolean</option>
                  <option value="enum">enum</option>
                </select>
                <span class="ext-prop-req"><input type="checkbox" v-model="p.required" /> 必填</span>
              </div>
            </div>
          </div>

          <div v-for="r in proposedRelations" :key="r.id" class="ext-card ext-card--rel">
            <div class="ext-card-head">
              <input type="checkbox" v-model="r.checked" />
              <strong>{{ relLabel(r) }}</strong>
              <span class="ext-card-tier">{{ r.cardinality }}</span>
            </div>
            <div class="ext-card-en">{{ r.name }}</div>
          </div>

          <div v-if="!proposedObjects.length && !proposedRelations.length && !extracting" class="extract-empty extract-empty--big">
            还没有抽取结果 — 上传文件后点"开始抽取"
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore } from '../../../store/builder'
import type {
  BuilderSession,
  OntologyObjectDraft,
  OntologyProperty,
  OntologyRelationDraft,
  SuggestedRule,
  SuggestedAction,
} from '../../../types/builder'

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'next'): void }>()
const store = useBuilderStore()

interface ExtractFile { id: string; name: string; ext: string; sizeText: string; file: File; status: 'pending' | 'parsing' | 'parsed' | 'error' }
interface ExtractedObject extends OntologyObjectDraft { checked: boolean }
interface ExtractedRelation extends OntologyRelationDraft { checked: boolean }

const fileInput = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)
const files = ref<ExtractFile[]>([])
const proposedObjects = ref<ExtractedObject[]>([])
const proposedRelations = ref<ExtractedRelation[]>([])
const suggestedRules = ref<SuggestedRule[]>([])
const suggestedActions = ref<SuggestedAction[]>([])
const extracting = ref(false)
const elapsed = ref(0)
const streamRef = ref<HTMLElement | null>(null)
let elapsedTimer: number | null = null

const canSubmit = computed(() =>
  proposedObjects.value.some(o => o.checked) && !extracting.value,
)

function uid(p: string) { return `${p}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}` }
function statusLabel(s: ExtractFile['status']) { return ({ pending: '待处理', parsing: '解析中', parsed: '已解析', error: '失败' } as const)[s] }
function extLabel(e: string) { return (e || 'FILE').slice(0, 4).toUpperCase() }
function relLabel(r: ExtractedRelation) {
  const from = proposedObjects.value.find(o => o.id === r.source)?.displayName || r.source
  const to   = proposedObjects.value.find(o => o.id === r.target)?.displayName || r.target
  return `${from} →[${r.displayName}]→ ${to}`
}

function onPick(e: Event) {
  const list = (e.target as HTMLInputElement).files
  if (!list) return
  for (const f of Array.from(list)) addFile(f)
  ;(e.target as HTMLInputElement).value = ''
}
function onDrop(e: DragEvent) {
  dragOver.value = false
  const list = e.dataTransfer?.files
  if (!list) return
  for (const f of Array.from(list)) addFile(f)
}
function addFile(f: File) {
  const ext = f.name.split('.').pop() || ''
  files.value.push({
    id: uid('f'), name: f.name, ext,
    sizeText: (f.size / 1024 / 1024).toFixed(2) + ' MB',
    file: f, status: 'pending',
  })
}
function removeFile(id: string) {
  files.value = files.value.filter(f => f.id !== id)
}

async function startExtract() {
  if (!files.value.length) return
  extracting.value = true
  elapsed.value = 0
  if (elapsedTimer) clearInterval(elapsedTimer)
  elapsedTimer = window.setInterval(() => elapsed.value++, 1000)
  proposedObjects.value = []
  proposedRelations.value = []
  suggestedRules.value = []
  suggestedActions.value = []

  const fd = new FormData()
  fd.append('session_id', props.session.sessionId)
  fd.append('scenario', props.session.scenarioId || '')
  for (const f of files.value) {
    fd.append('files', f.file, f.name)
    f.status = 'parsing'
  }

  try {
    const resp = await fetch('/api/v1/builder/extract', { method: 'POST', body: fd })
    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)
    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buf = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      let idx
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const chunk = buf.slice(0, idx).trim()
        buf = buf.slice(idx + 2)
        if (!chunk.startsWith('data:')) continue
        const payload = chunk.slice(5).trim()
        if (payload === '[DONE]') continue
        try { handleEvent(JSON.parse(payload)) } catch { /* ignore */ }
      }
    }
  } catch (e: any) {
    message.error('抽取失败：' + (e?.message || '未知错误'))
    files.value.forEach(f => { if (f.status === 'parsing') f.status = 'error' })
  } finally {
    extracting.value = false
    if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null }
  }
}

function handleEvent(ev: any) {
  const t = ev.type
  if (t === 'file_parsed') {
    const f = files.value.find(x => x.name === ev.file_name)
    if (f) f.status = 'parsed'
  } else if (t === 'file_failed') {
    const f = files.value.find(x => x.name === ev.file_name)
    if (f) f.status = 'error'
  } else if (t === 'entity_proposed') {
    proposedObjects.value.push({
      id: uid('obj'),
      name: ev.name,
      displayName: ev.display_name || ev.name,
      tier: ev.tier || 3,
      description: ev.description || '',
      primaryKey: ev.primary_key || 'id',
      icon: ev.icon || '🔷',
      instanceCount: 0,
      properties: [],
      derivedProperties: [], rules: [], actions: [],
      checked: true,
    })
  } else if (t === 'attr_proposed') {
    const obj = proposedObjects.value.find(o => o.name === ev.entity_name)
    if (obj) {
      const p: OntologyProperty = {
        id: uid('prop'),
        name: ev.name,
        displayName: ev.display_name || ev.name,
        type: ev.type || 'string',
        required: !!ev.required,
        description: ev.description || '',
      }
      obj.properties.push(p)
    }
  } else if (t === 'relation_proposed') {
    const from = proposedObjects.value.find(o => o.name === ev.from_entity)
    const to = proposedObjects.value.find(o => o.name === ev.to_entity)
    if (!from || !to) return
    proposedRelations.value.push({
      id: uid('rel'),
      name: ev.name,
      displayName: ev.display_name || ev.name,
      source: from.id,
      target: to.id,
      cardinality: ev.cardinality || '1:N',
      description: ev.description || '',
      relationType: 'ObjectProperty',
      semanticType: 'association',
      checked: true,
    })
  } else if (t === 'rule_suggested') {
    suggestedRules.value.push({
      id: uid('sgr'),
      name: ev.name,
      description: ev.description || '',
      conditionHint: ev.condition_hint,
      actionHint: ev.action_hint,
      targetObjectId: matchObj(ev.target_entity)?.id,
      source: ev.source_file,
    })
  } else if (t === 'action_suggested') {
    suggestedActions.value.push({
      id: uid('sga'),
      name: ev.name,
      description: ev.description || '',
      triggerHint: ev.trigger_hint,
      effectHint: ev.effect_hint,
      targetObjectId: matchObj(ev.target_entity)?.id,
      source: ev.source_file,
    })
  } else if (t === 'extract_finished') {
    message.success(`抽取完成 — 共 ${proposedObjects.value.length} 对象 / ${proposedRelations.value.length} 关系`)
  }
  // 自动滚到底部
  requestAnimationFrame(() => {
    if (streamRef.value) streamRef.value.scrollTop = streamRef.value.scrollHeight
  })
}

function matchObj(name: string) {
  return proposedObjects.value.find(o => o.name === name || o.displayName === name)
}

function confirmAll() {
  const objs = proposedObjects.value.filter(o => o.checked).map(({ checked: _c, ...rest }) => rest as OntologyObjectDraft)
  const objIds = new Set(objs.map(o => o.id))
  const rels = proposedRelations.value
    .filter(r => r.checked && objIds.has(r.source) && objIds.has(r.target))
    .map(({ checked: _c, ...rest }) => rest as OntologyRelationDraft)
  if (!objs.length) { message.warning('至少勾选 1 个对象'); return }
  store.patchActive({
    ontologyObjects: objs,
    ontologyRelations: rels,
    hints: {
      suggested_rules: [...suggestedRules.value],
      suggested_actions: [...suggestedActions.value],
    },
    status: 'pending_review',
  })
  emit('next')
}
</script>

<style scoped>
.extract-root {
  height: calc(100vh - 64px - 56px - 76px);
  display: flex; flex-direction: column;
  background: #f8fafc;
}
.extract-topbar {
  display: flex; align-items: center; gap: 16px;
  padding: 12px 20px; background: #fff; border-bottom: 1px solid #e2e8f0;
}
.extract-topbar-title { display: flex; flex-direction: column; flex: 1; line-height: 1.3; }
.extract-topbar-title span { font-size: 15px; font-weight: 600; color: #0f172a; }
.extract-topbar-title small { font-size: 11px; color: #94a3b8; }
.btn { padding: 6px 14px; border-radius: 8px; font-size: 12px; cursor: pointer; border: 1px solid transparent; }
.btn-primary { background: linear-gradient(135deg, #4f46e5, #7c3aed); color: #fff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.extract-body {
  flex: 1; overflow: hidden;
  display: grid; grid-template-columns: 320px 1fr; gap: 12px;
  padding: 12px;
}
.extract-files, .extract-stream {
  background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
  display: flex; flex-direction: column; overflow: hidden;
}
.extract-files { padding: 14px; gap: 12px; }
.extract-drop {
  border: 2px dashed #cbd5e1; border-radius: 10px;
  padding: 20px 12px; text-align: center; cursor: pointer;
  transition: all 150ms ease;
}
.extract-drop--active, .extract-drop:hover { border-color: #4f46e5; background: rgba(79,70,229,0.04); }
.extract-drop-icon { font-size: 28px; }
.extract-drop-title { font-size: 13px; font-weight: 600; color: #1e293b; margin-top: 4px; }
.extract-drop-sub { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.extract-file-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.extract-file-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; background: #f8fafc; border-radius: 8px;
}
.ef-icon {
  width: 30px; height: 30px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  background: #4f46e5; color: #fff; font-size: 10px; font-weight: 700;
}
.ef-meta { flex: 1; min-width: 0; line-height: 1.3; }
.ef-name { font-size: 12px; color: #0f172a; word-break: break-all; }
.ef-sub { font-size: 10px; color: #94a3b8; }
.ef-status--parsing { color: #f59e0b; }
.ef-status--parsed { color: #10b981; }
.ef-status--error { color: #ef4444; }
.iconbtn { width: 22px; height: 22px; border: 0; background: transparent; border-radius: 4px; cursor: pointer; color: #94a3b8; font-size: 14px; }
.iconbtn-danger:hover { background: #fee2e2; color: #ef4444; }

.extract-start { width: 100%; padding: 10px; }

.extract-stream-head {
  display: flex; align-items: center;
  padding: 12px 16px; border-bottom: 1px solid #f1f5f9;
  font-size: 13px; font-weight: 600; color: #0f172a;
}
.extract-stream-head > span:first-child { flex: 1; }
.extract-stream-stats { font-size: 11px; color: #64748b; font-weight: 500; }

.suggest-zone {
  padding: 12px 16px;
  background: rgba(245,158,11,0.06);
  border-bottom: 1px solid #fde68a;
}
.suggest-title { font-size: 11px; color: #b45309; font-weight: 600; margin-bottom: 6px; }
.suggest-card { padding: 8px 10px; border-radius: 8px; background: #fff; margin-bottom: 6px; font-size: 12px; }
.suggest-card strong { display: block; color: #0f172a; margin-bottom: 2px; }
.suggest-card span { color: #64748b; font-size: 11px; }
.suggest-card--rule { border-left: 3px solid #f59e0b; }
.suggest-card--action { border-left: 3px solid #6366f1; }

.card-stream { flex: 1; overflow-y: auto; padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.ext-card { padding: 12px 14px; border-radius: 10px; border: 1px solid #e2e8f0; }
.ext-card--obj { background: #fff; }
.ext-card--rel { background: #f8fafc; }
.ext-card-head { display: flex; align-items: center; gap: 8px; }
.ext-card-head input[type=checkbox] { flex-shrink: 0; }
.ext-card-name { flex: 1; font-size: 13px; font-weight: 600; color: #0f172a; border: 0; background: transparent; outline: none; padding: 2px 4px; }
.ext-card-name:focus { background: #f1f5f9; border-radius: 4px; }
.ext-card-tier { font-size: 10px; color: #64748b; padding: 2px 8px; background: #f1f5f9; border-radius: 999px; }
.ext-card-en { font-size: 11px; color: #94a3b8; margin-left: 24px; margin-top: 2px; font-family: monospace; }
.ext-prop-list { display: flex; flex-direction: column; gap: 4px; margin: 8px 0 0 24px; }
.ext-prop { display: grid; grid-template-columns: 1fr 100px 70px; gap: 6px; align-items: center; }
.ext-prop input, .ext-prop select { padding: 4px 6px; border: 1px solid #e2e8f0; border-radius: 4px; font-size: 11px; }
.ext-prop-req { font-size: 11px; color: #64748b; display: flex; align-items: center; gap: 3px; }

.extract-empty { padding: 16px; text-align: center; color: #94a3b8; font-size: 12px; }
.extract-empty--big { padding: 60px 16px; font-size: 13px; }
</style>
