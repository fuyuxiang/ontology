<template>
  <div class="chat-root">
    <aside class="chat-side">
      <div class="chat-header">
        <div class="copilot-avatar">
          <div style="width:36px;height:36px;border-radius:8px;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:14px">CP</div>
        </div>
        <div>
          <div class="copilot-name">本体构建助手</div>
          <div class="copilot-sub">对话生成 · 资产联动 · 流式抽取</div>
        </div>
      </div>

      <div class="chat-messages" ref="msgsRef">
        <div v-for="m in messages" :key="m.id" :class="['msg-row', m.role]">
          <div v-if="m.role === 'assistant'" class="msg-avatar">
            <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#06b6d4);display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;font-weight:700">AI</div>
          </div>
          <div class="msg-content">
            <div v-if="m.thinking" class="msg-thinking">
              <span style="color:#6366f1">⟳</span>
              <span>{{ m.thinking }}</span>
              <span class="thinking-dots"><span/><span/><span/></span>
            </div>
            <div v-else-if="m.toolNote" class="msg-note">
              🔧 {{ m.toolNote }}
            </div>
            <div v-else class="msg-bubble">
              <span v-for="(line, i) in (m.content || '').split('\n')" :key="i">{{ line }}<br v-if="i < (m.content || '').split('\n').length - 1" /></span>
            </div>

            <AssetPickerCard
              v-if="m.picker"
              :title="m.picker.title"
              :kind="m.picker.kind"
              :items="m.picker.items"
              @submit="onPickerSubmit($event, m.id)"
            />

            <div v-if="m.draft" class="msg-draft-summary">
              ✅ 已抽取 {{ m.draft.entities.length }} 对象 / {{ m.draft.relations.length }} 关系
              · 规则建议 {{ m.draft.suggested_rules.length }}
              · 动作建议 {{ m.draft.suggested_actions.length }}
              <button class="msg-draft-btn" @click="confirmAll">确认进入走测 →</button>
            </div>
          </div>
        </div>

        <div v-if="busy" class="msg-row assistant">
          <div class="msg-avatar">
            <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#06b6d4);display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;font-weight:700">AI</div>
          </div>
          <div class="msg-content">
            <div class="msg-thinking">
              <span style="color:#6366f1">⟳</span>
              <span>正在思考…</span>
              <span class="thinking-dots"><span/><span/><span/></span>
            </div>
          </div>
        </div>

        <div ref="bottomRef"></div>
      </div>

      <div class="chat-composer">
        <textarea
          class="chat-input"
          v-model="currentInput"
          :placeholder="placeholder"
          rows="2"
          :disabled="busy"
          @keydown.enter.exact.prevent="onSend"
        />
        <button class="send-btn" :disabled="!currentInput.trim() || busy" @click="onSend">▶</button>
      </div>
    </aside>

    <section class="chat-graph">
      <div class="graph-header">
        <span style="font-size:15px">🗺️</span>
        <span>本体草稿</span>
        <span v-if="draft" class="graph-stats">
          已有 {{ draft.entities.length }} 个对象 · {{ draft.relations.length }} 条关系
        </span>
      </div>

      <div v-if="!draft" class="graph-empty">
        <div class="graph-empty-icon">🗺️</div>
        <div>从左侧描述业务，AI 将逐步联动数据资产与文档生成本体草稿</div>
      </div>
      <div v-else style="flex:1;min-height:0;display:flex;flex-direction:column">
        <SemanticCanvas
          :objects="draftObjectsForCanvas"
          :relations="draftRelationsForCanvas"
          :phase="'graph_done'"
          :editable="false"
        />
        <button class="next-step-btn" @click="confirmAll">确认进入走测 →</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useBuilderStore } from '../../../store/builder'
import { authHeaders } from '../../../utils/authHeaders'
import type {
  BuilderSession,
  OntologyObjectDraft,
  OntologyProperty,
  OntologyRelationDraft,
  SuggestedRule,
  SuggestedAction,
} from '../../../types/builder'
import SemanticCanvas from './graph/SemanticCanvas.vue'
import AssetPickerCard from './copilot/AssetPickerCard.vue'

