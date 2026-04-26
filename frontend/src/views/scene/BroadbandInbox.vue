<template>
  <div class="ib-page">
    <div class="ib-header">
      <div class="ib-header__icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M3 8l9-5 9 5v8l-9 5-9-5V8z" stroke="#fff" stroke-width="2" stroke-linejoin="round"/><path d="M3 8l9 5 9-5" stroke="#fff" stroke-width="2" stroke-linejoin="round"/><path d="M12 13v9" stroke="#fff" stroke-width="2"/></svg>
      </div>
      <div>
        <h1 class="ib-header__title">智能收件箱</h1>
        <p class="ib-header__desc">审批稽核动作：回访核实、资源派修、工程师培训、营销外呼等</p>
      </div>
      <RouterLink to="/scene/broadband" class="ib-header__back">← 返回列表</RouterLink>
    </div>

    <PageState :loading="loading" :empty="!loading && list.length === 0" empty-text="暂无待审批动作">

    <div class="ib-kpis">
      <div class="ib-kpi ib-kpi--warn"><div class="ib-kpi__val">{{ kpis.pending }}</div><div class="ib-kpi__lbl">待审批</div></div>
      <div class="ib-kpi ib-kpi--error"><div class="ib-kpi__val">{{ kpis.high }}</div><div class="ib-kpi__lbl">高优先级</div></div>
      <div class="ib-kpi"><div class="ib-kpi__val">{{ total }}</div><div class="ib-kpi__lbl">总计</div></div>
    </div>

    <div class="ib-toolbar">
      <select v-model="filters.action_type" class="ib-select" @change="doSearch">
        <option value="">全部类型</option>
        <option v-for="a in actionTypes" :key="a.code" :value="a.code">{{ a.label }}</option>
      </select>
      <select v-model="filters.priority" class="ib-select" @change="doSearch">
        <option value="">全部优先级</option>
        <option value="high">高</option>
        <option value="medium">中</option>
        <option value="low">低</option>
      </select>
      <select v-model="filters.status" class="ib-select" @change="doSearch">
        <option value="pending_confirm">待确认</option>
        <option value="">全部状态</option>
        <option value="pending_feedback">待反馈</option>
        <option value="feedback_submitted">已反馈</option>
        <option value="rejected">已驳回</option>
      </select>
      <input v-model="filters.assignee" class="ib-input" placeholder="指派人..." @keyup.enter="doSearch" />
      <button class="ib-btn ib-btn--primary" @click="doSearch">查询</button>
      <div class="ib-toolbar__spacer"></div>
      <button class="ib-btn ib-btn--success" :disabled="!selected.length" @click="doBatchApprove">批量审批 ({{ selected.length }})</button>
    </div>

    <!-- PLACEHOLDER_TABLE -->

    <div class="ib-table-wrap">
      <table class="ib-table">
        <thead>
          <tr>
            <th><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
            <th>动作ID</th>
            <th>案件ID</th>
            <th>动作名称</th>
            <th>优先级</th>
            <th>状态</th>
            <th>客户</th>
            <th>根因</th>
            <th>指派人</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in list" :key="row.action_id">
            <td><input type="checkbox" :checked="selected.includes(row.action_id)" @change="toggleSelect(row.action_id)" /></td>
            <td class="ib-mono">{{ row.action_id }}</td>
            <td><RouterLink :to="`/scene/broadband/${row.churn_id}`" class="ib-link">{{ row.churn_id }}</RouterLink></td>
            <td>{{ row.action_name }}</td>
            <td><span class="ib-priority" :class="'ib-priority--' + row.priority">{{ row.priority }}</span></td>
            <td><span class="ib-status" :class="'ib-status--' + row.status">{{ statusLabel(row.status) }}</span></td>
            <td>{{ row.customer_name || '-' }}</td>
            <td><span v-if="row.root_cause_level_one" class="ib-cause">{{ row.root_cause_level_one }}</span><span v-else>-</span></td>
            <td>{{ row.assignee || '-' }}</td>
            <td>{{ fmt(row.created_at) }}</td>
            <td>
              <div class="ib-row-actions" v-if="row.status === 'pending_confirm'">
                <button class="ib-btn ib-btn--success ib-btn--sm" @click="doApprove(row)">确认</button>
                <button class="ib-btn ib-btn--warning ib-btn--sm" @click="doReject(row)">驳回</button>
              </div>
              <span v-else class="ib-muted">{{ statusLabel(row.status) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="ib-pagination">
      <span class="ib-pagination__info">共 {{ total }} 条</span>
      <div class="ib-pagination__btns">
        <button class="ib-btn ib-btn--sm" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <span class="ib-pagination__cur">{{ page }} / {{ totalPages }}</span>
        <button class="ib-btn ib-btn--sm" :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
      </div>
    </div>

    </PageState>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import PageState from '../../components/common/PageState.vue'
import { broadbandApi } from '../../api/broadband'
import type { InboxItem } from '../../api/broadband'

const loading = ref(true)
const list = ref<InboxItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const selected = ref<string[]>([])

const filters = reactive({ action_type: '', priority: '', assignee: '', status: 'pending_confirm' })

const kpis = computed(() => ({
  pending: list.value.filter(i => i.status === 'pending_confirm').length,
  high: list.value.filter(i => i.priority === 'high' && i.status === 'pending_confirm').length,
}))

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const allSelected = computed(() => list.value.length > 0 && list.value.filter(r => r.status === 'pending_confirm').every(r => selected.value.includes(r.action_id)))

const actionTypes = [
  { code: 'resource_check', label: '资源核实' },
  { code: 'followup_call', label: '回访核实' },
  { code: 'secondary_marketing', label: '二次营销' },
]

function fmt(t: string | null) { return t ? t.replace('T', ' ').slice(0, 16) : '-' }
function statusLabel(s: string) {
  const m: Record<string, string> = { pending_confirm: '待确认', pending_feedback: '待反馈', feedback_submitted: '已反馈', rejected: '已驳回' }
  return m[s] || s
}
function toggleSelect(id: string) {
  const idx = selected.value.indexOf(id)
  if (idx >= 0) selected.value.splice(idx, 1)
  else selected.value.push(id)
}
function toggleAll() {
  const pending = list.value.filter(r => r.status === 'pending_confirm').map(r => r.action_id)
  if (allSelected.value) selected.value = []
  else selected.value = [...pending]
}

async function fetchData() {
  loading.value = true
  try {
    const res = await broadbandApi.inbox({ page: page.value, page_size: pageSize, ...filters })
    list.value = res.items
    total.value = res.total
  } finally { loading.value = false }
}
function doSearch() { page.value = 1; selected.value = []; fetchData() }
function goPage(p: number) { page.value = p; selected.value = []; fetchData() }

async function doApprove(row: InboxItem) {
  await broadbandApi.approveAction(row.churn_id, row.action_id)
  fetchData()
}
async function doReject(row: InboxItem) {
  const reason = prompt('请输入驳回原因:')
  if (reason === null) return
  await broadbandApi.rejectAction(row.churn_id, row.action_id, reason)
  fetchData()
}
async function doBatchApprove() {
  if (!selected.value.length) return
  await broadbandApi.batchApprove(selected.value)
  selected.value = []
  fetchData()
}

onMounted(fetchData)
</script>

<!-- PLACEHOLDER_INBOX_STYLE -->

<style scoped>
.ib-page { padding: 24px; }
.ib-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; padding: 20px 24px; background: linear-gradient(135deg, var(--semantic-600), var(--semantic-500)); border-radius: var(--radius-xl); color: var(--neutral-0); }
.ib-header__icon { width: 40px; height: 40px; border-radius: var(--radius-lg); background: rgba(255,255,255,0.15); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ib-header__title { font-size: var(--text-h2-size); font-weight: 700; margin: 0; }
.ib-header__desc { font-size: var(--text-code-size); opacity: 0.8; margin: 2px 0 0; }
.ib-header__back { margin-left: auto; color: rgba(255,255,255,0.8); text-decoration: none; font-size: var(--text-body-size); }
.ib-header__back:hover { color: var(--neutral-0); }

.ib-kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.ib-kpi { padding: 16px; background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); text-align: center; }
.ib-kpi--warn { border-color: var(--kinetic-500); }
.ib-kpi--error { border-color: var(--status-error); }
.ib-kpi__val { font-size: var(--text-h1-size); font-weight: 700; color: var(--neutral-900); }
.ib-kpi--warn .ib-kpi__val { color: var(--kinetic-500); }
.ib-kpi--error .ib-kpi__val { color: var(--status-error); }
.ib-kpi__lbl { font-size: var(--text-code-size); color: var(--neutral-500); margin-top: 4px; }

.ib-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.ib-toolbar__spacer { flex: 1; }
.ib-select { height: 34px; padding: 0 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-body-size); background: var(--neutral-0); color: var(--neutral-700); min-width: 120px; }
.ib-input { height: 34px; padding: 0 10px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-body-size); background: var(--neutral-0); color: var(--neutral-700); min-width: 140px; }
.ib-btn { height: 34px; padding: 0 14px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: var(--text-body-size); font-weight: 500; cursor: pointer; background: var(--neutral-0); color: var(--neutral-700); transition: var(--transition-fast); }
.ib-btn:hover { background: var(--neutral-50); }
.ib-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ib-btn--primary { background: var(--semantic-500); color: var(--neutral-0); border-color: var(--semantic-500); }
.ib-btn--primary:hover { background: var(--semantic-600); }
.ib-btn--success { background: var(--status-success); color: var(--neutral-0); border-color: var(--status-success); }
.ib-btn--success:hover { opacity: 0.9; }
.ib-btn--warning { background: var(--kinetic-500); color: var(--neutral-0); border-color: var(--kinetic-500); }
.ib-btn--warning:hover { opacity: 0.9; }
.ib-btn--sm { height: 28px; padding: 0 10px; font-size: var(--text-code-size); }

