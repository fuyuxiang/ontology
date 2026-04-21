<template>
  <div class="mm-page">
    <!-- Header -->
    <div class="mm-header">
      <div class="mm-header-left">
        <div class="mm-header-title">模型管理</div>
        <div class="mm-header-sub">统一注册和管理 LLM / VLM / ASR / Embedding 模型</div>
      </div>
      <a-button type="primary" size="large" @click="openCreate">
        <template #icon><PlusOutlined /></template>注册模型
      </a-button>
    </div>

    <!-- Stats bar -->
    <div class="mm-stats">
      <div class="mm-stat-card" v-for="s in stats" :key="s.label">
        <div class="mm-stat-icon" :style="{ background: s.bg }">
          <component :is="s.icon" :style="{ color: s.color, fontSize: '18px' }" />
        </div>
        <div>
          <div class="mm-stat-num">{{ s.value }}</div>
          <div class="mm-stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="mm-toolbar">
      <a-input-search v-model:value="searchText" placeholder="搜索模型名称或模型ID…" style="width:280px" allow-clear />
      <a-segmented v-model:value="filterCap" :options="capFilterOpts" />
      <a-radio-group v-model:value="filterStatus" button-style="solid" size="small">
        <a-radio-button value="">全部</a-radio-button>
        <a-radio-button value="active">启用</a-radio-button>
        <a-radio-button value="inactive">停用</a-radio-button>
      </a-radio-group>
    </div>

    <!-- Model cards -->
    <div class="mm-body">
      <template v-for="cap in capGroups" :key="cap.key">
        <div v-if="filteredGrouped[cap.key]?.length" class="mm-section">
          <div class="mm-section-title">
            <component :is="cap.icon" style="margin-right:6px" />{{ cap.label }}
            <a-badge :count="filteredGrouped[cap.key].length" :number-style="{ background: cap.color }" style="margin-left:8px" />
          </div>
          <a-row :gutter="[16, 16]">
            <a-col v-for="m in filteredGrouped[cap.key]" :key="m.id" :xs="24" :sm="12" :lg="8" :xl="6">
              <a-card hoverable class="mm-card" :class="`mm-card--${m.provider}`">
                <div class="mm-card-provider-bar" :style="{ background: providerGradient(m.provider) }"></div>
                <div class="mm-card-body">
                  <div class="mm-card-top">
                    <div class="mm-card-icon" :style="{ background: providerBg(m.provider) }">
                      <span class="mm-card-icon-text">{{ m.provider.charAt(0).toUpperCase() }}</span>
                    </div>
                    <div class="mm-card-info">
                      <div class="mm-card-name">{{ m.name }}</div>
                      <div class="mm-card-model">{{ m.model_name }}</div>
                    </div>
                    <a-switch
                      :checked="m.status === 'active'"
                      size="small"
                      @change="(v: boolean) => toggleStatus(m, v)"
                    />
                  </div>

                  <div class="mm-card-meta">
                    <a-tag :color="providerColor(m.provider)" style="margin:0">{{ providerLabel(m.provider) }}</a-tag>
                    <span class="mm-card-base" v-if="m.api_base">{{ shortUrl(m.api_base) }}</span>
                  </div>

                  <div class="mm-card-caps">
                    <a-tag v-for="c in m.capabilities" :key="c" :color="capColor(c)" style="font-size:11px">{{ c }}</a-tag>
                  </div>

                  <div class="mm-card-params" v-if="m.config_json?.temperature !== undefined">
                    <span class="mm-param">temp <b>{{ m.config_json.temperature }}</b></span>
                    <span class="mm-param" v-if="m.config_json?.max_tokens">max_tokens <b>{{ m.config_json.max_tokens }}</b></span>
                  </div>

                  <div class="mm-card-actions">
                    <a-button size="small" @click="testModel(m)" :loading="testingId === m.id">
                      <template #icon><ThunderboltOutlined /></template>测试
                    </a-button>
                    <a-button size="small" @click="openEdit(m)">
                      <template #icon><EditOutlined /></template>编辑
                    </a-button>
                    <a-popconfirm title="确认删除该模型？" @confirm="deleteModel(m.id)">
                      <a-button size="small" danger>
                        <template #icon><DeleteOutlined /></template>
                      </a-button>
                    </a-popconfirm>
                  </div>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </div>
      </template>

      <a-empty v-if="!hasResults" description="没有匹配的模型" style="margin-top:80px" />
    </div>

    <!-- Drawer -->
    <a-drawer
      :title="editing ? '编辑模型' : '注册模型'"
      :open="drawerOpen"
      width="500"
      @close="drawerOpen = false"
      :footer-style="{ textAlign: 'right' }"
    >
      <a-form :model="form" layout="vertical" ref="formRef">
        <a-divider orientation="left" orientation-margin="0">基本信息</a-divider>
        <a-form-item label="显示名称" name="name" :rules="[{ required: true, message: '请输入名称' }]">
          <a-input v-model:value="form.name" placeholder="如：GPT-4o 生产环境" />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="厂商" name="provider">
              <a-select v-model:value="form.provider" style="width:100%">
                <a-select-option v-for="p in providers" :key="p.value" :value="p.value">
                  <a-tag :color="p.color" style="margin-right:6px;font-size:11px">{{ p.label }}</a-tag>
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="模型名称" name="model_name" :rules="[{ required: true, message: '请输入' }]">
              <a-auto-complete v-model:value="form.model_name" :options="modelSuggestions" placeholder="qwen-max" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left" orientation-margin="0">接入配置</a-divider>
        <a-form-item label="API Base URL">
          <a-input v-model:value="form.api_base" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
        </a-form-item>
        <a-form-item label="API Key">
          <a-input-password v-model:value="form.api_key" placeholder="sk-…（留空保持原值）" />
        </a-form-item>

        <a-divider orientation="left" orientation-margin="0">能力与参数</a-divider>
        <a-form-item label="模型能力">
          <a-checkbox-group v-model:value="form.capabilities">
            <a-checkbox v-for="c in allCaps" :key="c.value" :value="c.value">
              <a-tag :color="c.color" style="cursor:pointer">{{ c.label }}</a-tag>
            </a-checkbox>
          </a-checkbox-group>
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="Temperature" extra="0=确定性，1=创造性，2=随机">
              <a-slider v-model:value="form.config_json.temperature" :min="0" :max="2" :step="0.1" :marks="{ 0: '0', 1: '1', 2: '2' }" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Max Tokens">
              <a-input-number v-model:value="form.config_json.max_tokens" :min="256" :step="512" style="width:100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-alert v-if="testResult" :type="testResult.ok ? 'success' : 'error'"
          :message="testResult.ok ? '✓ 连接成功' : '✗ 连接失败'"
          :description="testResult.ok ? testResult.reply : testResult.error"
          show-icon closable @close="testResult = null" style="margin-top:4px" />
      </a-form>

      <template #footer>
        <a-space>
          <a-button :loading="testing" @click="testCurrent">
            <template #icon><ThunderboltOutlined /></template>测试连接
          </a-button>
          <a-button @click="drawerOpen = false">取消</a-button>
          <a-button type="primary" :loading="saving" @click="save">保存</a-button>
        </a-space>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ThunderboltOutlined,
  RobotOutlined, EyeOutlined, AudioOutlined, FunctionOutlined,
} from '@ant-design/icons-vue'
import { modelsApi, type ModelRegistry } from '../../api/agents'

