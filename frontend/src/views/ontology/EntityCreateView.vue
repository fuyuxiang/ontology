<template>
  <div class="create-page">
    <OntologyBreadcrumb :items="breadcrumbs" />

    <div class="create-page__header">
      <h1 class="create-page__title">新建本体对象</h1>
      <div class="mode-tabs">
        <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'ai' }" @click="mode = 'ai'">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1l1.5 3.5L12 6l-3.5 1.5L7 11l-1.5-3.5L2 6l3.5-1.5z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>
          AI 智能创建
        </button>
        <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'manual' }" @click="mode = 'manual'">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 4h10M2 7h7M2 10h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
          手动创建
        </button>
        <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'import' }" @click="mode = 'import'">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v7M4 6l3 3 3-3M2 10v1a1 1 0 001 1h8a1 1 0 001-1v-1" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          从文件导入
        </button>
      </div>
    </div>

    <!-- AI 智能创建 -->
    <div v-if="mode === 'ai'" class="ai-layout">
      <!-- 左：输入区 -->
      <div class="ai-panel ai-panel--input">
        <div class="panel-title">业务描述输入</div>
        <div class="ai-input-toggle">
          <button class="ai-toggle-btn" :class="{ 'ai-toggle-btn--active': aiInputMode === 'text' }" @click="aiInputMode = 'text'">文本输入</button>
          <button class="ai-toggle-btn" :class="{ 'ai-toggle-btn--active': aiInputMode === 'file' }" @click="aiInputMode = 'file'">文件上传</button>
        </div>
        <div v-if="aiInputMode === 'text'" class="form-row">
          <label class="form-label">业务场景描述</label>
          <textarea v-model="aiText" class="form-textarea" rows="14"
            placeholder="描述业务场景，AI 将自动提取实体、属性和关系。&#10;&#10;例如：&#10;客户是核心实体，包含姓名、手机号、等级属性。每个客户可有多个订单，订单包含订单号、金额、状态。工程师负责处理工单，工单关联客户和工程师。" />
          <span class="form-hint">{{ aiText.length }} / 8000 字符</span>
        </div>
        <div v-else class="form-row">
          <label class="form-label">上传文档</label>
          <div class="file-picker" @click="aiFileRef?.click()">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 4v12M8 8l4-4 4 4M4 18h16" stroke="var(--neutral-400)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span v-if="aiFile" class="file-name">{{ aiFile.name }}</span>
            <span v-else class="file-placeholder">点击选择文件</span>
            <input ref="aiFileRef" type="file" accept=".txt,.md,.doc,.docx,.pdf" class="file-input-hidden" @change="onAiFileChange" />
          </div>
          <span class="form-hint">支持 txt、md、doc、docx、pdf</span>
        </div>
        <button class="btn-primary btn-extract" @click="handleAiExtract" :disabled="aiExtracting || (!aiText && !aiFile)">
          <svg v-if="aiExtracting" class="spin" width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="rgba(255,255,255,0.4)" stroke-width="1.5"/><path d="M7 2a5 5 0 015 5" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>
          <svg v-else width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1l1.5 3.5L12 6l-3.5 1.5L7 11l-1.5-3.5L2 6l3.5-1.5z" stroke="white" stroke-width="1.2" stroke-linejoin="round"/></svg>
          {{ aiExtracting ? 'AI 提取中...' : 'AI 提取本体' }}
        </button>
      </div>

      <!-- 右：提取结果 -->
      <div class="ai-panel ai-panel--result">
        <div class="panel-title">
          提取结果预览
          <template v-if="aiResult">
            <span class="ai-tag ai-tag--blue">{{ aiResult.entities.length }} 个实体</span>
            <span class="ai-tag ai-tag--green">{{ aiTotalAttrs }} 个属性</span>
            <span class="ai-tag ai-tag--amber">{{ aiResult.relations.length }} 个关系</span>
            <button class="btn-sm ai-reset-btn" @click="aiResult = null">重新提取</button>
          </template>
        </div>

        <div v-if="!aiResult" class="result-empty">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><path d="M24 8l3 8 8 3-8 3-3 8-3-8-8-3 8-3z" stroke="var(--neutral-300)" stroke-width="2" stroke-linejoin="round"/><circle cx="36" cy="12" r="2" fill="var(--neutral-200)"/><circle cx="12" cy="36" r="2" fill="var(--neutral-200)"/></svg>
          <p class="text-caption">输入业务描述后点击「AI 提取本体」</p>
        </div>

        <div v-else class="result-content">
          <div v-for="(entity, ei) in aiResult.entities" :key="ei" class="ai-entity-card">
            <div class="ai-entity-header">
              <label class="ai-entity-check">
                <input type="checkbox" v-model="entity.selected" />
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <rect x="1" y="1" width="14" height="14" rx="3" :stroke="entity.selected ? 'var(--semantic-600)' : 'var(--neutral-300)'" stroke-width="1.5" :fill="entity.selected ? 'var(--semantic-600)' : 'none'" />
                  <path v-if="entity.selected" d="M4.5 8l2.5 2.5 4.5-5" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </label>
              <span class="ai-entity-name">{{ entity.name_cn }}</span>
              <span class="ai-entity-en">{{ entity.name }}</span>
              <span class="ai-tier-badge" :style="{ background: tierBg(entity.tier), color: tierFg(entity.tier) }">T{{ entity.tier }}</span>
            </div>
            <div v-if="entity.selected" class="ai-entity-body">
              <input v-model="entity.description" class="form-input form-input--sm" placeholder="描述" style="width:100%;margin-bottom:8px" />
              <div v-if="entity.attributes.length" class="ai-attr-list">
                <div class="ai-attr-row ai-attr-row--header">
                  <span>属性名</span><span>类型</span><span>说明</span>
                </div>
                <div v-for="(attr, ai) in entity.attributes" :key="ai" class="ai-attr-row">
                  <input v-model="attr.name" class="form-input form-input--sm" />
                  <select v-model="attr.type" class="form-input form-input--sm">
                    <option v-for="t in attrTypes" :key="t" :value="t">{{ t }}</option>
                  </select>
                  <input v-model="attr.description" class="form-input form-input--sm" />
                </div>
              </div>
            </div>
          </div>

          <div v-if="aiResult.relations.length" class="ai-relations">
            <div class="panel-subtitle">关系列表</div>
            <div class="ai-rel-list">
              <div class="ai-rel-row ai-rel-row--header">
                <span>源实体</span><span>目标实体</span><span>关系名</span><span>类型</span><span>基数</span>
              </div>
              <div v-for="(rel, ri) in aiResult.relations" :key="ri" class="ai-rel-row">
                <span>{{ rel.from_entity }}</span>
                <span>{{ rel.to_entity }}</span>
                <span>{{ rel.name }}</span>
                <span class="ai-rel-type">{{ rel.rel_type }}</span>
                <span class="ai-rel-card">{{ rel.cardinality }}</span>
              </div>
            </div>
          </div>

          <div class="result-actions">
            <button class="btn-secondary" @click="router.back()">取消</button>
            <button class="btn-primary" @click="handleAiCreate" :disabled="aiCreating || aiSelectedCount === 0">
              {{ aiCreating ? '创建中...' : `确认创建 (${aiSelectedCount} 个)` }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 手动创建 -->
    <div v-if="mode === 'manual'" class="single-panel">
      <form @submit.prevent="handleSubmit" class="entity-form">
        <div class="form-grid">
          <div class="form-row">
            <label class="form-label">对象名称 (英文) <span class="form-required">*</span></label>
            <input v-model="form.name" class="form-input" placeholder="如 Customer, FTTRSubscription" required />
          </div>
          <div class="form-row">
            <label class="form-label">中文名称 <span class="form-required">*</span></label>
            <input v-model="form.name_cn" class="form-input" placeholder="如 客户, FTTR订阅" required />
          </div>
          <div class="form-row">
            <label class="form-label">层级</label>
            <div class="tier-selector">
              <label v-for="t in [1,2,3]" :key="t" class="tier-option" :class="{ 'tier-option--active': form.tier === t, [`tier-option--t${t}`]: form.tier === t }">
                <input type="radio" :value="t" v-model="form.tier" style="display:none" />
                <span class="tier-option-label">T{{ t }}</span>
                <span class="tier-option-name">{{ { 1:'核心对象', 2:'领域对象', 3:'场景对象' }[t] }}</span>
              </label>
            </div>
          </div>
          <div class="form-row form-row--full">
            <label class="form-label">描述</label>
            <textarea v-model="form.description" class="form-textarea" rows="3" placeholder="描述该对象的业务含义" />
          </div>
        </div>

        <div class="attrs-section">
          <div class="attrs-header">
            <span class="panel-subtitle">属性列表</span>
            <button type="button" class="btn-sm" @click="addAttr">+ 添加属性</button>
          </div>
          <div v-if="form.attributes.length" class="attrs-table">
            <div class="attr-row attr-row--header">
              <span>属性名</span><span>类型</span><span>描述</span><span>必填</span><span></span>
            </div>
            <div v-for="(attr, i) in form.attributes" :key="i" class="attr-row">
              <input v-model="attr.name" class="form-input form-input--sm" placeholder="attr_name" />
              <select v-model="attr.type" class="form-input form-input--sm">
                <option v-for="t in attrTypes" :key="t" :value="t">{{ t }}</option>
              </select>
              <input v-model="attr.description" class="form-input form-input--sm" placeholder="说明" />
              <input type="checkbox" v-model="attr.required" />
              <button type="button" class="btn-icon-del" @click="form.attributes.splice(i,1)">×</button>
            </div>
          </div>
          <div v-else class="attrs-empty text-caption">暂无属性，点击「添加属性」</div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="router.back()">取消</button>
          <button type="submit" class="btn-primary" :disabled="submitting">{{ submitting ? '创建中...' : '创建对象' }}</button>
        </div>
      </form>
    </div>

    <!-- 从文件导入 -->
    <div v-if="mode === 'import'" class="single-panel">
      <div class="entity-form">
        <div class="form-row">
          <label class="form-label">文件格式</label>
          <div class="format-selector">
            <label v-for="f in ['json','owl','ttl']" :key="f" class="format-option" :class="{ 'format-option--active': fileFormat === f }">
              <input type="radio" :value="f" v-model="fileFormat" style="display:none" />
              {{ f.toUpperCase() }}
            </label>
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">命名空间前缀</label>
          <input v-model="fileNamespace" class="form-input" placeholder="如 telecom:" />
        </div>
        <div class="form-row">
          <label class="form-label">选择文件</label>
          <div class="file-picker" @click="fileInputRef?.click()">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 4v12M8 8l4-4 4 4M4 18h16" stroke="var(--neutral-400)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
            <span v-else class="file-placeholder">点击选择文件</span>
            <input ref="fileInputRef" type="file" :accept="fileAccept" class="file-input-hidden" @change="onFileChange" />
          </div>
        </div>

        <div v-if="jsonPreview" class="import-preview">
          <div class="import-preview__title">文件预览</div>
          <div class="import-preview__stats">
            <span>场景：{{ jsonPreview.scenario }}</span>
            <span>{{ jsonPreview.objectCount }} 个对象</span>
            <span>{{ jsonPreview.linkCount }} 个关系</span>
            <span>{{ jsonPreview.actionCount }} 个动作</span>
            <span>{{ jsonPreview.ruleCount }} 个规则</span>
          </div>
        </div>

        <div v-if="importResult" class="import-result">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" fill="var(--status-success-bg)"/><path d="M5 8l2 2 4-4" stroke="var(--status-success)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          导入完成：{{ importResult.entities_created }} 个实体，{{ importResult.relations_created }} 个关系
        </div>

        <div class="form-actions">
          <button class="btn-secondary" @click="router.back()">取消</button>
          <button class="btn-primary" @click="handleFileImport" :disabled="submitting || !selectedFile">
            {{ submitting ? '导入中...' : '导入文件' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import OntologyBreadcrumb from '../../components/common/OntologyBreadcrumb.vue'
import { entityApi } from '../../api/ontology'
import { relationApi } from '../../api/relations'
import { post } from '../../api/client'
import { useToast } from '../../composables/useToast'
import type { FileImportResult } from '../../types'

const router = useRouter()
const toast = useToast()

const breadcrumbs = [
  { label: '本体管理', path: '/ontology' },
  { label: '本体目录', path: '/browser' },
  { label: '新建本体对象' },
]

const mode = ref<'ai' | 'manual' | 'import'>('ai')
const attrTypes = ['string', 'number', 'boolean', 'date', 'ref', 'computed', 'enum', 'json']
const submitting = ref(false)

const tierColors: Record<number, { bg: string; fg: string }> = {
  1: { bg: 'var(--tier1-bg)', fg: 'var(--tier1-text)' },
  2: { bg: 'var(--tier2-bg)', fg: 'var(--tier2-text)' },
  3: { bg: 'var(--tier3-bg)', fg: 'var(--tier3-text)' },
}
const tierBg = (t: number) => tierColors[t]?.bg ?? '#eee'
const tierFg = (t: number) => tierColors[t]?.fg ?? '#333'

// ── 手动创建 ──
const form = reactive({
  name: '', name_cn: '', tier: 1, description: '',
  attributes: [] as { name: string; type: string; description: string; required: boolean }[],
})
function addAttr() { form.attributes.push({ name: '', type: 'string', description: '', required: false }) }
async function handleSubmit() {
  if (!form.name || !form.name_cn) return
  submitting.value = true
  try {
    await entityApi.create({ name: form.name, name_cn: form.name_cn, tier: form.tier, description: form.description, attributes: form.attributes.filter(a => a.name) } as never)
    toast.success('对象创建成功')
    router.push('/browser')
  } catch (e) { toast.error(`创建失败: ${(e as Error).message}`) }
  finally { submitting.value = false }
}

// ── 文件导入 ──
const fileFormat = ref<'json' | 'owl' | 'ttl'>('json')
const selectedFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const fileNamespace = ref('')
const jsonPreview = ref<{ scenario: string; objectCount: number; linkCount: number; actionCount: number; ruleCount: number } | null>(null)
const importResult = ref<FileImportResult | null>(null)
const fileAccept = computed(() => ({ json: '.json', owl: '.owl,.rdf,.xml', ttl: '.ttl' }[fileFormat.value]))

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0] || null
  selectedFile.value = file; jsonPreview.value = null; importResult.value = null
  if (file && fileFormat.value === 'json') {
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result as string)
        const scenario = data.scenario
        jsonPreview.value = { scenario: scenario?.scenario_name || scenario?.scenario_short_name || '未知', objectCount: data.object_types?.length || 0, linkCount: data.link_types?.length || 0, actionCount: data.action_types?.length || 0, ruleCount: data.business_rules?.length || 0 }
        if (scenario?.namespace && !fileNamespace.value) fileNamespace.value = scenario.namespace
      } catch { jsonPreview.value = null }
    }
    reader.readAsText(file)
  }
}
async function handleFileImport() {
  if (!selectedFile.value) return
  submitting.value = true; importResult.value = null
  try {
    const res = await entityApi.importFromFile(selectedFile.value, fileFormat.value, fileNamespace.value || undefined)
    importResult.value = res
    toast.success(`导入完成：创建 ${res.entities_created} 个实体，${res.relations_created} 个关系`)
  } catch (e) { toast.error(`导入失败: ${(e as Error).message}`) }
  finally { submitting.value = false }
}

