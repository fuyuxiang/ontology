<template>
  <div class="logic-page">
    <BuilderReturnBanner kind-label="动作" />
    <div class="logic-page__header">
      <div>
        <h1 class="text-display">行动管理</h1>
        <p class="text-caption" style="margin-top: 4px;">行动注册与执行管理</p>
      </div>
      <div class="logic-page__actions">
        <button class="btn-primary" @click="openCreate">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新建行动
        </button>
      </div>
    </div>

    <div class="logic-page__stats">
      <div class="stat-card stat-card--semantic">
        <div class="stat-card__value">{{ stats.total }}</div>
        <div class="stat-card__label">总行动数</div>
      </div>
      <div class="stat-card stat-card--dynamic">
        <div class="stat-card__value">{{ stats.active }}</div>
        <div class="stat-card__label">已激活</div>
      </div>
      <div class="stat-card stat-card--kinetic">
        <div class="stat-card__value">{{ stats.domain }}</div>
        <div class="stat-card__label">领域行动</div>
      </div>
      <div class="stat-card stat-card--error">
        <div class="stat-card__value">{{ stats.system }}</div>
        <div class="stat-card__label">系统行动</div>
      </div>
    </div>

    <div class="master-detail">
      <div class="master-detail__list">
        <div class="master-detail__toolbar">
          <input v-model="search" class="logic-search" placeholder="搜索行动名称..." />
          <div class="logic-filter-tags">
            <button
              v-for="f in filterOptions" :key="f.value"
              class="filter-tag"
              :class="{ 'filter-tag--active': activeFilter === f.value }"
              @click="setFilter(f.value)"
            >{{ f.label }}</button>
          </div>
        </div>

        <div class="master-detail__items">
          <div
            v-for="action in filteredActions" :key="action.id"
            class="list-item"
            :class="{ 'list-item--active': selectedId === action.id }"
            @click="selectedId = action.id"
          >
            <span class="list-item__status" :class="`list-item__status--${action.status}`"></span>
            <span class="list-item__name">{{ action.name }}</span>
            <span class="list-item__badge" :class="`priority--${action.category}`">{{ action.category === 'domain' ? '领域' : '系统' }}</span>
            <span class="list-item__meta">{{ action.entity_name || '系统' }}</span>
          </div>
          <div v-if="filteredActions.length === 0" class="logic-empty">
            <p class="text-caption">无匹配行动</p>
          </div>
        </div>
      </div>

      <div class="master-detail__detail">
        <template v-if="selectedAction">
          <div class="detail-panel__header">
            <h2 class="detail-panel__title">{{ selectedAction.name }}</h2>
            <span class="list-item__badge" :class="`priority--${selectedAction.category}`">{{ selectedAction.category === 'domain' ? '领域行动' : '系统行动' }}</span>
          </div>

          <div class="detail-panel__meta">
            <div class="detail-meta-item">
              <span class="detail-meta-label">状态</span>
              <span class="detail-meta-value">
                <span class="list-item__status" :class="`list-item__status--${selectedAction.status}`"></span>
                {{ selectedAction.status === 'active' ? '已激活' : '未激活' }}
              </span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">关联实体</span>
              <span class="detail-meta-value">{{ selectedAction.entity_name || '系统行动' }}</span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">行动类型</span>
              <span class="detail-meta-value">{{ getTypeLabel(selectedAction.action_type) }}</span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">执行次数</span>
              <span class="detail-meta-value">{{ selectedAction.impact_count ?? 0 }} 次</span>
            </div>
          </div>

          <div v-if="selectedAction.description" class="detail-panel__section">
            <h3 class="detail-section-title">描述</h3>
            <p class="detail-section-text">{{ selectedAction.description }}</p>
          </div>

          <div v-if="selectedAction.parameters_json?.length" class="detail-panel__section">
            <h3 class="detail-section-title">参数</h3>
            <code class="detail-code-block">{{ selectedAction.parameters_json.map((p: any) => p.name || p).join(', ') }}</code>
          </div>

          <div class="detail-panel__actions">
            <button class="btn-sm-exec" @click="handleExecute(selectedAction)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 1.5l7 4.5-7 4.5V1.5z" fill="currentColor"/></svg>
              执行
            </button>
            <button class="btn-sm-del" @click="handleDelete(selectedAction)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 3h8M4 3V2h4v1M3 3v7h6V3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              删除
            </button>
          </div>
        </template>
        <div v-else class="detail-panel__empty">
          <p class="text-caption">选择一个行动查看详情</p>
        </div>
      </div>
    </div>

    <Transition name="drawer">
      <div v-if="showAdd" class="drawer-overlay" @click.self="closeCreate">
        <div class="drawer-panel">
          <div class="drawer-panel__header">
            <h2>新建行动</h2>
            <button class="btn-icon" @click="closeCreate">✕</button>
          </div>

          <div class="drawer-panel__body">
            <div class="create-steps">
              <div class="create-steps__indicators">
                <span v-for="(s, i) in stepLabels" :key="i" class="step-dot" :class="{ 'step-dot--active': createStep === i, 'step-dot--done': createStep > i }">{{ i + 1 }}. {{ s }}</span>
              </div>

              <form class="rule-form" @submit.prevent="handleStepNext">
                <template v-if="createStep === 0">
                  <div class="form-row"><label class="form-label">行动名称</label><input v-model="form.name" class="form-input" required /></div>
                  <div class="form-row"><label class="form-label">描述</label><input v-model="form.description" class="form-input" /></div>
                  <div class="form-row"><label class="form-label">分类</label>
                    <select v-model="form.category" class="form-input" required>
                      <option value="domain">领域行动（绑定实体）</option>
                      <option value="system">系统行动（不绑定实体）</option>
                    </select>
                  </div>
                </template>

                <template v-if="createStep === 1">
                  <div v-if="form.category === 'domain'" class="form-row">
                    <label class="form-label">关联实体</label>
                    <select v-model="form.entity_id" class="form-input" required>
                      <option value="" disabled>选择实体</option>
                      <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name_cn || e.name }} ({{ e.name }})</option>
                    </select>
                  </div>
                  <div class="form-row">
                    <label class="form-label">行动类型</label>
                    <select v-model="form.action_type" class="form-input" required>
                      <option value="" disabled>选择类型</option>
                      <option v-for="t in actionTypes" :key="t.type_key" :value="t.type_key">{{ t.label }} - {{ t.description }}</option>
                    </select>
                  </div>
                </template>

                <template v-if="createStep === 2">
                  <p class="text-caption" style="margin-bottom: 12px;">配置「{{ getTypeLabel(form.action_type) }}」的执行参数：</p>
                  <div v-if="form.action_type === 'custom_script'" class="form-row" style="justify-content: flex-start;">
                    <button type="button" class="btn-secondary" @click="showAiPanel = true">
                      AI 生成
                    </button>
                  </div>
                  <div v-for="(field, key) in currentConfigSchema" :key="key" class="form-row">
                    <label class="form-label">{{ field.description || key }}</label>
                    <textarea v-if="field.type === 'object' || key === 'script' || key === 'sql'" v-model="typeConfigValues[key as string]" class="form-input form-textarea" rows="3"></textarea>
                    <select v-else-if="field.enum" v-model="typeConfigValues[key as string]" class="form-input">
                      <option v-for="opt in field.enum" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                    <input v-else v-model="typeConfigValues[key as string]" class="form-input" :required="field.required" />
                  </div>
                </template>

                <div class="form-row" style="justify-content: flex-end; gap: 8px;">
                  <button v-if="createStep > 0" type="button" class="btn-secondary" @click="createStep--">上一步</button>
                  <button v-if="createStep < 2" type="submit" class="btn-primary">下一步</button>
                  <button v-else type="button" class="btn-primary" @click="handleCreate">创建</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <AiCodePanel
      :visible="showAiPanel"
      :target-type="'action'"
      :target-id="selectedId || ''"
      :context-entity-ids="form.entity_id ? [form.entity_id] : []"
      @close="showAiPanel = false"
      @apply="(code: string) => { typeConfigValues['script'] = code; showAiPanel = false }"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { actionApi, type ActionItem, type ActionTypeInfo } from '../../api/actions'