const models = ref<ModelRegistry[]>([])
const drawerOpen = ref(false)
const editing = ref<string | null>(null)
const saving = ref(false)
const testing = ref(false)
const testingId = ref<string | null>(null)
const testResult = ref<{ ok: boolean; reply?: string; error?: string } | null>(null)
const formRef = ref()
const searchText = ref('')
const filterCap = ref('全部')
const filterStatus = ref('')

const providers = [
  { value: 'openai', label: 'OpenAI', color: 'green' },
  { value: 'dashscope', label: 'DashScope', color: 'orange' },
  { value: 'ollama', label: 'Ollama', color: 'purple' },
  { value: 'azure', label: 'Azure', color: 'blue' },
  { value: 'custom', label: '自定义', color: 'default' },
]

const allCaps = [
  { value: 'chat', label: '对话 Chat', color: 'blue' },
  { value: 'vision', label: '视觉 Vision', color: 'purple' },
  { value: 'asr', label: '语音 ASR', color: 'cyan' },
  { value: 'embedding', label: '向量 Embedding', color: 'geekblue' },
]

const capGroups = [
  { key: 'chat', label: 'LLM 对话模型', icon: RobotOutlined, color: '#2e5bff' },
  { key: 'vision', label: 'VLM 视觉模型', icon: EyeOutlined, color: '#7c3aed' },
  { key: 'asr', label: 'ASR 语音识别', icon: AudioOutlined, color: '#0891b2' },
  { key: 'embedding', label: 'Embedding 向量', icon: FunctionOutlined, color: '#059669' },
]