// ── AI 智能创建 ──
interface AiAttr { name: string; type: string; description: string }
interface AiEntity { name: string; name_cn: string; tier: number; description: string; attributes: AiAttr[]; selected: boolean }
interface AiRelation { from_entity: string; to_entity: string; name: string; rel_type: string; cardinality: string }
interface AiResult { entities: AiEntity[]; relations: AiRelation[] }

const aiInputMode = ref<'text' | 'file'>('text')
const aiText = ref('')
const aiFile = ref<File | null>(null)
const aiFileRef = ref<HTMLInputElement | null>(null)
const aiExtracting = ref(false)
const aiCreating = ref(false)
const aiResult = ref<AiResult | null>(null)
const aiTotalAttrs = computed(() => aiResult.value?.entities.reduce((s, e) => s + e.attributes.length, 0) ?? 0)
const aiSelectedCount = computed(() => aiResult.value?.entities.filter(e => e.selected).length ?? 0)

function onAiFileChange(e: Event) { aiFile.value = (e.target as HTMLInputElement).files?.[0] || null }

async function handleAiExtract() {
  aiExtracting.value = true
  try {
    let data: AiResult
    if (aiInputMode.value === 'text') {
      const fd = new FormData(); fd.append('text', aiText.value)
      data = await post<AiResult>('/entities/ai-extract', fd, { timeout: 60000 })
    } else {
      if (!aiFile.value) { toast.error('请选择文件'); return }
      const fd = new FormData(); fd.append('file', aiFile.value)
      data = await post<AiResult>('/entities/ai-extract', fd, { timeout: 60000 })
    }
    data.entities.forEach(e => { e.selected = true })
    aiResult.value = data
    toast.success(`AI 提取完成：${data.entities.length} 个实体`)
  } catch (e) { toast.error(`提取失败: ${(e as Error).message}`) }
  finally { aiExtracting.value = false }
}

