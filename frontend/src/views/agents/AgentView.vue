<template>
  <div class="av-layout">
    <!-- Left list -->
    <div class="av-list">
      <div class="av-list-head">
        <span class="av-list-title">智能体</span>
        <button class="btn btn--primary btn--sm" @click="createNew">+ 新建</button>
      </div>
      <div
        v-for="a in agents" :key="a.id"
        class="av-item" :class="{ 'av-item--active': current?.id === a.id }"
        @click="select(a)"
      >
        <div class="av-item-name">{{ a.name }}</div>
        <div class="av-item-meta">
          <span class="av-status" :class="a.status === 'published' ? 'av-status--pub' : 'av-status--draft'">
            {{ a.status === 'published' ? '已发布' : '草稿' }}
          </span>
          <span v-if="a.model_name" class="av-item-model">{{ a.model_name }}</span>
        </div>
      </div>
      <div v-if="!agents.length" class="av-empty-list">暂无智能体</div>
    </div>

    <!-- Right panel -->
    <div class="av-panel" v-if="current">
      <div class="av-panel-head">
        <span class="av-panel-title">{{ current.name || '未命名智能体' }}</span>
        <div class="av-panel-actions">
          <button class="btn btn--danger btn--sm" @click="deleteAgent">删除</button>
          <button class="btn btn--sm" :disabled="saving" @click="saveDraft">{{ saving ? '保存中…' : '保存草稿' }}</button>
          <button class="btn btn--primary btn--sm" :disabled="publishing" @click="publish">
            {{ publishing ? '发布中…' : current.status === 'published' ? '重新发布' : '发布' }}
          </button>
        </div>
      </div>

      <div class="av-tabs">
        <button v-for="t in tabs" :key="t.key" class="av-tab" :class="{ 'av-tab--active': activeTab === t.key }" @click="activeTab = t.key">
          {{ t.label }}
        </button>
      </div>

      <div class="av-tab-body">
        <!-- Tab: 基础 -->
        <template v-if="activeTab === 'basic'">
          <label class="av-label">名称</label>
          <input v-model="form.name" class="av-input" placeholder="智能体名称" />
          <label class="av-label">描述</label>
          <textarea v-model="form.description" class="av-input av-textarea" placeholder="描述该智能体的用途" rows="3" />
          <label class="av-label">标签（逗号分隔）</label>
          <input v-model="tagsStr" class="av-input" placeholder="如：宽带,客服,质检" />
        </template>

        <!-- Tab: 模型 -->
        <template v-if="activeTab === 'model'">
          <label class="av-label">选择模型</label>
          <select v-model="form.model_id" class="av-input">
            <option value="">使用全局默认模型</option>
            <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }} ({{ m.model_name }})</option>
          </select>
          <label class="av-label">Temperature 覆盖</label>
          <input v-model.number="form.tools_config.temperature" class="av-input" type="number" step="0.1" min="0" max="2" placeholder="留空使用模型默认值" />
          <label class="av-label">Max Tokens 覆盖</label>
          <input v-model.number="form.tools_config.max_tokens" class="av-input" type="number" step="256" min="256" placeholder="留空使用模型默认值" />
        </template>

        <!-- Tab: 知识 -->
        <template v-if="activeTab === 'knowledge'">
          <label class="av-label">关联知识库</label>
          <div class="av-check-list">
            <label v-for="kb in knowledgeBases" :key="kb.id" class="av-check-item">
              <input type="checkbox" :value="kb.id" v-model="form.kb_ids" />
              {{ kb.name }}
            </label>
            <div v-if="!knowledgeBases.length" class="av-hint">暂无知识库</div>
          </div>
          <label class="av-label" style="margin-top:16px">关联本体实体</label>
          <div class="av-check-list">
            <label v-for="e in entities" :key="e.id" class="av-check-item">
              <input type="checkbox" :value="e.id" v-model="form.entity_ids" />
              {{ e.name_cn || e.name }}
            </label>
            <div v-if="!entities.length" class="av-hint">暂无实体</div>
          </div>
        </template>

        <!-- Tab: 提示词 -->
        <template v-if="activeTab === 'prompt'">
          <label class="av-label">系统 Prompt</label>
          <textarea v-model="form.system_prompt" class="av-input av-textarea av-textarea--lg" placeholder="定义智能体的角色、行为和约束…" rows="14" />
        </template>
      </div>

      <!-- API Info panel (published) -->
      <div v-if="current.status === 'published' && apiInfo" class="av-api-panel">
        <div class="av-api-title">API 接入信息</div>
        <div class="av-api-row">
          <span class="av-api-label">Endpoint</span>
          <code class="av-api-val">{{ apiInfo.endpoint }}</code>
        </div>
        <div class="av-api-row">
          <span class="av-api-label">API Key</span>
          <code class="av-api-val">{{ apiInfo.api_key }}</code>
        </div>
        <div class="av-api-label" style="margin-top:10px">cURL 示例</div>
        <pre class="av-api-curl">{{ apiInfo.curl }}</pre>
      </div>
    </div>

    <div class="av-panel av-panel--empty" v-else>
      <span>选择或新建一个智能体</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { agentsApi, modelsApi, type AgentItem, type ModelRegistry, type ApiInfo } from '../../api/agents'
