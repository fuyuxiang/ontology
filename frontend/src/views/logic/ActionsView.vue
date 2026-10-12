<template>
  <div class="logic-page" :class="{ 'logic-page--embedded': embedded }">
    <BuilderReturnBanner kind-label="动作" />
    <div class="logic-page__header">
      <div v-if="!embedded">
        <h1 class="text-display">{{ text("行动建模") }}</h1>
        <p class="text-caption" style="margin-top: 4px">{{ text("行动注册与执行管理") }}</p>
      </div>
      <div class="logic-page__actions">
        <button class="btn-primary" @click="openCreate" :disabled="!canEdit">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path
              d="M7 2v10M2 7h10"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
          {{ text("新建行动") }}
        </button>
        <button class="btn-secondary" @click="showCreateModal = true" :disabled="!canEdit">{{ text("新建 Python 脚本") }}</button>
      </div>
    </div>

    <div v-if="error" class="logic-error" role="alert">
      <span>{{ error }}</span>
      <button class="btn-secondary" :disabled="loading" @click="fetchActions">{{ text("重试") }}</button>
    </div>
    <div class="master-detail" :aria-busy="loading">
      <div class="master-detail__list">
        <div class="master-detail__toolbar">
          <input
            v-model="search"
            class="logic-search"
            :aria-label="text('搜索行动')"
            :placeholder="text('搜索行动名称...')"
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
              action.category === 'domain' ? text('领域') : text('系统')
            }}</span>
            <span class="list-item__meta">{{ action.entity_name || text('系统') }}</span>
          </button>
          <div v-if="loading" class="logic-empty" role="status">{{ text("正在加载行动…") }}</div>
          <div v-else-if="!error && filteredActions.length === 0" class="logic-empty">
            <p class="text-caption">
              {{ actions.length ? text('无匹配行动，请调整搜索或筛选。') : text('暂无行动，从新建开始。') }}
            </p>
          </div>
        </div>
      </div>

      <div class="master-detail__detail">
        <template v-if="selectedAction">
          <div class="detail-panel__header">
            <h2 class="detail-panel__title">{{ selectedAction.name }}</h2>
            <span class="list-item__badge" :class="`priority--${selectedAction.category}`">{{
              selectedAction.category === 'domain' ? text('领域行动') : text('系统行动')
            }}</span>
          </div>

          <div class="detail-panel__meta">
            <div class="detail-meta-item">
              <span class="detail-meta-label">{{ text("状态") }}</span>
              <span class="detail-meta-value">
                <span
                  class="list-item__status"
                  :class="`list-item__status--${selectedAction.status}`"
                ></span>
                {{ selectedAction.status === 'active' ? text('已激活') : text('未激活') }}
              </span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">{{ text("关联实体") }}</span>
              <span class="detail-meta-value">{{ selectedAction.entity_name || text('系统行动') }}</span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">{{ text("行动类型") }}</span>
              <span class="detail-meta-value">{{ getTypeLabel(selectedAction.action_type) }}</span>
            </div>
            <div class="detail-meta-item">
              <span class="detail-meta-label">{{ text("执行次数") }}</span>
              <span class="detail-meta-value">{{ selectedAction.impact_count ?? 0 }} 次</span>
            </div>
          </div>

          <div v-if="selectedAction.description" class="detail-panel__section">
            <h3 class="detail-section-title">{{ text("描述") }}</h3>
            <p class="detail-section-text">{{ selectedAction.description }}</p>
          </div>

          <div v-if="selectedAction.parameters_json?.length" class="detail-panel__section">
            <h3 class="detail-section-title">{{ text("参数") }}</h3>
            <code class="detail-code-block">{{
              selectedAction.parameters_json.map((p: any) => p.name || p).join(', ')
            }}</code>
          </div>

          <div class="detail-panel__actions">
            <button class="btn-sm-exec" @click="openEdit(selectedAction.id)" :disabled="!canEdit">{{ text("编辑配置") }}</button>
            <button v-if="selectedAction.action_type === 'custom_script'" class="btn-sm-exec" @click="openCode(selectedAction.id)" :disabled="!canEdit">{{ text("Python 工作区") }}</button>
            <button
              class="btn-sm-exec"
              :disabled="!canExecute || executing || selectedAction.status !== 'active'"
              @click="openExecution(selectedAction)"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M3 1.5l7 4.5-7 4.5V1.5z" fill="currentColor" />
              </svg>
              {{ selectedAction.status === 'active' ? text('执行') : text('未激活') }}
            </button>
            <button class="btn-sm-del" :disabled="!canEdit || (!!deleting)" @click="handleDelete(selectedAction)">
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
          <p class="text-caption">{{ text("选择一个行动查看详情") }}</p>
        </div>
      </div>
    </div>

    <ModalDialog
      :visible="!!executionAction"
      :title="`${text('执行行动')} · ${executionAction?.name || ''}`"
      width="640px"
      @close="closeExecution"
    >
      <p class="execution-hint">{{ text("请核对参数后执行。刷新、断线和重试使用同一执行关联键；结果未知时请先核对业务回执。") }}</p>
      <p v-if="executionAttempt">{{ text('关联键：') }}<code>{{ executionAttempt.key }}</code></p>
      <ul v-if="executionAction?.parameters_json?.length" class="execution-parameters">
        <li v-for="parameter in executionAction.parameters_json" :key="parameter.name">
          <code>{{ parameter.name }}</code> · {{ parameter.type
          }}{{ parameter.required ? ' · 必填' : '' }}
          <span v-if="parameter.description"> — {{ parameter.description }}</span>
        </li>
      </ul>
      <label class="form-label" for="action-execution-input">{{ text("输入参数（JSON 对象）") }}</label>
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
        <strong>{{ executionStateLabel(executionResult) }}</strong>
        <p v-if="executionResult.execution_id">{{ text('执行记录：') }}{{ executionResult.execution_id }} · {{ executionResult.state }}</p>
        <p>{{ executionResult.message }}</p>
        <pre v-if="executionResult.output">{{
          JSON.stringify(executionResult.output, null, 2)
        }}</pre>
      </div>
      <template #footer>
        <button class="btn-secondary" :disabled="executing" @click="closeExecution">{{ text("关闭") }}</button>
        <section v-if="['unknown','committed_unrecorded'].includes(executionResult?.state || '') && executionResult?.execution_id" class="execution-reconciliation">
          <h4>{{ text("人工核查执行回执") }}</h4><p>{{ text("仅记录人工已核对的声明，不会再次发送原行动。请先检查真实源数据或外部回执。") }}</p>
          <label>{{ text("核查结果") }}<select v-model="reconciliationResolution" :disabled="executing"><option value="succeeded">{{ text("已确认业务成功") }}</option><option value="failed">{{ text("已确认未成功") }}</option></select></label>
          <label>{{ text("回执编号（可选）") }}<input v-model="reconciliationReceipt" :disabled="executing" /></label>
          <label>{{ text("核查依据") }}<textarea v-model="reconciliationEvidence" :disabled="executing" rows="3" :placeholder="text('记录源数据回读、外部回执及确认结果，至少10字')" /></label>
          <label><input type="checkbox" v-model="reconciliationAcknowledged" :disabled="executing" /> {{ text("我已核对业务源或回执，确认上述人工声明") }}</label>
          <button class="btn-secondary" :disabled="executing || !canExecute || !reconciliationAcknowledged || reconciliationEvidence.trim().length < 10" @click="reconcileExecution">{{ text("记录人工核查结果") }}</button>
        </section>
        <button v-if="executionAttempt" class="btn-secondary" :disabled="executing" @click="checkExecution">{{ text("核查已有执行结果") }}</button>
        <button v-if="executionResult?.state === 'succeeded' || executionResult?.state === 'failed'" class="btn-secondary" :disabled="executing || !canExecute" @click="newExecution">{{ text("开始新执行") }}</button>
        <button
          class="btn-primary"
          :disabled="!canExecute || executing || !!executionResult?.success || ['unknown','committed_unrecorded','partial_committed','executing','pending'].includes(executionResult?.state || '')"
          @click="handleExecute"
        >
          {{ executing ? text('执行中…') : executionResult?.success ? text('已执行') : text('执行') }}
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
import { useProductText } from '../../composables/useProductText'
const { text } = useProductText()