async function handleAiCreate() {
  if (!aiResult.value) return
  aiCreating.value = true
  try {
    const selected = aiResult.value.entities.filter(e => e.selected)
    const created: Record<string, string> = {}
    for (const entity of selected) {
      const res = await entityApi.create({ name: entity.name, name_cn: entity.name_cn, tier: entity.tier as any, description: entity.description, attributes: entity.attributes.map(a => ({ id: '', name: a.name, type: a.type as any, description: a.description, required: false })) } as any)
      created[entity.name] = res.id
    }
    for (const rel of aiResult.value.relations) {
      const fromId = created[rel.from_entity], toId = created[rel.to_entity]
      if (fromId && toId) await relationApi.create({ from_entity_id: fromId, to_entity_id: toId, name: rel.name, rel_type: rel.rel_type, cardinality: rel.cardinality })
    }
    toast.success(`成功创建 ${Object.keys(created).length} 个本体对象`)
    router.push('/browser')
  } catch (e) { toast.error(`创建失败: ${(e as Error).message}`) }
  finally { aiCreating.value = false }
}
</script>

<style scoped>
.create-page { padding: 24px; max-width: 1200px; }
.create-page__header { display: flex; align-items: center; justify-content: space-between; margin: 16px 0 24px; flex-wrap: wrap; gap: 12px; }
.create-page__title { font-size: 20px; font-weight: 700; color: var(--neutral-900); margin: 0; }

