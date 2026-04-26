<template>
  <div class="todo-page">
    <div class="todo-header">
      <div class="todo-header__icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="3" stroke="#fff" stroke-width="2"/><path d="M7 12l3 3 7-7" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </div>
      <div>
        <h1 class="todo-header__title">我的待办</h1>
        <p class="todo-header__desc">宽带退单稽核审批 — 确认退单或驳回退单</p>
      </div>
    </div>

    <PageState :loading="loading" :empty="!loading && list.length === 0" empty-text="暂无待审批退单">

    <div class="todo-kpis">
      <div class="todo-kpi todo-kpi--warn"><div class="todo-kpi__val">{{ kpis.pending }}</div><div class="todo-kpi__lbl">待审批</div></div>
      <div class="todo-kpi"><div class="todo-kpi__val">{{ total }}</div><div class="todo-kpi__lbl">总计</div></div>
    </div>

    <div class="todo-toolbar">
      <select v-model="filters.status" class="todo-select" @change="doSearch">
        <option value="pending_confirm">待审批</option>
        <option value="">全部状态</option>
        <option value="rejected">已驳回</option>
        <option value="pending_feedback">已确认</option>
      </select>
      <button class="todo-btn todo-btn--primary" @click="doSearch">查询</button>
    </div>

    <div class="todo-table-wrap">
      <table class="todo-table">
        <thead>
          <tr>
            <th>案件ID</th>
            <th>客户</th>
            <th>退单原因</th>
            <th>本体稽核原因</th>
            <th>置信度</th>
            <th>状态</th>
            <th>退单时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in list" :key="row.action_id">
            <td><RouterLink :to="`/scene/broadband/${row.churn_id}`" class="todo-link">{{ row.churn_id }}</RouterLink></td>
            <td>{{ row.customer_name || '-' }}</td>
            <td>
              <span class="todo-tag">{{ row.churn_category_l1 || '-' }}</span>
            </td>
            <td>
              <span class="todo-tag todo-tag--audit">{{ row.root_cause_level_one || '-' }}</span>
            </td>
            <td>
              <span v-if="row.root_cause_confidence != null" class="todo-confidence" :class="row.root_cause_confidence >= 0.85 ? 'todo-confidence--high' : 'todo-confidence--low'">
                {{ (row.root_cause_confidence * 100).toFixed(0) }}%
              </span>
              <span v-else>-</span>
            </td>
            <td><span class="todo-status" :class="'todo-status--' + row.status">{{ statusLabel(row.status) }}</span></td>
            <td>{{ fmt(row.churn_time) }}</td>
            <td>
              <div class="todo-row-actions" v-if="row.status === 'pending_confirm'">
                <button class="todo-btn todo-btn--success todo-btn--sm" @click="doConfirm(row)">确认退单</button>
                <button class="todo-btn todo-btn--warning todo-btn--sm" @click="doReject(row)">驳回退单</button>
              </div>
              <span v-else class="todo-muted">{{ statusLabel(row.status) }}</span>
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

const filters = reactive({ status: 'pending_confirm' })

const kpis = computed(() => ({
  pending: list.value.filter(i => i.status === 'pending_confirm').length,
}))

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function statusLabel(s: string) {
  const m: Record<string, string> = { pending_confirm: '待审批', pending_feedback: '已确认', feedback_submitted: '已反馈', rejected: '已驳回' }
  return m[s] || s
}

function fmt(d: string | null) {
  if (!d) return '-'
  return d.replace('T', ' ').slice(0, 16)
}

async function fetchList() {
  loading.value = true
  try {
    const res = await broadbandApi.inbox({ page: page.value, page_size: pageSize, status: filters.status })
    list.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function doSearch() { page.value = 1; fetchList() }
function goPage(p: number) { page.value = p; fetchList() }

async function doConfirm(row: InboxItem) {
  await broadbandApi.approveAction(row.churn_id, row.action_id)
  fetchList()
}
async function doReject(row: InboxItem) {
  const reason = prompt('请输入驳回原因')
  if (reason === null) return
  await broadbandApi.rejectAction(row.churn_id, row.action_id, reason)
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
.todo-kpi__val { font-size: 28px; font-weight: 700; color: var(--neutral-900); }
.todo-kpi__lbl { font-size: var(--text-caption-size); color: var(--neutral-500); margin-top: 2px; }

.todo-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.todo-select {
  height: 32px; padding: 0 10px; border-radius: var(--radius-sm);
  border: 1px solid var(--neutral-300); background: var(--neutral-0);
  font-size: var(--text-code-size); color: var(--neutral-700);
}

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
.todo-table th, .todo-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--neutral-200); }
.todo-table th { background: var(--neutral-50); color: var(--neutral-600); font-weight: 600; position: sticky; top: 0; white-space: nowrap; }
.todo-table tbody tr:hover { background: var(--neutral-50); }
.todo-link { color: var(--semantic-500); text-decoration: none; font-size: var(--text-code-size); font-weight: 500; }
.todo-link:hover { text-decoration: underline; }
.todo-muted { color: var(--neutral-400); font-size: var(--text-code-size); }

.todo-reason { display: flex; flex-direction: column; gap: 4px; }
.todo-reason-text { font-size: 12px; color: var(--neutral-500); line-height: 1.4; max-width: 200px; }
.todo-tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 500; background: var(--status-warning-bg); color: var(--kinetic-700); width: fit-content; }
.todo-tag--audit { background: var(--status-info-bg); color: var(--status-info); }

.todo-confidence { font-weight: 600; font-size: var(--text-code-size); }
.todo-confidence--high { color: var(--status-success); }
.todo-confidence--low { color: var(--status-warning); }

.todo-status { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 500; }
.todo-status--pending_confirm { background: var(--status-warning-bg); color: var(--kinetic-700); }
.todo-status--pending_feedback { background: var(--status-success-bg); color: var(--status-success); }
.todo-status--feedback_submitted { background: var(--status-success-bg); color: var(--status-success); }
.todo-status--rejected { background: var(--status-error-bg); color: var(--status-error); }

.todo-row-actions { display: flex; gap: 6px; }

.todo-pagination { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; padding: 0 4px; }
.todo-pagination__info { font-size: var(--text-code-size); color: var(--neutral-500); }
.todo-pagination__btns { display: flex; align-items: center; gap: 8px; }
.todo-pagination__cur { font-size: var(--text-code-size); color: var(--neutral-600); font-weight: 500; }
</style>