import { useManagementPermission } from '../../composables/useManagementPermission'
const { canEdit, canExecute } = useManagementPermission('rule:write')
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
import { useAuthStore } from '../../store/auth'
import { readActionAttempt, ensureActionAttempt, saveActionAttempt, clearCompletedActionAttempt, type ActionAttempt } from '../../utils/actionAttempt'

const props = defineProps<{ embedded?: boolean }>()
const auth = useAuthStore()

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
const reconciliationResolution = ref<'succeeded'|'failed'>('succeeded')
const reconciliationEvidence = ref(''), reconciliationReceipt = ref(''), reconciliationAcknowledged = ref(false)
const executionAttempt = ref<ActionAttempt | null>(null)
let executionEpoch = 0
onBeforeUnmount(() => { ++executionEpoch })
function executionStateLabel(result:ActionExecuteResult) {
  if (result.state === 'partial_committed') return text('部分写入已提交 · 已完成的写入保留，请核查回执；原行动不可重试')
  if (result.state === 'committed_unrecorded') return text('业务已提交 · 执行记录待核查，原行动不会重发')
  if (result.state === 'unknown') return text('结果待核对 · 原执行不会重发')
  if (result.state === 'executing' || result.state === 'pending') return text('执行正在进行')
  return text(result.success ? '执行成功' : '执行失败')
}
function newExecution() {
  const action = executionAction.value
  if (!canExecute.value || !action || executing.value || !auth.user?.id) return
  try { clearCompletedActionAttempt(auth.user.id, action.id); executionAttempt.value = null; executionResult.value = null; executionError.value = '' }
  catch (exception) { executionError.value = skillError(exception, '无法开始新执行') }
}
async function reconcileExecution() {
  const action=executionAction.value, result=executionResult.value, owner=auth.user?.id
  if (!action || !owner || !result?.execution_id || !['unknown','committed_unrecorded'].includes(result.state || '') || !canExecute.value || executing.value) return
  if (!reconciliationAcknowledged.value || reconciliationEvidence.value.trim().length < 10) { executionError.value=text('请确认已经人工核对，并填写至少10字的源数据或回执核查依据');return }
  const epoch=executionEpoch
  executing.value=true;executionError.value=''
  try {
    const resolved=await actionApi.reconcile(action.id,result.execution_id,{resolution:reconciliationResolution.value,evidence:reconciliationEvidence.value.trim(),receipt_id:reconciliationReceipt.value.trim() || undefined})
    if (executionAttempt.value) saveActionAttempt(owner,action.id,{key:executionAttempt.value.key,state:resolved.state || 'unknown',execution_id:resolved.execution_id})
    if (epoch !== executionEpoch) return
    executionResult.value=resolved
    await fetchActions()
  } catch (error) { if (epoch === executionEpoch) executionError.value=skillError(error,'人工核查结果记录失败，请核查原执行回执') }
  finally { if (epoch === executionEpoch) executing.value=false }
}
async function checkExecution() {
  const action = executionAction.value, attempt = executionAttempt.value, owner = auth.user?.id
  if (!action || !attempt || !owner || executing.value) return
  const epoch = executionEpoch
  executing.value = true; executionError.value = ''
  try {
    const record = await actionApi.executionByKey(action.id, attempt.key)
    saveActionAttempt(owner, action.id, {key:attempt.key, state:record.state || 'unknown', execution_id:record.execution_id})
    if (epoch !== executionEpoch || executionAction.value?.id !== action.id) return
    executionAttempt.value = readActionAttempt(owner, action.id); executionResult.value = record; executionInput.value = JSON.stringify(record.params, null, 2)
  } catch (exception:any) { if (epoch === executionEpoch) executionError.value = exception?.response?.status === 404 ? '服务端尚未登记该执行；使用原关联键重试，不会重复提交。' : skillError(exception, '核查执行结果失败') }
  finally { if (epoch === executionEpoch) executing.value = false }
}