.mode-tabs { display: flex; gap: 4px; background: var(--neutral-100); padding: 4px; border-radius: var(--radius-lg); }
.mode-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: var(--radius-md); border: none; background: transparent; font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-600); cursor: pointer; transition: all var(--transition-fast); }
.mode-tab:hover { color: var(--neutral-800); }
.mode-tab--active { background: var(--neutral-0); color: var(--semantic-600); box-shadow: 0 1px 4px rgba(0,0,0,0.08); }

/* AI 布局 */
.ai-layout { display: grid; grid-template-columns: 420px 1fr; gap: 20px; align-items: start; }
.ai-panel { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 20px; }
.ai-panel--result { min-height: 400px; }
.panel-title { font-size: 14px; font-weight: 600; color: var(--neutral-800); margin-bottom: 16px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.panel-subtitle { font-size: 13px; font-weight: 600; color: var(--neutral-700); margin-bottom: 8px; }

.ai-input-toggle { display: flex; gap: 4px; margin-bottom: 14px; }
.ai-toggle-btn { padding: 5px 14px; border-radius: var(--radius-md); border: 1px solid var(--neutral-200); background: transparent; font-size: var(--text-caption-size); color: var(--neutral-600); cursor: pointer; transition: all var(--transition-fast); }
.ai-toggle-btn--active { background: var(--semantic-50); border-color: var(--semantic-300); color: var(--semantic-700); }

.form-row { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.form-label { font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-700); }
.form-input { padding: 7px 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-body-size); color: var(--neutral-800); background: var(--neutral-0); outline: none; transition: border-color var(--transition-fast); }
.form-input:focus { border-color: var(--semantic-400); }
.form-input--sm { padding: 4px 8px; font-size: var(--text-caption-size); }
.form-textarea { padding: 8px 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-body-size); color: var(--neutral-800); background: var(--neutral-0); resize: vertical; outline: none; font-family: inherit; transition: border-color var(--transition-fast); }
.form-textarea:focus { border-color: var(--semantic-400); }
.form-hint { font-size: var(--text-caption-size); color: var(--neutral-400); }
.form-required { color: var(--status-error); }

