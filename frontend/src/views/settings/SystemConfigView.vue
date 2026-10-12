<template>
  <div class="dashboard-container"><a-result v-if="!canConfigure" status="403" title="系统配置需要管理员权限" />
    <template v-else>
    <!-- Header -->
    <div class="dashboard-header">
      <h2>{{ t('systemConfig.title') }}</h2>
      <div class="header-right">
        <a-button @click="openHistory">
          <template #icon><HistoryOutlined /></template>
          {{ t('common.changeHistory') }}
        </a-button>
      </div>
    </div>
    <a-alert v-if="configError" type="error" show-icon message="系统配置加载失败" :description="configError" style="margin-bottom:16px">
      <template #action><a-button size="small" @click="fetchConfig">重试</a-button></template>
    </a-alert>

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
      <a-spin wrapper-class-name="config-content" :spinning="loadingConfig" tip="正在加载配置…">
        <template v-for="g in groupList" :key="g.key">
          <!-- AI 配置：特殊处理为模型卡片列表 -->
          <a-card v-if="g.key === 'ai'" :bordered="false" :id="`config-group-${g.key}`" style="margin-bottom: 16px;">
            <template #title>
              <div class="config-card-title">
                <div>
                  <span>{{ g.label }}</span>
                  <p class="config-card-desc">{{ g.desc }}</p>
                </div>
                <a-button type="primary" size="small" :disabled="loadingModels || !!modelsError || savingModels" @click="openAddModel">＋ 添加模型</a-button>
              </div>
            </template>

            <a-alert v-if="modelsError" type="error" show-icon message="模型配置加载失败" :description="modelsError" style="margin-bottom:16px">
              <template #action><a-button size="small" @click="fetchAiModels">重试</a-button></template>
            </a-alert>
            <a-spin :spinning="loadingModels" tip="正在加载模型…"><div class="model-grid">
              <div v-for="model in aiModels" :key="model.id" class="model-card" :class="{ 'model-card--default': model.is_default }">
                <div class="model-card__header">
                  <div class="model-card__provider">{{ model.provider }}</div>
                  <div class="model-card__actions">
                    <span v-if="model.is_default" class="model-card__default-tag">默认</span>
                    <a-button type="text" size="small" :disabled="savingModels" @click="openEditModel(model)">编辑</a-button>
                    <a-button type="text" size="small" danger :disabled="savingModels" @click="handleDeleteModel(model.id)">删除</a-button>
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
                  <a-button size="small" @click="handleTestModel(model)" :loading="testingModelId === model.id" :disabled="!!testingModelId && testingModelId !== model.id">
                    {{ testingModelId === model.id ? '测试中...' : '🔗 测试连通性' }}
                  </a-button>
                  <a-button v-if="!model.is_default" size="small" type="link" :disabled="savingModels" @click="handleSetDefault(model.id)">设为默认</a-button>
                </div>
                <div v-if="testResults[model.id]" class="model-card__test-result" :class="testResults[model.id]?.success ? 'model-card__test-result--ok' : 'model-card__test-result--err'">
                  {{ testResults[model.id]?.success ? '✓' : '✗' }} {{ testResults[model.id]?.message }}
                </div>
              </div>
            </div>

            <div v-if="!loadingModels && !modelsError && !aiModels.length" class="empty-state">
              <div class="empty-state__icon">🤖</div>
              <p class="empty-state__title">暂无模型配置</p>
              <p class="empty-state__desc">点击「添加模型」配置第一个 AI 模型</p>
            </div></a-spin>
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

            <a-alert v-if="g.key === 'auth'" type="info" show-icon :message="t('systemConfig.oidcOnly')" style="margin-bottom:16px" />
            <a-alert v-if="g.key === 'basic'" type="info" show-icon :message="t('systemConfig.languageScope')" style="margin-bottom:16px" />
            <div class="config-fields">
              <template v-for="item in getGroupItems(g.key)" :key="item.key">
                <div class="config-field" :data-config-key="item.key">
                  <label class="config-field__label">{{ configItemLabel(item.key, item.description) }}</label>
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
                <a-button @click="handleReset(g.key)" :disabled="saving || !hasChanges(g.key)">{{ t('common.discardChanges') }}</a-button>
                <a-button type="primary" @click="handleSave(g.key)" :disabled="!hasChanges(g.key)" :loading="saving">{{ t('common.save') }}</a-button>
              </div>
            </div>

            <div v-if="testResult && testGroup === g.key" class="test-result" :class="testResult.success ? 'test-result--ok' : 'test-result--err'">
              <span>{{ testResult.success ? '✓' : '✗' }}</span>
              {{ testResult.message }}
            </div>
          </a-card>
        </template>
      </a-spin>
    </div>

    <!-- 模型编辑弹窗 -->
    <a-modal v-model:open="modelModalOpen" :title="modelModalIsEdit ? '编辑模型' : '添加模型'" :width="560" :confirm-loading="savingModels" :closable="!savingModels" :mask-closable="!savingModels" :keyboard="!savingModels" :cancel-button-props="{ disabled: savingModels }" @ok="handleSaveModel" @cancel="modelModalOpen = false">
      <div class="modal-form">
        <div class="modal-form__row">
          <div class="modal-form__field">
            <label class="modal-form__label">模型名称 <span class="modal-form__required">*</span></label>
            <a-input v-model:value="modelForm.name" placeholder="模型名称" />
          </div>
          <div class="modal-form__field">
            <label class="modal-form__label">提供商</label>
            <a-select v-model:value="modelForm.provider" :options="providerOptions" style="width: 100%" />
          </div>
        </div>
        <div class="modal-form__field">
          <label class="modal-form__label">模型 ID <span class="modal-form__required">*</span></label>
          <a-input v-model:value="modelForm.model_id" placeholder="供应商模型 ID" />
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
      <p v-if="historyLoading" role="status">加载中…</p><p v-if="historyError" role="alert">{{ historyError }} <a-button @click="openHistory">重试</a-button></p><p v-if="!historyLoading && !historyError && !changeHistory.length">暂无配置变更</p><div class="history-list">
        <div v-for="(record, idx) in changeHistory" :key="idx" class="history-item">
          <div class="history-item__dot" :class="`history-item__dot--${record.type}`"></div>
          <div class="history-item__content">
            <div class="history-item__header">
              <span class="history-item__user">{{ record.user }}</span>
              <span class="history-item__time">{{ formatPlatformDateTime(record.time) }}</span>
            </div>
            <div class="history-item__desc">{{ record.desc }}</div>
          </div>
        </div>
        <div v-if="!changeHistory.length" class="empty-state">暂无变更记录</div>
      </div>
    </a-drawer>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import {
  Input as AInput, InputPassword as AInputPassword, InputNumber as AInputNumber,
  Select as ASelect, Drawer as ADrawer, Modal as AModal,
  Slider as ASlider, CheckboxGroup as ACheckboxGroup,
  Alert as AAlert, Card as ACard, Button as AButton, Spin as ASpin,
} from 'ant-design-vue'
import { HistoryOutlined } from '@ant-design/icons-vue'
import { systemConfigApi, type ConfigItem, type TestResult, type AiModel, type ModelScene } from '../../api/systemConfig'
import { useAuthStore } from '../../store/auth'
import { get } from '../../api/client'
import { useToast } from '../../composables/useToast'
import { useLanguage } from '../../composables/useLanguage'
import { usePlatformConfigStore } from '../../store/platformConfig'
import type { PlatformConfig } from '../../api/platformConfig'
import { formatPlatformDateTime } from '../../utils/platformTime'