const filterOptions = [
  { label: text('全部'), value: 'all' },
  { label: text('已激活'), value: 'active' },
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
  drawerEditId.value = undefined
  drawerVisible.value = true
}

function openEdit(id: string) {
  drawerEditId.value = id
  drawerVisible.value = true
}
function openCode(id: string) {
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
      toast.warning(text('操作已完成，本体统计更新失败，请刷新本体列表'))
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
  if (!canExecute.value || executing.value || action.status !== 'active') return
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
  reconciliationEvidence.value='';reconciliationReceipt.value='';reconciliationAcknowledged.value=false
  ++executionEpoch
  executionAttempt.value = null
  try { if (auth.user?.id) executionAttempt.value = readActionAttempt(auth.user.id, action.id) }
  catch (exception) { executionError.value = skillError(exception, '执行关联恢复失败') }
  if (executionAttempt.value) void checkExecution()
}

function closeExecution() {
  if (!executing.value) executionAction.value = null
}

async function handleExecute() {
  const action = executionAction.value
  if (!canExecute.value || !action || executing.value || ['unknown','committed_unrecorded','partial_committed','executing','pending'].includes(executionResult.value?.state || '')) return
  executionError.value = ''
  executionResult.value = null
  let params: Record<string, unknown>
  try {
    const parsed = JSON.parse(executionInput.value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))
      throw new Error(text('请输入 JSON 对象，不能使用数组或空值'))
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
  const owner = auth.user?.id
  if (!owner) { executing.value = false; executionError.value = text('请重新登录'); return }
  const epoch = executionEpoch
  try {
    const attempt = ensureActionAttempt(owner, action.id)
    executionAttempt.value = attempt
    const result = await actionApi.execute(action.id, params, false, attempt.key)
    saveActionAttempt(owner, action.id, {key:attempt.key, state:result.state || (result.success ? 'succeeded' : 'unknown'), execution_id:result.execution_id})
    if (epoch !== executionEpoch) return
    executionResult.value = result
    await fetchActions()
  } catch (e) {
    if (epoch === executionEpoch) executionError.value = skillError(e, '请求结果待核对，请核查已有执行结果；重试保留原关联键')
  } finally {
    if (epoch === executionEpoch) executing.value = false
  }
}

async function handleDelete(action: ActionItem) {
  if (deleting.value || !confirm(`确定删除行动「${action.name}」？`)) return
  deleting.value = action.id
  try {
    await actionApi.remove(action.id)
    actions.value = actions.value.filter((item) => item.id !== action.id)
    toast.success(text('行动已删除'))
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
.execution-reconciliation{display:grid;gap:8px;flex-basis:100%;border:1px solid #f59e0b;border-radius:8px;padding:12px;}.execution-reconciliation label{display:grid;gap:4px;}.execution-reconciliation input,.execution-reconciliation textarea,.execution-reconciliation select{max-width:100%;}
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