interface PickerCard { title: string; kind: 'datasource' | 'document'; items: any[] }
interface DraftPayload {
  entities: any[]
  relations: any[]
  suggested_rules: any[]
  suggested_actions: any[]
}
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content?: string
  thinking?: string
  toolNote?: string
  picker?: PickerCard
  draft?: DraftPayload
}

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'next'): void }>()
const store = useBuilderStore()

const messages = ref<ChatMessage[]>([])
const currentInput = ref('')
const busy = ref(false)
const msgsRef = ref<HTMLElement | null>(null)
const bottomRef = ref<HTMLElement | null>(null)
const draft = ref<DraftPayload | null>(null)
const selectedDsIds = ref<string[]>([])
const selectedDocIds = ref<string[]>([])

const placeholder = computed(() => '描述你想构建本体的业务场景（例如：政企客户经营）...')

const draftObjectsForCanvas = computed<OntologyObjectDraft[]>(() => {
  if (!draft.value) return []
  return draft.value.entities.map((e: any, i: number) => ({
    id: `dobj-${i}`,
    name: e.name || `Object${i+1}`,
    displayName: e.display_name || e.name || `对象${i+1}`,
    tier: (e.tier || 3) as 1 | 2 | 3,
    description: e.description || '',
    primaryKey: e.primary_key || 'id',
    icon: e.icon || '🔷',
    instanceCount: 0,
    properties: (e.properties || []).map((p: any, pi: number) => ({
      id: `dprop-${i}-${pi}`,
      name: p.name, displayName: p.display_name || p.name,
      type: p.type || 'string', required: !!p.required,
      description: p.description || '',
    })),
    derivedProperties: [], rules: [], actions: [], approved: false,
  }))
})
const draftRelationsForCanvas = computed<OntologyRelationDraft[]>(() => {
  if (!draft.value) return []
  return draft.value.relations.map((r: any, i: number) => {
    const fromIdx = draft.value!.entities.findIndex((e: any) => e.name === r.from_entity)
    const toIdx   = draft.value!.entities.findIndex((e: any) => e.name === r.to_entity)
    return {
      id: `drel-${i}`,
      name: r.name, displayName: r.display_name || r.name,
      source: `dobj-${fromIdx}`, target: `dobj-${toIdx}`,
      cardinality: r.cardinality || '1:N',
      description: r.description || '',
      relationType: 'ObjectProperty' as const,
      semanticType: 'association' as const,
    }
  }).filter(r => !r.source.endsWith('-1') || !r.target.endsWith('-1'))
})

function uid(p: string) { return `${p}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}` }

function pushMessage(m: Omit<ChatMessage, 'id'>): ChatMessage {
  const msg: ChatMessage = { id: uid('msg'), ...m }
  messages.value.push(msg)
  scrollBottom()
  return msg
}
function scrollBottom() {
  nextTick(() => {
    bottomRef.value?.scrollIntoView({ behavior: 'smooth' })
    if (msgsRef.value) msgsRef.value.scrollTop = msgsRef.value.scrollHeight
  })
}

onMounted(() => {
  if (props.session.ontologyObjects.length > 0) {
    // 已恢复进度
    pushMessage({ role: 'assistant', content: '已恢复上次的本体草稿，可在右侧查看，或继续对话调整。' })
    return
  }
  pushMessage({
    role: 'assistant',
    content: `你好，我是本体构建助手。请用一两句话描述你想构建本体的业务场景，例如：\n· 我想建政企客户经营的本体\n· 想做退单根因分析的本体\n我会逐步联动数据资产与业务文档帮你生成。`,
  })
})

async function onSend() {
  if (!currentInput.value.trim() || busy.value) return
  const text = currentInput.value.trim()
  currentInput.value = ''
  pushMessage({ role: 'user', content: text })
  await callChat(text)
}

