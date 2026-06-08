<template>
  <div class="step2-root">
    <header class="step2-topbar">
      <button class="step2-back-btn" @click="$emit('prev')">← 返回</button>
      <div class="step2-topbar-title">本体走测 · 专家审批</div>
      <div class="step2-topbar-progress">
        <span class="step2-progress-label">已通过 {{ approvedCount }} / {{ objects.length }}</span>
        <div class="step2-progress-track">
          <div class="step2-progress-bar" :style="{ width: progressPct + '%' }"></div>
        </div>
        <span class="step2-progress-pct">{{ Math.round(progressPct) }}%</span>
      </div>
      <button class="step2-approve-all-btn" @click="approveAll">✅ 一键全部通过</button>
      <button
        :class="['step2-complete-btn', { active: approvedCount === objects.length && objects.length > 0 }]"
        :disabled="approvedCount < objects.length"
        @click="finishReview"
      >完成走测</button>
    </header>

    <!-- 数据源绑定面板（仅文档抽取/导入路径显示，手工建模在独立步骤处理） -->
    <div class="step2-binding-panel" v-if="props.session.buildMethod !== 'chat' && props.session.buildMethod !== 'manual'">
      <div class="step2-binding-head" @click="bindingOpen = !bindingOpen">
        <span>🔗 数据源绑定与自动映射</span>
        <span class="step2-binding-toggle">{{ bindingOpen ? '收起' : '展开' }}</span>
      </div>
      <div v-if="bindingOpen" class="step2-binding-body">
        <div class="step2-binding-row">
          <label>选择数据源：</label>
          <a-select
            v-model:value="selectedAssetIds"
            mode="multiple"
            placeholder="选择要映射的数据资产"
            :options="assetOptions"
            :loading="assetLoading"
            style="flex:1"
            size="small"
            @dropdown-visible-change="onAssetDropdownOpen"
            @change="syncStore"
          />
          <button class="step2-ai-btn" :disabled="autoMapping || !selectedAssetIds.length" @click="runAutoMap">
            {{ autoMapping ? '映射中...' : '自动映射' }}
          </button>
        </div>
        <div v-if="mapCoverage" class="step2-binding-stats">
          <span class="step2-stat step2-stat--high">高置信：{{ mapCoverage.high }}</span>
          <span class="step2-stat step2-stat--medium">中置信：{{ mapCoverage.medium }}</span>
          <span class="step2-stat step2-stat--low">低置信：{{ mapCoverage.low }}</span>
          <span class="step2-stat step2-stat--none">未匹配：{{ mapCoverage.none }}</span>
        </div>
      </div>
    </div>

    <!-- 顶部 LLM 建议区 -->
    <div v-if="hasHints" class="step2-hints">
      <div class="step2-hints-head">💡 LLM 建议（来自文档抽取/对话生成）</div>
      <div class="step2-hints-body">
        <div v-for="r in hints.suggested_rules" :key="r.id" class="step2-hint-card step2-hint-card--rule">
          <div class="step2-hint-head">
            <span class="step2-hint-tag step2-hint-tag--rule">规则建议</span>
            <strong>{{ r.name }}</strong>
            <span v-if="r.targetObjectId" class="step2-hint-target">建议挂到：{{ objectName(r.targetObjectId) }}</span>
          </div>
          <div class="step2-hint-desc">{{ r.description }}</div>
          <div v-if="r.conditionHint || r.actionHint" class="step2-hint-meta">
            <span v-if="r.conditionHint">条件提示：{{ r.conditionHint }}</span>
            <span v-if="r.actionHint">动作提示：{{ r.actionHint }}</span>
          </div>
          <div class="step2-hint-actions">
            <button class="btn-mini" :disabled="hintCreating" @click="createFromHint(r, 'rule')">一键创建</button>
            <button class="btn-mini" @click="attachExisting(r, 'rule')">挂到已有规则</button>
            <button class="btn-mini btn-ghost" @click="ignoreHint(r.id, 'rule')">忽略</button>
          </div>
        </div>
        <div v-for="a in hints.suggested_actions" :key="a.id" class="step2-hint-card step2-hint-card--action">
          <div class="step2-hint-head">
            <span class="step2-hint-tag step2-hint-tag--action">动作建议</span>
            <strong>{{ a.name }}</strong>
            <span v-if="a.targetObjectId" class="step2-hint-target">建议挂到：{{ objectName(a.targetObjectId) }}</span>
          </div>
          <div class="step2-hint-desc">{{ a.description }}</div>
          <div class="step2-hint-actions">
            <button class="btn-mini" :disabled="hintCreating" @click="createFromHint(a, 'action')">一键创建</button>
            <button class="btn-mini" @click="attachExisting(a, 'action')">挂到已有动作</button>
            <button class="btn-mini btn-ghost" @click="ignoreHint(a.id, 'action')">忽略</button>
          </div>
        </div>
      </div>
    </div>

    <div class="step2-body">
      <!-- 左：对象列表 -->
      <aside class="step2-left">
        <div class="step2-left-header">本体对象 · {{ objects.length }}</div>
        <div class="step2-story-list">
          <div
            v-for="c in objects"
            :key="c.id"
            :class="['step2-story-item', { active: selectedId === c.id }]"
            @click="selectedId = c.id"
          >
            <div class="step2-story-icon" :style="{ background: tierBg(c.tier), color: tierColor(c.tier) }">{{ c.icon || '🔷' }}</div>
            <div class="step2-story-meta">
              <div class="step2-story-name">{{ c.displayName }}</div>
              <div class="step2-story-output">{{ c.name }} · T{{ c.tier }} · {{ c.properties.length }} 属性</div>
            </div>
            <span :class="['step2-status-tag', c.approved ? 'approved' : 'pending']">{{ c.approved ? '已通过' : '待确认' }}</span>
          </div>
        </div>
      </aside>

      <!-- 中：图谱 -->
      <main class="step2-mid">
        <div class="step2-layer-header">
          <div class="step2-layer-title">
            图谱展示
            <span class="step2-layer-title-sub">点击节点在右侧编辑，拖拽节点调整布局</span>
          </div>
        </div>
        <div class="step2-layers-scroll" style="padding:0">
          <SemanticCanvas
            :objects="objects"
            :relations="relations"
            :phase="'graph_done'"
            :editable="false"
          />
        </div>
      </main>

      <!-- 右：编辑器 -->
      <aside class="step2-right">
        <div v-if="selected" class="step2-editor-card">
          <div class="step2-editor-head">
            <span>📝 对象编辑</span>
            <span :class="['step2-status-tag', selected.approved ? 'approved' : 'pending']">{{ selected.approved ? '已通过' : '待确认' }}</span>
          </div>
          <label class="step2-editor-label">对象名称（中文）</label>
          <a-input v-model:value="selected.displayName" size="small" @change="syncStore" />
          <label class="step2-editor-label">英文名 (API)</label>
          <a-input v-model:value="selected.name" size="small" @change="syncStore" />
          <label class="step2-editor-label">层级</label>
          <a-select v-model:value="selected.tier" size="small" :options="tierOptions" @change="syncStore" />
          <div class="step2-editor-meta">
            <span>关系：{{ relationCountFor(selected.id) }} 条</span>
            <span>属性：{{ selected.properties.length }} 个</span>
          </div>

          <div class="step2-editor-section-head">
            <span>属性 ({{ selected.properties.length }})</span>
            <div style="display:flex;gap:6px">
              <button class="step2-ai-btn" :disabled="aiSuggesting" @click="suggestAttributes">
                {{ aiSuggesting ? 'AI 思考中...' : 'AI 补全' }}
              </button>
              <button @click="addProp">+ 增加属性</button>
            </div>
          </div>
          <div class="step2-editor-props">
            <div v-for="p in selected.properties" :key="p.id" class="step2-editor-prop">
              <a-input v-model:value="p.name" size="small" placeholder="属性名" @change="syncStore" />
              <a-select v-model:value="p.type" size="small" :options="typeOptions" @change="syncStore" />
              <button class="step2-editor-del" title="删除属性" @click="removeProp(p.id)">×</button>
            </div>
          </div>

          <div class="step2-editor-section-head">
            <span>派生属性（Function）</span>
            <a class="step2-editor-link" :href="addFnHref" target="_blank">＋ 新建 ↗</a>
          </div>
          <ResourcePickerMulti type="function" v-model="selected.derivedProperties" @update:modelValue="syncStore" />

          <div class="step2-editor-section-head">
            <span>规则</span>
            <a class="step2-editor-link" :href="addRuleHref" target="_blank">＋ 新建 ↗</a>
          </div>
          <ResourcePickerMulti type="rule" v-model="selected.rules" @update:modelValue="syncStore" />

          <div class="step2-editor-section-head">
            <span>动作</span>
            <a class="step2-editor-link" :href="addActionHref" target="_blank">＋ 新建 ↗</a>
          </div>
          <ResourcePickerMulti type="action" v-model="selected.actions" @update:modelValue="syncStore" />

          <button
            class="step2-editor-approve"
            :disabled="!canApprove(selected)"
            @click="approveSelected"
          >{{ selected.approved ? '✓ 已通过' : '确认通过' }}</button>
        </div>

        <div class="step2-editor-card step2-relation-card">
          <div class="step2-editor-head">
            <span>🔗 关系</span>
            <button class="step2-ai-btn" :disabled="aiRelSuggesting" @click="suggestRelations" style="margin-left:auto">
              {{ aiRelSuggesting ? 'AI 思考中...' : 'AI 推断' }}
            </button>
          </div>
          <div v-for="r in relations" :key="r.id" class="step2-rel-row">
            <span>{{ objectName(r.source) }}</span>
            <span class="step2-rel-arrow">→</span>
            <span>{{ objectName(r.target) }}</span>
            <span class="step2-rel-label">{{ r.displayName }}</span>
            <button class="step2-editor-del" @click="removeRelation(r.id)">×</button>
          </div>
          <div v-if="!relations.length" class="step2-rel-empty">尚无关系</div>
        </div>

        <div v-if="hints.suggested_rules.length || hints.suggested_actions.length" class="step2-attach-tip">
          顶部还有 {{ hints.suggested_rules.length + hints.suggested_actions.length }} 条 LLM 建议待处理
        </div>
      </aside>
    </div>

    <!-- 挂载已有规则/动作的弹窗 -->
    <div v-if="attachModal.open" class="step2-modal-mask" @click.self="attachModal.open = false">
      <div class="step2-modal">
        <div class="step2-modal-head">挂载到 {{ attachModal.kind === 'rule' ? '已有规则' : '已有动作' }}</div>
        <div class="step2-modal-body">
          <div class="step2-form-row">
            <label>挂到对象</label>
            <select v-model="attachModal.objectId">
              <option v-for="o in objects" :key="o.id" :value="o.id">{{ o.displayName }}（{{ o.name }}）</option>
            </select>
          </div>
          <div class="step2-form-row">
            <label>{{ attachModal.kind === 'rule' ? '规则' : '动作' }}</label>
            <ResourcePickerMulti :type="attachModal.kind" v-model="attachModal.picked" />
          </div>
        </div>
        <div class="step2-modal-actions">
          <button class="btn-mini btn-ghost" @click="attachModal.open = false">取消</button>
          <button class="btn-mini" :disabled="!attachModal.picked.length || !attachModal.objectId" @click="confirmAttach">确认挂载</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { useBuilderStore } from '../../../store/builder'