const authStore = useAuthStore()
const canConfigure = computed(() => authStore.hasPermission('admin:users'))
const { success, error } = useToast()
const { t } = useLanguage()
const platform = usePlatformConfigStore()

const groupList = computed(() => [
  { key: 'basic', label: t('systemConfig.basic'), desc: t('systemConfig.basicDesc'), icon: '⚙️' },
  { key: 'auth', label: t('systemConfig.auth'), desc: t('systemConfig.authDesc'), icon: '🔐' },
  { key: 'storage', label: t('systemConfig.storage'), desc: t('systemConfig.storageDesc'), icon: '📁' },
  { key: 'ai', label: t('systemConfig.ai'), desc: t('systemConfig.aiDesc'), icon: '🤖' },
  { key: 'notification', label: t('systemConfig.notification'), desc: t('systemConfig.notificationDesc'), icon: '📧' },
])

const activeGroup = ref('basic')
let scrollContainer: Element | null = null
const showHistory = ref(false)
const configData = ref<Record<string, ConfigItem[]>>({})
const editingValues = reactive<Record<string, string | number>>({})
const originalValues = reactive<Record<string, string | null>>({})
const testing = ref(false)
const saving = ref(false)
const loadingConfig = ref(false)
const configError = ref('')
const loadingModels = ref(false)
const modelsError = ref('')
const savingModels = ref(false)
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

