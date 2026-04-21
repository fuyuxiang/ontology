<template>
  <div class="agent-page">
    <!-- 左侧列表 -->
    <div class="agent-list">
      <div class="list-header">
        <span class="list-title">智能体</span>
        <a-button type="primary" size="small" @click="createNew">
          <template #icon><PlusOutlined /></template>
          新建
        </a-button>
      </div>
      <div class="list-body">
        <template v-if="agents.length > 0">
          <div
            v-for="a in agents"
            :key="a.id"
            class="agent-item"
            :class="{ active: current?.id === a.id }"
            @click="select(a)"
          >
            <div class="item-row">
              <span class="item-name">{{ a.name }}</span>
              <a-tag :color="a.status === 'published' ? 'success' : 'warning'" size="small">
                {{ a.status === 'published' ? '已发布' : '草稿' }}
              </a-tag>
            </div>
            <div class="item-meta">
              <span>{{ a.model_name || '未选模型' }}</span>
              <span>知识库 {{ a.kb_count ?? 0 }}</span>
              <span>实体 {{ a.entity_count ?? 0 }}</span>
            </div>
          </div>
        </template>
        <a-empty v-else description="暂无智能体" style="margin-top: 40px" />
      </div>
    </div>

    <!-- 右侧面板 -->
    <div class="agent-panel" v-if="current">
      <div class="panel-header">
        <div class="panel-title">
          <RobotOutlined style="margin-right: 8px; color: #2e5bff" />
          <span>{{ form.name || '未命名智能体' }}</span>
          <a-badge
            :status="current.status === 'published' ? 'success' : 'warning'"
            :text="current.status === 'published' ? '已发布' : '草稿'"
            style="margin-left: 12px"
          />
        </div>
        <div class="panel-actions">
          <a-popconfirm title="确认删除该智能体？" @confirm="deleteAgent">
            <a-button danger size="small">删除</a-button>
          </a-popconfirm>
          <a-button size="small" :loading="saving" @click="saveDraft">保存草稿</a-button>
          <a-button type="primary" size="small" :loading="publishing" @click="publish">发布</a-button>
        </div>
      </div>

      <a-tabs v-model:activeKey="activeTab" class="panel-tabs">
        <!-- 基础 -->
        <a-tab-pane key="basic" tab="基础">
          <div class="tab-content">
            <a-form layout="vertical">
              <a-form-item label="名称">
                <a-input v-model:value="form.name" placeholder="请输入智能体名称" />
              </a-form-item>
              <a-form-item label="描述">
                <a-textarea v-model:value="form.description" :rows="4" placeholder="请输入描述" />
              </a-form-item>
              <a-form-item label="标签">
                <a-select v-model:value="form.tags" mode="tags" placeholder="输入标签后回车" style="width: 100%" />
              </a-form-item>
            </a-form>
          </div>
        </a-tab-pane>

        <!-- 模型 -->
        <a-tab-pane key="model" tab="模型">
          <div class="tab-content">
            <a-form layout="vertical">
              <a-form-item label="模型">
                <a-select
                  v-model:value="form.model_id"
                  placeholder="请选择模型"
                  style="width: 100%"
                  :options="models.map(m => ({ value: m.id, label: m.name }))"
                />
              </a-form-item>
              <a-form-item label="温度 (Temperature)">
                <a-slider
                  v-model:value="form.tools_config.temperature"
                  :min="0" :max="2" :step="0.1"
                  :marks="{ 0: '0', 1: '1', 2: '2' }"
                />
              </a-form-item>
              <a-form-item label="最大 Token 数">
                <a-input-number
                  v-model:value="form.tools_config.max_tokens"
                  :min="1" :max="32768" :step="256"
                  style="width: 200px"
                />
              </a-form-item>
            </a-form>
          </div>
        </a-tab-pane>

        <!-- 知识 -->
        <a-tab-pane key="knowledge" tab="知识">
          <div class="tab-content">
            <a-form layout="vertical">
              <a-form-item label="知识库">
                <a-select
                  v-model:value="form.kb_ids"
                  mode="multiple"
                  placeholder="请选择知识库"
                  style="width: 100%"
                  :options="knowledgeBases.map(k => ({ value: k.id, label: k.name }))"
                />
              </a-form-item>
              <a-form-item label="实体">
                <a-select
                  v-model:value="form.entity_ids"
                  mode="multiple"
                  show-search
                  placeholder="搜索并选择实体"
                  style="width: 100%"
                  :filter-option="(input, opt) => opt.label.toLowerCase().includes(input.toLowerCase())"
                  :options="entities.map(e => ({ value: e.id, label: e.name }))"
                />
              </a-form-item>
            </a-form>
          </div>
        </a-tab-pane>

        <!-- 提示词 -->
        <a-tab-pane key="prompt" tab="提示词">
          <div class="tab-content">
            <div class="prompt-templates">
              <span style="margin-right: 8px; color: #666; font-size: 13px">预设模板：</span>
              <a-button size="small" @click="applyTemplate('customer')">客服助手</a-button>
              <a-button size="small" @click="applyTemplate('analysis')">数据分析</a-button>
              <a-button size="small" @click="applyTemplate('ontology')">本体问答</a-button>
            </div>
            <a-textarea
              v-model:value="form.system_prompt"
              :rows="16"
              placeholder="请输入系统提示词..."
              class="prompt-textarea"
            />
          </div>
        </a-tab-pane>

        <!-- 测试 -->
        <a-tab-pane key="test" tab="测试">
          <div class="test-panel">
            <div class="test-messages" ref="messagesRef">
              <div v-if="testMessages.length === 0" class="test-empty">
                <RobotOutlined style="font-size: 32px; color: #ccc" />
                <p style="color: #999; margin-top: 8px">发送消息开始测试</p>
              </div>
              <div
                v-for="(msg, i) in testMessages"
                :key="i"
                class="test-message"
                :class="msg.role"
              >
                <div v-if="msg.role === 'assistant'" class="msg-avatar">
                  <RobotOutlined />
                </div>
                <div class="msg-bubble">{{ msg.content }}</div>
                <div v-if="msg.role === 'user'" class="msg-avatar user-avatar">
                  <UserOutlined />
                </div>
              </div>
            </div>
            <div class="test-input-area">
              <a-button size="small" style="margin-right: 8px" @click="testMessages = []" title="清空对话">
                <template #icon><ClearOutlined /></template>
              </a-button>
              <a-input
                v-model:value="testInput"
                placeholder="输入测试消息..."
                @pressEnter="sendTest"
                :disabled="testLoading"
              />
              <a-button type="primary" :loading="testLoading" @click="sendTest" style="margin-left: 8px">
                <template #icon><SendOutlined /></template>
                发送
              </a-button>
            </div>
          </div>
        </a-tab-pane>
      </a-tabs>

      <!-- API 信息面板 -->
      <div v-if="current.status === 'published' && apiInfo" class="api-panel">
        <div class="api-panel-title">
          <ApiOutlined style="margin-right: 6px" />
          API 接入信息
        </div>
        <a-descriptions :column="1" size="small" bordered>
          <a-descriptions-item label="接口地址">
            <a-typography-text copyable>{{ apiInfo.endpoint }}</a-typography-text>
          </a-descriptions-item>
          <a-descriptions-item label="API Key">
            <a-typography-text copyable :ellipsis="{ tooltip: apiInfo.api_key }">{{ apiInfo.api_key }}</a-typography-text>
          </a-descriptions-item>
          <a-descriptions-item label="cURL 示例">
            <pre class="curl-example">{{ apiInfo.curl_example }}</pre>
          </a-descriptions-item>
        </a-descriptions>
      </div>
    </div>

    <!-- 未选中空状态 -->
    <div class="agent-empty" v-else>
      <a-empty description="请从左侧选择或新建智能体" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import {
  PlusOutlined, ApiOutlined, SendOutlined,
  RobotOutlined, UserOutlined, ClearOutlined
} from '@ant-design/icons-vue'
import { agentsApi, modelsApi } from '../../api/agents'
import client from '../../api/client'