import { get } from '../../api/client'
import BuilderReturnBanner from '../../components/common/BuilderReturnBanner.vue'
import AiCodePanel from '../../components/logic/AiCodePanel.vue'

const route = useRoute()
const router = useRouter()

const actions = ref<ActionItem[]>([])
const entities = ref<any[]>([])
const actionTypes = ref<ActionTypeInfo[]>([])
const search = ref('')
const activeFilter = ref('all')
const selectedId = ref<string | null>(null)
const showAdd = ref(false)
const showAiPanel = ref(false)
const createStep = ref(0)

const form = ref({
  name: '',
  description: '',
  category: 'domain' as 'domain' | 'system',
  entity_id: '',
  action_type: '',
})
const typeConfigValues = ref<Record<string, string>>({})

const stepLabels = ['基本信息', '类型选择', '类型配置']

const filterOptions = [
  { label: '全部', value: 'all' },
  { label: '已激活', value: 'active' },
  { label: '领域', value: 'domain' },
  { label: '系统', value: 'system' },
]

const selectedAction = computed(() => filteredActions.value.find(a => a.id === selectedId.value) || null)

const stats = computed(() => {
  const all = actions.value
  return {
    total: all.length,
    active: all.filter(a => a.status === 'active').length,
    domain: all.filter(a => a.category === 'domain').length,
    system: all.filter(a => a.category === 'system').length,
  }
})

