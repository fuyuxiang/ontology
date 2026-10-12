<template>
  <div class="logic-page" :class="{ 'logic-page--embedded': embedded }">
    <BuilderReturnBanner kind-label="逻辑" />
    <div class="logic-page__header">
      <div v-if="!embedded">
        <h1 class="text-display">{{ text("逻辑管理") }}</h1>
        <p class="text-caption" style="margin-top: 4px">{{ text("计算逻辑管理") }}</p>
      </div>
      <div class="logic-page__actions">
        <button class="btn-primary" @click="editingFuncId = undefined; showAdd = true" :disabled="!canEdit">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path
              d="M7 2v10M2 7h10"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
          {{ text("新建逻辑") }}
        </button>
        <button class="btn-secondary" @click="showCreateModal = true" :disabled="!canEdit">{{ text("新建 Python 工作区") }}</button>
      </div>
    </div>

    <div v-if="error" class="logic-error" role="alert">
      <span>{{ error }}</span>
      <button class="btn-secondary" :disabled="loading" @click="fetchFunctions">{{ text("重试") }}</button>
    </div>
    <div class="master-detail" :aria-busy="loading">
      <div class="master-detail__list">
        <div class="master-detail__toolbar">
          <input
            v-model="search"
            class="logic-search"
            :aria-label="text('搜索逻辑')"
            :placeholder="text('搜索逻辑名称...')"
          />
          <div class="logic-filter-tags">
            <button
              v-for="f in filters"
              :key="f.value"
              class="filter-tag"
              :class="{ 'filter-tag--active': activeFilter === f.value }"
              :aria-pressed="activeFilter === f.value"
              @click="activeFilter = f.value"
            >
              {{ f.label }}
            </button>
          </div>
        </div>

        <div class="master-detail__items">
          <button
            type="button"
            v-for="fn in filteredFunctions"
            :key="fn.id"
            class="list-item"
            :class="{ 'list-item--active': selectedId === fn.id }"
            :aria-pressed="selectedId === fn.id"
            :title="fn.name"
            @click="selectedId = fn.id"
          >
            <span class="list-item__status" :class="`list-item__status--${fn.status}`"></span>
            <span class="list-item__name">{{ fn.name }}</span>
            <span class="list-item__badge priority--medium">{{ fn.logic_type }}</span>
            <span class="list-item__meta">{{ fn.entity_name || '—' }}</span>
          </button>
          <div v-if="loading" class="logic-empty" role="status">{{ text("正在加载逻辑…") }}</div>
          <div v-else-if="!error && filteredFunctions.length === 0" class="logic-empty">
            <p class="text-caption">
              {{ functions.length ? text('无匹配逻辑，请调整搜索或筛选。') : text('暂无逻辑，从新建开始。') }}
            </p>
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
              <span class="detail-meta-label">{{ text("状态") }}</span>
              <span class="detail-meta-value">
                <span
                  class="list-item__status"
                  :class="`list-item__status--${selectedFn.status}`"
                ></span>
                {{ selectedFn.status === 'active' ? text('已激活') : text('未激活') }}
              </span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">{{ text("关联实体") }}</span>
              <span class="detail-meta-value">{{ selectedFn.entity_name || '—' }}</span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">{{ text("返回类型") }}</span>
              <span class="detail-meta-value"
                ><code>{{ selectedFn.return_type }}</code></span
              >
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">{{ text("调用次数") }}</span>
              <span class="detail-meta-value">{{ selectedFn.execution_count }} 次</span>
            </div>
          </div>

          <div v-if="selectedFn.description" class="detail-panel__section">
            <h3 class="detail-section-title">{{ text("描述") }}</h3>
            <p class="detail-section-text">{{ selectedFn.description }}</p>
          </div>

          <div class="detail-panel__section">
            <h3 class="detail-section-title">{{ text("逻辑体") }}</h3>
            <code class="detail-code-block">{{ selectedFn.logic_body || '—' }}</code>
          </div>

          <div class="detail-panel__actions">
            <button class="btn-sm-exec" @click="handleEdit(selectedFn)" :disabled="!canEdit">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path
                  d="M8.5 1.5l2 2L4 10l-2.5.5L2 8l6.5-6.5z"
                  stroke="currentColor"
                  stroke-width="1.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
              {{ text("编辑配置") }}
            </button>
            <button v-if="selectedFn.logic_type === 'python'" class="btn-sm-exec" @click="openCode(selectedFn)" :disabled="!canEdit">{{ text("Python 工作区") }}</button>
            <button class="btn-sm-del" :disabled="!canEdit || (!!deleting)" @click="handleDelete(selectedFn)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path
                  d="M2 3h8M4 3V2h4v1M3 3v7h6V3"
                  stroke="currentColor"
                  stroke-width="1.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
              {{ text("删除") }}
            </button>
          </div>
        </template>
        <div v-else class="detail-panel__empty">
          <p class="text-caption">{{ text("选择一个逻辑查看详情") }}</p>
        </div>
      </div>
    </div>

    <FunctionCreateModal
      :visible="showCreateModal"
      @close="showCreateModal = false"
      @created="onFuncCreated"
    />

    <FunctionBuilderDrawer
      :visible="showAdd"
      :edit-id="editingFuncId"
      @close="closeFunctionDrawer"
      @saved="onFuncSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { useProductText } from '../../composables/useProductText'