const agents = ref([])
const models = ref([])
const knowledgeBases = ref([])
const entities = ref([])

const current = ref(null)
const activeTab = ref('basic')
const saving = ref(false)
const publishing = ref(false)
const apiInfo = ref(null)

const form = ref({
  name: '',
  description: '',
  model_id: null,
  system_prompt: '',
  kb_ids: [],
  entity_ids: [],
  tags: [],
  tools_config: { temperature: 0.7, max_tokens: 2048 }
})

const testMessages = ref([])
const testInput = ref('')
const testLoading = ref(false)
const messagesRef = ref(null)

const TEMPLATES = {
  customer: `你是一名专业的客服助手，负责解答用户的问题。\n请保持礼貌、耐心，用简洁清晰的语言回答。\n如果不确定答案，请如实告知并建议用户联系人工客服。`,
  analysis: `你是一名数据分析专家，擅长解读数据、发现规律和提供洞察。\n请根据用户提供的数据或问题，给出专业的分析结论和建议。\n回答时请使用结构化格式，必要时列出关键指标。`,
  ontology: `你是一名本体知识图谱问答助手，基于结构化知识库回答问题。\n请优先从知识库中检索相关实体和关系，给出准确的答案。\n回答时注明信息来源，对于知识库中没有的内容请明确说明。`
}

async function load() {
  try {
    const [agentRes, modelRes] = await Promise.all([agentsApi.list(), modelsApi.list()])
    agents.value = agentRes.data || agentRes
    models.value = modelRes.data || modelRes
  } catch (e) {
    message.error('加载失败：' + e.message)
  }
  try { knowledgeBases.value = (await client.get('/knowledge')).data || [] } catch (_) {}
  try { entities.value = (await client.get('/entities')).data || [] } catch (_) {}
}

function select(a) {
  current.value = a
  activeTab.value = 'basic'
  apiInfo.value = null
  form.value = {
    name: a.name || '',
    description: a.description || '',
    model_id: a.model_id || null,
    system_prompt: a.system_prompt || '',
    kb_ids: a.kb_ids || [],
    entity_ids: a.entity_ids || [],
    tags: a.tags || [],
    tools_config: { temperature: 0.7, max_tokens: 2048, ...(a.tools_config || {}) }
  }
  testMessages.value = []
  if (a.status === 'published') loadApiInfo(a.id)
}

