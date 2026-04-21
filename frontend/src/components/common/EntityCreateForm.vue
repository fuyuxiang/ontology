<template>
  <ModalDialog :visible="visible" title="新建本体对象" width="720px" @close="$emit('close')">
    <!-- 模式切换 -->
    <div class="mode-tabs">
      <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'ai' }" @click="mode = 'ai'">AI 智能创建</button>
      <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'manual' }" @click="mode = 'manual'">手动创建</button>
      <button class="mode-tab" :class="{ 'mode-tab--active': mode === 'import' }" @click="mode = 'import'">从文件导入</button>
    </div>

    <!-- AI 智能创建 -->
    <div v-if="mode === 'ai'" class="entity-form">
      <!-- 步骤一：输入 -->
      <template v-if="!aiResult">
        <div class="ai-input-toggle">
          <button class="ai-toggle-btn" :class="{ 'ai-toggle-btn--active': aiInputMode === 'text' }" @click="aiInputMode = 'text'">文本输入</button>
          <button class="ai-toggle-btn" :class="{ 'ai-toggle-btn--active': aiInputMode === 'file' }" @click="aiInputMode = 'file'">文件上传</button>
        </div>
        <div v-if="aiInputMode === 'text'" class="form-row">
          <label class="form-label">业务描述</label>
          <textarea v-model="aiText" class="form-input form-textarea" rows="6"
            placeholder="描述业务场景，AI 将自动提取实体、属性和关系。&#10;例如：客户是核心实体，包含姓名、手机号、等级属性。每个客户可有多个订单，订单包含订单号、金额、状态。" />
          <span class="form-hint">{{ aiText.length }} / 8000 字符</span>
        </div>
        <div v-else class="form-row">
          <label class="form-label">上传文档</label>
          <div class="file-picker">
            <input ref="aiFileRef" type="file" accept=".txt,.md,.doc,.docx,.pdf" class="file-input" @change="onAiFileChange" />
            <span v-if="aiFile" class="file-name">{{ aiFile.name }}</span>
          </div>
          <span class="form-hint">支持 txt、md、doc、docx、pdf</span>
        </div>
      </template>

      <!-- 步骤二：提取结果预览与审批 -->
      <template v-if="aiResult">
        <div class="ai-result-summary">
          <span class="ai-tag ai-tag--blue">{{ aiResult.entities.length }} 个实体</span>
          <span class="ai-tag ai-tag--green">{{ aiTotalAttrs }} 个属性</span>
          <span class="ai-tag ai-tag--amber">{{ aiResult.relations.length }} 个关系</span>
          <button class="btn-sm ai-reset-btn" @click="aiResult = null">重新提取</button>
        </div>

        <div v-for="(entity, ei) in aiResult.entities" :key="ei" class="ai-entity-card">
          <div class="ai-entity-header">
            <label class="ai-entity-check">
              <input type="checkbox" v-model="entity.selected" />
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="1" y="1" width="12" height="12" rx="3" :stroke="entity.selected ? 'var(--semantic-600)' : 'var(--neutral-300)'" stroke-width="1.5" :fill="entity.selected ? 'var(--semantic-600)' : 'none'" />
                <path v-if="entity.selected" d="M4 7l2 2 4-4" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </label>
            <span class="ai-entity-name">{{ entity.name_cn }}</span>
            <span class="ai-entity-en">{{ entity.name }}</span>
            <span class="ai-tier-badge" :style="{ background: tierBg(entity.tier), color: tierFg(entity.tier) }">T{{ entity.tier }}</span>
          </div>
          <div v-if="entity.selected" class="ai-entity-body">
            <div class="ai-entity-desc">
              <input v-model="entity.description" class="form-input form-input--sm" placeholder="描述" style="width:100%" />
            </div>
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
          <div class="form-label" style="margin-bottom:6px">关系列表</div>
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
      </template>
    </div>

    <!-- 手动创建 -->
    <form v-if="mode === 'manual'" @submit.prevent="handleSubmit" class="entity-form">
      <div class="form-row">
        <label class="form-label">对象名称 (英文)</label>
        <input v-model="form.name" class="form-input" placeholder="如 Customer, FTTRSubscription" required />
      </div>
      <div class="form-row">
        <label class="form-label">中文名称</label>
        <input v-model="form.name_cn" class="form-input" placeholder="如 客户, FTTR订阅" required />
      </div>
      <div class="form-row">
        <label class="form-label">Tier 层级</label>
        <div class="form-radio-group">
          <label v-for="t in [1,2,3]" :key="t" class="form-radio" :class="{ 'form-radio--active': form.tier === t }">
            <input type="radio" :value="t" v-model="form.tier" />
            <span class="tier-dot" :style="{ background: `var(--tier${t}-primary)` }"></span>
            Tier {{ t }} {{ tierNames[t] }}
          </label>
        </div>
      </div>
      <div class="form-row">
        <label class="form-label">描述</label>
        <textarea v-model="form.description" class="form-input form-textarea" placeholder="对象描述..." rows="2" />
      </div>
      <div class="form-section">
        <div class="form-section-header">
          <span class="form-label">属性列表</span>
          <button type="button" class="btn-sm" @click="addAttr">+ 添加属性</button>
        </div>
        <div v-for="(attr, i) in form.attributes" :key="i" class="attr-row">
          <input v-model="attr.name" class="form-input form-input--sm" placeholder="属性名" />
          <select v-model="attr.type" class="form-input form-input--sm">
            <option v-for="t in attrTypes" :key="t" :value="t">{{ t }}</option>
          </select>
          <input v-model="attr.description" class="form-input form-input--sm" placeholder="描述" style="flex:2" />
          <label class="form-checkbox"><input type="checkbox" v-model="attr.required" /> 必填</label>
          <button type="button" class="btn-icon" @click="form.attributes.splice(i, 1)">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
      </div>
    </form>

    <!-- 从文件导入 -->
    <div v-else class="entity-form">
      <!-- 文件格式选择 -->
      <div class="form-row">
        <label class="form-label">文件格式</label>
        <div class="form-radio-group">
          <label class="form-radio" :class="{ 'form-radio--active': fileFormat === 'json' }">
            <input type="radio" value="json" v-model="fileFormat" />
            <span>JSON（本体规范）</span>
          </label>
          <label class="form-radio" :class="{ 'form-radio--active': fileFormat === 'owl' }">
            <input type="radio" value="owl" v-model="fileFormat" />
            <span>OWL / RDF</span>
          </label>
          <label class="form-radio" :class="{ 'form-radio--active': fileFormat === 'ttl' }">
            <input type="radio" value="ttl" v-model="fileFormat" />
            <span>Turtle (TTL)</span>
          </label>
        </div>
      </div>

      <!-- 文件选择 -->
      <div class="form-row">
        <label class="form-label">选择文件</label>
        <div class="file-picker">
          <input ref="fileInputRef" type="file" :accept="fileAccept" class="file-input" @change="onFileChange" />
          <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
        </div>
      </div>

      <!-- JSON 预览 -->
      <div v-if="fileFormat === 'json' && jsonPreview" class="form-section">
        <div class="form-section-header">
          <span class="form-label">文件预览</span>
        </div>
        <div class="import-preview">
          <div class="preview-item"><span class="preview-label">场景</span><span>{{ jsonPreview.scenario }}</span></div>
          <div class="preview-item"><span class="preview-label">本体对象</span><span>{{ jsonPreview.objectCount }} 个</span></div>
          <div class="preview-item"><span class="preview-label">关系</span><span>{{ jsonPreview.linkCount }} 个</span></div>
          <div class="preview-item"><span class="preview-label">动作</span><span>{{ jsonPreview.actionCount }} 个</span></div>
          <div class="preview-item"><span class="preview-label">业务规则</span><span>{{ jsonPreview.ruleCount }} 个</span></div>
        </div>
      </div>

      <!-- JSON 模式下的 namespace -->
      <div v-if="fileFormat === 'json'" class="form-row">
        <label class="form-label">命名空间（可选，留空则从文件读取）</label>
        <input v-model="fileNamespace" class="form-input" placeholder="如 s1, s2" />
      </div>

      <!-- 导入结果 -->
      <div v-if="importResult" class="form-section">
        <div class="form-section-header">
          <span class="form-label">导入结果</span>
        </div>
        <div class="import-preview import-result">
          <div class="preview-item"><span class="preview-label">创建实体</span><span>{{ importResult.entities_created }} 个</span></div>
          <div class="preview-item"><span class="preview-label">跳过实体</span><span>{{ importResult.entities_skipped }} 个</span></div>
          <div class="preview-item"><span class="preview-label">创建属性</span><span>{{ importResult.attributes_created }} 个</span></div>
          <div class="preview-item"><span class="preview-label">创建关系</span><span>{{ importResult.relations_created }} 个</span></div>
          <div class="preview-item"><span class="preview-label">创建规则</span><span>{{ importResult.rules_created }} 个</span></div>
          <div class="preview-item"><span class="preview-label">创建动作</span><span>{{ importResult.actions_created }} 个</span></div>
          <div v-if="importResult.errors.length" class="preview-errors">
            <div v-for="(err, i) in importResult.errors" :key="i" class="preview-error">{{ err }}</div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <button class="btn-secondary" @click="$emit('close')">取消</button>
      <template v-if="mode === 'ai'">
        <button v-if="!aiResult" class="btn-primary" @click="handleAiExtract" :disabled="aiExtracting || (!aiText && !aiFile)">
          {{ aiExtracting ? 'AI 提取中...' : 'AI 提取本体' }}
        </button>
        <button v-else class="btn-primary" @click="handleAiCreate" :disabled="aiCreating || aiSelectedCount === 0">
          {{ aiCreating ? '创建中...' : `确认创建 (${aiSelectedCount} 个)` }}
        </button>
      </template>
      <button v-else-if="mode === 'manual'" class="btn-primary" @click="handleSubmit" :disabled="submitting">
        {{ submitting ? '创建中...' : '创建对象' }}
      </button>
      <button v-else class="btn-primary" @click="handleFileImport" :disabled="submitting || !selectedFile">
        {{ submitting ? '导入中...' : '导入文件' }}
      </button>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import ModalDialog from './ModalDialog.vue'
