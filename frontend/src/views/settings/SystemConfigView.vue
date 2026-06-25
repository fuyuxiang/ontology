<template>
  <div class="dashboard-container">
    <!-- Header -->
    <div class="dashboard-header">
      <h2>{{ t('systemConfig.title') }}</h2>
      <div class="header-right">
        <a-button @click="showHistory = true">
          <template #icon><HistoryOutlined /></template>
          {{ t('common.changeHistory') }}
        </a-button>
      </div>
    </div>

    <div class="config-body">
      <!-- 左侧导航 -->
      <nav class="config-nav">
        <a-button
          v-for="g in groupList"
          :key="g.key"
          :type="activeGroup === g.key ? 'primary' : 'text'"
          :ghost="activeGroup === g.key"
          block
          class="config-nav__item"
          @click="scrollToGroup(g.key)"
        >
          <span class="config-nav__icon">{{ g.icon }}</span>
          {{ g.label }}
        </a-button>
      </nav>

      <!-- 右侧配置区 -->
      <div class="config-content">
        <template v-for="g in groupList" :key="g.key">
          <!-- AI 配置：特殊处理为模型卡片列表 -->
          <a-card v-if="g.key === 'ai'" :bordered="false" :id="`config-group-${g.key}`" style="margin-bottom: 16px;">
            <template #title>
              <div class="config-card-title">
                <div>
                  <span>{{ g.label }}</span>
                  <p class="config-card-desc">{{ g.desc }}</p>
                </div>
                <a-button type="primary" size="small" @click="openAddModel">＋ 添加模型</a-button>
              </div>
            </template>

            <div class="model-grid">
              <div v-for="model in aiModels" :key="model.id" class="model-card" :class="{ 'model-card--default': model.is_default }">
                <div class="model-card__header">
                  <div class="model-card__provider">{{ model.provider }}</div>
                  <div class="model-card__actions">
                    <span v-if="model.is_default" class="model-card__default-tag">默认</span>
                    <a-button type="text" size="small" @click="openEditModel(model)">编辑</a-button>
                    <a-button type="text" size="small" danger @click="handleDeleteModel(model.id)">删除</a-button>
                  </div>
                </div>
                <div class="model-card__name">{{ model.name }}</div>
                <div class="model-card__id">{{ model.model_id }}</div>
                <div class="model-card__config">
                  <span>Temperature: {{ model.temperature }}</span>
                  <span>Max Tokens: {{ model.max_tokens }}</span>
                </div>
                <div class="model-card__scenes">
                  <span v-for="s in model.scenes" :key="s" class="model-card__scene-tag">{{ sceneLabel(s) }}</span>
                </div>
                <div class="model-card__footer">
                  <a-button size="small" @click="handleTestModel(model)" :loading="testingModelId === model.id">
                    {{ testingModelId === model.id ? '测试中...' : '🔗 测试连通性' }}
                  </a-button>
                  <a-button v-if="!model.is_default" size="small" type="link" @click="handleSetDefault(model.id)">设为默认</a-button>
                </div>
                <div v-if="testResults[model.id]" class="model-card__test-result" :class="testResults[model.id]?.success ? 'model-card__test-result--ok' : 'model-card__test-result--err'">
                  {{ testResults[model.id]?.success ? '✓' : '✗' }} {{ testResults[model.id]?.message }}
                </div>
              </div>
            </div>

            <div v-if="!aiModels.length" class="empty-state">
              <div class="empty-state__icon">🤖</div>
              <p class="empty-state__title">暂无模型配置</p>
              <p class="empty-state__desc">点击「添加模型」配置第一个 AI 模型</p>
            </div>
          </a-card>

          <!-- 其他配置组 -->
          <a-card v-else :bordered="false" :id="`config-group-${g.key}`" style="margin-bottom: 16px;">
            <template #title>
              <div class="config-card-title">
                <div>
                  <span>{{ g.label }}</span>
                  <p class="config-card-desc">{{ g.desc }}</p>
                </div>
              </div>
            </template>

            <div class="config-fields">
              <template v-for="item in getGroupItems(g.key)" :key="item.key">
                <div class="config-field">
                  <label class="config-field__label">{{ item.description || item.key }}</label>
                  <template v-if="item.is_sensitive">
                    <a-input-password v-model:value="editingValues[item.key]" placeholder="••••••••" />
                  </template>
                  <template v-else-if="isTextField(item.key)">
                    <a-input v-model:value="editingValues[item.key]" :placeholder="item.value || ''" />
                  </template>
                  <template v-else-if="isNumberField(item.key)">
                    <a-input-number v-model:value="editingValues[item.key]" :min="getMin(item.key)" :max="getMax(item.key)" :step="getStep(item.key)" style="width: 160px" />
                  </template>
                  <template v-else-if="getSelectOptions(item.key)">
                    <a-select v-model:value="editingValues[item.key]" :options="getSelectOptions(item.key)" style="width: 240px" />
                  </template>
                  <template v-else>
                    <a-input v-model:value="editingValues[item.key]" :placeholder="item.value || ''" />
                  </template>
                </div>
              </template>
            </div>

            <div class="config-card-footer">
              <div>
                <a-button v-if="g.key === 'notification'" @click="handleTestEmail" :loading="testing">📧 发送测试邮件</a-button>
              </div>
              <div class="config-card-footer__right">
                <a-button @click="handleReset(g.key)">恢复默认</a-button>
                <a-button type="primary" @click="handleSave(g.key)" :disabled="!hasChanges(g.key)" :loading="saving">保存</a-button>
              </div>
            </div>

            <div v-if="testResult && testGroup === g.key" class="test-result" :class="testResult.success ? 'test-result--ok' : 'test-result--err'">
              <span>{{ testResult.success ? '✓' : '✗' }}</span>
              {{ testResult.message }}
            </div>
          </a-card>
        </template>
      </div>
    </div>

    <!-- 模型编辑弹窗 -->
    <a-modal v-model:open="modelModalOpen" :title="modelModalIsEdit ? '编辑模型' : '添加模型'" :width="560" @ok="handleSaveModel" @cancel="modelModalOpen = false">
      <div class="modal-form">
        <div class="modal-form__row">
          <div class="modal-form__field">
            <label class="modal-form__label">模型名称 <span class="modal-form__required">*</span></label>
            <a-input v-model:value="modelForm.name" placeholder="如：Claude Sonnet 4" />
          </div>
          <div class="modal-form__field">
            <label class="modal-form__label">提供商</label>
            <a-select v-model:value="modelForm.provider" :options="providerOptions" style="width: 100%" />
          </div>
        </div>
        <div class="modal-form__field">
          <label class="modal-form__label">模型 ID <span class="modal-form__required">*</span></label>
          <a-input v-model:value="modelForm.model_id" placeholder="如：claude-sonnet-4-20250514" />
        </div>
        <div class="modal-form__field">
          <label class="modal-form__label">API Key</label>
          <a-input-password v-model:value="modelForm.api_key" placeholder="请输入 API Key" />
        </div>
        <div class="modal-form__field">
          <label class="modal-form__label">Base URL</label>
          <a-input v-model:value="modelForm.base_url" placeholder="https://api.anthropic.com" />
        </div>
        <div class="modal-form__row">
          <div class="modal-form__field">
            <label class="modal-form__label">Temperature</label>
            <a-slider v-model:value="modelForm.temperature" :min="0" :max="2" :step="0.1" style="width: 100%" />
          </div>
          <div class="modal-form__field" style="width: 120px">
            <label class="modal-form__label">&nbsp;</label>
            <a-input-number v-model:value="modelForm.temperature" :min="0" :max="2" :step="0.1" style="width: 100%" />
          </div>
        </div>
        <div class="modal-form__field">
          <label class="modal-form__label">最大 Token 数</label>
          <a-input-number v-model:value="modelForm.max_tokens" :min="256" :max="128000" :step="256" style="width: 160px" />
        </div>
        <div class="modal-form__field">
          <label class="modal-form__label">使用场景</label>
          <a-checkbox-group v-model:value="modelForm.scenes" :options="sceneOptions" />
        </div>
      </div>
    </a-modal>

    <!-- 变更记录抽屉 -->
    <a-drawer v-model:open="showHistory" title="配置变更记录" :width="520" @close="showHistory = false">
      <div class="history-list">
        <div v-for="(record, idx) in changeHistory" :key="idx" class="history-item">
          <div class="history-item__dot" :class="`history-item__dot--${record.type}`"></div>
          <div class="history-item__content">
            <div class="history-item__header">
              <span class="history-item__user">{{ record.user }}</span>
              <span class="history-item__time">{{ record.time }}</span>
            </div>
            <div class="history-item__desc">{{ record.desc }}</div>
          </div>
        </div>
        <div v-if="!changeHistory.length" class="empty-state">暂无变更记录</div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, computed, watch } from 'vue'