const { text } = useProductText()

import { useManagementPermission } from '../../composables/useManagementPermission'
const { canEdit } = useManagementPermission('rule:write')
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { functionApi, type FunctionItem } from '../../api/functions'
import { useOntologyStore } from '../../store/ontology'
import { useScenarioStore } from '../../store/scenarios'
import FunctionBuilderDrawer from '../../components/logic/FunctionBuilderDrawer.vue'
import FunctionCreateModal from '../../components/logic/FunctionCreateModal.vue'
import { skillError } from '../../api/skills'
import { useToast } from '../../composables/useToast'
import BuilderReturnBanner from '../../components/common/BuilderReturnBanner.vue'

const props = defineProps<{ embedded?: boolean }>()

const route = useRoute()
const router = useRouter()
const scenarioStore = useScenarioStore()
const ontologyStore = useOntologyStore()
const toast = useToast()
const loading = ref(false)
const error = ref('')
const deleting = ref('')
let listRequest = 0

const functions = ref<FunctionItem[]>([])
const search = ref('')
const activeFilter = ref('all')
const selectedId = ref<string | null>(null)
const showAdd = ref(false)
const showCreateModal = ref(false)
const editingFuncId = ref<string | undefined>()

const selectedFn = computed(
  () => filteredFunctions.value.find((f) => f.id === selectedId.value) || null,
)

const filters = [
  { label: text('全部'), value: 'all' },
  { label: text('已激活'), value: 'active' },
]

const filteredFunctions = computed(() => {
  let list = functions.value
  if (activeFilter.value === 'active') list = list.filter((f) => f.status === 'active')
  if (search.value) {
    const s = search.value.trim().toLowerCase()
    list = list.filter(
      (f) => f.name.toLowerCase().includes(s) || (f.description || '').toLowerCase().includes(s),
    )
  }
  return list
})

async function fetchFunctions() {
  const request = ++listRequest
  loading.value = true
  error.value = ''
  const query: Record<string, string> = {}
  if (props.embedded && route.params.code && ontologyStore.currentOntologyId) {
    query.ontology_id = ontologyStore.currentOntologyId
  }
  try {
    const result = await functionApi.list(query)
    if (request === listRequest) functions.value = result
  } catch (e) {
    if (request === listRequest) error.value = skillError(e, '逻辑列表加载失败')
  } finally {
    if (request === listRequest) loading.value = false
  }
}

watch(filteredFunctions, (items) => {
  if (!items.some((item) => item.id === selectedId.value)) selectedId.value = items[0]?.id || null
})
watch(
  () => (props.embedded && route.params.code ? ontologyStore.currentOntologyId : null),
  () => {
    functions.value = []
    selectedId.value = null
    fetchFunctions()
  },
)
onBeforeUnmount(() => {
  listRequest++
})