const historyLoading = ref(false), historyError = ref('')
async function openHistory() { showHistory.value = true; historyLoading.value = true; historyError.value = ''; try { changeHistory.value = await get('/system-config/history') } catch (exception: any) { historyError.value = exception?.response?.data?.detail || exception.message || '变更记录加载失败' } finally { historyLoading.value = false } }

const changeHistory = ref<Array<{ user: string; time: string; desc: string; type: string }>>([])

function getGroupItems(group: string): ConfigItem[] { return (configData.value[group] || []).filter(item => item.key !== 'ai.models' && !item.key.startsWith('auth.role_permissions.')) }
function configItemLabel(key: string, description: string | null) {
  const names: Record<string,string> = { system_name:'systemName', language:'language', timezone:'timezone' }
  const label = names[key.replace(/^basic\./, '')]
  return label ? t(`systemConfig.${label}`) : description || key
}
function isTextField(key: string) { return ['system_name', 'local_path', 'smtp_host', 'smtp_username', 'base_url', 'webhook_url', 'smtp_from_name', 'client_id', 'redirect_uri', 'issuer_url', 'callback_url'].some(k => key.includes(k)) }
function isNumberField(key: string) { return ['password_min_length', 'session_timeout', 'smtp_port', 'max_upload_mb', 'timeout_seconds'].some(k => key.includes(k)) }
function getMin(key: string) { if (key.includes('password_min_length')) return 6; if (key.includes('session_timeout')) return 5; if (key.includes('smtp_port')) return 1; if (key.includes('max_upload_mb')) return 1; if (key.includes('timeout_seconds')) return 10; return 0 }
function getMax(key: string) { if (key.includes('password_min_length')) return 32; if (key.includes('session_timeout')) return 1440; if (key.includes('smtp_port')) return 65535; if (key.includes('max_upload_mb')) return 1024; if (key.includes('timeout_seconds')) return 300; return 9999 }
function getStep(_key: string) { return 1 }
function getSelectOptions(key: string): { label: string; value: string; disabled?: boolean }[] | undefined {
  key = key.split('.').at(-1) || key
  if (key === 'language') return [{ label: '简体中文', value: 'zh-CN' }, { label: 'English', value: 'en' }]
  if (key === 'timezone') return [{ label: 'Asia/Shanghai', value: 'Asia/Shanghai' }, { label: 'UTC', value: 'UTC' }]
  if (key === 'backend') return [{ label: '本地文件系统', value: 'local' }, { label: 'MinIO', value: 'minio' }, { label: '阿里云 OSS', value: 'oss' }]
  if (key === 'smtp_encryption') return [{ label: 'SSL/TLS', value: 'ssl' }, { label: 'STARTTLS', value: 'tls' }, { label: '无', value: 'none' }]
  if (key === 'password_complexity') return [{ label: '大写+小写+数字', value: 'upper,lower,digit' }, { label: '全部（含特殊字符）', value: 'upper,lower,digit,special' }]
  if (key === 'sso_enabled') return [{ label: '关闭', value: 'false' }, { label: '开启', value: 'true' }]
  if (key === 'sso_provider') return [{ label: 'OIDC', value: 'oidc' }, { label: t('systemConfig.samlUnavailable'), value: 'saml', disabled: true }, { label: t('systemConfig.ldapUnavailable'), value: 'ldap', disabled: true }]
  return undefined
}
function hasChanges(group: string) {
  const items = getGroupItems(group)
  return items.some(item => { const edited = editingValues[item.key]; const original = originalValues[item.key]; return edited !== undefined && String(edited) !== String(original ?? '') })
}