import {
  Input as AInput, InputPassword as AInputPassword, InputNumber as AInputNumber,
  Select as ASelect, Drawer as ADrawer, Modal as AModal,
  Slider as ASlider, CheckboxGroup as ACheckboxGroup,
  Card as ACard, Button as AButton,
} from 'ant-design-vue'
import { HistoryOutlined } from '@ant-design/icons-vue'
import { systemConfigApi, type ConfigItem, type TestResult, type AiModel, type ModelScene } from '../../api/systemConfig'
import { useToast } from '../../composables/useToast'
import { useLanguage } from '../../composables/useLanguage'

const { success, error } = useToast()
const { switchLanguage, t } = useLanguage()

const groupList = computed(() => [
  { key: 'basic', label: t('systemConfig.basic'), desc: t('systemConfig.basicDesc'), icon: '⚙️' },
  { key: 'auth', label: t('systemConfig.auth'), desc: t('systemConfig.authDesc'), icon: '🔐' },
  { key: 'storage', label: t('systemConfig.storage'), desc: t('systemConfig.storageDesc'), icon: '📁' },
  { key: 'ai', label: t('systemConfig.ai'), desc: t('systemConfig.aiDesc'), icon: '🤖' },
  { key: 'notification', label: t('systemConfig.notification'), desc: t('systemConfig.notificationDesc'), icon: '📧' },
])