/** 增删改后同步刷新本体统计，使详情页侧栏计数即时更新 */
async function refreshAfterMutation() {
  await fetchFunctions()
  if (props.embedded) {
    try {
      await scenarioStore.refreshScenarios()
    } catch {
      toast.warning(text('操作已完成，本体统计更新失败，请刷新本体列表'))
    }
  }
}

function onFuncCreated(_fn: { id: string; name: string }) {
  showCreateModal.value = false
  refreshAfterMutation()
}
function closeFunctionDrawer() {
  showAdd.value = false
  editingFuncId.value = undefined
}

function onFuncSaved(fn: { id: string; name: string }) {
  showAdd.value = false
  editingFuncId.value = undefined
  refreshAfterMutation()
  if (route.query.from === 'builder') {
    const sid = route.query.session_id as string
    const oid = route.query.object_id as string
    if (sid && oid) {
      router.push({
        path: '/builder',
        query: { session_id: sid, attach_to: oid, new_id: fn.id, kind: 'function' },
      })
    }
  }
}

function handleEdit(fn: FunctionItem) {
  editingFuncId.value = fn.id
  showAdd.value = true
}
function openCode(fn: FunctionItem) {
  const query: Record<string, string> = {}
  if (route.params.code) {
    query.from = 'ontology'
    query.code = route.params.code as string
  }
  router.push({ path: `/logic/functions/${fn.id}/code`, query })
}

async function handleDelete(fn: FunctionItem) {
  if (deleting.value || !confirm(`确定删除逻辑「${fn.name}」？`)) return
  deleting.value = fn.id
  try {
    await functionApi.remove(fn.id)
    functions.value = functions.value.filter((item) => item.id !== fn.id)
    toast.success(text('逻辑已删除'))
    await refreshAfterMutation()
  } catch (e) {
    error.value = skillError(e, '删除逻辑失败')
  } finally {
    deleting.value = ''
  }
}

onMounted(async () => {
  await fetchFunctions()
  if (route.query.from === 'builder') {
    showAdd.value = true
  }
  // 自动选中第一个函数
  if (!selectedId.value && filteredFunctions.value.length > 0) {
    selectedId.value = filteredFunctions.value[0].id
  }
})
</script>

<style scoped>
@import './logic-shared.css';

.logic-page--embedded {
  padding: 0;
  max-width: none;
}
.logic-page--embedded .logic-page__header {
  margin-bottom: 16px;
  justify-content: flex-end;
}

.master-detail {
  display: grid;
  grid-template-columns: minmax(260px, 32%) minmax(0, 1fr);
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
  width: 100%;
  min-width: 0;
  border: 1px solid transparent;
  background: transparent;
  text-align: left;
  font-family: inherit;
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

.list-item__status--active {
  background: var(--status-success, #22c55e);
}
.list-item__status--warning {
  background: var(--status-warning, #f59e0b);
}
.list-item__status--disabled,
.list-item__status--inactive {
  background: var(--neutral-300, #d4d4d4);
}

.list-item__name {
  flex: 1;
  min-width: 0;
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
  min-width: 0;
  background: var(--neutral-0, #fff);
  padding: 24px;
  overflow-y: auto;
}

.detail-panel__header {
  flex-wrap: wrap;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.detail-panel__title {
  overflow-wrap: anywhere;
  min-width: 0;
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
  overflow-wrap: anywhere;
  min-width: 0;
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
  overflow-wrap: anywhere;
  line-height: 1.6;
  font-size: 13px;
  color: var(--neutral-700, #495057);
  margin: 0;
}

.detail-panel__actions {
  flex-wrap: wrap;
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
.logic-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 16px;
  border: 1px solid var(--status-error, #ef4444);
  border-radius: 8px;
  color: var(--status-error, #ef4444);
  overflow-wrap: anywhere;
}
.list-item:focus-visible {
  outline: 2px solid var(--semantic-500, #4c6ef5);
  outline-offset: -2px;
}
button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
@media (max-width: 900px) {
  .master-detail {
    grid-template-columns: minmax(220px, 38%) minmax(0, 1fr);
  }
  .master-detail__detail {
    padding: 16px;
  }
  .detail-panel__meta {
    grid-template-columns: 1fr;
  }
}
</style>
