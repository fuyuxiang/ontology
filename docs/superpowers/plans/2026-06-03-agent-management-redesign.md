# 智能体管理页面重设计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the agent management list page and detail page to match the "atomic capability unit" positioning, removing the canvas editor and adding proper CRUD management with chat testing.

**Architecture:** Rewrite two existing Vue components (AgentServiceView.vue → card grid list, AgentDetailView.vue → form + chat split). Add one backend query to return referenced scenes per agent. No DB migrations.

**Tech Stack:** Vue 3 Composition API, TypeScript, existing `api/client.ts` HTTP layer, existing CSS variables, FastAPI backend with SQLAlchemy.

---

### Task 1: Backend — Add referenced_scenes to GET /agents

**Files:**
- Modify: `backend/app/api/v1/agents.py:48-75`

- [ ] **Step 1: Update `_agent_out` to accept referenced_scenes parameter**

```python
def _agent_out(a: Agent, db: Session, referenced_scenes: list = None) -> dict:
    model_name = None
    if a.model_id:
        m = db.get(ModelRegistry, a.model_id)
        model_name = m.name if m else None
    result = {
        "id": a.id,
        "name": a.name,
        "description": a.description,
        "tags": a.tags or [],
        "model_id": a.model_id,
        "model_name": model_name,
        "system_prompt": a.system_prompt,
        "kb_ids": a.kb_ids or [],
        "entity_ids": a.entity_ids or [],
        "tools_config": a.tools_config or {},
        "status": a.status,
        "api_key": a.api_key if a.status == "published" else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
    if referenced_scenes is not None:
        result["referenced_scenes"] = referenced_scenes
    return result
```

- [ ] **Step 2: Update `list_agents` to query referenced scenes**

```python
@router.get("")
def list_agents(db: Session = Depends(get_db)):
    from app.models.scene import AipScene

    agents = db.query(Agent).all()
    scenes = db.query(AipScene).all()

    # Build agent_id -> [{id, name}] mapping
    agent_refs: dict[str, list] = {a.id: [] for a in agents}
    for scene in scenes:
        if not scene.nodes_json:
            continue
        for node in scene.nodes_json:
            node_data = node.get("data", {})
            agent_id = node_data.get("agent_id")
            if agent_id and agent_id in agent_refs:
                agent_refs[agent_id].append({"id": scene.id, "name": scene.name})
                break  # one scene only counted once per agent

    return [_agent_out(a, db, referenced_scenes=agent_refs.get(a.id, [])) for a in agents]
```

- [ ] **Step 3: Verify the endpoint works**

Run: `cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology/backend && python -c "from app.api.v1.agents import list_agents; print('import ok')"`
Expected: No import errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/agents.py
git commit -m "feat(agents): add referenced_scenes to GET /agents response"
```

---

### Task 2: Frontend — Update AgentItem type and API

**Files:**
- Modify: `frontend/src/api/agents.ts`

- [ ] **Step 1: Add referenced_scenes to AgentItem interface**

```typescript
export interface ReferencedScene {
  id: string
  name: string
}

export interface AgentItem {
  id: string
  name: string
  description: string
  tags: string[]
  model_id: string | null
  model_name: string | null
  system_prompt: string
  kb_ids: string[]
  entity_ids: string[]
  tools_config: Record<string, any>
  status: string
  api_key: string | null
  created_at: string
  updated_at: string
  referenced_scenes?: ReferencedScene[]
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/agents.ts
git commit -m "feat(agents): add referenced_scenes type to AgentItem"
```

---

### Task 3: Frontend — Rewrite Agent List Page (AgentServiceView)

**Files:**
- Rewrite: `frontend/src/views/service/AgentServiceView.vue`

- [ ] **Step 1: Write the new list page component**

Replace the entire content of `AgentServiceView.vue` with a card-grid management page:

```vue
<template>
  <div class="agent-manage">
    <div class="agent-manage__header">
      <div class="agent-manage__header-left">
        <h1 class="page-title">智能体管理</h1>
        <p class="page-desc">管理和配置智能体，作为原子能力单元供流程编排调用</p>
      </div>
      <button class="btn-primary" @click="$router.push('/agent/manage/new')">+ 新建智能体</button>
    </div>

