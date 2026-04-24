<template>
  <div class="todo-page">
    <div class="todo-header">
      <div class="todo-header__icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="3" stroke="#fff" stroke-width="2"/><path d="M7 12l3 3 7-7" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </div>
      <div>
        <h1 class="todo-header__title">我的待办</h1>
        <p class="todo-header__desc">审批稽核动作：回访核实、资源派修、工程师培训、营销外呼等</p>
      </div>
    </div>

    <PageState :loading="loading" :empty="!loading && list.length === 0" empty-text="暂无待审批动作">

    <div class="todo-kpis">
      <div class="todo-kpi todo-kpi--warn"><div class="todo-kpi__val">{{ kpis.pending }}</div><div class="todo-kpi__lbl">待审批</div></div>
      <div class="todo-kpi todo-kpi--error"><div class="todo-kpi__val">{{ kpis.high }}</div><div class="todo-kpi__lbl">高优先级</div></div>
      <div class="todo-kpi"><div class="todo-kpi__val">{{ total }}</div><div class="todo-kpi__lbl">总计</div></div>
    </div>

    <div class="todo-toolbar">
      <select v-model="filters.action_type" class="todo-select" @change="doSearch">
        <option value="">全部类型</option>
        <option v-for="a in actionTypes" :key="a.code" :value="a.code">{{ a.label }}</option>
      </select>
      <select v-model="filters.priority" class="todo-select" @change="doSearch">
        <option value="">全部优先级</option>
        <option value="high">高</option>
        <option value="medium">中</option>
        <option value="low">低</option>
      </select>
      <select v-model="filters.status" class="todo-select" @change="doSearch">
        <option value="pending_approval">待审批</option>
        <option value="">全部状态</option>
        <option value="approved">已审批</option>
        <option value="rejected">已驳回</option>
      </select>
      <input v-model="filters.assignee" class="todo-input" placeholder="指派人..." @keyup.enter="doSearch" />
      <button class="todo-btn todo-btn--primary" @click="doSearch">查询</button>
      <div class="todo-toolbar__spacer"></div>
      <button class="todo-btn todo-btn--success" :disabled="!selected.length" @click="doBatchApprove">批量审批 ({{ selected.length }})</button>
    </div>

    <div class="todo-table-wrap">
      <table class="todo-table">
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
            <td class="todo-mono">{{ row.action_id }}</td>
            <td><RouterLink :to="`/scene/broadband/${row.churn_id}`" class="todo-link">{{ row.churn_id }}</RouterLink></td>
            <td>{{ row.action_name }}</td>
            <td><span class="todo-priority" :class="'todo-priority--' + row.priority">{{ row.priority }}</span></td>
            <td><span class="todo-status" :class="'todo-status--' + row.status">{{ statusLabel(row.status) }}</span></td>
            <td>{{ row.customer_name || '-' }}</td>
            <td><span v-if="row.root_cause_level_one" class="todo-cause">{{ row.root_cause_level_one }}</span><span v-else>-</span></td>
            <td>{{ row.assignee || '-' }}</td>
            <td>{{ fmt(row.created_at) }}</td>
            <td>
              <div class="todo-row-actions" v-if="row.status === 'pending_approval'">
                <button class="todo-btn todo-btn--success todo-btn--sm" @click="doApprove(row)">通过</button>
                <button class="todo-btn todo-btn--warning todo-btn--sm" @click="doReject(row)">驳回</button>
              </div>
              <span v-else class="todo-muted">-</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="todo-pagination">
      <span class="todo-pagination__info">共 {{ total }} 条</span>
      <div class="todo-pagination__btns">
        <button class="todo-btn todo-btn--sm" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <span class="todo-pagination__cur">{{ page }} / {{ totalPages }}</span>
        <button class="todo-btn todo-btn--sm" :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
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

const filters = reactive({ action_type: '', priority: '', assignee: '', status: 'pending_approval' })

const kpis = computed(() => ({
  pending: list.value.filter(i => i.status === 'pending_approval').length,
  high: list.value.filter(i => i.priority === 'high' && i.status === 'pending_approval').length,
}))

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const allSelected = computed(() => list.value.length > 0 && selected.value.length === list.value.length)

const actionTypes = [
  { code: 'resource_check', label: '资源核实' },
  { code: 'followup_call', label: '回访核实' },
  { code: 'secondary_marketing', label: '二次营销' },
  { code: 'engineer_training', label: '工程师培训' },
  { code: 'manual_review', label: '人工审核' },
]

function statusLabel(s: string) {
  const m: Record<string, string> = { pending_approval: '待审批', approved: '已审批', rejected: '已驳回', executing: '执行中', completed: '已完成', failed: '失败' }
  return m[s] || s
}

function fmt(d: string | null) {
  if (!d) return '-'
  return d.replace('T', ' ').slice(0, 16)
}