.file-picker { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 24px; border: 2px dashed var(--neutral-200); border-radius: var(--radius-md); cursor: pointer; transition: border-color var(--transition-fast); }
.file-picker:hover { border-color: var(--semantic-300); }
.file-input-hidden { display: none; }
.file-name { font-size: var(--text-body-size); color: var(--semantic-600); font-weight: 500; }
.file-placeholder { font-size: var(--text-body-size); color: var(--neutral-400); }

.btn-extract { width: 100%; justify-content: center; display: flex; align-items: center; gap: 6px; padding: 10px; margin-top: 4px; }

.result-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 0; gap: 12px; color: var(--neutral-400); }

.result-content { display: flex; flex-direction: column; gap: 10px; }
.result-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; padding-top: 16px; border-top: 1px solid var(--neutral-100); }

.ai-entity-card { border: 1px solid var(--neutral-200); border-radius: var(--radius-md); padding: 12px; transition: border-color var(--transition-fast); }
.ai-entity-card:has(input:checked) { border-color: var(--semantic-300); background: var(--semantic-50); }
.ai-entity-header { display: flex; align-items: center; gap: 8px; }
.ai-entity-check { cursor: pointer; display: flex; align-items: center; }
.ai-entity-check input { display: none; }
.ai-entity-name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.ai-entity-en { font-size: var(--text-caption-size); color: var(--neutral-400); }
.ai-tier-badge { padding: 1px 7px; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.3px; margin-left: auto; }
.ai-entity-body { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--neutral-100); }
.ai-attr-list { font-size: var(--text-code-size); }
.ai-attr-row { display: grid; grid-template-columns: 1fr 90px 1.5fr; gap: 6px; margin-bottom: 4px; align-items: center; }
.ai-attr-row--header { font-weight: 500; color: var(--neutral-500); font-size: var(--text-caption-size); margin-bottom: 4px; }
.ai-relations { margin-top: 4px; }
.ai-rel-list { font-size: var(--text-code-size); }
.ai-rel-row { display: grid; grid-template-columns: 1fr 1fr 1fr 80px 55px; gap: 6px; padding: 4px 0; border-bottom: 1px solid var(--neutral-50); align-items: center; }
.ai-rel-row--header { font-weight: 500; color: var(--neutral-500); font-size: var(--text-caption-size); border-bottom-color: var(--neutral-200); }
.ai-rel-type { color: var(--semantic-600); font-size: var(--text-caption-size); }
.ai-rel-card { color: var(--neutral-500); font-size: var(--text-caption-size); }
.ai-tag { display: inline-block; padding: 1px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 500; }
.ai-tag--blue { background: var(--status-info-bg); color: var(--status-info); }
.ai-tag--green { background: var(--status-success-bg); color: var(--status-success); }
.ai-tag--amber { background: var(--status-warning-bg); color: var(--kinetic-700); }
.ai-reset-btn { margin-left: auto; }

