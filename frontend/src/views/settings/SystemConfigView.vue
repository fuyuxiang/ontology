<template>
  <div class="config-page">
    <!-- 标题区 -->
    <div class="config-page__header">
      <div>
        <h1 class="config-page__title">系统配置</h1>
        <p class="config-page__subtitle">平台全局参数与集成配置管理</p>
      </div>
      <div class="config-page__actions">
        <button class="config-btn" @click="showHistory = true">
          <span style="margin-right: 6px">🕐</span> 变更记录
        </button>
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
          <span class="config-nav__icon">{{ g.icon }}</span>
          {{ g.label }}
        </button>
      </nav>

      <!-- 右侧配置区 -->
      <div class="config-content" ref="contentRef">
        <div v-for="g in groupList" :key="g.key" :id="`config-group-${g.key}`" class="config-group">
          <div class="config-group__header">
            <h2 class="config-group__title">{{ g.label }}</h2>
            <p class="config-group__desc">{{ g.desc }}</p>
          </div>

          <div class="config-group__fields">
            <template v-for="item in getGroupItems(g.key)" :key="item.key">
              <div class="config-field">
                <label class="config-field__label">{{ item.description || item.key }}</label>
                <template v-if="item.is_sensitive">
                  <div class="config-field__sensitive">
                    <a-input-password v-model:value="editingValues[item.key]" placeholder="••••••••" />
                  </div>
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

          <div class="config-group__footer">
            <div class="config-group__footer-left">
              <button v-if="g.key === 'ai'" class="config-btn config-btn--secondary" @click="handleTestAi" :disabled="testing">
                {{ testing ? '测试中...' : '🔗 测试连通性' }}
              </button>
              <button v-if="g.key === 'notification'" class="config-btn config-btn--secondary" @click="handleTestEmail" :disabled="testing">
                {{ testing ? '发送中...' : '📧 发送测试邮件' }}
              </button>
            </div>
            <div class="config-group__footer-right">
              <button class="config-btn config-btn--ghost" @click="handleReset(g.key)">恢复默认</button>
              <button class="config-btn config-btn--primary" @click="handleSave(g.key)" :disabled="!hasChanges(g.key) || saving">
                {{ saving ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>

          <!-- 测试结果 -->
          <div v-if="testResult && testGroup === g.key" class="config-test-result" :class="testResult.success ? 'config-test-result--ok' : 'config-test-result--err'">
            <span class="config-test-result__icon">{{ testResult.success ? '✓' : '✗' }}</span>
            {{ testResult.message }}
          </div>
        </div>
      </div>
    </div>

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
        <div v-if="!changeHistory.length" class="history-empty">暂无变更记录</div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { Input as AInput, InputPassword as AInputPassword, InputNumber as AInputNumber, Select as ASelect, Drawer as ADrawer } from 'ant-design-vue'
import { systemConfigApi, type ConfigItem, type TestResult } from '../../api/systemConfig'
import { useToast } from '../../composables/useToast'

const { success, error } = useToast()

const groupList = [
  { key: 'basic', label: '基础配置', desc: '系统名称、语言、时区等基础参数', icon: '⚙️' },
  { key: 'auth', label: '认证配置', desc: '密码策略、会话超时、SSO 集成', icon: '🔐' },
  { key: 'storage', label: '存储配置', desc: '文件存储路径、上传大小限制', icon: '📁' },
  { key: 'ai', label: 'AI 配置', desc: '大模型 API Key、模型选择、参数调优', icon: '🤖' },
  { key: 'notification', label: '通知配置', desc: '邮件服务器、Webhook 集成', icon: '📧' },
]

const activeGroup = ref('basic')
const contentRef = ref<HTMLElement | null>(null)
const showHistory = ref(false)

const configData = ref<Record<string, ConfigItem[]>>({})
const editingValues = reactive<Record<string, string | number | null>>({})
const originalValues = reactive<Record<string, string | null>>({})

const testing = ref(false)
const saving = ref(false)
const testResult = ref<TestResult | null>(null)
const testGroup = ref<string | null>(null)

const changeHistory = ref([
  { user: 'admin', time: '2026-06-08 14:30', desc: '修改了「AI配置」→ Temperature: 0.5 → 0.7', type: 'update' },
  { user: 'admin', time: '2026-06-08 10:15', desc: '修改了「AI配置」→ LLM 模型: GPT-4o → Claude Sonnet 4', type: 'update' },
  { user: 'admin', time: '2026-06-07 16:45', desc: '修改了「通知配置」→ SMTP 服务器已配置', type: 'create' },
  { user: '系统', time: '2026-06-07 09:00', desc: '系统初始化：默认配置已写入', type: 'init' },
])

function getGroupItems(group: string): ConfigItem[] {
  return configData.value[group] || []
}

function isTextField(key: string) {
  return ['system_name', 'local_path', 'smtp_host', 'smtp_username', 'base_url', 'webhook_url', 'smtp_from_name', 'client_id', 'redirect_uri'].some(k => key.includes(k))
}

function isNumberField(key: string) {
  return ['password_min_length', 'session_timeout', 'smtp_port', 'max_upload_mb', 'temperature', 'max_tokens', 'top_p', 'timeout_seconds'].some(k => key.includes(k))
}

function getMin(key: string) {
  if (key.includes('password_min_length')) return 6
  if (key.includes('session_timeout')) return 5
  if (key.includes('smtp_port')) return 1
  if (key.includes('max_upload_mb')) return 1
  if (key.includes('temperature')) return 0
  if (key.includes('max_tokens')) return 256
  if (key.includes('top_p')) return 0
  if (key.includes('timeout_seconds')) return 10
  return 0
}

function getMax(key: string) {
  if (key.includes('password_min_length')) return 32
  if (key.includes('session_timeout')) return 1440
  if (key.includes('smtp_port')) return 65535
  if (key.includes('max_upload_mb')) return 1024
  if (key.includes('temperature')) return 2
  if (key.includes('max_tokens')) return 128000
  if (key.includes('top_p')) return 1
  if (key.includes('timeout_seconds')) return 300
  return 9999
}

function getStep(key: string) {
  if (key.includes('temperature')) return 0.1
  if (key.includes('top_p')) return 0.1
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
  if (key === 'sso_provider') return [{ label: 'OIDC', value: 'oidc' }, { label: 'SAML', value: 'saml' }, { label: 'LDAP', value: 'ldap' }]
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
    for (const [, items] of Object.entries(res.groups)) {
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
    for (const item of items) {
      originalValues[item.key] = item.value
    }
    changeHistory.value.unshift({
      user: 'admin',
      time: new Date().toLocaleString('zh-CN'),
      desc: `修改了「${groupList.find(g => g.key === group)?.label || group}」配置`,
      type: 'update',
    })
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
  testing.value = true; testResult.value = null; testGroup.value = 'ai'
  try { testResult.value = await systemConfigApi.testAi() } catch { testResult.value = { success: false, message: '测试请求失败' } } finally { testing.value = false }
}

async function handleTestEmail() {
  const recipient = prompt('请输入测试收件人邮箱:')
  if (!recipient) return
  testing.value = true; testResult.value = null; testGroup.value = 'notification'
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
.config-page__title { font-size: 28px; font-weight: 700; color: var(--neutral-900); margin: 0; }
.config-page__subtitle { font-size: 13px; color: var(--neutral-500); margin: 6px 0 0; }
.config-page__actions { display: flex; gap: 8px; }
.config-page__body { display: flex; gap: 32px; }

/* 左侧导航 */
.config-nav { width: 160px; flex-shrink: 0; position: sticky; top: 80px; align-self: flex-start; display: flex; flex-direction: column; gap: 4px; }
.config-nav__item { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border: none; background: transparent; font-size: 14px; color: var(--neutral-600); cursor: pointer; border-radius: 8px; text-align: left; transition: all 0.2s; font-family: inherit; border-left: 3px solid transparent; }
.config-nav__item:hover { background: var(--neutral-100); }
.config-nav__item--active { color: var(--semantic-600); background: var(--semantic-50, #f0f4ff); font-weight: 600; border-left-color: var(--semantic-600); }
.config-nav__icon { font-size: 16px; }

/* 右侧配置区 */
.config-content { flex: 1; min-width: 0; }
.config-group { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: 14px; padding: 28px; margin-bottom: 24px; transition: box-shadow 0.2s; }
.config-group:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.04); }
.config-group__header { margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--neutral-100); }
.config-group__title { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0 0 4px; }
.config-group__desc { font-size: 13px; color: var(--neutral-500); margin: 0; }
.config-group__fields { display: flex; flex-direction: column; gap: 18px; }
.config-field { display: flex; flex-direction: column; gap: 8px; }
.config-field__label { font-size: 13px; font-weight: 600; color: var(--neutral-700); }

.config-group__footer { display: flex; justify-content: space-between; align-items: center; margin-top: 24px; padding-top: 18px; border-top: 1px solid var(--neutral-100); }
.config-group__footer-left { display: flex; gap: 12px; }
.config-group__footer-right { display: flex; gap: 12px; }

/* 按钮 */
.config-btn { padding: 8px 16px; border-radius: 8px; font-size: 13px; cursor: pointer; border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); transition: all 0.2s; font-family: inherit; display: flex; align-items: center; }
.config-btn:hover { border-color: var(--neutral-300); }
.config-btn--primary { background: var(--semantic-600); color: #fff; border-color: var(--semantic-600); }
.config-btn--primary:hover { background: var(--semantic-700, #4f46e5); }
.config-btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.config-btn--secondary { background: var(--neutral-50); }
.config-btn--ghost { background: transparent; border-color: transparent; color: var(--neutral-500); }

/* 测试结果 */
.config-test-result { margin-top: 16px; padding: 12px 16px; border-radius: 8px; font-size: 13px; display: flex; align-items: center; gap: 10px; }
.config-test-result__icon { font-size: 18px; font-weight: 700; }
.config-test-result--ok { background: rgba(16, 185, 129, 0.08); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
.config-test-result--err { background: rgba(250, 82, 82, 0.08); color: #fa5252; border: 1px solid rgba(250, 82, 82, 0.2); }

/* 变更记录 */
.history-list { display: flex; flex-direction: column; }
.history-item { display: flex; gap: 14px; padding: 14px 0; border-bottom: 1px solid var(--neutral-100); }
.history-item:last-child { border-bottom: none; }
.history-item__dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
.history-item__dot--update { background: var(--semantic-500, #6366f1); }
.history-item__dot--create { background: var(--status-success, #10b981); }
.history-item__dot--init { background: var(--neutral-400); }
.history-item__content { flex: 1; }
.history-item__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.history-item__user { font-size: 13px; font-weight: 600; color: var(--neutral-800); }
.history-item__time { font-size: 12px; color: var(--neutral-400); font-family: var(--font-mono); }
.history-item__desc { font-size: 13px; color: var(--neutral-600); }
.history-empty { text-align: center; padding: 40px; color: var(--neutral-400); }

@media (max-width: 1280px) {
  .config-nav { display: none; }
  .config-page__body { flex-direction: column; }
}
</style>