const capFilterOpts = ['全部', 'LLM', 'VLM', 'ASR', 'Embedding']

const modelSuggestions = computed(() => {
  const map: Record<string, string[]> = {
    openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'text-embedding-3-large'],
    dashscope: ['qwen-max', 'qwen-plus', 'qwen-turbo', 'qwen-vl-max', 'text-embedding-v3'],
    ollama: ['llama3.2', 'qwen2.5', 'mistral', 'nomic-embed-text'],
    azure: ['gpt-4o', 'gpt-4', 'text-embedding-ada-002'],
  }
  return (map[form.value.provider] || []).map(v => ({ value: v }))
})

const providerColor = (p: string) => ({ openai: 'green', dashscope: 'orange', ollama: 'purple', azure: 'blue', custom: 'default' }[p] || 'default')
const providerLabel = (p: string) => providers.find(x => x.value === p)?.label || p
const providerGradient = (p: string) => ({ openai: 'linear-gradient(90deg,#10b981,#34d399)', dashscope: 'linear-gradient(90deg,#f59e0b,#fbbf24)', ollama: 'linear-gradient(90deg,#8b5cf6,#a78bfa)', azure: 'linear-gradient(90deg,#3b82f6,#60a5fa)', custom: 'linear-gradient(90deg,#6b7280,#9ca3af)' }[p] || '#e5e7eb')
const providerBg = (p: string) => ({ openai: '#ecfdf5', dashscope: '#fffbeb', ollama: '#f5f3ff', azure: '#eff6ff', custom: '#f9fafb' }[p] || '#f9fafb')
const capColor = (c: string) => ({ chat: 'blue', vision: 'purple', asr: 'cyan', embedding: 'geekblue' }[c] || 'default')
const shortUrl = (url: string) => url.replace(/^https?:\/\//, '').split('/')[0]

const stats = computed(() => [
  { label: '全部模型', value: models.value.length, icon: RobotOutlined, bg: '#eff6ff', color: '#2e5bff' },
  { label: '对话模型', value: models.value.filter(m => m.capabilities?.includes('chat')).length, icon: RobotOutlined, bg: '#ecfdf5', color: '#10b981' },
  { label: '视觉模型', value: models.value.filter(m => m.capabilities?.includes('vision')).length, icon: EyeOutlined, bg: '#f5f3ff', color: '#8b5cf6' },
  { label: '已启用', value: models.value.filter(m => m.status === 'active').length, icon: ThunderboltOutlined, bg: '#fefce8', color: '#f59e0b' },
])

const filteredModels = computed(() => {
  let list = models.value
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(m => m.name.toLowerCase().includes(q) || m.model_name.toLowerCase().includes(q))
  }
  if (filterStatus.value) list = list.filter(m => m.status === filterStatus.value)
  if (filterCap.value !== '全部') {
    const capMap: Record<string, string> = { LLM: 'chat', VLM: 'vision', ASR: 'asr', Embedding: 'embedding' }
    list = list.filter(m => m.capabilities?.includes(capMap[filterCap.value]))
  }
  return list
})

const filteredGrouped = computed(() => {
  const g: Record<string, ModelRegistry[]> = {}
  for (const m of filteredModels.value) {
    for (const c of (m.capabilities || [])) {
      if (!g[c]) g[c] = []
      if (!g[c].find(x => x.id === m.id)) g[c].push(m)
    }
  }
  return g
})

const hasResults = computed(() => capGroups.some(c => filteredGrouped.value[c.key]?.length))

const emptyForm = () => ({
  name: '', provider: 'dashscope', model_name: '', api_base: '', api_key: '',
  capabilities: ['chat'] as string[],
  config_json: { temperature: 0.7, max_tokens: 2048 },
  status: 'active',
})
const form = ref(emptyForm())

async function load() { models.value = await modelsApi.list() }

function openCreate() {
  editing.value = null; form.value = emptyForm(); testResult.value = null; drawerOpen.value = true
}