/* 手动/导入 单栏 */
.single-panel { max-width: 700px; background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); padding: 24px; }
.entity-form { display: flex; flex-direction: column; gap: 0; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 20px; margin-bottom: 20px; }
.form-row--full { grid-column: 1 / -1; }

.tier-selector { display: flex; gap: 8px; }
.tier-option { display: flex; flex-direction: column; align-items: center; padding: 8px 16px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); cursor: pointer; transition: all var(--transition-fast); gap: 2px; }
.tier-option:hover { border-color: var(--neutral-400); }
.tier-option--active { border-color: var(--semantic-400); background: var(--semantic-50); }
.tier-option-label { font-size: 13px; font-weight: 700; color: var(--neutral-700); }
.tier-option-name { font-size: 11px; color: var(--neutral-500); }

.attrs-section { margin-bottom: 20px; }
.attrs-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.attrs-table { display: flex; flex-direction: column; gap: 4px; }
.attr-row { display: grid; grid-template-columns: 1.2fr 90px 1.5fr 40px 28px; gap: 6px; align-items: center; }
.attr-row--header { font-size: var(--text-caption-size); font-weight: 500; color: var(--neutral-500); padding: 0 2px; }
.attrs-empty { color: var(--neutral-400); padding: 12px 0; }
.btn-icon-del { width: 24px; height: 24px; border: none; background: transparent; color: var(--neutral-400); cursor: pointer; font-size: 16px; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; }
.btn-icon-del:hover { background: var(--status-error-bg); color: var(--status-error); }