async function fetchList() {
  loading.value = true
  try {
    const res = await broadbandApi.inbox({ page: page.value, page_size: pageSize, ...filters })
    list.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function doSearch() { page.value = 1; selected.value = []; fetchList() }
function goPage(p: number) { page.value = p; selected.value = []; fetchList() }
function toggleAll() { selected.value = allSelected.value ? [] : list.value.map(i => i.action_id) }
function toggleSelect(id: string) {
  const idx = selected.value.indexOf(id)
  idx >= 0 ? selected.value.splice(idx, 1) : selected.value.push(id)
}

async function doApprove(row: InboxItem) {
  await broadbandApi.approveAction(row.churn_id, row.action_id)
  fetchList()
}
async function doReject(row: InboxItem) {
  const reason = prompt('驳回原因')
  if (reason === null) return
  await broadbandApi.rejectAction(row.churn_id, row.action_id, reason)
  fetchList()
}
async function doBatchApprove() {
  await broadbandApi.batchApprove(selected.value)
  selected.value = []
  fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.todo-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
.todo-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
.todo-header__icon {
  width: 44px; height: 44px; border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--semantic-500), var(--semantic-700));
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.todo-header__title { font-size: var(--text-h2-size); font-weight: 700; color: var(--neutral-900); margin: 0; }
.todo-header__desc { font-size: var(--text-caption-size); color: var(--neutral-500); margin: 2px 0 0; }

.todo-kpis { display: flex; gap: 16px; margin-bottom: 20px; }
.todo-kpi {
  flex: 1; padding: 16px 20px; border-radius: var(--radius-md);
  background: var(--neutral-50); border: 1px solid var(--neutral-200);
}
.todo-kpi--warn { border-color: var(--status-warning); background: var(--status-warning-bg); }
.todo-kpi--error { border-color: var(--status-error); background: var(--status-error-bg); }
.todo-kpi__val { font-size: 28px; font-weight: 700; color: var(--neutral-900); }
.todo-kpi__lbl { font-size: var(--text-caption-size); color: var(--neutral-500); margin-top: 2px; }

.todo-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.todo-toolbar__spacer { flex: 1; }
.todo-select, .todo-input {
  height: 32px; padding: 0 10px; border-radius: var(--radius-sm);
  border: 1px solid var(--neutral-300); background: var(--neutral-0);
  font-size: var(--text-code-size); color: var(--neutral-700);
}
.todo-input { width: 120px; }

.todo-btn {
  height: 32px; padding: 0 14px; border-radius: var(--radius-sm);
  border: 1px solid var(--neutral-300); background: var(--neutral-0);
  font-size: var(--text-code-size); color: var(--neutral-700); cursor: pointer;
  transition: all var(--transition-fast);
}
.todo-btn:hover { background: var(--neutral-100); }
.todo-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.todo-btn--primary { background: var(--semantic-500); color: #fff; border-color: var(--semantic-500); }
.todo-btn--primary:hover { background: var(--semantic-600); }
.todo-btn--success { background: var(--status-success); color: #fff; border-color: var(--status-success); }
.todo-btn--success:hover { opacity: 0.9; }
.todo-btn--warning { background: var(--status-warning); color: #fff; border-color: var(--status-warning); }
.todo-btn--sm { height: 26px; padding: 0 10px; font-size: 12px; }

.todo-table-wrap { overflow-x: auto; }
.todo-table { width: 100%; border-collapse: collapse; font-size: var(--text-code-size); }
.todo-table th, .todo-table td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--neutral-200); white-space: nowrap; }
.todo-table th { background: var(--neutral-50); color: var(--neutral-600); font-weight: 600; position: sticky; top: 0; }
.todo-table tbody tr:hover { background: var(--neutral-50); }
.todo-mono { font-family: var(--font-mono); font-size: 12px; color: var(--neutral-500); }
.todo-link { color: var(--semantic-500); text-decoration: none; font-size: var(--text-code-size); font-weight: 500; }
.todo-link:hover { text-decoration: underline; }
.todo-muted { color: var(--neutral-400); font-size: var(--text-code-size); }

.todo-priority { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 500; }
.todo-priority--high { background: var(--status-error-bg); color: var(--status-error); }
.todo-priority--medium { background: var(--status-warning-bg); color: var(--kinetic-700); }
.todo-priority--low { background: var(--neutral-100); color: var(--neutral-600); }

.todo-status { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 500; }
.todo-status--pending_approval { background: var(--status-warning-bg); color: var(--kinetic-700); }
.todo-status--approved { background: var(--status-success-bg); color: var(--status-success); }
.todo-status--rejected { background: var(--status-error-bg); color: var(--status-error); }
.todo-status--executing { background: var(--status-info-bg); color: var(--status-info); }
.todo-status--completed { background: var(--status-success-bg); color: var(--status-success); }
.todo-status--failed { background: var(--status-error-bg); color: var(--status-error); }

.todo-cause { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); background: var(--neutral-100); color: var(--neutral-600); }
.todo-row-actions { display: flex; gap: 6px; }

.todo-pagination { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; padding: 0 4px; }
.todo-pagination__info { font-size: var(--text-code-size); color: var(--neutral-500); }
.todo-pagination__btns { display: flex; align-items: center; gap: 8px; }
.todo-pagination__cur { font-size: var(--text-code-size); color: var(--neutral-600); font-weight: 500; }
</style>