import { ruleApi } from '../../../api/rules'
import { actionApi } from '../../../api/actions'
import type {
  BuilderSession,
  OntologyHints,
  SuggestedRule,
  SuggestedAction,
} from '../../../types/builder'
import SemanticCanvas from './graph/SemanticCanvas.vue'
import ResourcePickerMulti from './manual/ResourcePickerMulti.vue'

const props = defineProps<{ session: BuilderSession }>()
const emit = defineEmits<{ (e: 'prev'): void; (e: 'next'): void }>()
const store = useBuilderStore()
const router = useRouter()

const selectedId = ref<string | null>(props.session.ontologyObjects[0]?.id || null)
const objects = ref([...props.session.ontologyObjects])
const relations = ref([...props.session.ontologyRelations])
const aiSuggesting = ref(false)
const aiRelSuggesting = ref(false)
const hintCreating = ref(false)
const hints = ref<OntologyHints>({
  suggested_rules: [...(props.session.hints?.suggested_rules || [])],
  suggested_actions: [...(props.session.hints?.suggested_actions || [])],
})

// ── 数据源绑定 ──
const bindingOpen = ref(false)
const selectedAssetIds = ref<string[]>([...(props.session.selectedAssetIds || [])])
const assetOptions = ref<{ label: string; value: string }[]>([])
const assetLoading = ref(false)
const autoMapping = ref(false)
const mapCoverage = ref<{ high: number; medium: number; low: number; none: number } | null>(null)