async function fetchConfig() {
  loadingConfig.value = true
  configError.value = ''
  try {
    const res = await systemConfigApi.getAll()
    configData.value = res.groups
    for (const [, items] of Object.entries(res.groups)) {
      for (const item of items) { editingValues[item.key] = item.value ?? ''; originalValues[item.key] = item.value ?? '' }
    }
  } catch (e: any) { configError.value = e?.response?.data?.detail || e.message || '无法读取配置，请重试' }
  finally { loadingConfig.value = false }
}


async function fetchAiModels() {
  loadingModels.value = true
  modelsError.value = ''
  try { const res = await systemConfigApi.getAiModels(); aiModels.value = res.models; modelScenes.value = res.scenes }
  catch (e: any) { modelsError.value = e?.response?.data?.detail || e.message || '无法读取模型配置，请重试' }
  finally { loadingModels.value = false }
}

async function handleSave(group: string) {
  if (saving.value || !hasChanges(group)) return
  saving.value = true
  try {
    const items = getGroupItems(group).map(item => ({ key: item.key, value: editingValues[item.key] !== undefined ? String(editingValues[item.key]) : null }))
    if (group === 'auth' && items.some(item => item.key.endsWith('sso_enabled') && item.value === 'true') && items.some(item => item.key.endsWith('sso_provider') && item.value !== 'oidc')) {
      error(t('systemConfig.oidcOnly'))
      return
    }
    await systemConfigApi.save(group, items)
    if (group === 'basic') platform.applySaved(Object.fromEntries(items.map(item => [item.key.replace(/^basic\./, ''), item.value])) as Partial<PlatformConfig>)
    success(t('common.saveSuccess'))
    for (const item of items) originalValues[item.key] = item.value
  } catch (e: any) { error(e?.response?.data?.detail || t('common.saveFailed')) } finally { saving.value = false }
}

function handleReset(group: string) {
  const items = configData.value[group] || []
  for (const item of items) editingValues[item.key] = originalValues[item.key] ?? ''
}

async function handleTestEmail() {
  if (testing.value) return
  if (hasChanges('notification')) { error('请先保存邮件配置，再发送测试邮件'); return }
  const recipient = prompt('请输入测试收件人邮箱:')
  if (!recipient) return
  testing.value = true; testResult.value = null; testGroup.value = 'notification'
  try { testResult.value = await systemConfigApi.testEmail(recipient) } catch { testResult.value = { success: false, message: '测试请求失败' } } finally { testing.value = false }
}

