<template>
  <div class="audit-tab">
    <!-- 筛选工具栏 -->
    <div class="audit-tab__toolbar">
      <div class="audit-tab__filters">
        <a-range-picker
          v-model:value="dateRange"
          :placeholder="['开始时间', '结束时间']"
          format="YYYY-MM-DD"
          style="width: 260px"
          allow-clear
          @change="handleSearch"
        />
        <a-select
          v-model:value="filterAction"
          placeholder="全部操作类型"
          allow-clear
          style="width: 140px"
          :options="actionOptions"
          @change="handleSearch"
        />
        <a-input-search
          v-model:value="filterKeyword"
          placeholder="搜索目标对象或操作人"
          style="width: 240px"
          allow-clear
          @search="handleSearch"
          @change="(e: Event) => { if (!(e.target as HTMLInputElement).value) handleSearch() }"
        />
      </div>
    </div>

    <!-- 审计表格 -->
    <div class="audit-tab__table-wrap">
      <table class="data-table" v-if="items.length">
        <thead>
          <tr>
            <th style="width: 160px">时间</th>
            <th style="width: 100px">操作人</th>
            <th style="width: 100px">操作类型</th>
            <th>目标对象</th>
            <th style="width: 100px">结果</th>
            <th style="width: 60px">详情</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in items"
            :key="item.id"
            class="data-table__row--clickable"
            @click="selectedItem = item; drawerOpen = true"
          >
            <td class="audit-tab__mono">{{ formatTime(item.timestamp) }}</td>
            <td>{{ item.user_name || '系统' }}</td>
            <td>
              <span class="action-tag" :class="`action--${item.action}`">{{ actionLabel(item.action) }}</span>
            </td>
            <td class="audit-tab__target">{{ item.target_name || item.target_id }}</td>
            <td class="audit-tab__status">
              <span :class="item.status === 'success' ? 'status--success' : 'status--fail'">
                {{ item.status === 'success' ? '✓ 成功' : '✗ 失败' }}
              </span>
            </td>
            <td class="audit-tab__detail-btn">
              <span class="audit-tab__detail-icon">→</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 空状态 -->
      <div v-else-if="!loading" class="audit-tab__empty">
        <div class="audit-tab__empty-icon">📋</div>
        <p class="audit-tab__empty-title">暂无审计记录</p>
        <p class="audit-tab__empty-desc">系统操作将自动记录在此</p>
      </div>

      <!-- 骨架屏 -->
      <div v-if="loading" class="audit-tab__skeleton">
        <div v-for="i in 5" :key="i" class="skeleton-row">
          <div class="skeleton skeleton--w160"></div>
          <div class="skeleton skeleton--w80"></div>
          <div class="skeleton skeleton--w80"></div>
          <div class="skeleton skeleton--flex"></div>
          <div class="skeleton skeleton--w60"></div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="audit-tab__pagination" v-if="total > 0">
      <span class="audit-tab__total">共 {{ total.toLocaleString() }} 条</span>
      <a-pagination
        v-model:current="currentPage"
        :page-size="pageSize"
        :total="total"
        :show-size-changer="false"
        size="small"
        @change="fetchData"
      />
    </div>

    <!-- 详情抽屉 -->
    <AuditDetailDrawer v-model:open="drawerOpen" :item="selectedItem" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { RangePicker as ARangePicker, Select as ASelect, InputSearch as AInputSearch, Pagination as APagination } from 'ant-design-vue'
import dayjs, { type Dayjs } from 'dayjs'
import { governanceApi, type AuditLogItem } from '../../api/governance'
import AuditDetailDrawer from './AuditDetailDrawer.vue'

const items = ref<AuditLogItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const loading = ref(false)

// 筛选条件
const dateRange = ref<[Dayjs, Dayjs] | null>(null)
const filterAction = ref<string | undefined>(undefined)
const filterKeyword = ref('')

// 操作类型选项
const actionOptions = ref<{ label: string; value: string }[]>([])

// 详情抽屉
const drawerOpen = ref(false)
const selectedItem = ref<AuditLogItem | null>(null)

const actionMap: Record<string, string> = {
  create: '创建', update: '修改', delete: '删除',
  login: '登录', export: '导出', import: '导入',
}

function actionLabel(action: string) {
  return actionMap[action] || action
}

function formatTime(ts: string) {
  return ts ? ts.replace('T', ' ').slice(0, 19) : '-'
}

async function fetchActions() {
  try {
    const actions = await governanceApi.listAuditActions()
    actionOptions.value = actions.map(a => ({ label: actionLabel(a), value: a }))
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (filterAction.value) params.action = filterAction.value
    if (filterKeyword.value) params.keyword = filterKeyword.value
    if (dateRange.value) {
      params.date_from = dateRange.value[0].format('YYYY-MM-DD')
      params.date_to = dateRange.value[1].format('YYYY-MM-DD')
    }
    const res = await governanceApi.listAuditLogs(params)
    items.value = res.items
    total.value = res.total
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchData()
}

onMounted(() => {
  fetchActions()
  fetchData()
})
</script>

<style scoped>
.audit-tab__toolbar {
  margin-bottom: 16px;
}
.audit-tab__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

/* 表格 */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid var(--neutral-200);
  background: var(--neutral-50);
  color: var(--neutral-500);
  font-weight: 600;
  font-size: 12px;
}
.data-table td {
  padding: 12px;
  border-bottom: 1px solid var(--neutral-100);
  color: var(--neutral-700);
}
.data-table__row--clickable {
  cursor: pointer;
  transition: background 0.15s;
}
.data-table__row--clickable:hover {
  background: var(--neutral-50);
}

.audit-tab__mono {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--neutral-500);
}
.audit-tab__target {
  color: var(--neutral-800);
}
.audit-tab__status {
  text-align: center;
}
.status--success { color: var(--status-success, #10b981); font-weight: 500; }
.status--fail { color: var(--status-error, #fa5252); font-weight: 500; }
.audit-tab__detail-btn {
  text-align: center;
}
.audit-tab__detail-icon {
  color: var(--neutral-400);
  font-size: 16px;
}

/* 操作类型标签 */
.action-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.action--create { background: #e6fcf5; color: #10b981; }
.action--update { background: #edf2ff; color: #5c7cfa; }
.action--delete { background: #fff5f5; color: #fa5252; }
.action--login  { background: #e7f5ff; color: #339af0; }
.action--export { background: #fff9db; color: #f59f00; }
.action--import { background: #f3f0ff; color: #7950f2; }

/* 分页 */
.audit-tab__pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--neutral-100);
}
.audit-tab__total {
  font-size: 13px;
  color: var(--neutral-500);
}

/* 空状态 */
.audit-tab__empty {
  text-align: center;
  padding: 60px 20px;
}
.audit-tab__empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}
.audit-tab__empty-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--neutral-600);
  margin-bottom: 4px;
}
.audit-tab__empty-desc {
  font-size: 13px;
  color: var(--neutral-400);
}

/* 骨架屏 */
.audit-tab__skeleton {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.skeleton-row {
  display: flex;
  gap: 16px;
  padding: 12px 0;
}
.skeleton {
  height: 16px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--neutral-100) 25%, var(--neutral-50) 50%, var(--neutral-100) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skeleton--w160 { width: 160px; }
.skeleton--w80 { width: 80px; }
.skeleton--w60 { width: 60px; }
.skeleton--flex { flex: 1; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
</style>