import client from '../../api/client'

const agents = ref<AgentItem[]>([])
const models = ref<ModelRegistry[]>([])
const knowledgeBases = ref<any[]>([])
const entities = ref<any[]>([])
const current = ref<AgentItem | null>(null)
const activeTab = ref('basic')
const saving = ref(false)
const publishing = ref(false)
const apiInfo = ref<ApiInfo | null>(null)

const tabs = [
  { key: 'basic', label: '基础' },
  { key: 'model', label: '模型' },
  { key: 'knowledge', label: '知识' },
  { key: 'prompt', label: '提示词' },
]

const emptyForm = () => ({
  name: '',
  description: '',
  model_id: '' as string | null,
  system_prompt: '',
  kb_ids: [] as string[],
  entity_ids: [] as string[],
  tools_config: {} as Record<string, any>,
})

const form = ref(emptyForm())
const tagsStr = ref('')

function fillForm(a: AgentItem) {
  form.value = {
    name: a.name,
    description: a.description,
    model_id: a.model_id || '',
    system_prompt: a.system_prompt,
    kb_ids: [...(a.kb_ids || [])],
    entity_ids: [...(a.entity_ids || [])],
    tools_config: { ...(a.tools_config || {}) },
  }
  tagsStr.value = (a.tags || []).join(', ')
}

async function load() {
  agents.value = await agentsApi.list()
}

async function select(a: AgentItem) {
  current.value = a
  fillForm(a)
  activeTab.value = 'basic'
  apiInfo.value = null
  if (a.status === 'published') {
    try { apiInfo.value = await agentsApi.apiInfo(a.id) } catch {}
  }
}

function createNew() {
  current.value = { id: '', name: '新智能体', description: '', tags: [], model_id: null, model_name: null, system_prompt: '', kb_ids: [], entity_ids: [], tools_config: {}, status: 'draft', api_key: null, created_at: '', updated_at: '' }
  form.value = emptyForm()
  form.value.name = '新智能体'
  tagsStr.value = ''
  activeTab.value = 'basic'
  apiInfo.value = null
}

async function saveDraft() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      model_id: form.value.model_id || null,
      tags: tagsStr.value.split(',').map(s => s.trim()).filter(Boolean),
    }
    if (current.value?.id) {
      const updated = await agentsApi.update(current.value.id, payload)
      current.value = updated
    } else {
      const created = await agentsApi.create(payload)
      current.value = created
    }
    await load()
  } finally {
    saving.value = false
  }
}