const filteredActions = computed(() => {
  let list = actions.value
  if (activeFilter.value === 'active') list = list.filter(a => a.status === 'active')
  else if (activeFilter.value === 'domain') list = list.filter(a => a.category === 'domain')
  else if (activeFilter.value === 'system') list = list.filter(a => a.category === 'system')
  if (search.value) {
    const s = search.value.toLowerCase()
    list = list.filter(a => a.name.toLowerCase().includes(s) || (a.entity_name || '').toLowerCase().includes(s))
  }
  return list
})

const currentConfigSchema = computed(() => {
  const t = actionTypes.value.find(at => at.type_key === form.value.action_type)
  return t?.config_schema || {}
})

function getTypeLabel(typeKey: string): string {
  const t = actionTypes.value.find(at => at.type_key === typeKey)
  return t?.label || typeKey
}

function setFilter(value: string) {
  activeFilter.value = value
}

function openCreate() {
  createStep.value = 0
  form.value = { name: '', description: '', category: 'domain', entity_id: '', action_type: '' }
  typeConfigValues.value = {}
  showAdd.value = true
}

function closeCreate() {
  showAdd.value = false
}

function handleStepNext() {
  if (createStep.value < 2) createStep.value++
}

async function fetchActions() {
  const params: any = {}
  if (search.value) params.search = search.value
  actions.value = await actionApi.list(params)
}

async function fetchEntities() {
  entities.value = await get<any[]>('/entities')
}

async function fetchActionTypes() {
  actionTypes.value = await actionApi.types()
}