const activeGroup = ref('basic')
const showHistory = ref(false)
const configData = ref<Record<string, ConfigItem[]>>({})
const editingValues = reactive<Record<string, string | number>>({})
const originalValues = reactive<Record<string, string | null>>({})
const testing = ref(false)
const saving = ref(false)
const testResult = ref<TestResult | null>(null)
const testGroup = ref<string | null>(null)

const aiModels = ref<AiModel[]>([])
const modelScenes = ref<ModelScene[]>([])
const testingModelId = ref<string | null>(null)
const testResults = reactive<Record<string, TestResult | null>>({})

const modelModalOpen = ref(false)
const modelModalIsEdit = ref(false)
const editingModelId = ref<string | null>(null)
const modelForm = reactive<Partial<AiModel>>({
  name: '', provider: 'Anthropic', model_id: '', api_key: '', base_url: 'https://api.anthropic.com',
  temperature: 0.7, max_tokens: 4096, scenes: ['general'], is_default: false,
})

const providerOptions = [
  { label: 'Anthropic', value: 'Anthropic' },
  { label: 'OpenAI', value: 'OpenAI' },
  { label: 'DeepSeek', value: 'DeepSeek' },
  { label: 'Google', value: 'Google' },
  { label: '其他', value: '其他' },
]

const sceneOptions = computed(() => modelScenes.value.map(s => ({ label: s.label, value: s.key })))
function sceneLabel(key: string) { return modelScenes.value.find(s => s.key === key)?.label || key }

const changeHistory = ref([
  { user: 'admin', time: '2026-06-08 14:30', desc: '修改了「AI配置」→ 添加模型 DeepSeek V3', type: 'create' },
  { user: 'admin', time: '2026-06-08 10:15', desc: '修改了「AI配置」→ 默认模型改为 Claude Sonnet 4', type: 'update' },
  { user: 'admin', time: '2026-06-07 16:45', desc: '修改了「通知配置」→ SMTP 服务器已配置', type: 'create' },
  { user: '系统', time: '2026-06-07 09:00', desc: '系统初始化：默认配置已写入', type: 'init' },
])

