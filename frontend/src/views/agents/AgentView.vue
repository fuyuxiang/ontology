<template>
  <div class="av-page">
    <div class="av-list">
      <div class="av-list-head">
        <span class="av-list-title">智能体</span>
        <a-button type="primary" size="small" @click="createNew">
          <template #icon><PlusOutlined /></template>新建
        </a-button>
      </div>
      <div class="av-list-body">
        <div
          v-for="a in agents" :key="a.id"
          class="av-item" :class="{ 'av-item--active': current?.id === a.id }"
          @click="select(a)"
        >
          <div class="av-item-name">{{ a.name }}</div>
          <div class="av-item-meta">
            <a-tag :color="a.status === 'published' ? 'success' : 'warning'" style="font-size:11px">
              {{ a.status === 'published' ? '已发布' : '草稿' }}
            </a-tag>
            <span v-if="a.model_name" class="av-item-model">{{ a.model_name }}</span>
          </div>
        </div>
        <a-empty v-if="!agents.length" :image="Empty.PRESENTED_IMAGE_SIMPLE" description="暂无智能体" style="margin-top:40px" />
      </div>
    </div>

    <div class="av-panel" v-if="current">
      <div class="av-panel-head">
        <span class="av-panel-title">{{ form.name || '未命名智能体' }}</span>
        <a-space>
          <a-popconfirm v-if="current.id" title="确认删除？" @confirm="deleteAgent">
            <a-button danger size="small">删除</a-button>
          </a-popconfirm>
          <a-button size="small" :loading="saving" @click="saveDraft">保存草稿</a-button>
          <a-button type="primary" size="small" :loading="publishing" @click="publish">
            {{ current.status === 'published' ? '重新发布' : '发布' }}
          </a-button>
        </a-space>
      </div>

      <a-tabs v-model:activeKey="activeTab" class="av-tabs">
        <a-tab-pane key="basic" tab="基础">
          <a-form :model="form" layout="vertical" style="max-width:600px">
            <a-form-item label="名称">
              <a-input v-model:value="form.name" placeholder="智能体名称" />
            </a-form-item>
            <a-form-item label="描述">
              <a-textarea v-model:value="form.description" placeholder="描述该智能体的用途" :rows="3" />
            </a-form-item>
            <a-form-item label="标签">
              <a-select v-model:value="form.tags" mode="tags" placeholder="输入后回车添加标签" style="width:100%" />
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="model" tab="模型">
          <a-form :model="form" layout="vertical" style="max-width:600px">
            <a-form-item label="选择模型">
              <a-select v-model:value="form.model_id" placeholder="使用全局默认模型" allow-clear style="width:100%">
                <a-select-option v-for="m in models" :key="m.id" :value="m.id">
                  {{ m.name }} <span style="color:#999;font-size:12px">{{ m.model_name }}</span>
                </a-select-option>
              </a-select>
            </a-form-item>
            <a-row :gutter="16">
              <a-col :span="12">
                <a-form-item label="Temperature 覆盖">
                  <a-input-number v-model:value="form.tools_config.temperature" :min="0" :max="2" :step="0.1" style="width:100%" placeholder="使用模型默认" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="Max Tokens 覆盖">
                  <a-input-number v-model:value="form.tools_config.max_tokens" :min="256" :step="256" style="width:100%" placeholder="使用模型默认" />
                </a-form-item>
              </a-col>
            </a-row>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="knowledge" tab="知识">
          <a-form layout="vertical" style="max-width:600px">
            <a-form-item label="关联知识库">
              <a-select v-model:value="form.kb_ids" mode="multiple" placeholder="选择知识库" style="width:100%">
                <a-select-option v-for="kb in knowledgeBases" :key="kb.id" :value="kb.id">{{ kb.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="关联本体实体">
              <a-select v-model:value="form.entity_ids" mode="multiple" placeholder="选择本体实体" style="width:100%" :filter-option="filterEntity" show-search>
                <a-select-option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name_cn || e.name }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="prompt" tab="提示词">
          <a-form layout="vertical">
            <a-form-item label="系统 Prompt">
              <a-textarea v-model:value="form.system_prompt" placeholder="定义智能体的角色、行为和约束…" :rows="16" style="font-family:monospace;font-size:13px" />
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>

      <!-- API Info -->
      <div v-if="current.status === 'published' && apiInfo" class="av-api-panel">
        <div class="av-api-title">
          <ApiOutlined style="margin-right:6px" />API 接入信息
        </div>
        <a-descriptions :column="1" bordered size="small">
          <a-descriptions-item label="Endpoint">
            <a-typography-text code copyable>{{ apiInfo.endpoint }}</a-typography-text>
          </a-descriptions-item>
          <a-descriptions-item label="API Key">
            <a-typography-text code copyable>{{ apiInfo.api_key }}</a-typography-text>
          </a-descriptions-item>
        </a-descriptions>
        <div style="margin-top:12px">
          <div style="font-size:12px;color:#999;margin-bottom:6px">cURL 示例</div>
          <a-typography-paragraph>
            <pre style="font-size:12px;background:#f5f5f5;padding:12px;border-radius:6px;overflow-x:auto">{{ apiInfo.curl }}</pre>
          </a-typography-paragraph>
        </div>
      </div>
    </div>

    <div class="av-panel av-panel--empty" v-else>
      <a-empty description="选择或新建一个智能体" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message, Empty } from 'ant-design-vue'