function openEdit(m: ModelRegistry) {
  editing.value = m.id
  form.value = { name: m.name, provider: m.provider, model_name: m.model_name, api_base: m.api_base || '', api_key: '', capabilities: [...(m.capabilities || [])], config_json: { temperature: 0.7, max_tokens: 2048, ...(m.config_json || {}) }, status: m.status }
  testResult.value = null; drawerOpen.value = true
}

async function save() {
  try { await formRef.value?.validate() } catch { return }
  saving.value = true
  try {
    const payload = { ...form.value }
    if (!payload.api_key) delete (payload as any).api_key
    editing.value ? await modelsApi.update(editing.value, payload) : await modelsApi.create(payload)
    message.success('保存成功'); drawerOpen.value = false; await load()
  } finally { saving.value = false }
}

async function deleteModel(id: string) {
  await modelsApi.delete(id); message.success('已删除'); await load()
}

async function toggleStatus(m: ModelRegistry, active: boolean) {
  await modelsApi.update(m.id, { status: active ? 'active' : 'inactive' })
  await load()
}

async function testModel(m: ModelRegistry) {
  testingId.value = m.id
  const r = await modelsApi.test(m.id)
  testingId.value = null
  r.ok ? message.success(`✓ ${m.name} 连接成功`) : message.error(`✗ ${m.name}: ${r.error}`)
}

async function testCurrent() {
  if (!editing.value) { message.warning('请先保存后再测试'); return }
  testing.value = true; testResult.value = null
  try { testResult.value = await modelsApi.test(editing.value) } finally { testing.value = false }
}

onMounted(load)
</script>

<style scoped>
.mm-page { height: 100vh; display: flex; flex-direction: column; background: #f5f7fa; overflow: hidden; }
.mm-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px 16px; background: #fff; border-bottom: 1px solid #e8e8e8; flex-shrink: 0; }
.mm-header-title { font-size: 20px; font-weight: 700; color: #1a1a2e; }
.mm-header-sub { font-size: 13px; color: #999; margin-top: 2px; }
.mm-stats { display: flex; gap: 16px; padding: 16px 24px; background: #fff; border-bottom: 1px solid #f0f0f0; flex-shrink: 0; }
.mm-stat-card { display: flex; align-items: center; gap: 12px; padding: 12px 20px; background: #f8faff; border-radius: 10px; border: 1px solid #e8eeff; flex: 1; }
.mm-stat-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.mm-stat-num { font-size: 22px; font-weight: 700; color: #1a1a2e; line-height: 1; }
.mm-stat-label { font-size: 12px; color: #999; margin-top: 3px; }
.mm-toolbar { display: flex; align-items: center; gap: 12px; padding: 12px 24px; background: #fff; border-bottom: 1px solid #f0f0f0; flex-shrink: 0; }
.mm-body { flex: 1; overflow-y: auto; padding: 20px 24px; }
.mm-section { margin-bottom: 28px; }
.mm-section-title { display: flex; align-items: center; font-size: 13px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px; }
.mm-card { border-radius: 10px !important; overflow: hidden; border: 1px solid #e8e8e8 !important; }
.mm-card-provider-bar { height: 4px; margin: -24px -24px 16px; }
.mm-card-body { padding: 0; }
.mm-card-top { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.mm-card-icon { width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.mm-card-icon-text { font-size: 16px; font-weight: 700; color: #555; }
.mm-card-info { flex: 1; min-width: 0; }
.mm-card-name { font-weight: 600; font-size: 14px; color: #1a1a2e; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mm-card-model { font-size: 11px; color: #999; font-family: monospace; margin-top: 2px; }
.mm-card-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.mm-card-base { font-size: 11px; color: #aaa; font-family: monospace; }
.mm-card-caps { margin-bottom: 10px; display: flex; flex-wrap: wrap; gap: 4px; }
.mm-card-params { display: flex; gap: 12px; margin-bottom: 12px; }
.mm-param { font-size: 11px; color: #999; background: #f5f5f5; padding: 2px 8px; border-radius: 4px; }
.mm-param b { color: #555; }
.mm-card-actions { display: flex; gap: 8px; padding-top: 10px; border-top: 1px solid #f5f5f5; }
:deep(.ant-card-body) { padding: 16px 20px; }
</style>