async function loadApiInfo(id) {
  try { apiInfo.value = (await client.get(`/agents/${id}/api-info`)).data || null } catch (_) {}
}

function createNew() {
  current.value = { id: null, status: 'draft' }
  activeTab.value = 'basic'
  apiInfo.value = null
  form.value = {
    name: '', description: '', model_id: null, system_prompt: '',
    kb_ids: [], entity_ids: [], tags: [],
    tools_config: { temperature: 0.7, max_tokens: 2048 }
  }
  testMessages.value = []
}

async function saveDraft() {
  saving.value = true
  try {
    const payload = { ...form.value, status: 'draft' }
    const res = current.value.id
      ? await agentsApi.update(current.value.id, payload)
      : await agentsApi.create(payload)
    current.value = { ...current.value, ...(res.data || res) }
    await load()
    message.success('草稿已保存')
  } catch (e) {
    message.error('保存失败：' + e.message)
  } finally {
    saving.value = false
  }
}

async function publish() {
  publishing.value = true
  try {
    const payload = { ...form.value, status: 'published' }
    const res = current.value.id
      ? await agentsApi.update(current.value.id, payload)
      : await agentsApi.create(payload)
    current.value = { ...current.value, ...(res.data || res), status: 'published' }
    await load()
    await loadApiInfo(current.value.id)
    message.success('发布成功')
  } catch (e) {
    message.error('发布失败：' + e.message)
  } finally {
    publishing.value = false
  }
}

async function deleteAgent() {
  if (!current.value.id) { current.value = null; return }
  try {
    await agentsApi.delete(current.value.id)
    current.value = null
    await load()
    message.success('已删除')
  } catch (e) {
    message.error('删除失败：' + e.message)
  }
}

function applyTemplate(key) {
  form.value.system_prompt = TEMPLATES[key] || ''
}

async function sendTest() {
  const text = testInput.value.trim()
  if (!text || testLoading.value) return
  if (!current.value?.id) { message.warning('请先保存智能体'); return }

  testMessages.value.push({ role: 'user', content: text })
  testInput.value = ''
  testLoading.value = true

  const assistantMsg = { role: 'assistant', content: '' }
  testMessages.value.push(assistantMsg)
  const idx = testMessages.value.length - 1

  await nextTick()
  scrollToBottom()

  try {
    const resp = await fetch(`/api/v1/agents/${current.value.id}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: testMessages.value.slice(0, -1) })
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      for (const line of chunk.split('\n')) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6).trim()
        if (data === '[DONE]') continue
        try {
          const parsed = JSON.parse(data)
          const delta = parsed.choices?.[0]?.delta?.content || parsed.content || ''
          testMessages.value[idx].content += delta
          await nextTick()
          scrollToBottom()
        } catch (_) {}
      }
    }
  } catch (e) {
    testMessages.value[idx].content = '请求失败：' + e.message
  } finally {
    testLoading.value = false
  }
}

function scrollToBottom() {
  if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
}

onMounted(load)
</script>

<style scoped>
.agent-page {
  display: flex;
  flex-direction: row;
  height: 100vh;
  background: #f5f7fa;
  overflow: hidden;
}

.agent-list {
  width: 240px;
  min-width: 240px;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 12px;
  border-bottom: 1px solid #f0f0f0;
}

.list-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.list-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.agent-item {
  padding: 10px 14px;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: background 0.15s;
}

.agent-item:hover {
  background: #f5f7fa;
}

.agent-item.active {
  background: #e6f4ff;
  border-left: 3px solid #2e5bff;
}

.item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  color: #1a1a2e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 130px;
}

.item-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: #999;
}

.agent-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.panel-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0 20px;
}

.panel-tabs :deep(.ant-tabs-content-holder) {
  overflow-y: auto;
}

.tab-content {
  padding: 16px 0;
  max-width: 640px;
}

.prompt-templates {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.prompt-textarea {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.test-panel {
  display: flex;
  flex-direction: column;
  height: 480px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  margin-top: 8px;
}

.test-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.test-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.test-message {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.test-message.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  color: #666;
}

.msg-avatar.user-avatar {
  background: #2e5bff;
  color: #fff;
}

.msg-bubble {
  max-width: 70%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.test-message.user .msg-bubble {
  background: #2e5bff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.test-message.assistant .msg-bubble {
  background: #f0f0f0;
  color: #1a1a2e;
  border-bottom-left-radius: 4px;
}

.test-input-area {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-top: 1px solid #e8e8e8;
  background: #fff;
}

.agent-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.api-panel {
  margin: 0 20px 16px;
  padding: 14px 16px;
  background: #f0f5ff;
  border: 1px solid #d0e4ff;
  border-radius: 8px;
  flex-shrink: 0;
}

.api-panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #2e5bff;
  margin-bottom: 10px;
}

.curl-example {
  margin: 0;
  font-size: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
  white-space: pre-wrap;
  word-break: break-all;
  color: #333;
}
</style>

