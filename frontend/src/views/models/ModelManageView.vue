<template>
  <div class="mm-page">
    <div class="mm-header">
      <h2 class="mm-title">模型管理</h2>
      <button class="btn btn--primary" @click="openCreate">+ 注册模型</button>
    </div>

    <div class="mm-groups" v-if="models.length">
      <template v-for="cap in capGroups" :key="cap.key">
        <div v-if="grouped[cap.key]?.length" class="mm-group">
          <div class="mm-group-label">{{ cap.label }}</div>
          <div class="mm-cards">
            <div v-for="m in grouped[cap.key]" :key="m.id" class="mm-card">
              <div class="mm-card-head">
                <span class="mm-card-name">{{ m.name }}</span>
                <span class="mm-badge" :class="`mm-badge--${m.provider}`">{{ m.provider }}</span>
                <span class="mm-status" :class="m.status === 'active' ? 'mm-status--on' : 'mm-status--off'">
                  {{ m.status === 'active' ? '启用' : '停用' }}
                </span>
              </div>
              <div class="mm-card-model">{{ m.model_name }}</div>
              <div class="mm-card-caps">
                <span v-for="c in m.capabilities" :key="c" class="mm-cap">{{ c }}</span>
              </div>
              <div class="mm-card-actions">
                <button class="btn btn--sm" @click="testModel(m)">测试</button>
                <button class="btn btn--sm" @click="openEdit(m)">编辑</button>
                <button class="btn btn--sm btn--danger" @click="deleteModel(m.id)">删除</button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
    <div v-else class="mm-empty">暂无模型，点击「注册模型」添加</div>

    <!-- Drawer -->
    <div v-if="drawerOpen" class="mm-overlay" @click.self="drawerOpen = false">
      <div class="mm-drawer">
        <div class="mm-drawer-head">
          <span>{{ editing ? '编辑模型' : '注册模型' }}</span>
          <button class="mm-close" @click="drawerOpen = false">✕</button>
        </div>
        <div class="mm-drawer-body">
          <label class="mm-label">名称</label>
          <input v-model="form.name" class="mm-input" placeholder="模型显示名称" />

          <label class="mm-label">厂商</label>
          <select v-model="form.provider" class="mm-input">
            <option value="openai">OpenAI</option>
            <option value="dashscope">DashScope (阿里云)</option>
            <option value="ollama">Ollama</option>
            <option value="azure">Azure OpenAI</option>
            <option value="custom">自定义</option>
          </select>

          <label class="mm-label">模型名称</label>
          <input v-model="form.model_name" class="mm-input" placeholder="如 gpt-4o / qwen-max" />

          <label class="mm-label">API Base URL</label>
          <input v-model="form.api_base" class="mm-input" placeholder="https://api.openai.com/v1" />

          <label class="mm-label">API Key</label>
          <input v-model="form.api_key" class="mm-input" type="password" placeholder="sk-..." />

          <label class="mm-label">能力</label>
          <div class="mm-caps-check">
            <label v-for="c in allCaps" :key="c" class="mm-cap-opt">
              <input type="checkbox" :value="c" v-model="form.capabilities" />
              {{ c }}
            </label>
          </div>

          <label class="mm-label">Temperature</label>
          <input v-model.number="form.config_json.temperature" class="mm-input" type="number" step="0.1" min="0" max="2" />

          <label class="mm-label">Max Tokens</label>
          <input v-model.number="form.config_json.max_tokens" class="mm-input" type="number" step="256" min="256" />

          <div v-if="testResult" class="mm-test-result" :class="testResult.ok ? 'mm-test-ok' : 'mm-test-fail'">
            {{ testResult.ok ? '✓ 连接成功: ' + testResult.reply : '✗ 失败: ' + testResult.error }}
          </div>
        </div>
        <div class="mm-drawer-foot">
          <button class="btn" :disabled="testing" @click="testCurrent">{{ testing ? '测试中…' : '测试连接' }}</button>
          <button class="btn btn--primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { modelsApi, type ModelRegistry } from '../../api/agents'

const models = ref<ModelRegistry[]>([])
const drawerOpen = ref(false)
const editing = ref<string | null>(null)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ ok: boolean; reply?: string; error?: string } | null>(null)

const allCaps = ['chat', 'vision', 'asr', 'embedding']
const capGroups = [
  { key: 'chat', label: 'LLM 对话模型' },
  { key: 'vision', label: 'VLM 视觉模型' },
  { key: 'asr', label: 'ASR 语音识别' },
  { key: 'embedding', label: 'Embedding 向量模型' },
]