const tierOptions = [
  { label: 'Tier 1 核心', value: 1 },
  { label: 'Tier 2 领域', value: 2 },
  { label: 'Tier 3 场景', value: 3 },
]
const typeOptions = [
  { label: '字符串', value: 'string' },
  { label: '数值', value: 'number' },
  { label: '日期', value: 'date' },
  { label: '布尔', value: 'boolean' },
  { label: '枚举', value: 'enum' },
]

const selected = computed(() => objects.value.find(c => c.id === selectedId.value))
const approvedCount = computed(() => objects.value.filter(c => c.approved).length)
const progressPct = computed(() => objects.value.length ? (approvedCount.value / objects.value.length) * 100 : 0)
const hasHints = computed(() => hints.value.suggested_rules.length || hints.value.suggested_actions.length)

const addRuleHref   = computed(() => `/logic/rules?from=builder&session_id=${props.session.sessionId}&object_id=${selected.value?.id || ''}&kind=rule`)
const addActionHref = computed(() => `/logic/actions?from=builder&session_id=${props.session.sessionId}&object_id=${selected.value?.id || ''}&kind=action`)
const addFnHref     = computed(() => `/logic/functions?from=builder&session_id=${props.session.sessionId}&object_id=${selected.value?.id || ''}&kind=function`)

