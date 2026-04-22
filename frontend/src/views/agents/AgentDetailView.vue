<template>
  <div class="agent-detail">
    <div class="detail-topbar">
      <button class="btn-back" @click="router.push('/agents')">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        返回
      </button>
      <span class="detail-name">{{ form.name || '未命名智能体' }}</span>
      <span class="detail-badge" :class="current?.status === 'published' ? 'badge--green' : 'badge--gray'">
        {{ current?.status === 'published' ? '已发布' : '草稿' }}
      </span>
      <div class="detail-actions">
        <button class="btn btn--ghost" :disabled="saving" @click="saveDraft">{{ saving ? '保存中...' : '保存草稿' }}</button>
        <button class="btn btn--primary" :disabled="publishing" @click="publish">{{ publishing ? '发布中...' : '发布' }}</button>
      </div>
    </div>

    <div class="detail-body" v-if="current">
      <div class="detail-tabs">
        <button v-for="t in tabs" :key="t.key" class="tab-btn" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">{{ t.label }}</button>
      </div>

      <div class="detail-content">
        <!-- 基础 -->
        <div v-show="activeTab === 'basic'" class="tab-pane">
          <div class="field">
            <label>名称</label>
            <input v-model="form.name" class="input" placeholder="请输入智能体名称" />
          </div>
          <div class="field">
            <label>描述</label>
            <textarea v-model="form.description" class="input input--ta" rows="4" placeholder="请输入描述"></textarea>
          </div>
          <div class="field">
            <label>标签</label>
            <div class="tags-input">
              <span v-for="(t, i) in form.tags" :key="i" class="tag">
                {{ t }}
                <button @click="form.tags.splice(i, 1)">×</button>
              </span>
              <input v-model="tagInput" class="tag-input" placeholder="输入后回车添加" @keydown.enter.prevent="addTag" />
            </div>
          </div>
        </div>

        <!-- 模型 -->
        <div v-show="activeTab === 'model'" class="tab-pane">
          <div class="field">
            <label>模型</label>
            <select v-model="form.model_id" class="input">
              <option :value="null">使用默认模型</option>
              <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }}</option>
            </select>
          </div>
          <div class="field">
            <label>温度 (Temperature) — {{ form.tools_config.temperature }}</label>
            <input type="range" v-model.number="form.tools_config.temperature" min="0" max="2" step="0.1" class="slider" />
            <div class="slider-labels"><span>0</span><span>1</span><span>2</span></div>
          </div>
          <div class="field">
            <label>最大 Token 数</label>
            <input type="number" v-model.number="form.tools_config.max_tokens" class="input" style="width:160px" min="1" max="32768" step="256" />
          </div>
        </div>

        <!-- 知识 -->
        <div v-show="activeTab === 'knowledge'" class="tab-pane">
          <div class="field">
            <label>关联知识库</label>
            <div class="check-list">
              <label v-for="k in knowledgeBases" :key="k.id" class="check-item">
                <input type="checkbox" :value="k.id" v-model="form.kb_ids" />
                {{ k.name }}
              </label>
              <span v-if="!knowledgeBases.length" class="empty-hint">暂无知识库</span>
            </div>
          </div>
          <div class="field">
            <label>关联实体</label>
            <div class="entity-search">
              <input v-model="entitySearch" class="input" placeholder="搜索实体..." />
            </div>
            <div class="check-list check-list--scroll">
              <label v-for="e in filteredEntities" :key="e.id" class="check-item">
                <input type="checkbox" :value="e.id" v-model="form.entity_ids" />
                {{ e.name }}
              </label>
            </div>
          </div>
        </div>

        <!-- 提示词 -->
        <div v-show="activeTab === 'prompt'" class="tab-pane">
          <div class="prompt-templates">
            <span class="template-label">预设模板：</span>
            <button class="btn btn--ghost btn--sm" @click="applyTemplate('customer')">客服助手</button>
            <button class="btn btn--ghost btn--sm" @click="applyTemplate('analysis')">数据分析</button>
            <button class="btn btn--ghost btn--sm" @click="applyTemplate('ontology')">本体问答</button>
          </div>
          <textarea v-model="form.system_prompt" class="input input--ta input--mono" rows="18" placeholder="请输入系统提示词..."></textarea>
        </div>

        <!-- 测试 -->
        <div v-show="activeTab === 'test'" class="tab-pane tab-pane--test">
          <div class="test-messages" ref="messagesRef">
            <div v-if="!testMessages.length" class="test-empty">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" opacity=".3"><path d="M12 2a5 5 0 100 10A5 5 0 0012 2z" stroke="currentColor" stroke-width="1.5"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" stroke-width="1.5"/></svg>
              <p>发送消息开始测试</p>
            </div>
            <div v-for="(msg, i) in testMessages" :key="i" class="test-msg" :class="msg.role">
              <div class="msg-bubble">{{ msg.content }}</div>
            </div>
          </div>
          <div class="test-input-row">
            <button class="btn btn--ghost btn--sm" @click="testMessages = []">清空</button>
            <input v-model="testInput" class="input" placeholder="输入测试消息..." @keydown.enter="sendTest" :disabled="testLoading" />
            <button class="btn btn--primary btn--sm" :disabled="testLoading" @click="sendTest">{{ testLoading ? '...' : '发送' }}</button>
          </div>
        </div>
      </div>

      <!-- API 信息 -->
      <div v-if="current.status === 'published' && apiInfo" class="api-panel">
        <div class="api-panel__title">API 接入信息</div>
        <div class="api-row"><span class="api-label">接口地址</span><code class="api-val">{{ apiInfo.endpoint }}</code></div>
        <div class="api-row"><span class="api-label">API Key</span><code class="api-val">{{ apiInfo.api_key }}</code></div>
        <div class="api-row api-row--block">
          <span class="api-label">cURL 示例</span>
          <pre class="api-curl">{{ apiInfo.curl }}</pre>
        </div>
      </div>
    </div>

    <div v-else class="detail-loading">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { agentsApi, modelsApi, type AgentItem } from '../../api/agents'