async function handleCreate() {
  const typeConfig: Record<string, any> = {}
  for (const [key, val] of Object.entries(typeConfigValues.value)) {
    if (!val) continue
    const schema = currentConfigSchema.value[key]
    if (schema?.type === 'object') {
      try { typeConfig[key] = JSON.parse(val) } catch { typeConfig[key] = val }
    } else {
      typeConfig[key] = val
    }
  }

  const payload: any = {
    name: form.value.name,
    description: form.value.description || undefined,
    category: form.value.category,
    action_type: form.value.action_type,
    type_config: Object.keys(typeConfig).length > 0 ? typeConfig : undefined,
  }
  if (form.value.category === 'domain') {
    payload.entity_id = form.value.entity_id
  }

  try {
    const created = await actionApi.create(payload)
    closeCreate()
    await fetchActions()

    if (route.query.from === 'builder') {
      const sid = route.query.session_id as string
      const oid = route.query.object_id as string
      if (sid && oid && (created as any)?.id) {
        router.push({ path: '/builder', query: { session_id: sid, attach_to: oid, new_id: (created as any).id, kind: 'action' } })
      }
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '创建失败'
    alert(`创建行动失败: ${msg}`)
  }
}

async function handleExecute(action: ActionItem) {
  await actionApi.execute(action.id, {})
  await fetchActions()
}

async function handleDelete(action: ActionItem) {
  if (!confirm(`确定删除行动「${action.name}」？`)) return
  await actionApi.remove(action.id)
  if (selectedId.value === action.id) selectedId.value = null
  await fetchActions()
}

onMounted(() => {
  fetchActions()
  fetchEntities()
  fetchActionTypes()
  if (route.query.from === 'builder') {
    form.value = {
      name: (route.query.prefill_name || '') as string,
      description: '',
      category: 'domain',
      entity_id: (route.query.object_id || '') as string,
      action_type: '',
    }
    showAdd.value = true
  }
})
</script>

<style scoped>
@import './logic-shared.css';

.master-detail {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 1px;
  background: var(--neutral-200, #e5e5e5);
  border: 1px solid var(--neutral-200, #e5e5e5);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
  min-height: 480px;
}

.master-detail__list {
  background: var(--neutral-0, #fff);
  display: flex;
  flex-direction: column;
}

.master-detail__toolbar {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-bottom: 1px solid var(--neutral-100, #f0f0f0);
}

.master-detail__toolbar .logic-search {
  width: 100%;
  box-sizing: border-box;
}

.master-detail__items {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  transition: background 0.15s;
}

.list-item:hover {
  background: var(--neutral-50, #fafafa);
}

.list-item--active {
  background: var(--semantic-50, #eef2ff);
  border: 1px solid var(--semantic-200, #c7d2fe);
}

.list-item__status {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.list-item__status--active { background: var(--status-success, #22c55e); }
.list-item__status--inactive { background: var(--neutral-300, #d4d4d4); }

.list-item__name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.list-item__badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  flex-shrink: 0;
}

.list-item__meta {
  font-size: 11px;
  color: var(--neutral-500, #888);
  flex-shrink: 0;
  max-width: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.master-detail__detail {
  background: var(--neutral-0, #fff);
  padding: 24px;
  overflow-y: auto;
}

.detail-panel__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.detail-panel__title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.detail-panel__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 24px;
  padding: 16px;
  background: var(--neutral-50, #fafafa);
  border-radius: var(--radius-md, 8px);
}

.detail-meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-meta-label {
  font-size: 11px;
  color: var(--neutral-500, #888);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.detail-meta-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-800, #333);
  display: flex;
  align-items: center;
  gap: 6px;
}

.detail-panel__section {
  margin-bottom: 20px;
}

.detail-section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--neutral-500, #888);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin: 0 0 8px;
}

.detail-code-block {
  display: block;
  padding: 12px 16px;
  background: var(--neutral-50, #fafafa);
  border: 1px solid var(--neutral-100, #f0f0f0);
  border-radius: var(--radius-md, 8px);
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  color: var(--neutral-700, #495057);
  white-space: pre-wrap;
  word-break: break-all;
}

.detail-section-text {
  font-size: 13px;
  color: var(--neutral-700, #495057);
  margin: 0;
}

.detail-panel__actions {
  display: flex;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--neutral-100, #f0f0f0);
}

.detail-panel__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--neutral-400, #aaa);
}

.create-steps__indicators {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--neutral-100, #f0f0f0);
}

.step-dot {
  font-size: 12px;
  color: var(--neutral-500, #999);
}

.step-dot--active {
  color: var(--semantic-600, #4c6ef5);
  font-weight: 600;
}

.step-dot--done {
  color: var(--status-success, #22c55e);
}

.form-textarea {
  min-height: 72px;
  resize: vertical;
  font-family: monospace;
}
</style>
