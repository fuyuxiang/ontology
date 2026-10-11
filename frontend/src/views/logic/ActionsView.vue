<template>
  <div class="logic-page" :class="{ 'logic-page--embedded': embedded }">
    <BuilderReturnBanner kind-label="动作" />
    <div class="logic-page__header">
      <div v-if="!embedded">
        <h1 class="text-display">行动建模</h1>
        <p class="text-caption" style="margin-top: 4px">行动注册与执行管理</p>
      </div>
      <div class="logic-page__actions">
        <button class="btn-primary" @click="openCreate">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path
              d="M7 2v10M2 7h10"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
          新建行动
        </button>
      </div>
    </div>

    <div v-if="error" class="logic-error" role="alert">
      <span>{{ error }}</span>
      <button class="btn-secondary" :disabled="loading" @click="fetchActions">重试</button>
    </div>
    <div class="master-detail" :aria-busy="loading">
      <div class="master-detail__list">
        <div class="master-detail__toolbar">
          <input
            v-model="search"
            class="logic-search"
            aria-label="搜索行动"
            placeholder="搜索行动名称..."
          />
          <div class="logic-filter-tags">
            <button
              v-for="f in filterOptions"
              :key="f.value"
              class="filter-tag"
              :class="{ 'filter-tag--active': activeFilter === f.value }"
              :aria-pressed="activeFilter === f.value"
              @click="setFilter(f.value)"
            >
              {{ f.label }}
            </button>
          </div>
        </div>

        <div class="master-detail__items">
          <button
            type="button"
            v-for="action in filteredActions"
            :key="action.id"
            class="list-item"
            :class="{ 'list-item--active': selectedId === action.id }"
            :aria-pressed="selectedId === action.id"
            :title="action.name"
            @click="selectedId = action.id"
          >
            <span class="list-item__status" :class="`list-item__status--${action.status}`"></span>
            <span class="list-item__name">{{ action.name }}</span>
            <span class="list-item__badge" :class="`priority--${action.category}`">{{
              action.category === 'domain' ? '领域' : '系统'
            }}</span>
            <span class="list-item__meta">{{ action.entity_name || '系统' }}</span>
          </button>
          <div v-if="loading" class="logic-empty" role="status">正在加载行动…</div>
          <div v-else-if="!error && filteredActions.length === 0" class="logic-empty">
            <p class="text-caption">
              {{ actions.length ? '无匹配行动，请调整搜索或筛选。' : '暂无行动，从新建开始。' }}
            </p>
          </div>
        </div>
      </div>

      <div class="master-detail__detail">
        <template v-if="selectedAction">
          <div class="detail-panel__header">
            <h2 class="detail-panel__title">{{ selectedAction.name }}</h2>
            <span class="list-item__badge" :class="`priority--${selectedAction.category}`">{{
              selectedAction.category === 'domain' ? '领域行动' : '系统行动'
            }}</span>
          </div>

          <div class="detail-panel__meta">
            <div class="detail-meta-item">
              <span class="detail-meta-label">状态</span>
              <span class="detail-meta-value">
                <span
                  class="list-item__status"
                  :class="`list-item__status--${selectedAction.status}`"
                ></span>
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
            <code class="detail-code-block">{{
              selectedAction.parameters_json.map((p: any) => p.name || p).join(', ')
            }}</code>
          </div>

          <div class="detail-panel__actions">
            <button class="btn-sm-exec" @click="openEdit(selectedAction.id)">编辑</button>
            <button
              class="btn-sm-exec"
              :disabled="executing || selectedAction.status !== 'active'"
              @click="openExecution(selectedAction)"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M3 1.5l7 4.5-7 4.5V1.5z" fill="currentColor" />
              </svg>
              {{ selectedAction.status === 'active' ? '执行' : '未激活' }}
            </button>
            <button class="btn-sm-del" :disabled="!!deleting" @click="handleDelete(selectedAction)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path
                  d="M2 3h8M4 3V2h4v1M3 3v7h6V3"
                  stroke="currentColor"
                  stroke-width="1.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
              删除
            </button>
          </div>
        </template>
        <div v-else class="detail-panel__empty">
          <p class="text-caption">选择一个行动查看详情</p>
        </div>
      </div>
    </div>

    <ModalDialog
      :visible="!!executionAction"
      :title="`执行行动 · ${executionAction?.name || ''}`"
      width="640px"
      @close="closeExecution"
    >
      <p class="execution-hint">请核对参数后执行。执行结果会显示在此窗口中。</p>
      <ul v-if="executionAction?.parameters_json?.length" class="execution-parameters">
        <li v-for="parameter in executionAction.parameters_json" :key="parameter.name">
          <code>{{ parameter.name }}</code> · {{ parameter.type
          }}{{ parameter.required ? ' · 必填' : '' }}
          <span v-if="parameter.description"> — {{ parameter.description }}</span>
        </li>
      </ul>
      <label class="form-label" for="action-execution-input">输入参数（JSON 对象）</label>
      <textarea
        id="action-execution-input"
        v-model="executionInput"
        class="form-input execution-input"
        rows="8"
        :disabled="executing"
        spellcheck="false"
      />
      <p v-if="executionError" class="execution-error" role="alert">{{ executionError }}</p>
      <div
        v-if="executionResult"
        class="execution-result"
        :class="{ 'execution-error': !executionResult.success }"
        role="status"
      >
        <strong>{{ executionResult.success ? '执行成功' : '执行失败' }}</strong>
        <p>{{ executionResult.message }}</p>
        <pre v-if="executionResult.output">{{
          JSON.stringify(executionResult.output, null, 2)
        }}</pre>
      </div>
      <template #footer>
        <button class="btn-secondary" :disabled="executing" @click="closeExecution">关闭</button>
        <button
          class="btn-primary"
          :disabled="executing || !!executionResult?.success"
          @click="handleExecute"
        >
          {{ executing ? '执行中…' : executionResult?.success ? '已执行' : '执行' }}
        </button>
      </template>
    </ModalDialog>

    <ActionCreateModal
      :visible="showCreateModal"
      @close="showCreateModal = false"
      @created="onActionCreated"
    />

    <ActionBuilderDrawer
      :visible="drawerVisible"
      :edit-id="drawerEditId"
      @close="drawerVisible = false"
      @saved="onActionSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  actionApi,
  type ActionItem,
  type ActionTypeInfo,
  type ActionExecuteResult,
} from '../../api/actions'
import ModalDialog from '../../components/common/ModalDialog.vue'
import { useOntologyStore } from '../../store/ontology'
import { useScenarioStore } from '../../store/scenarios'
import { skillError } from '../../api/skills'
import { useToast } from '../../composables/useToast'
import BuilderReturnBanner from '../../components/common/BuilderReturnBanner.vue'
import ActionBuilderDrawer from '../../components/logic/ActionBuilderDrawer.vue'
import ActionCreateModal from '../../components/logic/ActionCreateModal.vue'

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