function objectName(id: string) { return objects.value.find(o => o.id === id)?.displayName || id }
function relationCountFor(id: string) { return relations.value.filter(r => r.source === id || r.target === id).length }
function tierBg(t: 1 | 2 | 3) { return t === 1 ? 'rgba(46,91,255,0.12)' : t === 2 ? 'rgba(0,199,177,0.12)' : 'rgba(255,107,53,0.12)' }
function tierColor(t: 1 | 2 | 3) { return t === 1 ? '#2E5BFF' : t === 2 ? '#00C7B1' : '#FF6B35' }

function syncStore() {
  store.patchActive({
    ontologyObjects: [...objects.value],
    ontologyRelations: [...relations.value],
    hints: { ...hints.value },
    selectedAssetIds: [...selectedAssetIds.value],
  })
}

function canApprove(_o: typeof objects.value[0]) {
  return true
}

function approveSelected() {
  if (!selected.value) return
  selected.value.approved = true
  syncStore()
  const next = objects.value.find(c => !c.approved)
  if (next) selectedId.value = next.id
}

function approveAll() {
  objects.value = objects.value.map(c => ({ ...c, approved: true }))
  syncStore()
  message.success('已一键通过全部对象')
}

function addProp() {
  if (!selected.value) return
  selected.value.properties.push({
    id: 'p-' + Date.now(),
    name: 'newField',
    displayName: '新属性',
    type: 'string',
    required: false,
  })
  syncStore()
}

async function suggestAttributes() {
  if (!selected.value || aiSuggesting.value) return
  aiSuggesting.value = true
  try {
    const resp = await fetch('/api/v1/builder/suggest-attributes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        object_name: selected.value.name,
        display_name: selected.value.displayName,
        tier: selected.value.tier,
        description: selected.value.description,
        existing_properties: selected.value.properties.map(p => ({
          name: p.name, displayName: p.displayName, type: p.type, required: p.required,
        })),
      }),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }
    const data = await resp.json()
    const existingNames = new Set(selected.value.properties.map(p => p.name))
    let added = 0
    for (const sp of data.suggested_properties || []) {
      if (!sp.name || existingNames.has(sp.name)) continue
      selected.value.properties.push({
        id: 'p-' + Date.now() + '-' + added,
        name: sp.name,
        displayName: sp.displayName || sp.name,
        type: sp.type || 'string',
        required: sp.required || false,
        description: sp.description,
      })
      existingNames.add(sp.name)
      added++
    }
    syncStore()
    if (added > 0) message.success(`AI 补全了 ${added} 个属性`)
    else message.info('没有新属性可建议')
  } catch (e: any) {
    message.error('AI 补全失败：' + (e.message || e))
  } finally {
    aiSuggesting.value = false
  }
}