import { PlusOutlined, ApiOutlined } from '@ant-design/icons-vue'
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

const emptyForm = () => ({
  name: '',
  description: '',
  model_id: null as string | null,
  system_prompt: '',
  kb_ids: [] as string[],
  entity_ids: [] as string[],
  tags: [] as string[],
  tools_config: {} as Record<string, any>,
})

const form = ref(emptyForm())

function fillForm(a: AgentItem) {
  form.value = {
    name: a.name,
    description: a.description,
    model_id: a.model_id || null,
    system_prompt: a.system_prompt,
    kb_ids: [...(a.kb_ids || [])],
    entity_ids: [...(a.entity_ids || [])],
    tags: [...(a.tags || [])],
    tools_config: { ...(a.tools_config || {}) },
  }
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
  current.value = { id: '', name: '', description: '', tags: [], model_id: null, model_name: null, system_prompt: '', kb_ids: [], entity_ids: [], tools_config: {}, status: 'draft', api_key: null, created_at: '', updated_at: '' }
  form.value = emptyForm()
  activeTab.value = 'basic'
  apiInfo.value = null
}

async function saveDraft() {
  if (!form.value.name) { message.warning('请输入智能体名称'); return }
  saving.value = true
  try {
    const payload = { ...form.value }
    if (current.value?.id) {
      const updated = await agentsApi.update(current.value.id, payload)
      current.value = updated
    } else {
      const created = await agentsApi.create(payload)
      current.value = created
    }
    message.success('保存成功')
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
    message.success('发布成功')
    await load()
  } finally {
    publishing.value = false
  }
}

async function deleteAgent() {
  if (!current.value?.id) return
  await agentsApi.delete(current.value.id)
  message.success('已删除')
  current.value = null
  await load()
}

function filterEntity(input: string, option: any) {
  return option.children?.toLowerCase().includes(input.toLowerCase())
}

onMounted(async () => {
  await load()
  models.value = await modelsApi.list()
  try { knowledgeBases.value = (await client.get('/knowledge')).data } catch {}
  try {
    const r = await client.get('/entities')
    entities.value = r.data?.items || r.data || []
  } catch {}
})
</script>

<style scoped>
.av-page { display: flex; height: 100vh; overflow: hidden; background: #f5f7fa; }
.av-list { width: 240px; min-width: 240px; background: #fff; border-right: 1px solid #e8e8e8; display: flex; flex-direction: column; }
.av-list-head { display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid #e8e8e8; }
.av-list-title { font-weight: 600; font-size: 15px; }
.av-list-body { flex: 1; overflow-y: auto; }
.av-item { padding: 12px 16px; cursor: pointer; border-bottom: 1px solid #f0f0f0; transition: background 0.15s; }
.av-item:hover { background: #f5f7fa; }
.av-item--active { background: #e6f4ff; border-right: 2px solid #2e5bff; }
.av-item-name { font-size: 14px; font-weight: 500; margin-bottom: 6px; }
.av-item-meta { display: flex; align-items: center; gap: 6px; }
.av-item-model { font-size: 11px; color: #999; }
.av-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #fff; }
.av-panel--empty { align-items: center; justify-content: center; }
.av-panel-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid #e8e8e8; flex-shrink: 0; }
.av-panel-title { font-size: 16px; font-weight: 600; }
.av-api-panel { margin: 0 24px 24px; padding: 16px; background: #f8faff; border: 1px solid #d0e4ff; border-radius: 8px; flex-shrink: 0; }
.av-api-title { font-weight: 600; font-size: 14px; margin-bottom: 12px; color: #2e5bff; }
:deep(.av-tabs) { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
:deep(.av-tabs .ant-tabs-nav) { padding: 0 24px; margin: 0; flex-shrink: 0; }
:deep(.av-tabs .ant-tabs-content-holder) { flex: 1; overflow-y: auto; }
:deep(.av-tabs .ant-tabs-content) { height: 100%; }
:deep(.av-tabs .ant-tabs-tabpane) { padding: 20px 24px; }
</style>
