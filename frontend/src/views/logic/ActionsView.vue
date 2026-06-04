<template>
  <div class="logic-page">
    <BuilderReturnBanner kind-label="动作" />
    <div class="logic-page__header">
      <div>
        <h1 class="text-display">行动管理</h1>
        <p class="text-caption" style="margin-top: 4px;">行动注册表 · 多类型配置 · 领域行动与系统行动</p>
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

    <div class="logic-page__filter">
      <input v-model="search" class="logic-search" placeholder="搜索行动名称..." @input="fetchActions" />
      <div class="logic-filter-tags">
        <button v-for="f in filterOptions" :key="f.value" class="filter-tag" :class="{ 'filter-tag--active': activeFilter === f.value }" @click="setFilter(f.value)">{{ f.label }}</button>
      </div>
    </div>

    <div class="logic-page__list">
      <div v-for="action in filteredActions" :key="action.id" class="rule-card" :class="{ 'rule-card--expanded': expandedId === action.id }" @click="expandedId = expandedId === action.id ? null : action.id">
        <div class="rule-card__header">
          <span class="rule-card__status" :class="`rule-card__status--${action.status}`"></span>
          <span class="rule-card__name text-body-medium">{{ action.name }}</span>
          <span class="rule-card__entity text-caption">{{ action.entity_name || '系统行动' }}</span>
          <span class="rule-card__priority" :class="`priority--${action.category}`">{{ action.category === 'domain' ? '领域' : '系统' }}</span>
          <span class="rule-card__type text-caption" style="margin-left: 8px;">{{ getTypeLabel(action.action_type) }}</span>
        </div>
        <div v-if="expandedId === action.id" class="rule-card__detail">
          <div class="rule-detail-row" v-if="action.description">
            <span class="rule-detail-label">描述</span>
            <span>{{ action.description }}</span>
          </div>
          <div class="rule-detail-row">
            <span class="rule-detail-label">行动类型</span>
            <span>{{ getTypeLabel(action.action_type) }}</span>
          </div>
          <div class="rule-detail-row">
            <span class="rule-detail-label">执行次数</span>
            <span>{{ action.impact_count ?? 0 }} 次</span>
          </div>
          <div class="rule-detail-row" v-if="action.parameters_json?.length">
            <span class="rule-detail-label">参数</span>
            <code class="text-code">{{ action.parameters_json.map((p: any) => p.name || p).join(', ') }}</code>
          </div>
          <div class="rule-card__actions">
            <button class="btn-sm-exec" @click.stop="handleExecute(action)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 1.5l7 4.5-7 4.5V1.5z" fill="currentColor"/></svg>
              执行
            </button>
            <button class="btn-sm-del" @click.stop="handleDelete(action)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 3h8M4 3V2h4v1M3 3v7h6V3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              删除
            </button>
          </div>
        </div>
      </div>
      <div v-if="filteredActions.length === 0" class="logic-empty">
        <p class="text-caption">无匹配行动</p>
      </div>
    </div>

    <ModalDialog :visible="showAdd" title="新建行动" width="640px" @close="closeCreate">
      <div class="create-steps">
        <div class="create-steps__indicators">
          <span v-for="(s, i) in stepLabels" :key="i" class="step-dot" :class="{ 'step-dot--active': createStep === i, 'step-dot--done': createStep > i }">{{ i + 1 }}. {{ s }}</span>
        </div>

        <form class="rule-form" @submit.prevent="handleStepNext">
          <!-- Step 0: basic info -->
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

          <!-- Step 1: entity (domain only) + action type -->
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

          <!-- Step 2: type config -->
          <template v-if="createStep === 2">
            <p class="text-caption" style="margin-bottom: 12px;">配置「{{ getTypeLabel(form.action_type) }}」的执行参数：</p>
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
    </ModalDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { actionApi, type ActionItem, type ActionTypeInfo } from '../../api/actions'
import { get } from '../../api/client'
import ModalDialog from '../../components/common/ModalDialog.vue'
import BuilderReturnBanner from '../../components/common/BuilderReturnBanner.vue'

const route = useRoute()
const router = useRouter()

const actions = ref<ActionItem[]>([])
const entities = ref<any[]>([])
const actionTypes = ref<ActionTypeInfo[]>([])
const search = ref('')
const activeFilter = ref('all')
const expandedId = ref<string | null>(null)
const showAdd = ref(false)
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
}

async function handleExecute(action: ActionItem) {
  await actionApi.execute(action.id, {})
  await fetchActions()
}

async function handleDelete(action: ActionItem) {
  if (!confirm(`确定删除行动「${action.name}」？`)) return
  await actionApi.remove(action.id)
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

.create-steps__indicators {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle, #eee);
}

.step-dot {
  font-size: 12px;
  color: var(--text-tertiary, #999);
}

.step-dot--active {
  color: var(--color-primary, #1677ff);
  font-weight: 600;
}

.step-dot--done {
  color: var(--color-success, #52c41a);
}

.form-textarea {
  min-height: 72px;
  resize: vertical;
  font-family: monospace;
}

.btn-secondary {
  padding: 6px 16px;
  border-radius: 6px;
  border: 1px solid var(--border-default, #d9d9d9);
  background: transparent;
  cursor: pointer;
  font-size: 13px;
}
</style>