    <div class="agent-manage__toolbar">
      <input v-model="searchText" class="search-input" placeholder="搜索名称或描述..." />
      <div class="filter-group">
        <button
          v-for="f in statusFilters" :key="f.value"
          class="filter-btn" :class="{ 'filter-btn--active': statusFilter === f.value }"
          @click="statusFilter = f.value"
        >{{ f.label }}</button>
      </div>
    </div>

    <div class="agent-manage__grid" v-if="filteredAgents.length">
      <div v-for="agent in filteredAgents" :key="agent.id" class="agent-card" @click="$router.push(`/agent/manage/${agent.id}`)">
        <div class="agent-card__top">
          <span class="agent-card__name">{{ agent.name }}</span>
          <span class="agent-card__status" :class="`agent-card__status--${agent.status}`">
            {{ agent.status === 'published' ? '已发布' : '草稿' }}
          </span>
        </div>
        <div class="agent-card__desc">{{ agent.description || '暂无描述' }}</div>
        <div class="agent-card__tags" v-if="agent.tags?.length">
          <span v-for="tag in agent.tags" :key="tag" class="agent-card__tag">{{ tag }}</span>
        </div>
        <div class="agent-card__footer">
          <span class="agent-card__refs" :title="refsTooltip(agent)">
            被 {{ agent.referenced_scenes?.length || 0 }} 个场景引用
          </span>
          <button class="btn-icon btn-danger" @click.stop="confirmDelete(agent)" title="删除">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
      </div>
    </div>
    <div v-else class="agent-manage__empty">
      {{ agents.length === 0 ? '暂无智能体，点击右上角创建' : '没有匹配的结果' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { agentsApi, type AgentItem } from '../../api/agents'

const searchText = ref('')
const statusFilter = ref('all')
const agents = ref<AgentItem[]>([])

const statusFilters = [
  { label: '全部', value: 'all' },
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
]

const filteredAgents = computed(() => {
  let list = agents.value
  if (statusFilter.value !== 'all') {
    list = list.filter(a => a.status === statusFilter.value)
  }
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(a => a.name.toLowerCase().includes(q) || a.description?.toLowerCase().includes(q))
  }
  return list
})

function refsTooltip(agent: AgentItem): string {
  if (!agent.referenced_scenes?.length) return '未被任何场景引用'
  return agent.referenced_scenes.map(s => s.name).join('\n')
}

async function confirmDelete(agent: AgentItem) {
  const refs = agent.referenced_scenes?.length || 0
  const msg = refs > 0
    ? `该智能体被 ${refs} 个场景引用，确定删除吗？`
    : `确定删除智能体「${agent.name}」吗？`
  if (!confirm(msg)) return
  await agentsApi.delete(agent.id)
  agents.value = agents.value.filter(a => a.id !== agent.id)
}

onMounted(async () => {
  agents.value = await agentsApi.list()
})
</script>
```

- [ ] **Step 2: Add scoped styles**

Append the `<style scoped>` section to the component:

```css
<style scoped>
.agent-manage { padding: 24px; height: 100%; display: flex; flex-direction: column; overflow: hidden; }
.agent-manage__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.agent-manage__header-left { display: flex; flex-direction: column; gap: 4px; }
.page-title { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.page-desc { font-size: 13px; color: var(--neutral-500); margin: 0; }
.btn-primary { padding: 8px 16px; border: none; border-radius: 6px; background: var(--semantic-600); color: #fff; font-size: 13px; cursor: pointer; font-weight: 500; }
.btn-primary:hover { background: var(--semantic-700); }

.agent-manage__toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 20px; }
.search-input { width: 240px; padding: 7px 12px; border: 1px solid var(--neutral-200); border-radius: 6px; font-size: 13px; outline: none; }
.search-input:focus { border-color: var(--semantic-500); }
.filter-group { display: flex; gap: 4px; }
.filter-btn { padding: 5px 12px; border: 1px solid var(--neutral-200); border-radius: 5px; background: var(--neutral-0); font-size: 12px; cursor: pointer; color: var(--neutral-600); }
.filter-btn:hover { background: var(--neutral-50); }
.filter-btn--active { background: var(--semantic-50); border-color: var(--semantic-300); color: var(--semantic-700); font-weight: 500; }

.agent-manage__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; flex: 1; overflow-y: auto; }
.agent-card { padding: 16px; border: 1px solid var(--neutral-200); border-radius: 10px; cursor: pointer; transition: all 0.15s; display: flex; flex-direction: column; gap: 8px; }
.agent-card:hover { border-color: var(--semantic-300); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.agent-card__top { display: flex; justify-content: space-between; align-items: center; }
.agent-card__name { font-size: 14px; font-weight: 600; color: var(--neutral-800); }
.agent-card__status { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.agent-card__status--published { background: #d1fae5; color: #059669; }
.agent-card__status--draft { background: var(--neutral-100); color: var(--neutral-500); }
.agent-card__desc { font-size: 12px; color: var(--neutral-500); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.agent-card__tags { display: flex; flex-wrap: wrap; gap: 4px; }
.agent-card__tag { font-size: 11px; padding: 1px 6px; border-radius: 3px; background: var(--neutral-100); color: var(--neutral-600); }
.agent-card__footer { display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 8px; border-top: 1px solid var(--neutral-100); }
.agent-card__refs { font-size: 11px; color: var(--neutral-400); }
.btn-icon { width: 28px; height: 28px; border: none; border-radius: 5px; background: transparent; cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--neutral-400); }
.btn-icon:hover { background: var(--neutral-100); }
.btn-danger:hover { background: #fee2e2; color: #dc2626; }
.agent-manage__empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--neutral-400); font-size: 13px; }
</style>
```

- [ ] **Step 3: Verify no TypeScript errors**

Run: `cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology/frontend && npx vue-tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors related to AgentServiceView.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/service/AgentServiceView.vue
git commit -m "feat(agents): rewrite agent list page as card-grid management view"
```

---

### Task 4: Frontend — Rewrite Agent Detail Page (AgentDetailView)

**Files:**
- Rewrite: `frontend/src/views/agents/AgentDetailView.vue`

- [ ] **Step 1: Write the new detail page — template section**

Replace `AgentDetailView.vue` with a left-right split (form + chat):

```vue
<template>
  <div class="agent-detail">
    <!-- Top bar -->
    <div class="agent-detail__topbar">
      <div class="agent-detail__topbar-left">
        <button class="btn-ghost" @click="$router.push('/agent/manage')">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          返回
        </button>
        <span class="topbar-divider"></span>
        <input v-model="form.name" class="topbar-name-input" placeholder="智能体名称" />
        <span class="topbar-status" :class="`topbar-status--${agent?.status || 'draft'}`">
          {{ agent?.status === 'published' ? '已发布' : '草稿' }}
        </span>
        <span class="topbar-dirty" v-if="isDirty">● 未保存</span>
      </div>
      <div class="agent-detail__topbar-right">
        <button class="btn-outline" @click="saveAgent" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        <button class="btn-outline" @click="publishAgent" v-if="agent && agent.status === 'draft'">发布</button>
        <button class="btn-outline" @click="unpublishAgent" v-if="agent && agent.status === 'published'">下线</button>
      </div>
    </div>

    <!-- Body: left form + right chat -->
    <div class="agent-detail__body">
      <!-- Left: config form -->
      <div class="agent-detail__form">
        <div class="form-section">
          <label class="form-label">描述</label>
          <textarea v-model="form.description" class="form-textarea" rows="2" placeholder="智能体用途描述"></textarea>
        </div>
        <div class="form-section">
          <label class="form-label">标签</label>
          <input v-model="form.tagsStr" class="form-input" placeholder="用逗号分隔多个标签" />
        </div>
        <div class="form-section">
          <label class="form-label">模型</label>
          <select v-model="form.model_id" class="form-select">
            <option value="">请选择模型</option>
            <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }} ({{ m.model_name }})</option>
          </select>
        </div>
        <div class="form-section form-section--grow">
          <label class="form-label">System Prompt</label>
          <textarea v-model="form.system_prompt" class="form-textarea form-textarea--tall" placeholder="系统提示词..."></textarea>
        </div>
        <div class="form-section">
          <label class="form-label">本体实体绑定</label>
          <select v-model="form.entity_ids" class="form-select" multiple>
            <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name_cn || e.name }}</option>
          </select>
        </div>
      </div>

      <!-- Right: chat test -->
      <div class="agent-detail__chat">
        <div class="chat-header">
          <span class="chat-header__title">对话测试</span>
          <button class="btn-ghost btn-sm" @click="resetChat">重置对话</button>
        </div>
        <div v-if="!agent" class="chat-placeholder">请先保存智能体后测试</div>
        <template v-else>
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
            <div v-if="isDirty" class="chat-save-hint">配置已修改，保存后测试最新配置</div>
            <textarea v-model="userInput" class="chat-textarea" placeholder="输入消息..." rows="2" @keydown.enter.exact.prevent="sendMessage" :disabled="streaming"></textarea>
            <button class="btn-send" @click="sendMessage" :disabled="streaming || !userInput.trim()">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 8l12-5-4 5 4 5-12-5z" fill="currentColor"/></svg>
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Write the script section**