const actions = ref<ActionItem[]>([])
const actionTypes = ref<ActionTypeInfo[]>([])
const search = ref('')
const activeFilter = ref('all')
const selectedId = ref<string | null>(null)
const drawerVisible = ref(false)
const drawerEditId = ref<string | undefined>(undefined)
const showCreateModal = ref(false)
const executionAction = ref<ActionItem | null>(null)
const executionInput = ref('{}')
const executionError = ref('')
const executionResult = ref<ActionExecuteResult | null>(null)
const executing = ref(false)

const filterOptions = [
  { label: '全部', value: 'all' },
  { label: '已激活', value: 'active' },
]

const selectedAction = computed(
  () => filteredActions.value.find((a) => a.id === selectedId.value) || null,
)

const filteredActions = computed(() => {
  let list = actions.value
  if (activeFilter.value === 'active') list = list.filter((a) => a.status === 'active')
  if (search.value) {
    const s = search.value.trim().toLowerCase()
    list = list.filter(
      (a) => a.name.toLowerCase().includes(s) || (a.entity_name || '').toLowerCase().includes(s),
    )
  }
  return list
})

function getTypeLabel(typeKey: string): string {
  const t = actionTypes.value.find((at) => at.type_key === typeKey)
  return t?.label || typeKey
}

function setFilter(value: string) {
  activeFilter.value = value
}

function openCreate() {
  showCreateModal.value = true
}

function openEdit(id: string) {
  const query: Record<string, string> = {}
  if (route.params.code) {
    query.from = 'ontology'
    query.code = route.params.code as string
  }
  router.push({ path: `/logic/actions/${id}/code`, query })
}

function onActionCreated() {
  showCreateModal.value = false
  refreshAfterMutation()
}
function onActionSaved() {
  drawerVisible.value = false
  refreshAfterMutation()
}

