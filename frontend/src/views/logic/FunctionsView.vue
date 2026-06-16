<template>
  <div class="logic-page">
    <BuilderReturnBanner kind-label="函数" />
    <div class="logic-page__header">
      <div>
        <h1 class="text-display">函数管理</h1>
        <p class="text-caption" style="margin-top: 4px;">计算逻辑管理</p>
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
      <div class="stat-card stat-card--error">
        <div class="stat-card__value">{{ stats.standalone }}</div>
        <div class="stat-card__label">独立函数</div>
      </div>
    </div>

    <div class="master-detail">
      <div class="master-detail__list">
        <div class="master-detail__toolbar">
          <input v-model="search" class="logic-search" placeholder="搜索函数名称..." />
          <div class="logic-filter-tags">
            <button
              v-for="f in filters" :key="f.value"
              class="filter-tag"
              :class="{ 'filter-tag--active': activeFilter === f.value }"
              @click="activeFilter = f.value"
            >{{ f.label }}</button>
          </div>
        </div>

        <div class="master-detail__items">
          <div
            v-for="fn in filteredFunctions" :key="fn.id"
            class="list-item"
            :class="{ 'list-item--active': selectedId === fn.id }"
            @click="selectedId = fn.id"
          >
            <span class="list-item__status" :class="`list-item__status--${fn.status}`"></span>
            <span class="list-item__name">{{ fn.name }}</span>
            <span class="list-item__badge priority--medium">{{ fn.logic_type }}</span>
            <span class="list-item__meta">{{ fn.entity_name || '独立' }}</span>
          </div>
          <div v-if="filteredFunctions.length === 0" class="logic-empty">
            <p class="text-caption">无匹配函数</p>
          </div>
        </div>
      </div>

      <div class="master-detail__detail">
        <template v-if="selectedFn">
          <div class="detail-panel__header">
            <h2 class="detail-panel__title">{{ selectedFn.name }}</h2>
            <span class="list-item__badge priority--medium">{{ selectedFn.logic_type }}</span>
          </div>

          <div class="detail-panel__meta">
            <div class="detail-meta-item">
              <span class="detail-meta-label">状态</span>
              <span class="detail-meta-value">
                <span class="list-item__status" :class="`list-item__status--${selectedFn.status}`"></span>
                {{ selectedFn.status === 'active' ? '已激活' : '未激活' }}
              </span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">关联实体</span>
              <span class="detail-meta-value">{{ selectedFn.entity_name || '独立函数' }}</span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">返回类型</span>
              <span class="detail-meta-value"><code>{{ selectedFn.return_type }}</code></span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">调用次数</span>
              <span class="detail-meta-value">{{ selectedFn.execution_count }} 次</span>
            </div>
          </div>

          <div v-if="selectedFn.description" class="detail-panel__section">
            <h3 class="detail-section-title">描述</h3>
            <p class="detail-section-text">{{ selectedFn.description }}</p>
          </div>

          <div class="detail-panel__section">
            <h3 class="detail-section-title">逻辑体</h3>
            <code class="detail-code-block">{{ selectedFn.logic_body || '—' }}</code>
          </div>

          <div class="detail-panel__actions">
            <button class="btn-sm-exec" @click="handleTest(selectedFn)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 1.5l7 4.5-7 4.5V1.5z" fill="currentColor"/></svg>
              测试
            </button>
            <button class="btn-sm-del" @click="handleDelete(selectedFn)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 3h8M4 3V2h4v1M3 3v7h6V3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              删除
            </button>
          </div>
        </template>
        <div v-else class="detail-panel__empty">
          <p class="text-caption">选择一个函数查看详情</p>
        </div>
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
const selectedId = ref<string | null>(null)
const showAdd = ref(false)
const editingFuncId = ref<string | undefined>()

const selectedFn = computed(() => filteredFunctions.value.find(f => f.id === selectedId.value) || null)

const filters = [
  { label: '全部', value: 'all' },
  { label: '已激活', value: 'active' },
  { label: '独立函数', value: 'standalone' },
]

const stats = computed(() => {
  const all = functions.value
  return {
    total: all.length,
    active: all.filter(f => f.status === 'active').length,
    standalone: all.filter(f => !f.entity_id).length,
  }
})

const filteredFunctions = computed(() => {
  let list = functions.value
  if (activeFilter.value === 'active') list = list.filter(f => f.status === 'active')
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
  if (selectedId.value === fn.id) selectedId.value = null
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
.list-item__status--warning { background: var(--status-warning, #f59e0b); }
.list-item__status--disabled, .list-item__status--inactive { background: var(--neutral-300, #d4d4d4); }

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
</style>