function getGroupItems(group: string): ConfigItem[] { return configData.value[group] || [] }
function isTextField(key: string) { return ['system_name', 'local_path', 'smtp_host', 'smtp_username', 'base_url', 'webhook_url', 'smtp_from_name', 'client_id', 'redirect_uri'].some(k => key.includes(k)) }
function isNumberField(key: string) { return ['password_min_length', 'session_timeout', 'smtp_port', 'max_upload_mb', 'timeout_seconds'].some(k => key.includes(k)) }
function getMin(key: string) { if (key.includes('password_min_length')) return 6; if (key.includes('session_timeout')) return 5; if (key.includes('smtp_port')) return 1; if (key.includes('max_upload_mb')) return 1; if (key.includes('timeout_seconds')) return 10; return 0 }
function getMax(key: string) { if (key.includes('password_min_length')) return 32; if (key.includes('session_timeout')) return 1440; if (key.includes('smtp_port')) return 65535; if (key.includes('max_upload_mb')) return 1024; if (key.includes('timeout_seconds')) return 300; return 9999 }
function getStep(_key: string) { return 1 }
function getSelectOptions(key: string): { label: string; value: string }[] | undefined {
  if (key === 'language') return [{ label: '简体中文', value: 'zh-CN' }, { label: 'English', value: 'en' }]
  if (key === 'timezone') return [{ label: 'Asia/Shanghai', value: 'Asia/Shanghai' }, { label: 'UTC', value: 'UTC' }]
  if (key === 'backend') return [{ label: '本地文件系统', value: 'local' }, { label: 'MinIO', value: 'minio' }, { label: '阿里云 OSS', value: 'oss' }]
  if (key === 'smtp_encryption') return [{ label: 'SSL/TLS', value: 'ssl' }, { label: 'STARTTLS', value: 'tls' }, { label: '无', value: 'none' }]
  if (key === 'password_complexity') return [{ label: '大写+小写+数字', value: 'upper,lower,digit' }, { label: '全部（含特殊字符）', value: 'upper,lower,digit,special' }]
  if (key === 'sso_enabled') return [{ label: '关闭', value: 'false' }, { label: '开启', value: 'true' }]
  if (key === 'sso_provider') return [{ label: 'OIDC', value: 'oidc' }, { label: 'SAML', value: 'saml' }, { label: 'LDAP', value: 'ldap' }]
  return undefined
}
function hasChanges(group: string) {
  const items = configData.value[group] || []
  return items.some(item => { const edited = editingValues[item.key]; const original = originalValues[item.key]; return edited !== undefined && String(edited) !== String(original ?? '') })
}

async function fetchConfig() {
  try {
    const res = await systemConfigApi.getAll()
    configData.value = res.groups
    for (const [, items] of Object.entries(res.groups)) {
      for (const item of items) { editingValues[item.key] = item.value ?? ''; originalValues[item.key] = item.value ?? '' }
    }
    const savedLang = editingValues['language']
    if (savedLang && (savedLang === 'zh-CN' || savedLang === 'en')) { switchLanguage(savedLang as string) }
  } catch { /* ignore */ }
}

watch(() => editingValues['language'], (newLang) => {
  if (newLang && (newLang === 'zh-CN' || newLang === 'en')) { switchLanguage(newLang as string) }
})

async function fetchAiModels() {
  try { const res = await systemConfigApi.getAiModels(); aiModels.value = res.models; modelScenes.value = res.scenes } catch { /* ignore */ }
}

async function handleSave(group: string) {
  saving.value = true
  try {
    const items = (configData.value[group] || []).map(item => ({ key: item.key, value: editingValues[item.key] !== undefined ? String(editingValues[item.key]) : null }))
    await systemConfigApi.save(group, items)
    success('保存成功')
    for (const item of items) originalValues[item.key] = item.value
    changeHistory.value.unshift({ user: 'admin', time: new Date().toLocaleString('zh-CN'), desc: `修改了「${groupList.value.find(g => g.key === group)?.label || group}」配置`, type: 'update' })
  } catch (e: any) { error(e?.response?.data?.detail || '保存失败') } finally { saving.value = false }
}