import client from '../../api/client'

const route = useRoute()
const router = useRouter()

const current = ref<AgentItem | null>(null)
const models = ref<any[]>([])
const knowledgeBases = ref<any[]>([])
const entities = ref<any[]>([])
const apiInfo = ref<any>(null)
const activeTab = ref('basic')
const saving = ref(false)
const publishing = ref(false)
const tagInput = ref('')
const entitySearch = ref('')
const testMessages = ref<{ role: string; content: string }[]>([])
const testInput = ref('')
const testLoading = ref(false)
const messagesRef = ref<HTMLElement>()

const tabs = [
  { key: 'basic', label: '基础' },
  { key: 'model', label: '模型' },
  { key: 'knowledge', label: '知识' },
  { key: 'prompt', label: '提示词' },
  { key: 'test', label: '测试' },
]

const form = ref({
  name: '', description: '', model_id: null as string | null,
  system_prompt: '', kb_ids: [] as string[], entity_ids: [] as string[],
  tags: [] as string[], tools_config: { temperature: 0.7, max_tokens: 2048 }
})

const TEMPLATES: Record<string, string> = {
  customer: '你是一名专业的客服助手，负责解答用户的问题。\n请保持礼貌、耐心，用简洁清晰的语言回答。\n如果不确定答案，请如实告知并建议用户联系人工客服。',
  analysis: '你是一名数据分析专家，擅长解读数据、发现规律和提供洞察。\n请根据用户提供的数据或问题，给出专业的分析结论和建议。\n回答时请使用结构化格式，必要时列出关键指标。',
  ontology: '你是一名本体知识图谱问答助手，基于结构化知识库回答问题。\n请优先从知识库中检索相关实体和关系，给出准确的答案。\n回答时注明信息来源，对于知识库中没有的内容请明确说明。'
}

const filteredEntities = computed(() => {
  const q = entitySearch.value.trim().toLowerCase()
  return q ? entities.value.filter(e => e.name.toLowerCase().includes(q)) : entities.value
})

