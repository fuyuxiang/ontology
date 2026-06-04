<template>
  <div class="logic-page">
    <BuilderReturnBanner kind-label="函数" />
    <div class="logic-page__header">
      <div>
        <h1 class="text-display">Functions 管理</h1>
        <p class="text-caption" style="margin-top: 4px;">计算逻辑 · 派生属性 · 独立函数</p>
      </div>
      <div class="logic-page__actions">
        <button class="btn-primary" @click="showAdd = true">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新建函数
        </button>
      </div>
    </div>

    <div class="logic-page__stats">
      <div class="stat-card stat-card--semantic">
        <div class="stat-card__value">{{ stats.total }}</div>
        <div class="stat-card__label">总函数数</div>
      </div>
      <div class="stat-card stat-card--dynamic">
        <div class="stat-card__value">{{ stats.active }}</div>
        <div class="stat-card__label">已激活</div>
      </div>
      <div class="stat-card stat-card--kinetic">
        <div class="stat-card__value">{{ stats.derived }}</div>
        <div class="stat-card__label">派生属性</div>
      </div>
      <div class="stat-card stat-card--error">
        <div class="stat-card__value">{{ stats.standalone }}</div>
        <div class="stat-card__label">独立函数</div>
      </div>
    </div>

    <div class="logic-page__filter">
      <input v-model="search" class="logic-search" placeholder="搜索函数名称或描述..." />
      <div class="logic-filter-tags">
        <button v-for="f in filters" :key="f.value" class="filter-tag" :class="{ 'filter-tag--active': activeFilter === f.value }" @click="activeFilter = f.value">{{ f.label }}</button>
      </div>
    </div>

    <div class="logic-page__list">
      <div v-for="fn in filteredFunctions" :key="fn.id" class="rule-card" :class="{ 'rule-card--expanded': expandedId === fn.id }" @click="expandedId = expandedId === fn.id ? null : fn.id">
        <div class="rule-card__header">
          <span class="rule-card__status" :class="`rule-card__status--${fn.status}`"></span>
          <span class="rule-card__name text-body-medium">{{ fn.name }}</span>
          <span class="rule-card__entity text-caption">{{ fn.entity_name || '独立函数' }}</span>
          <span class="rule-card__priority" :class="fn.is_derived_property ? 'priority--high' : 'priority--medium'">{{ fn.is_derived_property ? '派生属性' : fn.logic_type }}</span>
        </div>
        <div v-if="expandedId === fn.id" class="rule-card__detail">
          <div class="rule-detail-row">
            <span class="rule-detail-label">描述</span>
            <span>{{ fn.description || '—' }}</span>
          </div>
          <div class="rule-detail-row">
            <span class="rule-detail-label">返回类型</span>
            <code class="text-code">{{ fn.return_type }}</code>
          </div>
          <div class="rule-detail-row">
            <span class="rule-detail-label">逻辑体</span>
            <code class="text-code">{{ fn.logic_body || '—' }}</code>
          </div>
          <div class="rule-detail-row">
            <span class="rule-detail-label">调用次数</span>
            <span>{{ fn.execution_count }} 次</span>
          </div>
          <div class="rule-card__actions">
            <button class="btn-sm-exec" @click.stop="handleTest(fn)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 1.5l7 4.5-7 4.5V1.5z" fill="currentColor"/></svg>
              测试
            </button>
            <button class="btn-sm-del" @click.stop="handleDelete(fn)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 3h8M4 3V2h4v1M3 3v7h6V3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              删除
            </button>
          </div>
        </div>
      </div>
      <div v-if="filteredFunctions.length === 0" class="logic-empty">
        <p class="text-caption">无匹配函数</p>
      </div>
    </div>

    <FunctionBuilderDrawer
      :visible="showAdd"
      :edit-id="editingFuncId"
      @close="showAdd = false; editingFuncId = undefined"
      @saved="onFuncSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { functionApi, type FunctionItem } from '../../api/functions'
import FunctionBuilderDrawer from '../../components/logic/FunctionBuilderDrawer.vue'
import BuilderReturnBanner from '../../components/common/BuilderReturnBanner.vue'

const route = useRoute()
const router = useRouter()

const functions = ref<FunctionItem[]>([])
const search = ref('')
const activeFilter = ref('all')
const expandedId = ref<string | null>(null)
const showAdd = ref(false)
const editingFuncId = ref<string | undefined>()

const filters = [
  { label: '全部', value: 'all' },
  { label: '已激活', value: 'active' },
  { label: '派生属性', value: 'derived' },
  { label: '独立函数', value: 'standalone' },
]

const stats = computed(() => {
  const all = functions.value
  return {
    total: all.length,
    active: all.filter(f => f.status === 'active').length,
    derived: all.filter(f => f.is_derived_property).length,
    standalone: all.filter(f => !f.entity_id).length,
  }
})

const filteredFunctions = computed(() => {
  let list = functions.value
  if (activeFilter.value === 'active') list = list.filter(f => f.status === 'active')
  else if (activeFilter.value === 'derived') list = list.filter(f => f.is_derived_property)
  else if (activeFilter.value === 'standalone') list = list.filter(f => !f.entity_id)
  if (search.value) {
    const s = search.value.toLowerCase()
    list = list.filter(f => f.name.toLowerCase().includes(s) || f.description.toLowerCase().includes(s))
  }
  return list
})

async function fetchFunctions() {
  functions.value = await functionApi.list()
}

function onFuncSaved(fn: { id: string; name: string }) {
  showAdd.value = false
  editingFuncId.value = undefined
  fetchFunctions()
  if (route.query.from === 'builder') {
    const sid = route.query.session_id as string
    const oid = route.query.object_id as string
    if (sid && oid) {
      router.push({ path: '/builder', query: { session_id: sid, attach_to: oid, new_id: fn.id, kind: 'function' } })
    }
  }
}

async function handleTest(fn: FunctionItem) {
  const result = await functionApi.test(fn.id)
  alert(result.success ? `结果: ${result.result} (${result.execution_ms.toFixed(1)}ms)` : `错误: ${result.error}`)
  await fetchFunctions()
}

async function handleDelete(fn: FunctionItem) {
  if (!confirm(`确定删除函数「${fn.name}」？`)) return
  await functionApi.remove(fn.id)
  await fetchFunctions()
}

onMounted(() => {
  fetchFunctions()
  if (route.query.from === 'builder') {
    showAdd.value = true
  }
})
</script>

<style scoped>
@import './logic-shared.css';
</style>