.ib-table-wrap { overflow-x: auto; background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-lg); }
.ib-table { width: 100%; border-collapse: collapse; font-size: var(--text-body-size); }
.ib-table th { text-align: left; padding: 10px 12px; font-size: var(--text-caption-size); font-weight: 600; color: var(--neutral-500); background: var(--neutral-50); border-bottom: 1px solid var(--neutral-200); white-space: nowrap; }
.ib-table td { padding: 10px 12px; border-bottom: 1px solid var(--neutral-50); color: var(--neutral-700); }
.ib-table tr:hover td { background: var(--semantic-50); }
.ib-mono { font-family: var(--font-mono); font-size: var(--text-code-size); }
.ib-link { color: var(--semantic-500); text-decoration: none; font-size: var(--text-code-size); font-weight: 500; }
.ib-link:hover { text-decoration: underline; }
.ib-muted { color: var(--neutral-400); font-size: var(--text-code-size); }

.ib-priority { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 500; }
.ib-priority--high { background: var(--status-error-bg); color: var(--status-error); }
.ib-priority--medium { background: var(--status-warning-bg); color: var(--kinetic-700); }
.ib-priority--low { background: var(--neutral-100); color: var(--neutral-600); }

.ib-status { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 500; }
.ib-status--pending_confirm { background: var(--status-warning-bg); color: var(--kinetic-700); }
.ib-status--pending_feedback { background: var(--status-info-bg); color: var(--status-info); }
.ib-status--feedback_submitted { background: var(--status-success-bg); color: var(--status-success); }
.ib-status--rejected { background: var(--status-error-bg); color: var(--status-error); }

.ib-cause { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); background: var(--neutral-100); color: var(--neutral-600); }
.ib-row-actions { display: flex; gap: 6px; }

.ib-pagination { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; padding: 0 4px; }
.ib-pagination__info { font-size: var(--text-code-size); color: var(--neutral-500); }
.ib-pagination__btns { display: flex; align-items: center; gap: 8px; }
.ib-pagination__cur { font-size: var(--text-code-size); color: var(--neutral-600); font-weight: 500; }
</style>