async function callChat(userText: string) {
  busy.value = true
  const fd = new FormData()
  fd.append('session_id', props.session.sessionId)
  fd.append('message', userText)
  let pendingThinking: ChatMessage | null = null
  try {
    const resp = await fetch('/api/v1/builder/chat', { method: 'POST', headers: authHeaders(), body: fd })
    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)
    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buf = ''
    let assistantBuf = ''
    let assistantMsg: ChatMessage | null = null

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
        let ev: any
        try { ev = JSON.parse(payload) } catch { continue }

        if (ev.type === 'tool_start') {
          if (pendingThinking) {
            // 保留
          } else {
            pendingThinking = pushMessage({ role: 'assistant', thinking: `调用工具 ${ev.tool}…` })
          }
        } else if (ev.type === 'tool_result') {
          // 把 thinking 行替换为简短 toolNote
          if (pendingThinking) {
            pendingThinking.thinking = undefined
            pendingThinking.toolNote = `${ev.tool} → ${ev.summary || '完成'}`
            pendingThinking = null
          } else {
            pushMessage({ role: 'assistant', toolNote: `${ev.tool} → ${ev.summary || '完成'}` })
          }
          // 处理三类工具的 detail
          handleToolResult(ev)
        } else if (ev.type === 'content') {
          assistantBuf += ev.content || ''
          if (!assistantMsg) {
            assistantMsg = pushMessage({ role: 'assistant', content: '' })
          }
          assistantMsg.content = assistantBuf
        } else if (ev.type === 'done') {
          assistantBuf = ''
          assistantMsg = null
          if (pendingThinking) { pendingThinking.thinking = undefined; pendingThinking.toolNote = '思考完成'; pendingThinking = null }
        } else if (ev.type === 'answer') {
          // ask 直接走到 answer 分支
          pushMessage({ role: 'assistant', content: ev.content })
        } else if (ev.type === 'error') {
          pushMessage({ role: 'assistant', content: `❌ ${ev.content || '出错了'}` })
        }
      }
    }
  } catch (e: any) {
    pushMessage({ role: 'assistant', content: `❌ 网络错误：${e?.message || e}` })
  } finally {
    busy.value = false
  }
}

function handleToolResult(ev: any) {
  const tool = ev.tool
  const detail = ev.detail || {}
  // tool_router 的工具返回值不在 detail 里，需要前端从 SSE 拿原始结果。
  // orchestrator 的 _extract_tool_detail 没覆盖三个新工具，所以 detail 通常是 null。
  // 解决方案：tool_router 把 result.display_card 也作为 ev.summary 之外的钩子。这里直接根据 tool 名 + summary 处理：
  // 理想做法：后端额外把 raw_result 透传。这里临时通过 fetch 单独拿一次工具结果不合适。
  // 折中：直接根据工具名在前端再调一次"列出资产"接口（GET）— 用户体验差。
  // 最稳的方案是后端把 display_card 透到 detail 里。这里 fallback：
  if (!detail) return
  if (tool === 'list_business_datasources' && detail.display_card) {
    const dc = detail.display_card
    const last = messages.value[messages.value.length - 1]
    if (last) last.picker = { title: dc.title, kind: 'datasource', items: dc.items || [] }
  } else if (tool === 'list_business_documents' && detail.display_card) {
    const dc = detail.display_card
    const last = messages.value[messages.value.length - 1]
    if (last) last.picker = { title: dc.title, kind: 'document', items: dc.items || [] }
  } else if (tool === 'analyze_assets_for_ontology' && detail.entities) {
    draft.value = {
      entities: detail.entities || [],
      relations: detail.relations || [],
      suggested_rules: detail.suggested_rules || [],
      suggested_actions: detail.suggested_actions || [],
    }
    const last = messages.value[messages.value.length - 1]
    if (last) last.draft = draft.value
  }
}