.format-selector { display: flex; gap: 8px; }
.format-option { padding: 5px 16px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-600); transition: all var(--transition-fast); }
.format-option--active { border-color: var(--semantic-400); background: var(--semantic-50); color: var(--semantic-700); }

.import-preview { background: var(--neutral-50); border: 1px solid var(--neutral-200); border-radius: var(--radius-md); padding: 12px 14px; margin-bottom: 14px; }
.import-preview__title { font-size: var(--text-caption-size); font-weight: 600; color: var(--neutral-600); margin-bottom: 6px; }
.import-preview__stats { display: flex; gap: 16px; flex-wrap: wrap; font-size: var(--text-caption-size); color: var(--neutral-700); }
.import-result { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: var(--status-success-bg); border-radius: var(--radius-md); font-size: var(--text-body-size); color: var(--status-success); margin-bottom: 14px; }

.form-actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 16px; border-top: 1px solid var(--neutral-100); }

/* 通用按钮 */
.btn-primary { padding: 8px 20px; border-radius: var(--radius-md); border: none; background: var(--semantic-600); color: #fff; font-size: var(--text-body-size); font-weight: 500; cursor: pointer; transition: background var(--transition-fast); }
.btn-primary:hover:not(:disabled) { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { padding: 8px 20px; border-radius: var(--radius-md); border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); font-size: var(--text-body-size); font-weight: 500; cursor: pointer; transition: all var(--transition-fast); }
.btn-secondary:hover { border-color: var(--neutral-400); }
.btn-sm { padding: 4px 12px; border-radius: var(--radius-md); border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-600); font-size: var(--text-caption-size); cursor: pointer; transition: all var(--transition-fast); }
.btn-sm:hover { border-color: var(--neutral-400); color: var(--neutral-800); }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