async function publish() {
  if (!current.value?.id) { await saveDraft(); if (!current.value?.id) return }
  publishing.value = true
  try {
    const updated = await agentsApi.publish(current.value.id)
    current.value = updated
    apiInfo.value = await agentsApi.apiInfo(updated.id)
    await load()
  } finally {
    publishing.value = false
  }
}

async function deleteAgent() {
  if (!current.value?.id) return
  if (!confirm(`确认删除智能体「${current.value.name}」？`)) return
  await agentsApi.delete(current.value.id)
  current.value = null
  await load()
}

onMounted(async () => {
  await load()
  models.value = await modelsApi.list()
  try { knowledgeBases.value = (await client.get('/knowledge')).data } catch {}
  try { entities.value = (await client.get('/entities')).data?.items || (await client.get('/entities')).data } catch {}
})
</script>

<style scoped>
.av-layout { display: flex; height: 100vh; overflow: hidden; }
.av-list { width: 240px; min-width: 240px; border-right: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }
.av-list-head { display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid var(--border); }
.av-list-title { font-weight: 600; font-size: 15px; }
.av-item { padding: 12px 16px; cursor: pointer; border-bottom: 1px solid var(--border); transition: background 0.15s; }
.av-item:hover { background: var(--surface-1); }
.av-item--active { background: var(--surface-2); }
.av-item-name { font-size: 14px; font-weight: 500; margin-bottom: 4px; }
.av-item-meta { display: flex; gap: 8px; align-items: center; }
.av-status { font-size: 11px; padding: 2px 6px; border-radius: 4px; }
.av-status--pub { background: #d1fae5; color: #065f46; }
.av-status--draft { background: #fef3c7; color: #92400e; }
.av-item-model { font-size: 11px; color: var(--text-muted); }
.av-empty-list { padding: 24px 16px; color: var(--text-muted); font-size: 13px; }
.av-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.av-panel--empty { align-items: center; justify-content: center; color: var(--text-muted); }
.av-panel-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.av-panel-title { font-size: 16px; font-weight: 600; }
.av-panel-actions { display: flex; gap: 8px; }
.av-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); padding: 0 24px; flex-shrink: 0; }
.av-tab { padding: 10px 16px; border: none; background: none; cursor: pointer; font-size: 14px; color: var(--text-muted); border-bottom: 2px solid transparent; margin-bottom: -1px; }
.av-tab--active { color: var(--semantic-600, #2563eb); border-bottom-color: var(--semantic-600, #2563eb); font-weight: 500; }
.av-tab-body { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 4px; }
.av-label { font-size: 13px; font-weight: 500; color: var(--text-muted); margin-top: 12px; }
.av-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--surface-1); color: var(--text); box-sizing: border-box; }
.av-textarea { resize: vertical; font-family: inherit; }
.av-textarea--lg { min-height: 280px; font-family: monospace; font-size: 13px; }
.av-check-list { display: flex; flex-direction: column; gap: 8px; padding: 8px 0; max-height: 200px; overflow-y: auto; }
.av-check-item { display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer; }
.av-hint { font-size: 13px; color: var(--text-muted); }
.av-api-panel { margin: 0 24px 24px; padding: 16px; background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; flex-shrink: 0; }
.av-api-title { font-weight: 600; font-size: 14px; margin-bottom: 12px; }
.av-api-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.av-api-label { font-size: 12px; color: var(--text-muted); min-width: 70px; }
.av-api-val { font-family: monospace; font-size: 12px; background: var(--surface-2); padding: 3px 8px; border-radius: 4px; word-break: break-all; }
.av-api-curl { font-family: monospace; font-size: 12px; background: var(--surface-2); padding: 12px; border-radius: 6px; overflow-x: auto; white-space: pre; margin: 6px 0 0; }
.btn { padding: 7px 14px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface-1); cursor: pointer; font-size: 13px; font-weight: 500; }
.btn--primary { background: var(--semantic-600, #2563eb); color: #fff; border-color: transparent; }
.btn--danger { color: #dc2626; }
.btn--sm { padding: 5px 12px; font-size: 12px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