async function suggestRelations() {
  if (aiRelSuggesting.value) return
  if (objects.value.length < 2) { message.warning('至少需要 2 个对象才能推断关系'); return }
  aiRelSuggesting.value = true
  try {
    const resp = await fetch('/api/v1/builder/suggest-relations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        objects: objects.value.map(o => ({
          name: o.name, displayName: o.displayName, tier: o.tier,
          properties: o.properties.map(p => p.name),
        })),
        existing_relations: relations.value.map(r => ({
          source: r.source, target: r.target, name: r.name,
        })),
      }),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }
    const data = await resp.json()
    const existingPairs = new Set(relations.value.map(r => `${r.source}->${r.target}`))
    let added = 0
    for (const sr of data.suggested_relations || []) {
      const key = `${sr.source}->${sr.target}`
      const revKey = `${sr.target}->${sr.source}`
      if (!sr.source || !sr.target) continue
      if (existingPairs.has(key) || existingPairs.has(revKey)) continue
      relations.value.push({
        id: 'r-' + Date.now() + '-' + added,
        name: sr.name || 'relates_to',
        displayName: sr.displayName || sr.name || '关联',
        source: sr.source,
        target: sr.target,
        cardinality: sr.cardinality || '1:N',
        description: sr.description || '',
        relationType: sr.relationType || 'ObjectProperty',
        semanticType: sr.semanticType || 'association',
      })
      existingPairs.add(key)
      added++
    }
    syncStore()
    if (added > 0) message.success(`AI 推断了 ${added} 条关系`)
    else message.info('没有新关系可推断')
  } catch (e: any) {
    message.error('AI 推断失败：' + (e.message || e))
  } finally {
    aiRelSuggesting.value = false
  }
}
function removeProp(id: string) {
  if (!selected.value) return
  selected.value.properties = selected.value.properties.filter(p => p.id !== id)
  syncStore()
}
function removeRelation(id: string) {
  relations.value = relations.value.filter(r => r.id !== id)
  syncStore()
}

// ── LLM 建议卡片三种处理 ──
function ignoreHint(id: string, kind: 'rule' | 'action') {
  if (kind === 'rule') hints.value.suggested_rules = hints.value.suggested_rules.filter(r => r.id !== id)
  else hints.value.suggested_actions = hints.value.suggested_actions.filter(a => a.id !== id)
  syncStore()
}
async function createFromHint(h: SuggestedRule | SuggestedAction, kind: 'rule' | 'action') {
  const objectId = h.targetObjectId || selected.value?.id || objects.value[0]?.id || ''
  if (!objectId) { message.warning('没有可挂载的对象'); return }
  hintCreating.value = true
  try {
    if (kind === 'rule') {
      const rh = h as SuggestedRule
      const created = await ruleApi.create({
        entity_id: objectId,
        name: rh.name,
        condition_expr: rh.conditionHint || rh.description || '',
        action_desc: rh.actionHint || '',
        status: 'active',
        priority: 'medium',
      })
      const obj = objects.value.find(o => o.id === objectId)
      if (obj && created?.id) {
        obj.rules = [...new Set([...obj.rules, created.id])]
      }
      message.success(`规则「${rh.name}」已创建`)
    } else {
      const ah = h as SuggestedAction
      const created = await actionApi.create({
        entity_id: objectId,
        name: ah.name,
        type: 'manual',
        status: 'active',
      })
      const obj = objects.value.find(o => o.id === objectId)
      if (obj && created?.id) {
        obj.actions = [...new Set([...obj.actions, created.id])]
      }
      message.success(`动作「${ah.name}」已创建`)
    }
    ignoreHint(h.id, kind)
    syncStore()
  } catch (e: any) {
    message.error('创建失败：' + (e.message || e))
  } finally {
    hintCreating.value = false
  }
}

const attachModal = reactive<{ open: boolean; kind: 'rule' | 'action'; objectId: string; picked: string[]; hintId: string }>({
  open: false, kind: 'rule', objectId: '', picked: [], hintId: '',
})
function attachExisting(h: SuggestedRule | SuggestedAction, kind: 'rule' | 'action') {
  attachModal.open = true
  attachModal.kind = kind
  attachModal.objectId = h.targetObjectId || selected.value?.id || objects.value[0]?.id || ''
  attachModal.picked = []
  attachModal.hintId = h.id
}
function confirmAttach() {
  const obj = objects.value.find(o => o.id === attachModal.objectId)
  if (!obj) return
  if (attachModal.kind === 'rule') obj.rules = [...new Set([...obj.rules, ...attachModal.picked])]
  else obj.actions = [...new Set([...obj.actions, ...attachModal.picked])]
  ignoreHint(attachModal.hintId, attachModal.kind)
  attachModal.open = false
  syncStore()
  message.success('已挂载')
}