import { entityApi } from '../../api/ontology'
import { relationApi } from '../../api/relations'
import { post } from '../../api/client'
import { useToast } from '../../composables/useToast'
import type { FileImportResult } from '../../types'

defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: []; created: [] }>()
const toast = useToast()

const mode = ref<'ai' | 'manual' | 'import'>('ai')
const tierNames: Record<number, string> = { 1: '核心', 2: '领域', 3: '场景' }
const attrTypes = ['string', 'number', 'boolean', 'date', 'ref', 'computed', 'enum', 'json']
const submitting = ref(false)

// ── 手动创建 ──
const form = reactive({
  name: '', name_cn: '', tier: 1, description: '',
  attributes: [] as { name: string; type: string; description: string; required: boolean }[],
})

function addAttr() {
  form.attributes.push({ name: '', type: 'string', description: '', required: false })
}

async function handleSubmit() {
  if (!form.name || !form.name_cn) return
  submitting.value = true
  try {
    await entityApi.create({ name: form.name, name_cn: form.name_cn, tier: form.tier, description: form.description, attributes: form.attributes.filter(a => a.name) } as never)
    form.name = ''; form.name_cn = ''; form.tier = 1; form.description = ''; form.attributes = []
    toast.success('对象创建成功'); emit('created'); emit('close')
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

const fileAccept = computed(() => {
  if (fileFormat.value === 'json') return '.json'
  if (fileFormat.value === 'owl') return '.owl,.rdf,.xml'
  return '.ttl'
})

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0] || null
  selectedFile.value = file
  jsonPreview.value = null
  importResult.value = null

  if (file && fileFormat.value === 'json') {
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result as string)
        const scenario = data.scenario
        jsonPreview.value = {
          scenario: scenario?.scenario_name || scenario?.scenario_short_name || '未知',
          objectCount: data.object_types?.length || 0,
          linkCount: data.link_types?.length || 0,
          actionCount: data.action_types?.length || 0,
          ruleCount: data.business_rules?.length || 0,
        }
        if (scenario?.namespace && !fileNamespace.value) {
          fileNamespace.value = scenario.namespace
        }
      } catch { jsonPreview.value = null }
    }
    reader.readAsText(file)
  }
}