```vue
<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { agentsApi, modelsApi, type AgentItem, type ModelRegistry } from '../../api/agents'
import { entityApi } from '../../api/ontology'

const route = useRoute()
const router = useRouter()

const isNew = computed(() => route.params.id === 'new')
const agent = ref<AgentItem | null>(null)
const models = ref<ModelRegistry[]>([])
const entities = ref<{ id: string; name: string; name_cn: string }[]>([])
const saving = ref(false)
const streaming = ref(false)
const messages = ref<{ role: 'user' | 'assistant'; content: string }[]>([])
const userInput = ref('')
const messagesRef = ref<HTMLElement | null>(null)

const form = reactive({
  name: '',
  description: '',
  tagsStr: '',
  model_id: '',
  system_prompt: '',
  entity_ids: [] as string[],
})

const savedSnapshot = ref('')
const isDirty = computed(() => JSON.stringify(formToPayload()) !== savedSnapshot.value)

function formToPayload() {
  return {
    name: form.name,
    description: form.description,
    tags: form.tagsStr ? form.tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [],
    model_id: form.model_id || null,
    system_prompt: form.system_prompt,
    entity_ids: form.entity_ids,
  }
}

function loadFormFromAgent(a: AgentItem) {
  form.name = a.name
  form.description = a.description || ''
  form.tagsStr = (a.tags || []).join(', ')
  form.model_id = a.model_id || ''
  form.system_prompt = a.system_prompt || ''
  form.entity_ids = a.entity_ids || []
  savedSnapshot.value = JSON.stringify(formToPayload())
}

async function saveAgent() {
  saving.value = true
  try {
    const payload = formToPayload()
    if (isNew.value || !agent.value) {
      const created = await agentsApi.create(payload)
      agent.value = created
      router.replace(`/agent/manage/${created.id}`)
    } else {
      agent.value = await agentsApi.update(agent.value.id, payload)
    }
    loadFormFromAgent(agent.value)
  } finally {
    saving.value = false
  }
}

async function publishAgent() {
  if (!agent.value) return
  agent.value = await agentsApi.publish(agent.value.id)
  loadFormFromAgent(agent.value)
}

async function unpublishAgent() {
  if (!agent.value) return
  agent.value = await agentsApi.update(agent.value.id, { status: 'draft' })
  loadFormFromAgent(agent.value)
}

function resetChat() {
  messages.value = []
}

function scrollToBottom() {
  nextTick(() => { if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight })
}

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || !agent.value) return
  messages.value.push({ role: 'user', content: text })
  userInput.value = ''
  streaming.value = true
  scrollToBottom()

  try {
    const token = localStorage.getItem('token')
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const res = await fetch(`/api/v1/agents/${agent.value.id}/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ question: text }),
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
            } else if (event.type === 'answer' && event.content) {
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

onMounted(async () => {
  const [modelList, entityList] = await Promise.all([
    modelsApi.list(),
    entityApi.list(),
  ])
  models.value = modelList
  entities.value = entityList as any

  if (!isNew.value) {
    const id = route.params.id as string
    agent.value = await agentsApi.get(id)
    loadFormFromAgent(agent.value)
  } else {
    form.name = '新智能体'
    savedSnapshot.value = JSON.stringify(formToPayload())
  }
})
</script>
```

- [ ] **Step 3: Write the style section**

```vue
<style scoped>
.agent-detail { display: flex; flex-direction: column; height: 100%; overflow: hidden; }

.agent-detail__topbar { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; border-bottom: 1px solid var(--neutral-200); flex-shrink: 0; }
.agent-detail__topbar-left { display: flex; align-items: center; gap: 10px; }
.agent-detail__topbar-right { display: flex; gap: 8px; }
.btn-ghost { padding: 4px 8px; border: none; background: none; cursor: pointer; font-size: 12px; color: var(--neutral-600); border-radius: 4px; display: flex; align-items: center; gap: 4px; }
.btn-ghost:hover { background: var(--neutral-100); }
.btn-outline { padding: 6px 14px; border: 1px solid var(--neutral-200); border-radius: 6px; background: var(--neutral-0); font-size: 12px; cursor: pointer; color: var(--neutral-700); }
.btn-outline:hover { background: var(--neutral-50); }
.btn-outline:disabled { opacity: 0.5; cursor: not-allowed; }
.topbar-divider { width: 1px; height: 16px; background: var(--neutral-200); }
.topbar-name-input { border: none; font-size: 14px; font-weight: 600; color: var(--neutral-800); outline: none; width: 200px; background: transparent; }
.topbar-name-input:focus { border-bottom: 1px solid var(--semantic-500); }
.topbar-status { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.topbar-status--published { background: #d1fae5; color: #059669; }
.topbar-status--draft { background: var(--neutral-100); color: var(--neutral-500); }
.topbar-dirty { font-size: 11px; color: #f59e0b; }

.agent-detail__body { display: flex; flex: 1; overflow: hidden; }

.agent-detail__form { width: 420px; flex-shrink: 0; overflow-y: auto; padding: 20px; border-right: 1px solid var(--neutral-200); display: flex; flex-direction: column; gap: 16px; }
.form-section { display: flex; flex-direction: column; gap: 4px; }
.form-section--grow { flex: 1; min-height: 0; }
.form-label { font-size: 12px; font-weight: 500; color: var(--neutral-600); }
.form-input, .form-select, .form-textarea { padding: 7px 10px; border: 1px solid var(--neutral-200); border-radius: 6px; font-size: 13px; outline: none; font-family: inherit; }
.form-input:focus, .form-select:focus, .form-textarea:focus { border-color: var(--semantic-500); }
.form-textarea { resize: vertical; }
.form-textarea--tall { flex: 1; min-height: 120px; resize: none; }
.form-select[multiple] { height: 80px; }

.agent-detail__chat { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.chat-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--neutral-100); }
.chat-header__title { font-size: 13px; font-weight: 600; color: var(--neutral-700); }
.btn-sm { font-size: 11px; padding: 3px 8px; }
.chat-placeholder { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--neutral-400); font-size: 13px; }

.chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.chat-msg { display: flex; }
.chat-msg--user { justify-content: flex-end; }
.chat-msg--assistant { justify-content: flex-start; }
.chat-msg__bubble { max-width: 75%; padding: 8px 12px; border-radius: 10px; font-size: 13px; line-height: 1.5; white-space: pre-wrap; }
.chat-msg--user .chat-msg__bubble { background: var(--semantic-600); color: #fff; border-bottom-right-radius: 3px; }
.chat-msg--assistant .chat-msg__bubble { background: var(--neutral-100); color: var(--neutral-800); border-bottom-left-radius: 3px; }
.chat-msg__typing { display: flex; gap: 4px; padding: 10px 14px; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--neutral-400); animation: bounce 1.2s infinite; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100% { transform: translateY(0); } 40% { transform: translateY(-4px); } }

.chat-input { padding: 12px 16px; border-top: 1px solid var(--neutral-100); display: flex; flex-direction: column; gap: 6px; }
.chat-save-hint { font-size: 11px; color: #f59e0b; }
.chat-textarea { padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: 8px; font-size: 13px; resize: none; outline: none; font-family: inherit; }
.chat-textarea:focus { border-color: var(--semantic-500); }
.btn-send { width: 36px; height: 36px; border-radius: 8px; border: none; background: var(--semantic-600); color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; align-self: flex-end; }
.btn-send:hover:not(:disabled) { background: var(--semantic-700); }
.btn-send:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
```

- [ ] **Step 4: Verify no TypeScript errors**

Run: `cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology/frontend && npx vue-tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors related to AgentDetailView.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/agents/AgentDetailView.vue
git commit -m "feat(agents): rewrite agent detail page as form + chat split view"
```

---

### Task 5: Router — Add /agent/manage/new route

**Files:**
- Modify: `frontend/src/router/index.ts:57`

- [ ] **Step 1: Add the new route for agent creation**

Insert a new route before the `:id` route so it matches first:

```typescript
{ path: '/agent/manage/new', name: 'agent-new', component: () => import('../views/agents/AgentDetailView.vue'), meta: { title: '新建智能体' } },
```

The routes section for agent should now be:

```typescript
// 智能体应用中心
{ path: '/agent/manage', name: 'agent-manage', component: () => import('../views/service/AgentServiceView.vue'), meta: { title: '智能体管理' } },
{ path: '/agent/manage/new', name: 'agent-new', component: () => import('../views/agents/AgentDetailView.vue'), meta: { title: '新建智能体' } },
{ path: '/agent/manage/:id', name: 'agent-detail', component: () => import('../views/agents/AgentDetailView.vue'), meta: { title: '智能体详情' } },
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat(agents): add /agent/manage/new route for agent creation"
```

---

### Task 6: Smoke Test — Verify full flow in browser

- [ ] **Step 1: Start dev servers**

Run backend: `cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology/backend && python -m uvicorn app.main:app --reload --port 8000`

Run frontend: `cd /Users/fuyuxiang/Documents/100-主业/130-东方国信/13.代码仓库/ontology/frontend && npm run dev`

- [ ] **Step 2: Verify list page**

Open `http://localhost:5173/agent/manage`. Expected:
- Card grid layout displays
- Search and status filter work
- Each card shows name, description, status, tags, reference count
- Clicking a card navigates to detail page
- Delete button works (with confirmation)

- [ ] **Step 3: Verify new agent flow**

Click "新建智能体" button → navigates to `/agent/manage/new`. Expected:
- Form is empty except name = "新智能体"
- Right side shows "请先保存智能体后测试"
- Fill in fields, click save → URL changes to `/agent/manage/{id}`
- Chat test area becomes active

- [ ] **Step 4: Verify detail page**

Navigate to existing agent detail. Expected:
- Form loads agent data
- Chat test works (send message, receive SSE response)
- "未保存" indicator shows when form is modified
- Save button persists changes
- Publish/unpublish buttons work

- [ ] **Step 5: Verify referenced_scenes displays**

Go back to list page. If any agent is referenced by an AIP scene, the card should show "被 N 个场景引用" with hover tooltip showing scene names.