async function fetchActions() {
  const request = ++listRequest
  loading.value = true
  error.value = ''
  const query: Record<string, string> = {}
  if (props.embedded && ontologyStore.currentOntologyId) {
    query.ontology_id = ontologyStore.currentOntologyId
  }
  try {
    const result = await actionApi.list(query)
    if (request === listRequest) actions.value = result
  } catch (e) {
    if (request === listRequest) error.value = skillError(e, '行动列表加载失败')
  } finally {
    if (request === listRequest) loading.value = false
  }
}

watch(filteredActions, (items) => {
  if (!items.some((item) => item.id === selectedId.value)) selectedId.value = items[0]?.id || null
})
watch(
  () => (props.embedded ? ontologyStore.currentOntologyId : null),
  () => {
    actions.value = []
    selectedId.value = null
    fetchActions()
  },
)
onBeforeUnmount(() => {
  listRequest++
})

/** 增删改后同步刷新本体统计，使详情页侧栏计数即时更新 */
async function refreshAfterMutation() {
  await fetchActions()
  if (props.embedded) {
    try {
      await scenarioStore.refreshScenarios()
    } catch {
      toast.warning('操作已完成，本体统计更新失败，请刷新本体列表')
    }
  }
}

async function fetchActionTypes() {
  try {
    actionTypes.value = await actionApi.types()
  } catch (e) {
    toast.error(skillError(e, '行动类型加载失败'))
  }
}

function openExecution(action: ActionItem) {
  if (executing.value || action.status !== 'active') return
  executionAction.value = action
  const parameters: Record<string, unknown> = {}
  for (const parameter of action.parameters_json || []) {
    if (parameter.default_value !== undefined && parameter.default_value !== null) {
      try {
        parameters[parameter.name] = JSON.parse(parameter.default_value)
      } catch {
        parameters[parameter.name] = parameter.default_value
      }
    }
  }
  executionInput.value = JSON.stringify(parameters, null, 2)
  executionError.value = ''
  executionResult.value = null
}

function closeExecution() {
  if (!executing.value) executionAction.value = null
}

async function handleExecute() {
  const action = executionAction.value
  if (!action || executing.value) return
  executionError.value = ''
  executionResult.value = null
  let params: Record<string, unknown>
  try {
    const parsed = JSON.parse(executionInput.value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))
      throw new Error('请输入 JSON 对象，不能使用数组或空值')
    params = parsed
    const missing = (action.parameters_json || []).filter(
      (parameter) => parameter.required && !(parameter.name in params),
    )
    if (missing.length)
      throw new Error(`请填写必填参数：${missing.map((parameter) => parameter.name).join('、')}`)
  } catch (e) {
    executionError.value =
      e instanceof SyntaxError ? '参数不是合法 JSON，请检查格式' : (e as Error).message
    return
  }
  executing.value = true
  try {
    executionResult.value = await actionApi.execute(action.id, params)
    await fetchActions()
  } catch (e) {
    executionError.value = skillError(e, '行动执行请求失败，请重试')
  } finally {
    executing.value = false
  }
}

async function handleDelete(action: ActionItem) {
  if (deleting.value || !confirm(`确定删除行动「${action.name}」？`)) return
  deleting.value = action.id
  try {
    await actionApi.remove(action.id)
    actions.value = actions.value.filter((item) => item.id !== action.id)
    toast.success('行动已删除')
    await refreshAfterMutation()
  } catch (e) {
    error.value = skillError(e, '删除行动失败')
  } finally {
    deleting.value = ''
  }
}

onMounted(() => {
  fetchActions()
  fetchActionTypes()
  if (route.query.from === 'builder') {
    showCreateModal.value = true
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
.execution-hint,
.execution-parameters {
  color: var(--neutral-600);
  font-size: 13px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.execution-input {
  display: block;
  box-sizing: border-box;
  width: 100%;
  margin-top: 8px;
  font-family: var(--font-mono, monospace);
  resize: vertical;
}
.execution-error {
  color: var(--status-error, #ef4444);
  overflow-wrap: anywhere;
}
.execution-result {
  margin-top: 16px;
  padding: 12px;
  border-radius: 8px;
  background: var(--neutral-50);
  font-size: 13px;
  overflow-wrap: anywhere;
}
.execution-result pre {
  max-height: 240px;
  overflow: auto;
  white-space: pre-wrap;
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
