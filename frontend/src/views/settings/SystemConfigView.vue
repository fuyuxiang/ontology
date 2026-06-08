<template>
  <div class="config-page">
    <!-- 标题区 -->
    <div class="config-page__header">
      <div>
        <h1 class="text-display">系统配置</h1>
        <p class="text-caption" style="margin-top: 4px;">平台全局参数与集成配置管理</p>
      </div>
      <div class="config-page__actions">
        <button class="config-btn" @click="showHistory = true">🕐 变更记录</button>
      </div>
    </div>

    <div class="config-page__body">
      <!-- 左侧导航 -->
      <nav class="config-nav">
        <button
          v-for="g in groupList"
          :key="g.key"
          class="config-nav__item"
          :class="{ 'config-nav__item--active': activeGroup === g.key }"
          @click="scrollToGroup(g.key)"
        >
          {{ g.label }}
        </button>
      </nav>

      <!-- 右侧配置区 -->
      <div class="config-content" ref="contentRef">
        <div v-for="g in groupList" :key="g.key" :id="`config-group-${g.key}`" class="config-group">
          <h2 class="config-group__title">{{ g.label }}</h2>
          <p class="config-group__desc">{{ g.desc }}</p>

          <div class="config-group__fields">
            <template v-for="item in getGroupItems(g.key)" :key="item.key">
              <div class="config-field">
                <label class="config-field__label">{{ item.description || item.key }}</label>
                <!-- 敏感字段 -->
                <template v-if="item.is_sensitive">
                  <a-input-password v-model:value="editingValues[item.key]" placeholder="••••••••" />
                </template>
                <!-- 普通文本 -->
                <template v-else-if="isTextField(item.key)">
                  <a-input v-model:value="editingValues[item.key]" :placeholder="item.value || ''" />
                </template>
                <!-- 数字 -->
                <template v-else-if="isNumberField(item.key)">
                  <a-input-number v-model:value="editingValues[item.key]" :min="getMin(item.key)" :max="getMax(item.key)" :step="getStep(item.key)" style="width: 160px" />
                </template>
                <!-- Select -->
                <template v-else-if="getSelectOptions(item.key)">
                  <a-select v-model:value="editingValues[item.key]" :options="getSelectOptions(item.key)" style="width: 240px" />
                </template>
                <!-- 默认文本 -->
                <template v-else>
                  <a-input v-model:value="editingValues[item.key]" :placeholder="item.value || ''" />
                </template>
              </div>
            </template>
          </div>

          <div class="config-group__footer">
            <button v-if="g.key === 'ai'" class="config-btn config-btn--secondary" @click="handleTestAi" :disabled="testing">
              {{ testing ? '测试中...' : '🔗 测试连通性' }}
            </button>
            <button v-if="g.key === 'notification'" class="config-btn config-btn--secondary" @click="handleTestEmail" :disabled="testing">
              {{ testing ? '发送中...' : '📧 发送测试邮件' }}
            </button>
            <button class="config-btn config-btn--ghost" @click="handleReset(g.key)">恢复默认</button>
            <button class="config-btn config-btn--primary" @click="handleSave(g.key)" :disabled="!hasChanges(g.key)">
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>

          <!-- 测试结果 -->
          <div v-if="testResult" class="config-test-result" :class="testResult.success ? 'config-test-result--ok' : 'config-test-result--err'">
            {{ testResult.success ? '✓' : '✗' }} {{ testResult.message }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { Input as AInput, InputPassword as AInputPassword, InputNumber as AInputNumber, Select as ASelect } from 'ant-design-vue'
import { systemConfigApi, type ConfigItem, type TestResult } from '../../api/systemConfig'
import { useToast } from '../../composables/useToast'

const { success, error } = useToast()

// 分组定义
const groupList = [
  { key: 'basic', label: '基础配置', desc: '系统名称、语言、时区等基础参数' },
  { key: 'auth', label: '认证配置', desc: '密码策略、会话超时、SSO 集成' },
  { key: 'storage', label: '存储配置', desc: '文件存储路径、上传大小限制' },
  { key: 'ai', label: 'AI 配置', desc: '大模型 API Key、模型选择、参数调优' },
  { key: 'notification', label: '通知配置', desc: '邮件服务器、Webhook 集成' },
]

const activeGroup = ref('basic')
const contentRef = ref<HTMLElement | null>(null)
const showHistory = ref(false)

// 配置数据
const configData = ref<Record<string, ConfigItem[]>>({})
const editingValues = reactive<Record<string, string | number | null>>({})
const originalValues = reactive<Record<string, string | null>>({})

const testing = ref(false)
const saving = ref(false)
const testResult = ref<TestResult | null>(null)

function getGroupItems(group: string): ConfigItem[] {
  return configData.value[group] || []
}

function isTextField(key: string) {
  return ['system_name', 'local_path', 'smtp_host', 'smtp_username', 'base_url', 'webhook_url'].some(k => key.includes(k))
}

function isNumberField(key: string) {
  return ['password_min_length', 'session_timeout', 'smtp_port', 'max_upload_mb', 'temperature', 'max_tokens'].some(k => key.includes(k))
}

function getMin(key: string) {
  if (key.includes('password_min_length')) return 6
  if (key.includes('session_timeout')) return 5
  if (key.includes('smtp_port')) return 1
  if (key.includes('max_upload_mb')) return 1
  if (key.includes('temperature')) return 0
  if (key.includes('max_tokens')) return 256
  return 0
}

function getMax(key: string) {
  if (key.includes('password_min_length')) return 32
  if (key.includes('session_timeout')) return 1440
  if (key.includes('smtp_port')) return 65535
  if (key.includes('max_upload_mb')) return 1024
  if (key.includes('temperature')) return 2
  if (key.includes('max_tokens')) return 128000
  return 9999
}

function getStep(key: string) {
  if (key.includes('temperature')) return 0.1
  if (key.includes('max_tokens')) return 256
  return 1
}

function getSelectOptions(key: string) {
  if (key === 'language') return [{ label: '简体中文', value: 'zh-CN' }, { label: 'English', value: 'en' }]
  if (key === 'timezone') return [{ label: 'Asia/Shanghai', value: 'Asia/Shanghai' }, { label: 'UTC', value: 'UTC' }]
  if (key === 'backend') return [{ label: '本地文件系统', value: 'local' }, { label: 'MinIO', value: 'minio' }, { label: '阿里云 OSS', value: 'oss' }]
  if (key === 'model') return [{ label: 'Claude Sonnet 4', value: 'claude-sonnet-4-20250514' }, { label: 'Claude Opus 4', value: 'claude-opus-4-20250514' }, { label: 'GPT-4o', value: 'gpt-4o' }, { label: 'DeepSeek V3', value: 'deepseek-chat' }]
  if (key === 'smtp_encryption') return [{ label: 'SSL/TLS', value: 'ssl' }, { label: 'STARTTLS', value: 'tls' }, { label: '无', value: 'none' }]
  if (key === 'password_complexity') return [{ label: '大写+小写+数字', value: 'upper,lower,digit' }, { label: '全部（含特殊字符）', value: 'upper,lower,digit,special' }]
  if (key === 'sso_enabled') return [{ label: '关闭', value: 'false' }, { label: '开启', value: 'true' }]
  return null
}

function hasChanges(group: string) {
  const items = configData.value[group] || []
  return items.some(item => {
    const edited = editingValues[item.key]
    const original = originalValues[item.key]
    return edited !== undefined && String(edited) !== String(original ?? '')
  })
}

async function fetchConfig() {
  try {
    const res = await systemConfigApi.getAll()
    configData.value = res.groups
    // 初始化编辑值
    for (const [group, items] of Object.entries(res.groups)) {
      for (const item of items) {
        editingValues[item.key] = item.value ?? ''
        originalValues[item.key] = item.value ?? ''
      }
    }
  } catch { /* ignore */ }
}

async function handleSave(group: string) {
  saving.value = true
  try {
    const items = (configData.value[group] || []).map(item => ({
      key: item.key,
      value: editingValues[item.key] !== undefined ? String(editingValues[item.key]) : null,
    }))
    await systemConfigApi.save(group, items)
    success('保存成功')
    // 更新 original
    for (const item of items) {
      originalValues[item.key] = item.value
    }
  } catch (e: any) { error(e?.response?.data?.detail || '保存失败') } finally { saving.value = false }
}

function handleReset(group: string) {
  if (!confirm('确定恢复该组配置为默认值？')) return
  const items = configData.value[group] || []
  for (const item of items) {
    editingValues[item.key] = originalValues[item.key] ?? ''
  }
}

async function handleTestAi() {
  testing.value = true; testResult.value = null
  try { testResult.value = await systemConfigApi.testAi() } catch { testResult.value = { success: false, message: '测试请求失败' } } finally { testing.value = false }
}

async function handleTestEmail() {
  const recipient = prompt('请输入测试收件人邮箱:')
  if (!recipient) return
  testing.value = true; testResult.value = null
  try { testResult.value = await systemConfigApi.testEmail(recipient) } catch { testResult.value = { success: false, message: '测试请求失败' } } finally { testing.value = false }
}

function scrollToGroup(key: string) {
  activeGroup.value = key
  nextTick(() => {
    document.getElementById(`config-group-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

onMounted(() => { fetchConfig() })
</script>

<style scoped>
.config-page { padding: 24px 32px; }
.config-page__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.config-page__body { display: flex; gap: 32px; }

/* 左侧导航 */
.config-nav { width: 160px; flex-shrink: 0; position: sticky; top: 80px; align-self: flex-start; display: flex; flex-direction: column; gap: 4px; }
.config-nav__item { padding: 10px 16px; border: none; background: transparent; font-size: 14px; color: var(--neutral-600); cursor: pointer; border-radius: 6px; text-align: left; transition: all 0.15s; font-family: inherit; border-left: 3px solid transparent; }
.config-nav__item:hover { background: var(--neutral-100); }
.config-nav__item--active { color: var(--semantic-600); background: var(--semantic-50, #edf2ff); font-weight: 500; border-left-color: var(--semantic-600); }

/* 右侧配置区 */
.config-content { flex: 1; min-width: 0; }
.config-group { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: 12px; padding: 24px; margin-bottom: 24px; }
.config-group__title { font-size: 18px; font-weight: 600; color: var(--neutral-900); margin-bottom: 4px; }
.config-group__desc { font-size: 13px; color: var(--neutral-500); margin-bottom: 20px; }
.config-group__fields { display: flex; flex-direction: column; gap: 16px; }
.config-field { display: flex; flex-direction: column; gap: 6px; }
.config-field__label { font-size: 13px; font-weight: 500; color: var(--neutral-700); }

.config-group__footer { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--neutral-100); }

/* 按钮 */
.config-btn { padding: 6px 16px; border-radius: 6px; font-size: 13px; cursor: pointer; border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); transition: all 0.15s; font-family: inherit; }
.config-btn:hover { border-color: var(--neutral-300); }
.config-btn--primary { background: var(--semantic-600); color: #fff; border-color: var(--semantic-600); }
.config-btn--primary:hover { opacity: 0.9; }
.config-btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.config-btn--secondary { background: var(--neutral-50); }
.config-btn--ghost { background: transparent; border-color: transparent; color: var(--neutral-500); }

/* 测试结果 */
.config-test-result { margin-top: 12px; padding: 10px 16px; border-radius: 6px; font-size: 13px; }
.config-test-result--ok { background: #e6fcf5; color: #10b981; }
.config-test-result--err { background: #fff5f5; color: #fa5252; }

@media (max-width: 1280px) {
  .config-nav { display: none; }
  .config-page__body { flex-direction: column; }
}
</style>