async function onAssetDropdownOpen(open: boolean) {
  if (!open || assetOptions.value.length) return
  assetLoading.value = true
  try {
    const resp = await fetch('/api/v1/assets?page=1&page_size=200')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    const items = data.items || data || []
    assetOptions.value = items.map((a: any) => ({
      label: `${a.alias || a.name}（${a.kind || 'table'}）`,
      value: a.id,
    }))
  } catch (e: any) {
    message.error('加载数据源失败：' + (e.message || e))
  } finally {
    assetLoading.value = false
  }
}

async function runAutoMap() {
  if (!selectedAssetIds.value.length || autoMapping.value) return
  autoMapping.value = true
  mapCoverage.value = null
  try {
    const resp = await fetch('/api/v1/builder/auto-map', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        objects: objects.value.map(o => ({
          id: o.id,
          properties: o.properties.map(p => ({
            name: p.name, type: p.type, description: p.description,
          })),
        })),
        asset_ids: selectedAssetIds.value,
      }),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }
    const data = await resp.json()
    const mappings = data.mappings || {}
    let totalHigh = 0, totalMedium = 0, totalLow = 0, totalNone = 0

    for (const obj of objects.value) {
      const objMap = mappings[obj.id]
      if (!objMap) { totalNone += obj.properties.length; continue }
      // 回写 backing_asset_ids
      if (!obj.backing_asset_ids?.length) {
        obj.backing_asset_ids = [objMap.asset_id]
      }
      for (const prop of obj.properties) {
        const pm = objMap.property_mappings?.[prop.name]
        if (pm && pm.score > 0) {
          prop.source_asset_id = pm.asset_id
          prop.source_column = pm.column
          if (pm.score >= 0.8) totalHigh++
          else if (pm.score >= 0.5) totalMedium++
          else totalLow++
        } else {
          totalNone++
        }
      }
    }

    mapCoverage.value = { high: totalHigh, medium: totalMedium, low: totalLow, none: totalNone }
    syncStore()
    const mapped = totalHigh + totalMedium + totalLow
    message.success(`自动映射完成：${mapped} 个属性已匹配，${totalNone} 个未匹配`)
  } catch (e: any) {
    message.error('自动映射失败：' + (e.message || e))
  } finally {
    autoMapping.value = false
  }
}

function finishReview() {
  if (approvedCount.value < objects.value.length) {
    message.warning('请将所有对象审批通过后再完成走测')
    return
  }
  store.patchActive({
    ontologyObjects: objects.value,
    ontologyRelations: relations.value,
    hints: { ...hints.value },
    status: 'pending_hydration',
    approvedScenarios: objects.value.map(c => c.id),
    reviewLog: [
      {
        storyId: 'review-all',
        storyName: '全部走测节点',
        action: 'approved',
        reviewer: localStorage.getItem('username') || '当前用户',
        reviewedAt: new Date().toISOString(),
        comment: '走测节点全部通过',
      },
    ],
  })
  message.success('走测完成，进入水合演练')
  emit('next')
}

watch(() => props.session.sessionId, () => {
  objects.value = [...props.session.ontologyObjects]
  relations.value = [...props.session.ontologyRelations]
  hints.value = {
    suggested_rules: [...(props.session.hints?.suggested_rules || [])],
    suggested_actions: [...(props.session.hints?.suggested_actions || [])],
  }
  selectedId.value = objects.value[0]?.id || null
})

// 父级 OntologyBuilderView 已通过 query 自动挂载新建 ID，这里同步本地 state
watch(() => props.session.ontologyObjects, (v) => {
  objects.value = [...v]
}, { deep: true })
</script>