const emptyForm = () => ({
  name: '',
  provider: 'openai',
  model_name: '',
  api_base: '',
  api_key: '',
  capabilities: ['chat'] as string[],
  config_json: { temperature: 0.7, max_tokens: 2048 },
  status: 'active',
})

const form = ref(emptyForm())

const grouped = computed(() => {
  const g: Record<string, ModelRegistry[]> = {}
  for (const m of models.value) {
    for (const c of (m.capabilities || [])) {
      if (!g[c]) g[c] = []
      if (!g[c].find(x => x.id === m.id)) g[c].push(m)
    }
  }
  return g
})

async function load() {
  models.value = await modelsApi.list()
}

function openCreate() {
  editing.value = null
  form.value = emptyForm()
  testResult.value = null
  drawerOpen.value = true
}

function openEdit(m: ModelRegistry) {
  editing.value = m.id
  form.value = {
    name: m.name,
    provider: m.provider,
    model_name: m.model_name,
    api_base: m.api_base || '',
    api_key: '',
    capabilities: [...(m.capabilities || [])],
    config_json: { temperature: 0.7, max_tokens: 2048, ...(m.config_json || {}) },
    status: m.status,
  }
  testResult.value = null
  drawerOpen.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (!payload.api_key) delete (payload as any).api_key
    if (editing.value) {
      await modelsApi.update(editing.value, payload)
    } else {
      await modelsApi.create(payload)
    }
    drawerOpen.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function deleteModel(id: string) {
  if (!confirm('确认删除该模型？')) return
  await modelsApi.delete(id)
  await load()
}

async function testModel(m: ModelRegistry) {
  const r = await modelsApi.test(m.id)
  alert(r.ok ? `✓ 成功: ${r.reply}` : `✗ 失败: ${r.error}`)
}

async function testCurrent() {
  if (!editing.value) { alert('请先保存模型后再测试'); return }
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await modelsApi.test(editing.value)
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mm-page { padding: 24px; max-width: 1200px; }
.mm-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.mm-title { font-size: 20px; font-weight: 600; margin: 0; }
.mm-group { margin-bottom: 28px; }
.mm-group-label { font-size: 13px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
.mm-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.mm-card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
.mm-card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.mm-card-name { font-weight: 600; font-size: 14px; flex: 1; }
.mm-badge { font-size: 11px; padding: 2px 7px; border-radius: 4px; background: var(--surface-2); color: var(--text-muted); }
.mm-status { font-size: 11px; padding: 2px 7px; border-radius: 4px; }
.mm-status--on { background: #d1fae5; color: #065f46; }
.mm-status--off { background: #fee2e2; color: #991b1b; }
.mm-card-model { font-size: 12px; color: var(--text-muted); margin-bottom: 8px; font-family: monospace; }
.mm-card-caps { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 12px; }
.mm-cap { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: var(--semantic-50, #eff6ff); color: var(--semantic-600, #2563eb); }
.mm-card-actions { display: flex; gap: 8px; }
.mm-empty { color: var(--text-muted); padding: 48px; text-align: center; }
.mm-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); z-index: 100; display: flex; justify-content: flex-end; }
.mm-drawer { width: 420px; background: var(--surface-0); height: 100%; display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(0,0,0,.15); }
.mm-drawer-head { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-bottom: 1px solid var(--border); font-weight: 600; font-size: 16px; }
.mm-close { background: none; border: none; cursor: pointer; font-size: 18px; color: var(--text-muted); }
.mm-drawer-body { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 4px; }
.mm-drawer-foot { padding: 16px 24px; border-top: 1px solid var(--border); display: flex; gap: 12px; justify-content: flex-end; }
.mm-label { font-size: 13px; font-weight: 500; color: var(--text-muted); margin-top: 10px; }
.mm-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--surface-1); color: var(--text); box-sizing: border-box; }
.mm-caps-check { display: flex; gap: 16px; flex-wrap: wrap; padding: 6px 0; }
.mm-cap-opt { display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; }
.mm-test-result { margin-top: 12px; padding: 10px 12px; border-radius: 6px; font-size: 13px; }
.mm-test-ok { background: #d1fae5; color: #065f46; }
.mm-test-fail { background: #fee2e2; color: #991b1b; }
.btn { padding: 7px 14px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface-1); cursor: pointer; font-size: 13px; font-weight: 500; }
.btn--primary { background: var(--semantic-600, #2563eb); color: #fff; border-color: transparent; }
.btn--danger { color: #dc2626; }
.btn--sm { padding: 4px 10px; font-size: 12px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
