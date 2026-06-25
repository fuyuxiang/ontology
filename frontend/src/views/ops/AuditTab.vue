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
      <template v-if="items.length">
        <table class="audit-table">
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
              class="audit-table__row"
              @click="selectedItem = item; drawerOpen = true"
            >
              <td class="audit-table__mono">{{ formatTime(item.timestamp) }}</td>
              <td>
                <div class="audit-table__user">
                  <span class="audit-table__user-avatar">{{ (item.user_name || '系')[0] }}</span>
                  {{ item.user_name || '系统' }}
                </div>
              </td>
              <td>
                <span class="action-tag" :class="`action--${item.action}`">{{ actionLabel(item.action) }}</span>
              </td>
              <td class="audit-table__target">{{ item.target_name || item.target_id }}</td>
              <td class="audit-table__status">
                <span class="status-badge" :class="item.status === 'success' ? 'status-badge--ok' : 'status-badge--err'">
                  {{ item.status === 'success' ? '✓ 成功' : '✗ 失败' }}
                </span>
              </td>
              <td class="audit-table__detail-btn">
                <span class="audit-table__detail-icon">→</span>
              </td>
            </tr>
          </tbody>
        </table>
      </template>

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
      <span class="audit-tab__total">共 {{ total.toLocaleString() }} 条记录</span>
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
import { ref, onMounted } from 'vue'
import { RangePicker as ARangePicker, Select as ASelect, InputSearch as AInputSearch, Pagination as APagination } from 'ant-design-vue'
import { type Dayjs } from 'dayjs'
import { governanceApi, type AuditLogItem } from '../../api/governance'
import AuditDetailDrawer from './AuditDetailDrawer.vue'

const emit = defineEmits<{ 'count-change': [count: number] }>()

const items = ref<AuditLogItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const loading = ref(false)

const dateRange = ref<[Dayjs, Dayjs] | undefined>(undefined)
const filterAction = ref<string | undefined>(undefined)
const filterKeyword = ref('')

const actionOptions = ref<{ label: string; value: string }[]>([])

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
    emit('count-change', res.total)
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
  gap: 10px;
  align-items: center;
}

/* 表格 */
.audit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.audit-table th {
  text-align: left;
  padding: 12px 14px;
  border-bottom: 2px solid var(--neutral-200);
  background: var(--neutral-50);
  color: var(--neutral-500);
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.audit-table td {
  padding: 14px;
  border-bottom: 1px solid var(--neutral-100);
  color: var(--neutral-700);
}
.audit-table__row {
  cursor: pointer;
  transition: all 0.15s ease;
}
.audit-table__row:hover {
  background: var(--neutral-50);
}

.audit-table__mono {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--neutral-500);
}

.audit-table__user {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}
.audit-table__user-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--semantic-100, #e8f0fe);
  color: var(--semantic-600);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
}

.audit-table__target {
  color: var(--neutral-800);
  font-weight: 500;
}

/* 操作类型标签 */
.action-tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 12px;
  font-weight: 600;
  display: inline-block;
}
.action--create { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.action--update { background: rgba(92, 124, 250, 0.1); color: #5c7cfa; }
.action--delete { background: rgba(250, 82, 82, 0.1); color: #fa5252; }
.action--login  { background: rgba(51, 154, 240, 0.1); color: #339af0; }
.action--export { background: rgba(245, 159, 0, 0.1); color: #f59f00; }
.action--import { background: rgba(121, 80, 242, 0.1); color: #7950f2; }

/* 状态徽章 */
.status-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.status-badge--ok { color: var(--status-success, #10b981); background: rgba(16, 185, 129, 0.08); }
.status-badge--err { color: var(--status-error, #fa5252); background: rgba(250, 82, 82, 0.08); }

.audit-table__detail-btn {
  text-align: center;
}
.audit-table__detail-icon {
  color: var(--neutral-400);
  font-size: 16px;
  transition: transform 0.2s;
}
.audit-table__row:hover .audit-table__detail-icon {
  transform: translateX(4px);
  color: var(--semantic-600);
}

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
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.8;
}
.audit-tab__empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--neutral-700);
  margin-bottom: 6px;
}
.audit-tab__empty-desc {
  font-size: 13px;
  color: var(--neutral-400);
}

/* 骨架屏 */
.audit-tab__skeleton {
  display: flex;
  flex-direction: column;
}
.skeleton-row {
  display: flex;
  gap: 16px;
  padding: 14px;
  border-bottom: 1px solid var(--neutral-100);
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