<style scoped>
.step2-hints {
  margin: 12px 16px 0;
  padding: 12px 14px;
  background: rgba(245,158,11,0.06);
  border: 1px solid #fde68a;
  border-radius: 12px;
}
.step2-hints-head { font-size: 12px; font-weight: 600; color: #b45309; margin-bottom: 8px; }
.step2-hints-body { display: flex; flex-direction: column; gap: 8px; }
.step2-hint-card {
  padding: 10px 12px; background: #fff; border-radius: 8px;
  border-left: 3px solid #f59e0b;
}
.step2-hint-card--action { border-left-color: #6366f1; }
.step2-hint-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.step2-hint-tag { font-size: 10px; padding: 1px 8px; border-radius: 999px; font-weight: 600; }
.step2-hint-tag--rule { background: rgba(245,158,11,0.12); color: #b45309; }
.step2-hint-tag--action { background: rgba(99,102,241,0.12); color: #4f46e5; }
.step2-hint-target { font-size: 10px; color: #94a3b8; margin-left: auto; }
.step2-hint-desc { font-size: 12px; color: #475569; margin-bottom: 4px; }
.step2-hint-meta { font-size: 10px; color: #94a3b8; display: flex; gap: 12px; margin-bottom: 6px; }
.step2-hint-actions { display: flex; gap: 6px; }
.btn-mini {
  padding: 3px 10px; border-radius: 6px; font-size: 11px; cursor: pointer;
  background: #4f46e5; color: #fff; border: 1px solid #4f46e5;
}
.btn-mini:hover { background: #4338ca; }
.btn-mini:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-mini.btn-ghost { background: #fff; color: #475569; border-color: #e2e8f0; }
.btn-mini.btn-ghost:hover { color: #4f46e5; border-color: #4f46e5; }

.step2-editor-link { font-size: 11px; color: #4f46e5; text-decoration: none; }
.step2-editor-link:hover { text-decoration: underline; }
.step2-approve-hint { font-size: 11px; color: #b45309; text-align: center; margin-top: 6px; }
.step2-attach-tip { padding: 8px 12px; font-size: 11px; color: #b45309; background: rgba(245,158,11,0.08); border-radius: 8px; margin: 12px; }
.step2-ai-btn {
  padding: 2px 10px; border-radius: 6px; font-size: 11px; cursor: pointer;
  background: linear-gradient(135deg, #7c3aed, #4f46e5); color: #fff; border: none;
  transition: opacity 0.2s;
}
.step2-ai-btn:hover { opacity: 0.85; }
.step2-ai-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.step2-binding-panel {
  margin: 8px 16px 0;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
}
.step2-binding-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; cursor: pointer; font-size: 12px; font-weight: 600; color: #334155;
}
.step2-binding-head:hover { background: #f8fafc; }
.step2-binding-toggle { font-size: 11px; color: #94a3b8; font-weight: 400; }
.step2-binding-body { padding: 0 14px 12px; }
.step2-binding-row {
  display: flex; align-items: center; gap: 8px;
}
.step2-binding-row label { font-size: 11px; color: #64748b; white-space: nowrap; }
.step2-binding-stats {
  display: flex; gap: 12px; margin-top: 8px; font-size: 11px;
}
.step2-stat { padding: 2px 8px; border-radius: 4px; }
.step2-stat--high { background: rgba(16,185,129,0.1); color: #059669; }
.step2-stat--medium { background: rgba(245,158,11,0.1); color: #b45309; }
.step2-stat--low { background: rgba(239,68,68,0.1); color: #dc2626; }
.step2-stat--none { background: rgba(148,163,184,0.1); color: #64748b; }

.step2-rel-row {
  display: grid; grid-template-columns: 1fr 14px 1fr 1.4fr 24px; gap: 6px;
  align-items: center; padding: 6px 0; font-size: 11px;
  border-bottom: 1px dashed #e2e8f0;
}
.step2-rel-row:last-child { border-bottom: 0; }
.step2-rel-arrow { color: #94a3b8; text-align: center; }
.step2-rel-label { color: #4f46e5; font-family: monospace; }
.step2-rel-empty { font-size: 11px; color: #94a3b8; text-align: center; padding: 12px 0; }

.step2-modal-mask {
  position: fixed; inset: 0; background: rgba(15,23,42,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.step2-modal { background: #fff; border-radius: 12px; padding: 16px 20px; width: 460px; max-width: 90vw; }
.step2-modal-head { font-size: 14px; font-weight: 600; color: #0f172a; margin-bottom: 12px; }
.step2-form-row { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.step2-form-row label { font-size: 11px; color: #64748b; }
.step2-form-row select { padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 12px; }
.step2-modal-actions { display: flex; gap: 6px; justify-content: flex-end; }

.step2-right { overflow-y: auto; }
.step2-editor-props { max-height: 360px; overflow-y: auto; }
</style>