function addTag() {
  const t = tagInput.value.trim()
  if (t && !form.value.tags.includes(t)) form.value.tags.push(t)
  tagInput.value = ''
}

function applyTemplate(key: string) {
  form.value.system_prompt = TEMPLATES[key] || ''
}

async function saveDraft() {
  saving.value = true
  try {
    const payload = { ...form.value, status: 'draft' }
    const res = await agentsApi.update(current.value!.id, payload)
    current.value = res
  } catch (e) { console.error(e) }
  finally { saving.value = false }
}

async function publish() {
  publishing.value = true
  try {
    const payload = { ...form.value, status: 'published' }
    const res = await agentsApi.update(current.value!.id, payload)
    current.value = res
    apiInfo.value = await agentsApi.apiInfo(current.value!.id)
  } catch (e) { console.error(e) }
  finally { publishing.value = false }
}

async function sendTest() {
  const text = testInput.value.trim()
  if (!text || testLoading.value) return
  testMessages.value.push({ role: 'user', content: text })
  testInput.value = ''
  testLoading.value = true
  const assistantMsg = { role: 'assistant', content: '' }
  testMessages.value.push(assistantMsg)
  const idx = testMessages.value.length - 1
  await nextTick()
  if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  try {
    const resp = await fetch(`/api/v1/agents/${current.value!.id}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: testMessages.value.slice(0, -1) })
    })
    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      for (const line of decoder.decode(value, { stream: true }).split('\n')) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6).trim()
        if (data === '[DONE]') continue
        try {
          const parsed = JSON.parse(data)
          testMessages.value[idx].content += parsed.choices?.[0]?.delta?.content || parsed.content || ''
          await nextTick()
          if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
        } catch (_) {}
      }
    }
  } catch (e: any) {
    testMessages.value[idx].content = '请求失败：' + e.message
  } finally { testLoading.value = false }
}

<style scoped>
.agent-detail { display: flex; flex-direction: column; height: 100vh; background: #f5f7fa; overflow: hidden; }
.detail-topbar { display: flex; align-items: center; gap: 10px; padding: 12px 20px; background: #fff; border-bottom: 1px solid #e8e8e8; flex-shrink: 0; }
.btn-back { display: flex; align-items: center; gap: 4px; font-size: 13px; color: #666; background: none; border: none; cursor: pointer; padding: 4px 8px; border-radius: 5px; }
.btn-back:hover { background: #f5f5f5; color: #333; }
.detail-name { font-size: 15px; font-weight: 600; color: #1a1a2e; flex: 1; }
.detail-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 500; }
.badge--green { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.badge--gray { background: #f5f5f5; color: #888; border: 1px solid #e0e0e0; }
.detail-actions { display: flex; gap: 8px; }
.btn { display: inline-flex; align-items: center; gap: 5px; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid transparent; transition: all 0.15s; }
.btn--primary { background: #4c6ef5; color: #fff; border-color: #4c6ef5; }
.btn--primary:hover { background: #3b5bdb; }
.btn--ghost { background: transparent; color: #555; border-color: #d9d9d9; }
.btn--ghost:hover { background: #f5f5f5; }
.btn--sm { padding: 4px 10px; font-size: 12px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.detail-body { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.detail-tabs { display: flex; gap: 2px; border-bottom: 1px solid #e8e8e8; }
.tab-btn { padding: 8px 16px; font-size: 13px; font-weight: 500; color: #888; background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; transition: all 0.15s; margin-bottom: -1px; }
.tab-btn:hover { color: #4c6ef5; }
.tab-btn.active { color: #4c6ef5; border-bottom-color: #4c6ef5; }
.detail-content { background: #fff; border-radius: 8px; border: 1px solid #e8e8e8; padding: 20px; }
.tab-pane { display: flex; flex-direction: column; gap: 16px; max-width: 640px; }
.tab-pane--test { max-width: 100%; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 13px; font-weight: 500; color: #333; }
.input { padding: 7px 10px; border: 1px solid #d9d9d9; border-radius: 6px; font-size: 13px; color: #333; outline: none; transition: border-color 0.15s; width: 100%; box-sizing: border-box; }
.input:focus { border-color: #4c6ef5; }
.input--ta { resize: vertical; font-family: inherit; }
.input--mono { font-family: 'Consolas', 'Monaco', monospace; }
.slider { width: 100%; accent-color: #4c6ef5; }
.slider-labels { display: flex; justify-content: space-between; font-size: 11px; color: #aaa; }
.tags-input { display: flex; flex-wrap: wrap; gap: 6px; padding: 6px 8px; border: 1px solid #d9d9d9; border-radius: 6px; min-height: 38px; align-items: center; }
.tag { display: inline-flex; align-items: center; gap: 4px; background: #e8f0fe; color: #3b5bdb; font-size: 12px; padding: 2px 8px; border-radius: 4px; }
.tag button { background: none; border: none; cursor: pointer; color: #3b5bdb; font-size: 14px; line-height: 1; padding: 0; }
.tag-input { border: none; outline: none; font-size: 13px; min-width: 120px; flex: 1; }
.check-list { display: flex; flex-direction: column; gap: 6px; max-height: 160px; overflow-y: auto; padding: 8px; border: 1px solid #e8e8e8; border-radius: 6px; }
.check-list--scroll { max-height: 200px; }
.check-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #333; cursor: pointer; }
.check-item input { accent-color: #4c6ef5; }
.empty-hint { font-size: 12px; color: #aaa; }
.entity-search { margin-bottom: 6px; }
.prompt-templates { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.template-label { font-size: 12px; color: #888; }
.test-messages { flex: 1; min-height: 320px; max-height: 400px; overflow-y: auto; background: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.test-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 8px; color: #bbb; font-size: 13px; }
.test-msg { display: flex; }
.test-msg.user { justify-content: flex-end; }
.msg-bubble { max-width: 70%; padding: 8px 12px; border-radius: 10px; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
.test-msg.user .msg-bubble { background: #4c6ef5; color: #fff; border-bottom-right-radius: 3px; }
.test-msg.assistant .msg-bubble { background: #f0f0f0; color: #1a1a2e; border-bottom-left-radius: 3px; }
.test-input-row { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
.api-panel { background: #f0f5ff; border: 1px solid #d0e4ff; border-radius: 8px; padding: 16px; }
.api-panel__title { font-size: 13px; font-weight: 600; color: #2e5bff; margin-bottom: 12px; }
.api-row { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 8px; font-size: 12px; }
.api-row--block { flex-direction: column; gap: 4px; }
.api-label { color: #888; min-width: 60px; flex-shrink: 0; }
.api-val { background: #fff; border: 1px solid #d0e4ff; border-radius: 4px; padding: 2px 8px; color: #333; word-break: break-all; }
.api-curl { margin: 0; background: #fff; border: 1px solid #d0e4ff; border-radius: 4px; padding: 10px; font-size: 11px; white-space: pre-wrap; word-break: break-all; color: #333; }
.detail-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; gap: 12px; color: #999; font-size: 14px; }
.spinner { width: 28px; height: 28px; border: 3px solid #e8e8e8; border-top-color: #4c6ef5; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>

onMounted(async () => {
  const id = route.params.id as string
  const [agentRes, modelRes] = await Promise.all([
    agentsApi.get(id),
    modelsApi.list(),
  ])
  current.value = agentRes
  models.value = modelRes
  form.value = {
    name: agentRes.name || '',
    description: agentRes.description || '',
    model_id: agentRes.model_id || null,
    system_prompt: agentRes.system_prompt || '',
    kb_ids: agentRes.kb_ids || [],
    entity_ids: agentRes.entity_ids || [],
    tags: agentRes.tags || [],
    tools_config: { temperature: 0.7, max_tokens: 2048, ...(agentRes.tools_config || {}) }
  }
  if (agentRes.status === 'published') {
    try { apiInfo.value = await agentsApi.apiInfo(id) } catch (_) {}
  }
  try { knowledgeBases.value = (await client.get('/knowledge')).data || [] } catch (_) {}
  try { entities.value = (await client.get('/entities')).data || [] } catch (_) {}
})
</script>
