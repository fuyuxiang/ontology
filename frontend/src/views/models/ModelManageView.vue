<template>
  <div class="mm-page">
    <a-page-header title="模型管理" subtitle="统一注册和管理 LLM / VLM / ASR / Embedding 模型">
      <template #extra>
        <a-button type="primary" @click="openCreate">
          <template #icon><PlusOutlined /></template>
          注册模型
        </a-button>
      </template>
    </a-page-header>

    <div class="mm-body">
      <template v-for="cap in capGroups" :key="cap.key">
        <div v-if="grouped[cap.key]?.length" class="mm-section">
          <div class="mm-section-title">{{ cap.label }}</div>
          <a-row :gutter="[16, 16]">
            <a-col v-for="m in grouped[cap.key]" :key="m.id" :xs="24" :sm="12" :lg="8" :xl="6">
              <a-card hoverable class="mm-card">
                <template #title>
                  <div class="mm-card-head">
                    <span class="mm-card-name">{{ m.name }}</span>
                    <a-tag :color="providerColor(m.provider)">{{ m.provider }}</a-tag>
                    <a-badge :status="m.status === 'active' ? 'success' : 'default'" :text="m.status === 'active' ? '启用' : '停用'" />
                  </div>
                </template>
                <div class="mm-card-model">{{ m.model_name }}</div>
                <div class="mm-card-caps">
                  <a-tag v-for="c in m.capabilities" :key="c" color="blue" style="margin-bottom:4px">{{ c }}</a-tag>
                </div>
                <template #actions>
                  <a-tooltip title="测试连接"><ThunderboltOutlined @click="testModel(m)" /></a-tooltip>
                  <a-tooltip title="编辑"><EditOutlined @click="openEdit(m)" /></a-tooltip>
                  <a-popconfirm title="确认删除该模型？" @confirm="deleteModel(m.id)">
                    <a-tooltip title="删除"><DeleteOutlined /></a-tooltip>
                  </a-popconfirm>
                </template>
              </a-card>
            </a-col>
          </a-row>
        </div>
      </template>

      <a-empty v-if="!models.length" description="暂无模型，点击「注册模型」添加" style="margin-top:80px" />
    </div>

    <!-- Drawer -->
    <a-drawer
      :title="editing ? '编辑模型' : '注册模型'"
      :open="drawerOpen"
      width="480"
      @close="drawerOpen = false"
      :footer-style="{ textAlign: 'right' }"
    >
      <a-form :model="form" layout="vertical" ref="formRef">
        <a-form-item label="名称" name="name" :rules="[{ required: true, message: '请输入名称' }]">
          <a-input v-model:value="form.name" placeholder="模型显示名称" />
        </a-form-item>
        <a-form-item label="厂商" name="provider">
          <a-select v-model:value="form.provider">
            <a-select-option value="openai">OpenAI</a-select-option>
            <a-select-option value="dashscope">DashScope (阿里云)</a-select-option>
            <a-select-option value="ollama">Ollama</a-select-option>
            <a-select-option value="azure">Azure OpenAI</a-select-option>
            <a-select-option value="custom">自定义</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模型名称" name="model_name" :rules="[{ required: true, message: '请输入模型名称' }]">
          <a-input v-model:value="form.model_name" placeholder="如 gpt-4o / qwen-max" />
        </a-form-item>
        <a-form-item label="API Base URL">
          <a-input v-model:value="form.api_base" placeholder="https://api.openai.com/v1" />
        </a-form-item>
        <a-form-item label="API Key">
          <a-input-password v-model:value="form.api_key" placeholder="sk-..." />
        </a-form-item>
        <a-form-item label="能力">
          <a-checkbox-group v-model:value="form.capabilities" :options="allCaps" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Temperature">
              <a-input-number v-model:value="form.config_json.temperature" :min="0" :max="2" :step="0.1" style="width:100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Max Tokens">
              <a-input-number v-model:value="form.config_json.max_tokens" :min="256" :step="256" style="width:100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-alert v-if="testResult" :type="testResult.ok ? 'success' : 'error'"
          :message="testResult.ok ? '连接成功: ' + testResult.reply : '连接失败: ' + testResult.error"
          show-icon style="margin-top:8px" />
      </a-form>
      <template #footer>
        <a-space>
          <a-button :loading="testing" @click="testCurrent">测试连接</a-button>
          <a-button type="primary" :loading="saving" @click="save">保存</a-button>
        </a-space>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, EditOutlined, DeleteOutlined, ThunderboltOutlined } from '@ant-design/icons-vue'
import { modelsApi, type ModelRegistry } from '../../api/agents'

const models = ref<ModelRegistry[]>([])
const drawerOpen = ref(false)
const editing = ref<string | null>(null)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ ok: boolean; reply?: string; error?: string } | null>(null)
const formRef = ref()

const allCaps = ['chat', 'vision', 'asr', 'embedding']
const capGroups = [
  { key: 'chat', label: 'LLM 对话模型' },
  { key: 'vision', label: 'VLM 视觉模型' },
  { key: 'asr', label: 'ASR 语音识别' },
  { key: 'embedding', label: 'Embedding 向量模型' },
]

const providerColor = (p: string) => ({ openai: 'green', dashscope: 'orange', ollama: 'purple', azure: 'blue', custom: 'default' }[p] || 'default')

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
    name: m.name, provider: m.provider, model_name: m.model_name,
    api_base: m.api_base || '', api_key: '',
    capabilities: [...(m.capabilities || [])],
    config_json: { temperature: 0.7, max_tokens: 2048, ...(m.config_json || {}) },
    status: m.status,
  }
  testResult.value = null
  drawerOpen.value = true
}

async function save() {
  try { await formRef.value?.validate() } catch { return }
  saving.value = true
  try {
    const payload = { ...form.value, model_id: undefined }
    if (!payload.api_key) delete (payload as any).api_key
    if (editing.value) await modelsApi.update(editing.value, payload)
    else await modelsApi.create(payload)
    message.success('保存成功')
    drawerOpen.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function deleteModel(id: string) {
  await modelsApi.delete(id)
  message.success('已删除')
  await load()
}

async function testModel(m: ModelRegistry) {
  const hide = message.loading('测试中…', 0)
  const r = await modelsApi.test(m.id)
  hide()
  r.ok ? message.success(`连接成功: ${r.reply}`) : message.error(`连接失败: ${r.error}`)
}

async function testCurrent() {
  if (!editing.value) { message.warning('请先保存模型后再测试'); return }
  testing.value = true
  testResult.value = null
  try { testResult.value = await modelsApi.test(editing.value) }
  finally { testing.value = false }
}

onMounted(load)
</script>

<style scoped>
.mm-page { height: 100vh; display: flex; flex-direction: column; background: #f5f7fa; }
.mm-body { flex: 1; overflow-y: auto; padding: 0 24px 24px; }
.mm-section { margin-bottom: 32px; }
.mm-section-title { font-size: 13px; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
.mm-card-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.mm-card-name { font-weight: 600; font-size: 14px; flex: 1; }
.mm-card-model { font-size: 12px; color: #999; font-family: monospace; margin-bottom: 8px; }
.mm-card-caps { min-height: 28px; }
:deep(.ant-page-header) { background: #fff; border-bottom: 1px solid #e8e8e8; padding: 16px 24px; }
:deep(.ant-card-actions) { background: #fafafa; }
</style>