function handleReset(group: string) {
  if (!confirm('确定恢复该组配置为默认值？')) return
  const items = configData.value[group] || []
  for (const item of items) editingValues[item.key] = originalValues[item.key] ?? ''
}

async function handleTestEmail() {
  const recipient = prompt('请输入测试收件人邮箱:')
  if (!recipient) return
  testing.value = true; testResult.value = null; testGroup.value = 'notification'
  try { testResult.value = await systemConfigApi.testEmail(recipient) } catch { testResult.value = { success: false, message: '测试请求失败' } } finally { testing.value = false }
}

function scrollToGroup(key: string) {
  activeGroup.value = key
  nextTick(() => { document.getElementById(`config-group-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) })
}

function openAddModel() {
  modelModalIsEdit.value = false; editingModelId.value = null
  Object.assign(modelForm, { id: '', name: '', provider: 'Anthropic', model_id: '', api_key: '', base_url: 'https://api.anthropic.com', temperature: 0.7, max_tokens: 4096, scenes: ['general'], is_default: false })
  modelModalOpen.value = true
}

function openEditModel(model: AiModel) {
  modelModalIsEdit.value = true; editingModelId.value = model.id
  Object.assign(modelForm, { ...model })
  modelModalOpen.value = true
}

async function handleSaveModel() {
  if (!modelForm.name || !modelForm.model_id) { error('请填写模型名称和模型 ID'); return }
  let models = [...aiModels.value]
  if (modelModalIsEdit.value && editingModelId.value) {
    models = models.map(m => m.id === editingModelId.value ? { ...m, ...modelForm } as AiModel : m)
  } else {
    const newModel: AiModel = { id: `model-${Date.now()}`, name: modelForm.name || '', provider: modelForm.provider || '其他', model_id: modelForm.model_id || '', api_key: modelForm.api_key || '', base_url: modelForm.base_url || '', temperature: modelForm.temperature ?? 0.7, max_tokens: modelForm.max_tokens ?? 4096, scenes: modelForm.scenes || ['general'], is_default: models.length === 0 }
    models.push(newModel)
  }
  try {
    await systemConfigApi.saveAiModels(models)
    success(modelModalIsEdit.value ? '模型已更新' : '模型已添加')
    modelModalOpen.value = false; fetchAiModels()
    changeHistory.value.unshift({ user: 'admin', time: new Date().toLocaleString('zh-CN'), desc: `${modelModalIsEdit.value ? '修改' : '添加'}了AI模型「${modelForm.name}」`, type: modelModalIsEdit.value ? 'update' : 'create' })
  } catch (e: any) { error(e?.response?.data?.detail || '保存失败') }
}

async function handleDeleteModel(id: string) {
  if (!confirm('确定删除该模型？')) return
  const models = aiModels.value.filter(m => m.id !== id)
  try { await systemConfigApi.saveAiModels(models); success('模型已删除'); fetchAiModels() } catch { error('删除失败') }
}

async function handleSetDefault(id: string) {
  const models = aiModels.value.map(m => ({ ...m, is_default: m.id === id }))
  try { await systemConfigApi.saveAiModels(models); success('已设为默认模型'); fetchAiModels() } catch { error('设置失败') }
}

async function handleTestModel(model: AiModel) {
  testingModelId.value = model.id; testResults[model.id] = null
  try { testResults[model.id] = await systemConfigApi.testAiModel({ api_key: model.api_key, base_url: model.base_url, model_id: model.model_id }) } catch { testResults[model.id] = { success: false, message: '测试请求失败' } } finally { testingModelId.value = null }
}

onMounted(() => { fetchConfig(); fetchAiModels() })
</script>

<style scoped>
.dashboard-container { padding: 24px 32px; }
.dashboard-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.dashboard-header h2 { margin: 0; font-size: 22px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 12px; }

.config-body { display: flex; gap: 24px; }
.config-nav { width: 150px; flex-shrink: 0; position: sticky; top: 80px; align-self: flex-start; display: flex; flex-direction: column; gap: 4px; }
.config-nav__item { text-align: left !important; }
.config-nav__icon { margin-right: 6px; }
.config-content { flex: 1; min-width: 0; }

.config-card-title { display: flex; justify-content: space-between; align-items: flex-start; }
.config-card-title span { font-size: 16px; font-weight: 600; }
.config-card-desc { font-size: 12px; color: var(--color-text-secondary, #888); margin: 4px 0 0; font-weight: 400; }

.config-fields { display: flex; flex-direction: column; gap: 18px; }
.config-field { display: flex; flex-direction: column; gap: 8px; }
.config-field__label { font-size: 13px; font-weight: 500; }

.config-card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--color-bg-elevated, #f0f0f0); }
.config-card-footer__right { display: flex; gap: 8px; }

.test-result { margin-top: 12px; padding: 10px 14px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 8px; }
.test-result--ok { background: rgba(16, 185, 129, 0.08); color: #10b981; }
.test-result--err { background: rgba(250, 82, 82, 0.08); color: #fa5252; }

.model-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.model-card { border: 1px solid var(--color-bg-elevated, #f0f0f0); border-radius: 8px; padding: 16px; transition: all 0.2s; }
.model-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.model-card--default { border-color: #a5b4fc; background: rgba(99, 102, 241, 0.04); }
.model-card__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.model-card__provider { font-size: 11px; color: var(--color-text-secondary, #888); text-transform: uppercase; letter-spacing: 0.5px; }
.model-card__actions { display: flex; align-items: center; gap: 4px; }
.model-card__default-tag { font-size: 11px; padding: 2px 8px; background: #e0e7ff; color: #6366f1; border-radius: 4px; font-weight: 600; }
.model-card__name { font-size: 15px; font-weight: 600; margin-bottom: 2px; }
.model-card__id { font-size: 12px; font-family: var(--font-mono, monospace); color: var(--color-text-secondary, #888); margin-bottom: 8px; }
.model-card__config { display: flex; gap: 16px; font-size: 12px; color: var(--color-text-secondary, #888); margin-bottom: 8px; }
.model-card__scenes { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.model-card__scene-tag { font-size: 11px; padding: 2px 8px; background: var(--color-bg-container, #fafafa); color: var(--color-text-secondary, #888); border-radius: 4px; }
.model-card__footer { display: flex; gap: 8px; align-items: center; }
.model-card__test-result { margin-top: 8px; padding: 6px 10px; border-radius: 4px; font-size: 12px; }
.model-card__test-result--ok { background: rgba(16, 185, 129, 0.08); color: #10b981; }
.model-card__test-result--err { background: rgba(250, 82, 82, 0.08); color: #fa5252; }

.empty-state { text-align: center; padding: 40px; }
.empty-state__icon { font-size: 48px; margin-bottom: 12px; opacity: 0.8; }
.empty-state__title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.empty-state__desc { font-size: 13px; color: var(--color-text-secondary, #888); }

.modal-form { display: flex; flex-direction: column; gap: 16px; }
.modal-form__row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.modal-form__field { display: flex; flex-direction: column; gap: 6px; }
.modal-form__label { font-size: 13px; font-weight: 500; }
.modal-form__required { color: #fa5252; }

.history-list { display: flex; flex-direction: column; }
.history-item { display: flex; gap: 14px; padding: 14px 0; border-bottom: 1px solid var(--color-bg-elevated, #f0f0f0); }
.history-item:last-child { border-bottom: none; }
.history-item__dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
.history-item__dot--update { background: #6366f1; }
.history-item__dot--create { background: #10b981; }
.history-item__dot--init { background: #999; }
.history-item__content { flex: 1; }
.history-item__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.history-item__user { font-size: 13px; font-weight: 600; }
.history-item__time { font-size: 12px; color: var(--color-text-secondary, #888); font-family: var(--font-mono, monospace); }
.history-item__desc { font-size: 13px; color: var(--color-text-secondary, #888); }

@media (max-width: 1440px) { .model-grid { grid-template-columns: 1fr; } }
@media (max-width: 1280px) { .config-nav { display: none; } .config-body { flex-direction: column; } }
</style>