function scrollToGroup(key: string) {
  activeGroup.value = key
  nextTick(() => { document.getElementById(`config-group-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) })
}

function updateActiveGroup() {
  if (!scrollContainer) return
  const viewport = scrollContainer.getBoundingClientRect()
  let visibleKey = activeGroup.value
  const readingLine = viewport.top + 120
  let firstVisible: string | null = null
  for (const group of groupList.value) {
    const rect = document.getElementById(`config-group-${group.key}`)?.getBoundingClientRect()
    if (!rect) continue
    if (rect.bottom > viewport.top && rect.top < viewport.bottom && !firstVisible) firstVisible = group.key
    if (rect.top <= readingLine && rect.bottom > readingLine) { visibleKey = group.key; firstVisible = null; break }
  }
  if (firstVisible) visibleKey = firstVisible
  activeGroup.value = visibleKey
}

function openAddModel() {
  modelModalIsEdit.value = false; editingModelId.value = null
  Object.assign(modelForm, { id: '', name: '', provider: 'Anthropic', model_id: '', api_key: '', base_url: 'https://api.anthropic.com', temperature: 0.7, max_tokens: 4096, scenes: ['general'], is_default: false })
  modelModalOpen.value = true
}

function openEditModel(model: AiModel) {
  modelModalIsEdit.value = true; editingModelId.value = model.id
  Object.assign(modelForm, { ...model, scenes: [...model.scenes] })
  modelModalOpen.value = true
}

async function handleSaveModel() {
  if (savingModels.value) return
  if (!modelForm.name?.trim() || !modelForm.model_id?.trim()) { error('请填写模型名称和模型 ID'); return }
  modelForm.name = modelForm.name.trim(); modelForm.model_id = modelForm.model_id.trim()
  let models = [...aiModels.value]
  if (modelModalIsEdit.value && editingModelId.value) {
    models = models.map(m => m.id === editingModelId.value ? { ...m, ...modelForm } as AiModel : m)
  } else {
    const newModel: AiModel = { id: `model-${Date.now()}`, name: modelForm.name || '', provider: modelForm.provider || '其他', model_id: modelForm.model_id || '', api_key: modelForm.api_key || '', base_url: modelForm.base_url || '', temperature: modelForm.temperature ?? 0.7, max_tokens: modelForm.max_tokens ?? 4096, scenes: modelForm.scenes || ['general'], is_default: models.length === 0 }
    models.push(newModel)
  }
  savingModels.value = true
  try {
    await systemConfigApi.saveAiModels(models)
    success(modelModalIsEdit.value ? '模型已更新' : '模型已添加')
    modelModalOpen.value = false; await fetchAiModels()
  } catch (e: any) { error(e?.response?.data?.detail || '保存失败') }
  finally { savingModels.value = false }
}

async function handleDeleteModel(id: string) {
  if (savingModels.value) return
  if (!confirm('确定删除该模型？')) return
  const models = aiModels.value.filter(m => m.id !== id)
  savingModels.value = true
  try { await systemConfigApi.saveAiModels(models); success('模型已删除'); await fetchAiModels() } catch { error('删除失败') }
  finally { savingModels.value = false }
}

async function handleSetDefault(id: string) {
  if (savingModels.value) return
  const models = aiModels.value.map(m => ({ ...m, is_default: m.id === id }))
  savingModels.value = true
  try { await systemConfigApi.saveAiModels(models); success('已设为默认模型'); await fetchAiModels() } catch { error('设置失败') }
  finally { savingModels.value = false }
}

async function handleTestModel(model: AiModel) {
  if (testingModelId.value) return
  testingModelId.value = model.id; testResults[model.id] = null
  try { testResults[model.id] = await systemConfigApi.testAiModel({ id: model.id, api_key: model.api_key, base_url: model.base_url, model_id: model.model_id }) } catch { testResults[model.id] = { success: false, message: '测试请求失败' } } finally { testingModelId.value = null }
}

onMounted(async () => {
  if (!authStore.user) await authStore.fetchUser()
  if (!canConfigure.value) return
  await Promise.all([fetchConfig(), fetchAiModels()])
  await nextTick()
  scrollContainer = document.querySelector('.app-content')
  scrollContainer?.addEventListener('scroll', updateActiveGroup, { passive: true })
  updateActiveGroup()
})
onBeforeUnmount(() => scrollContainer?.removeEventListener('scroll', updateActiveGroup))
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
.config-card-desc { font-size: 12px; color: var(--neutral-600, #6b7280); margin: 4px 0 0; font-weight: 400; white-space: normal; line-height: 1.6; }

.config-fields { display: flex; flex-direction: column; gap: 18px; }
.config-field { display: flex; flex-direction: column; gap: 8px; }
.config-field__label { font-size: 13px; font-weight: 500; }

.config-card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--neutral-200, #e5e7eb); }
.config-card-footer__right { display: flex; gap: 8px; }

.test-result { margin-top: 12px; padding: 10px 14px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 8px; }
.test-result--ok { background: rgba(16, 185, 129, 0.08); color: #10b981; }
.test-result--err { background: rgba(250, 82, 82, 0.08); color: #fa5252; }

.model-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.model-card { border: 1px solid var(--neutral-200, #e5e7eb); border-radius: 8px; padding: 16px; transition: all 0.2s; }
.model-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.model-card--default { border-color: #a5b4fc; background: rgba(99, 102, 241, 0.04); }
.model-card__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.model-card__provider { font-size: 11px; color: var(--neutral-600, #6b7280); text-transform: uppercase; letter-spacing: 0.5px; }
.model-card__actions { display: flex; align-items: center; gap: 4px; }
.model-card__default-tag { font-size: 11px; padding: 2px 8px; background: #e0e7ff; color: #6366f1; border-radius: 4px; font-weight: 600; }
.model-card__name { font-size: 15px; font-weight: 600; margin-bottom: 2px; overflow-wrap: anywhere; }
.model-card__id { font-size: 12px; font-family: var(--font-mono, monospace); color: var(--neutral-600, #6b7280); margin-bottom: 8px; overflow-wrap: anywhere; }
.model-card__config { display: flex; gap: 16px; font-size: 12px; color: var(--neutral-600, #6b7280); margin-bottom: 8px; }
.model-card__scenes { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.model-card__scene-tag { font-size: 11px; padding: 2px 8px; background: var(--neutral-50, #fafafa); color: var(--neutral-600, #6b7280); border-radius: 4px; }
.model-card__footer { display: flex; gap: 8px; align-items: center; }
.model-card__test-result { margin-top: 8px; padding: 6px 10px; border-radius: 4px; font-size: 12px; }
.model-card__test-result--ok { background: rgba(16, 185, 129, 0.08); color: #10b981; }
.model-card__test-result--err { background: rgba(250, 82, 82, 0.08); color: #fa5252; }

.empty-state { text-align: center; padding: 40px; }
.empty-state__icon { font-size: 48px; margin-bottom: 12px; opacity: 0.8; }
.empty-state__title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.empty-state__desc { font-size: 13px; color: var(--neutral-600, #6b7280); }

.modal-form { display: flex; flex-direction: column; gap: 16px; }
.modal-form__row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.modal-form__field { display: flex; flex-direction: column; gap: 6px; }
.modal-form__label { font-size: 13px; font-weight: 500; }
.modal-form__required { color: #fa5252; }

.history-list { display: flex; flex-direction: column; }
.history-item { display: flex; gap: 14px; padding: 14px 0; border-bottom: 1px solid var(--neutral-200, #e5e7eb); }
.history-item:last-child { border-bottom: none; }
.history-item__dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
.history-item__dot--update { background: #6366f1; }
.history-item__dot--create { background: #10b981; }
.history-item__dot--init { background: #999; }
.history-item__content { flex: 1; }
.history-item__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.history-item__user { font-size: 13px; font-weight: 600; }
.history-item__time { font-size: 12px; color: var(--neutral-600, #6b7280); font-family: var(--font-mono, monospace); }
.history-item__desc { font-size: 13px; color: var(--neutral-600, #6b7280); }

@media (max-width: 1440px) { .model-grid { grid-template-columns: 1fr; } }
.config-card-footer, .model-card__config, .model-card__footer { flex-wrap: wrap; gap: 12px; }
.config-card-title { gap: 16px; }
.model-card__test-result, .test-result { overflow-wrap: anywhere; }
@media (max-width: 1280px) { .config-nav { position: static; flex-direction: row; flex-wrap: wrap; width: auto; } .config-nav__item { width: auto; } .config-body { flex-direction: column; } }
</style>