function onPickerSubmit(payload: { kind: string; ids: string[]; names: string[] }, _msgId: string) {
  if (payload.kind === 'datasource') {
    selectedDsIds.value = payload.ids
    pushMessage({ role: 'user', content: `已选好 ${payload.ids.length} 个数据源：${payload.names.join('、')}（ids=${payload.ids.join(',')}）` })
    callChat(`用户已选好数据源，ids=[${payload.ids.map(i => `"${i}"`).join(',')}]，请继续列出业务文档。`)
  } else if (payload.kind === 'document') {
    selectedDocIds.value = payload.ids
    pushMessage({ role: 'user', content: `已选好 ${payload.ids.length} 份文档：${payload.names.join('、')}（ids=${payload.ids.join(',')}）` })
    const ctx = messages.value.filter(m => m.role === 'user').map(m => m.content).join(' ')
    callChat(`用户已选好文档，ids=[${payload.ids.map(i => `"${i}"`).join(',')}]，已选数据源 ids=[${selectedDsIds.value.map(i => `"${i}"`).join(',')}]，业务上下文：${ctx.slice(0, 500)}。请调用 analyze_assets_for_ontology 抽取本体草稿。`)
  }
}

function confirmAll() {
  if (!draft.value) { message.warning('请先完成抽取'); return }
  const objects: OntologyObjectDraft[] = draft.value.entities.map((e: any, i: number) => ({
    id: `obj-${Date.now().toString(36)}-${i}`,
    name: e.name || `Object${i+1}`,
    displayName: e.display_name || e.name || `对象${i+1}`,
    tier: (e.tier || 3) as 1 | 2 | 3,
    description: e.description || '',
    primaryKey: e.primary_key || 'id',
    icon: e.icon || '🔷',
    instanceCount: 0,
    // M2.2：自动落 backing —— 来自 LLM 抽取时启发式匹配的 source asset
    backing_asset_ids: Array.isArray(e.backing_asset_ids) && e.backing_asset_ids.length
      ? e.backing_asset_ids
      : (selectedDsIds.value.length ? [...selectedDsIds.value] : []),
    evidence_asset_ids: Array.isArray(e.evidence_asset_ids)
      ? e.evidence_asset_ids
      : [...selectedDocIds.value],
    properties: (e.properties || []).map((p: any, pi: number) => ({
      id: `prop-${Date.now().toString(36)}-${i}-${pi}`,
      name: p.name, displayName: p.display_name || p.name,
      type: p.type || 'string', required: !!p.required,
      description: p.description || '',
      source_asset_id: p.source_asset_id ?? null,
      source_column: p.source_column ?? p.source_field ?? null,
      source_field: p.source_field ?? null,
      source_table: p.source_table ?? null,
    } as OntologyProperty)),
    derivedProperties: [], rules: [], actions: [], approved: false,
  }))
  const nameToId = new Map<string, string>()
  draft.value.entities.forEach((e: any, i: number) => nameToId.set(e.name, objects[i].id))
  const relations: OntologyRelationDraft[] = draft.value.relations
    .filter((r: any) => nameToId.has(r.from_entity) && nameToId.has(r.to_entity))
    .map((r: any, i: number) => ({
      id: `rel-${Date.now().toString(36)}-${i}`,
      name: r.name, displayName: r.display_name || r.name,
      source: nameToId.get(r.from_entity)!, target: nameToId.get(r.to_entity)!,
      cardinality: r.cardinality || '1:N',
      description: r.description || '',
      relationType: 'ObjectProperty' as const,
      semanticType: 'association' as const,
    }))
  const suggested_rules: SuggestedRule[] = draft.value.suggested_rules.map((s: any, i: number) => ({
    id: `sgr-${Date.now().toString(36)}-${i}`,
    name: s.name, description: s.description || '',
    conditionHint: s.condition_hint, actionHint: s.action_hint,
    targetObjectId: nameToId.get(s.target_entity || '') || undefined,
  }))
  const suggested_actions: SuggestedAction[] = draft.value.suggested_actions.map((s: any, i: number) => ({
    id: `sga-${Date.now().toString(36)}-${i}`,
    name: s.name, description: s.description || '',
    triggerHint: s.trigger_hint, effectHint: s.effect_hint,
    targetObjectId: nameToId.get(s.target_entity || '') || undefined,
  }))
  store.patchActive({
    ontologyObjects: objects,
    ontologyRelations: relations,
    hints: { suggested_rules, suggested_actions },
    selectedAssetIds: selectedDsIds.value,
    status: 'pending_review',
  })
  emit('next')
}
</script>

