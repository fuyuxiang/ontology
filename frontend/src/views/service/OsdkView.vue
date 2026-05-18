<template>
  <div class="osdk-page">
    <div class="osdk-page__header">
      <h1 class="page-title">OSDK 生成</h1>
      <p class="page-desc">根据本体 Schema 自动生成类型安全的 SDK，供开发者在应用中直接操作业务对象</p>
    </div>

    <div class="osdk-page__body">
      <!-- 左侧：配置 -->
      <div class="osdk-config">
        <div class="config-section">
          <h3 class="config-title">语言选择</h3>
          <div class="lang-tabs">
            <button class="lang-tab" :class="{ 'lang-tab--active': language === 'typescript' }" @click="language = 'typescript'">TypeScript</button>
            <button class="lang-tab" :class="{ 'lang-tab--active': language === 'python' }" @click="language = 'python'">Python</button>
          </div>
        </div>

        <div class="config-section">
          <h3 class="config-title">包含实体 <span class="config-hint">({{ selectedCount }}/{{ entities.length }})</span></h3>
          <div class="entity-check-list">
            <label class="entity-check" v-for="e in entities" :key="e.id">
              <input type="checkbox" v-model="e.selected" />
              <span class="entity-check__name">{{ e.name_cn }}</span>
              <span class="entity-check__en">{{ e.name }}</span>
              <span class="entity-check__tier">T{{ e.tier }}</span>
            </label>
          </div>
          <div class="check-actions">
            <button class="btn-sm" @click="selectAll">全选</button>
            <button class="btn-sm" @click="selectNone">取消全选</button>
          </div>
        </div>

        <button class="btn-primary btn-generate" @click="generate" :disabled="generating || selectedCount === 0">
          {{ generating ? '生成中...' : '生成 SDK' }}
        </button>
      </div>

      <!-- 右侧：代码预览 -->
      <div class="osdk-preview">
        <div class="preview-header">
          <span class="preview-title">代码预览</span>
          <button v-if="generatedCode" class="btn-sm" @click="downloadSdk">下载 SDK</button>
        </div>
        <div v-if="generatedCode" class="preview-code">
          <div v-for="file in generatedCode.files" :key="file.name" class="code-file">
            <div class="code-file__name">{{ file.name }}</div>
            <pre class="code-file__content">{{ file.content }}</pre>
          </div>
        </div>
        <div v-else class="preview-empty">
          <p>选择实体并点击"生成 SDK"预览代码</p>
        </div>

        <!-- 使用示例 -->
        <div v-if="generatedCode" class="usage-section">
          <h3 class="config-title">使用示例</h3>
          <pre class="code-file__content">{{ usageExample }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { get, post } from '../../api/client'

interface EntityItem { id: string; name: string; name_cn: string; tier: number; selected: boolean }
interface CodeFile { name: string; content: string }
interface GeneratedSdk { files: CodeFile[]; usage: string }

const language = ref<'typescript' | 'python'>('typescript')
const entities = ref<EntityItem[]>([])
const generating = ref(false)
const generatedCode = ref<GeneratedSdk | null>(null)

const selectedCount = computed(() => entities.value.filter(e => e.selected).length)
const usageExample = computed(() => generatedCode.value?.usage || '')

function selectAll() { entities.value.forEach(e => e.selected = true) }
function selectNone() { entities.value.forEach(e => e.selected = false) }

async function loadEntities() {
  try {
    const data = await get<any[]>('/entities')
    entities.value = data.filter(e => e.status === 'published').map(e => ({ id: e.id, name: e.name, name_cn: e.name_cn, tier: e.tier, selected: true }))
  } catch { /* empty */ }
}

async function generate() {
  generating.value = true
  generatedCode.value = null
  try {
    const entityIds = entities.value.filter(e => e.selected).map(e => e.id)
    const result = await post<GeneratedSdk>('/osdk/generate', { language: language.value, entity_ids: entityIds })
    generatedCode.value = result
  } catch (e: any) {
    generatedCode.value = { files: [{ name: 'error.txt', content: e?.response?.data?.detail || '生成失败' }], usage: '' }
  } finally {
    generating.value = false
  }
}

async function downloadSdk() {
  try {
    const entityIds = entities.value.filter(e => e.selected).map(e => e.id)
    const res = await post('/osdk/download', { language: language.value, entity_ids: entityIds }, { responseType: 'blob' })
    const blob = new Blob([res as any], { type: 'application/zip' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ontology-sdk-${language.value}.zip`
    a.click()
    URL.revokeObjectURL(url)
  } catch { /* ignore */ }
}

onMounted(loadEntities)
</script>

<style scoped>
.osdk-page { display: flex; flex-direction: column; height: 100%; }
.osdk-page__header { padding: 20px 24px 12px; flex-shrink: 0; }
.page-title { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0 0 4px; }
.page-desc { font-size: 13px; color: var(--neutral-500); margin: 0; }
.osdk-page__body { display: flex; flex: 1; overflow: hidden; border-top: 1px solid var(--neutral-200); }

.osdk-config { width: 300px; flex-shrink: 0; border-right: 1px solid var(--neutral-200); padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.config-section { display: flex; flex-direction: column; gap: 8px; }
.config-title { font-size: 13px; font-weight: 600; color: var(--neutral-800); margin: 0; }
.config-hint { font-weight: 400; color: var(--neutral-400); font-size: 11px; }

.lang-tabs { display: flex; gap: 4px; }
.lang-tab { padding: 6px 14px; border: 1px solid var(--neutral-200); border-radius: 6px; background: var(--neutral-0); font-size: 12px; cursor: pointer; color: var(--neutral-600); }
.lang-tab--active { background: var(--semantic-600); color: #fff; border-color: var(--semantic-600); }

.entity-check-list { display: flex; flex-direction: column; gap: 2px; max-height: 360px; overflow-y: auto; }
.entity-check { display: flex; align-items: center; gap: 6px; padding: 4px 6px; border-radius: 4px; font-size: 12px; cursor: pointer; }
.entity-check:hover { background: var(--neutral-50); }
.entity-check input { margin: 0; }
.entity-check__name { font-weight: 500; color: var(--neutral-800); }
.entity-check__en { color: var(--neutral-400); font-size: 10px; font-family: monospace; }
.entity-check__tier { margin-left: auto; font-size: 10px; color: var(--neutral-400); }
.check-actions { display: flex; gap: 6px; }
.btn-sm { padding: 3px 10px; border: 1px solid var(--neutral-200); border-radius: 5px; background: var(--neutral-0); font-size: 11px; cursor: pointer; color: var(--neutral-600); }
.btn-sm:hover { background: var(--neutral-50); }

.btn-primary { padding: 8px 16px; border-radius: 6px; border: none; background: var(--semantic-600); color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-generate { margin-top: auto; }

.osdk-preview { flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 16px; }
.preview-header { display: flex; align-items: center; justify-content: space-between; }
.preview-title { font-size: 14px; font-weight: 600; color: var(--neutral-800); }
.preview-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--neutral-400); font-size: 13px; }
.preview-code { display: flex; flex-direction: column; gap: 12px; }
.code-file__name { font-size: 11px; font-weight: 600; color: var(--neutral-500); margin-bottom: 4px; font-family: monospace; }
.code-file__content { background: var(--neutral-900); color: #a5f3fc; padding: 12px; border-radius: 6px; font-size: 11px; overflow-x: auto; max-height: 400px; overflow-y: auto; white-space: pre; font-family: monospace; margin: 0; }
.usage-section { border-top: 1px solid var(--neutral-200); padding-top: 16px; }
</style>
