<template>
  <div class="logic-page">
    <div class="logic-page__header">
      <div>
        <h1 class="text-display">Actions 管理</h1>
        <p class="text-caption" style="margin-top: 4px;">本体动作注册表 · 执行统计 · 全局视图</p>
      </div>
      <div class="logic-page__actions">
        <button class="btn-primary" @click="showAdd = true">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新建动作
        </button>
      </div>
    </div>

    <div class="logic-page__stats">
      <div class="stat-card stat-card--semantic">
        <div class="stat-card__value">{{ stats.total }}</div>
        <div class="stat-card__label">总动作数</div>
      </div>
      <div class="stat-card stat-card--dynamic">
        <div class="stat-card__value">{{ stats.active }}</div>
        <div class="stat-card__label">已激活</div>
      </div>
      <div class="stat-card stat-card--kinetic">
        <div class="stat-card__value">{{ stats.manual }}</div>
        <div class="stat-card__label">手动触发</div>
      </div>
      <div class="stat-card stat-card--error">
        <div class="stat-card__value">{{ stats.auto }}</div>
        <div class="stat-card__label">自动触发</div>
      </div>
    </div>

    <div class="logic-page__filter">
      <input v-model="search" class="logic-search" placeholder="搜索动作名称..." />
      <div class="logic-filter-tags">
        <button v-for="f in filters" :key="f.value" class="filter-tag" :class="{ 'filter-tag--active': activeFilter === f.value }" @click="activeFilter = f.value">{{ f.label }}</button>
      </div>
    </div>

    <div class="logic-page__list">
      <div v-for="action in filteredActions" :key="action.id" class="rule-card" :class="{ 'rule-card--expanded': expandedId === action.id }" @click="expandedId = expandedId === action.id ? null : action.id">
        <div class="rule-card__header">
          <span class="rule-card__status" :class="`rule-card__status--${action.status}`"></span>
          <span class="rule-card__name text-body-medium">{{ action.name }}</span>
          <span class="rule-card__entity text-caption">{{ action.entity_name }}</span>
          <span class="rule-card__priority" :class="`priority--${action.type}`">{{ action.type }}</span>
        </div>
        <div v-if="expandedId === action.id" class="rule-card__detail">
          <div class="rule-detail-row">
            <span class="rule-detail-label">触发方式</span>
            <span>{{ action.type }}</span>
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
        <p class="text-caption">无匹配动作</p>
      </div>
    </div>

    <ModalDialog :visible="showAdd" title="新建动作" width="520px" @close="showAdd = false">
      <form class="rule-form" @submit.prevent="handleCreate">
        <div class="form-row"><label class="form-label">动作名称</label><input v-model="form.name" class="form-input" required /></div>
        <div class="form-row"><label class="form-label">关联实体</label>
          <select v-model="form.entity_id" class="form-input" required>
            <option value="" disabled>选择实体</option>
            <option v-for="e in entities" :key="e.id" :value="e.id">{{ e.name_cn }} ({{ e.name }})</option>
          </select>
        </div>
        <div class="form-row"><label class="form-label">触发方式</label>
          <select v-model="form.type" class="form-input">
            <option value="manual">手动</option>
            <option value="auto">自动</option>
            <option value="api">API</option>
          </select>
        </div>
        <button type="submit" class="btn-primary" style="align-self: flex-end;">创建</button>
      </form>
    </ModalDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { actionApi, type ActionItem } from '../../api/actions'
import { get } from '../../api/client'
import ModalDialog from '../../components/common/ModalDialog.vue'

const actions = ref<ActionItem[]>([])
const entities = ref<any[]>([])
const search = ref('')
const activeFilter = ref('all')
const expandedId = ref<string | null>(null)
const showAdd = ref(false)
const form = ref({ name: '', entity_id: '', type: 'manual' })

const filters = [
  { label: '全部', value: 'all' },
  { label: '已激活', value: 'active' },
  { label: '手动', value: 'manual' },
  { label: '自动', value: 'auto' },
]

const stats = computed(() => {
  const all = actions.value
  return {
    total: all.length,
    active: all.filter(a => a.status === 'active').length,
    manual: all.filter(a => a.type === 'manual').length,
    auto: all.filter(a => a.type === 'auto' || a.type === 'api').length,
  }
})

const filteredActions = computed(() => {
  let list = actions.value
  if (activeFilter.value === 'active') list = list.filter(a => a.status === 'active')
  else if (activeFilter.value === 'manual') list = list.filter(a => a.type === 'manual')
  else if (activeFilter.value === 'auto') list = list.filter(a => a.type === 'auto' || a.type === 'api')
  if (search.value) {
    const s = search.value.toLowerCase()
    list = list.filter(a => a.name.toLowerCase().includes(s) || a.entity_name.toLowerCase().includes(s))
  }
  return list
})

async function fetchActions() {
  actions.value = await actionApi.list()
}

async function fetchEntities() {
  entities.value = await get<any[]>('/entities')
}

async function handleCreate() {
  await actionApi.create(form.value)
  showAdd.value = false
  form.value = { name: '', entity_id: '', type: 'manual' }
  await fetchActions()
}

async function handleExecute(action: ActionItem) {
  await actionApi.execute(action.id)
  await fetchActions()
}

async function handleDelete(action: ActionItem) {
  if (!confirm(`确定删除动作「${action.name}」？`)) return
  await actionApi.remove(action.id)
  await fetchActions()
}

onMounted(() => { fetchActions(); fetchEntities() })
</script>

<style scoped>
@import './logic-shared.css';
</style>