<style scoped>
.chat-root { display: grid; grid-template-columns: 480px 1fr; height: 100%; background: #f8fafc; gap: 0; }
.chat-side { background: #fff; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; min-height: 0; }
.chat-header { display: flex; align-items: center; gap: 10px; padding: 14px 16px; border-bottom: 1px solid #f1f5f9; }
.copilot-name { font-size: 14px; font-weight: 600; color: #1e293b; }
.copilot-sub { font-size: 11px; color: #94a3b8; }

.chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.msg-row { display: flex; gap: 10px; align-items: flex-start; }
.msg-row.user { flex-direction: row-reverse; }
.msg-content { flex: 1; max-width: 380px; display: flex; flex-direction: column; gap: 6px; }
.msg-row.user .msg-content { align-items: flex-end; }
.msg-bubble {
  padding: 10px 14px; border-radius: 12px; font-size: 13px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-word;
}
.msg-row.assistant .msg-bubble { background: #f8fafc; border: 1px solid #e2e8f0; color: #334155; border-radius: 4px 12px 12px; }
.msg-row.user .msg-bubble { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; border-radius: 12px 4px 12px 12px; }
.msg-thinking { display: flex; align-items: center; gap: 6px; padding: 8px 12px; background: #f8fafc; border-radius: 10px; color: #64748b; font-size: 12px; }
.msg-note { padding: 6px 12px; background: rgba(99,102,241,0.06); border-radius: 6px; color: #4338ca; font-size: 11px; }
.msg-draft-summary { padding: 10px 12px; background: rgba(16,185,129,0.08); border-radius: 8px; font-size: 12px; color: #059669; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.msg-draft-btn { margin-left: auto; padding: 5px 12px; border: 0; border-radius: 6px; background: #10b981; color: #fff; font-size: 11px; cursor: pointer; }

.thinking-dots { display: inline-flex; gap: 3px; }
.thinking-dots span { width: 4px; height: 4px; background: #6366f1; border-radius: 50%; animation: dot 1.2s ease-in-out infinite; }
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot { 0%, 60%, 100% { opacity: 0.3; } 30% { opacity: 1; } }

.chat-composer { display: flex; gap: 8px; padding: 12px; border-top: 1px solid #f1f5f9; }
.chat-input { flex: 1; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 13px; resize: none; outline: none; }
.chat-input:focus { border-color: #4f46e5; box-shadow: 0 0 0 2px rgba(79,70,229,0.1); }
.send-btn { width: 40px; border: 0; border-radius: 10px; background: linear-gradient(135deg, #4f46e5, #7c3aed); color: #fff; cursor: pointer; }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.chat-graph { display: flex; flex-direction: column; min-height: 0; }
.graph-header { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: #fff; border-bottom: 1px solid #e2e8f0; font-size: 13px; font-weight: 600; color: #0f172a; }
.graph-stats { font-size: 11px; color: #64748b; font-weight: 500; margin-left: auto; }
.graph-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: #94a3b8; font-size: 13px; }
.graph-empty-icon { font-size: 36px; }
.next-step-btn {
  margin: 14px;
  padding: 10px;
  border: 0; border-radius: 10px;
  background: linear-gradient(135deg, #10b981, #059669); color: #fff;
  font-size: 13px; font-weight: 600; cursor: pointer;
}
</style>