async function handleFileImport() {
  if (!selectedFile.value) return
  submitting.value = true
  importResult.value = null
  try {
    const res = await entityApi.importFromFile(selectedFile.value, fileFormat.value, fileNamespace.value || undefined)
    importResult.value = res
    toast.success(`导入完成：创建 ${res.entities_created} 个实体，${res.relations_created} 个关系`)
    emit('created')
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

const tierColors: Record<number, { bg: string; fg: string }> = {
  1: { bg: '#dbe4ff', fg: '#4c6ef5' },
  2: { bg: '#e5dbff', fg: '#7950f2' },
  3: { bg: '#c3fae8', fg: '#20c997' },
}
function tierBg(t: number) { return tierColors[t]?.bg || '#dbe4ff' }
function tierFg(t: number) { return tierColors[t]?.fg || '#4c6ef5' }

function onAiFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  aiFile.value = input.files?.[0] || null
}

async function handleAiExtract() {
  aiExtracting.value = true
  try {
    let data: AiResult
    if (aiInputMode.value === 'text') {
      if (!aiText.value.trim()) { toast.error('请输入业务描述'); return }
      data = await post<AiResult>('/entities/ai-extract', (() => { const fd = new FormData(); fd.append('text', aiText.value); return fd })(), { timeout: 60000 })
    } else {
      if (!aiFile.value) { toast.error('请选择文件'); return }
      const fd = new FormData()
      fd.append('file', aiFile.value)
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
      const res = await entityApi.create({
        name: entity.name,
        name_cn: entity.name_cn,
        tier: entity.tier as any,
        description: entity.description,
        attributes: entity.attributes.map(a => ({ id: '', name: a.name, type: a.type as any, description: a.description, required: false })),
      } as any)
      created[entity.name] = res.id
    }
    for (const rel of aiResult.value.relations) {
      const fromId = created[rel.from_entity]
      const toId = created[rel.to_entity]
      if (fromId && toId) {
        await relationApi.create({ from_entity_id: fromId, to_entity_id: toId, name: rel.name, rel_type: rel.rel_type, cardinality: rel.cardinality })
      }
    }
    toast.success(`成功创建 ${Object.keys(created).length} 个本体对象`)
    aiResult.value = null
    aiText.value = ''
    aiFile.value = null
    emit('created'); emit('close')
  } catch (e) { toast.error(`创建失败: ${(e as Error).message}`) }
  finally { aiCreating.value = false }
}
</script>

<style scoped>
/* 模式切换 */
.mode-tabs { display: flex; gap: 4px; margin-bottom: 16px; padding: 3px; background: var(--neutral-100); border-radius: 8px; }
.mode-tab {
  flex: 1; padding: 7px 0; border: none; border-radius: 6px; font-size: var(--text-body-size); font-weight: 500;
  background: transparent; color: var(--neutral-500); cursor: pointer; transition: all 0.15s;
}
.mode-tab--active { background: var(--neutral-0); color: var(--semantic-600); box-shadow: 0 1px 3px rgba(0,0,0,0.08); }

.entity-form { display: flex; flex-direction: column; gap: 14px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: var(--text-code-size); font-weight: 500; color: var(--neutral-600); }
.form-input {
  padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
  font-size: var(--text-body-size); color: var(--neutral-800); background: var(--neutral-0); outline: none;
}
.form-input:focus { border-color: var(--semantic-500); }
.form-input--sm { padding: 6px 8px; font-size: var(--text-code-size); }
.form-textarea { resize: vertical; font-family: inherit; }
.form-radio-group { display: flex; gap: 12px; }
.form-radio {
  display: flex; align-items: center; gap: 6px; padding: 6px 12px;
  border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
  font-size: var(--text-code-size); cursor: pointer; transition: all var(--transition-fast);
}
.form-radio input { display: none; }
.form-radio--active { border-color: var(--semantic-500); background: var(--semantic-50); }
.tier-dot { width: 8px; height: 8px; border-radius: 50%; }
.form-section { margin-top: 4px; }
.form-section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.attr-row { display: flex; gap: 6px; align-items: center; margin-bottom: 6px; }
.attr-row .form-input { flex: 1; }
.form-checkbox { display: flex; align-items: center; gap: 4px; font-size: var(--text-caption-size); color: var(--neutral-600); white-space: nowrap; }
.btn-sm { padding: 4px 10px; border-radius: var(--radius-md); border: 1px solid var(--semantic-400); background: transparent; color: var(--semantic-600); font-size: var(--text-caption-size); cursor: pointer; }
.btn-sm:hover { background: var(--semantic-50); }
.btn-icon { width: 24px; height: 24px; border: none; background: transparent; color: var(--neutral-400); cursor: pointer; display: flex; align-items: center; justify-content: center; }
.btn-icon:hover { color: var(--status-error); }
.btn-primary { padding: 8px 20px; border-radius: var(--radius-md); border: none; background: var(--semantic-600); color: var(--neutral-0); font-size: var(--text-body-size); font-weight: 500; cursor: pointer; }
.btn-primary:hover { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { padding: 8px 16px; border-radius: var(--radius-md); border: 1px solid var(--neutral-300); background: var(--neutral-0); color: var(--neutral-700); font-size: var(--text-body-size); cursor: pointer; }
.btn-secondary:hover { background: var(--neutral-50); }

/* 文件导入 */
.file-picker { position: relative; }
.file-input {
  width: 100%; padding: 8px 12px; border: 1px dashed var(--neutral-300); border-radius: var(--radius-md);
  font-size: var(--text-body-size); color: var(--neutral-600); background: var(--neutral-0); cursor: pointer;
}
.file-input:hover { border-color: var(--semantic-500); }
.file-name { display: block; margin-top: 4px; font-size: var(--text-code-size); color: var(--semantic-600); }
.import-preview {
  border: 1px solid var(--neutral-200); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 6px;
}
.import-result { background: var(--semantic-50); border-color: var(--semantic-200); }
.preview-item { display: flex; justify-content: space-between; font-size: var(--text-code-size); color: var(--neutral-700); }
.preview-label { font-weight: 500; color: var(--neutral-500); }
.preview-errors { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--neutral-200); }
.preview-error { font-size: var(--text-caption-size); color: var(--status-error); margin-bottom: 2px; }

/* AI 智能创建 */
.ai-input-toggle { display: flex; gap: 4px; margin-bottom: 8px; }
.ai-toggle-btn {
  padding: 5px 14px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
  font-size: var(--text-caption-size); font-weight: 500; background: var(--neutral-0);
  color: var(--neutral-500); cursor: pointer; transition: all 0.15s;
}
.ai-toggle-btn--active { border-color: var(--semantic-500); color: var(--semantic-600); background: var(--semantic-50); }
.form-hint { font-size: var(--text-caption-size); color: var(--neutral-400); margin-top: 2px; }

.ai-result-summary { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.ai-tag {
  padding: 2px 10px; border-radius: 10px; font-size: var(--text-caption-size); font-weight: 600;
}
.ai-tag--blue { background: #dbe4ff; color: #4c6ef5; }
.ai-tag--green { background: #c3fae8; color: #0ca678; }
.ai-tag--amber { background: #fff3bf; color: #e67700; }
.ai-reset-btn { margin-left: auto; }

.ai-entity-card {
  border: 1px solid var(--neutral-200); border-radius: 8px; padding: 10px 12px; margin-bottom: 10px;
  transition: border-color 0.15s;
}
.ai-entity-card:hover { border-color: var(--neutral-300); }
.ai-entity-header { display: flex; align-items: center; gap: 8px; }
.ai-entity-check { cursor: pointer; display: flex; align-items: center; }
.ai-entity-check input { display: none; }
.ai-entity-name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.ai-entity-en { font-size: var(--text-caption-size); color: var(--neutral-400); }
.ai-tier-badge {
  padding: 1px 7px; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.3px;
}
.ai-entity-body { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--neutral-100); }
.ai-entity-desc { margin-bottom: 8px; }

.ai-attr-list { font-size: var(--text-code-size); }
.ai-attr-row { display: grid; grid-template-columns: 1fr 100px 1.5fr; gap: 6px; margin-bottom: 4px; align-items: center; }
.ai-attr-row--header { font-weight: 500; color: var(--neutral-500); font-size: var(--text-caption-size); margin-bottom: 2px; }

.ai-relations { margin-top: 8px; }
.ai-rel-list { font-size: var(--text-code-size); }
.ai-rel-row { display: grid; grid-template-columns: 1fr 1fr 1fr 90px 60px; gap: 6px; padding: 4px 0; border-bottom: 1px solid var(--neutral-50); align-items: center; }
.ai-rel-row--header { font-weight: 500; color: var(--neutral-500); font-size: var(--text-caption-size); border-bottom-color: var(--neutral-200); }
.ai-rel-type { color: var(--semantic-600); font-size: var(--text-caption-size); }
.ai-rel-card { color: var(--neutral-500); font-size: var(--text-caption-size); }
</style>
