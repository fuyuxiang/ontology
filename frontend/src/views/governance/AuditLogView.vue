<template>
  <div class="audit-page">
    <!-- 顶部审计追溯告警条 -->
    <div class="audit-banner">
      <ExclamationCircleOutlined class="audit-banner__icon" />
      <span class="audit-banner__label">审计追溯:</span>
      <span class="audit-banner__desc">所有本体操作 · 策略执行 · 规则修改 · 审批记录 — 全程可追溯</span>
    </div>

    <!-- 工具条：搜索 + 操作筛选 + 视图切换 -->
    <div class="audit-toolbar">
      <a-input
        v-model:value="keyword"
        placeholder="搜索操作详情、目标、用户..."
        allow-clear
        class="audit-toolbar__search"
        @change="onKeywordChange"
        @press-enter="doSearch"
      >
        <template #prefix>
          <SearchOutlined style="color: #94a3b8" />
        </template>
      </a-input>

      <a-select
        v-model:value="actionFilter"
        class="audit-toolbar__select"
        @change="doSearch"
      >
        <a-select-option value="all">全部操作</a-select-option>
        <a-select-option v-for="opt in actionOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </a-select-option>
      </a-select>

      <a-select
        v-model:value="targetTypeFilter"
        placeholder="对象类型"
        allow-clear
        class="audit-toolbar__select"
        @change="doSearch"
      >
        <a-select-option value="entity">实体</a-select-option>
        <a-select-option value="relation">关系</a-select-option>
        <a-select-option value="rule">规则</a-select-option>
        <a-select-option value="action">动作</a-select-option>
        <a-select-option value="strategy">策略</a-select-option>
        <a-select-option value="attribute_mapping">属性映射</a-select-option>
      </a-select>

      <div class="audit-toolbar__spacer" />

      <a-segmented
        v-model:value="viewMode"
        :options="viewOptions"
      />
    </div>

    <PageState :loading="loading" :empty="!loading && filteredList.length === 0" empty-text="暂无匹配的审计记录">
      <!-- 时间线视图 -->
      <a-timeline v-if="viewMode === 'timeline'" class="audit-timeline">
        <a-timeline-item
          v-for="row in filteredList"
          :key="row.id"
          :color="row.status === 'failed' ? '#EF4444' : actionMeta(row.action).color"
        >
          <template v-if="row.status === 'failed'" #dot>
            <CloseCircleOutlined style="font-size: 14px; color: #EF4444" />
          </template>
          <div class="timeline-item">
            <div class="timeline-item__head">
              <span class="timeline-item__user">{{ row.user_name || '系统' }}</span>
              <span
                class="timeline-item__action"
                :style="{
                  background: actionMeta(row.action).color + '1F',
                  color: actionMeta(row.action).color,
                }"
              >
                {{ actionMeta(row.action).label }}
              </span>
              <span
                v-if="parseTarget(row)"
                class="timeline-item__target timeline-item__target--link"
                :title="row.target_id"
                @click.stop="openDetail(row)"
              >
                {{ parseTarget(row)!.label }}
              </span>
              <span v-else class="timeline-item__target" :title="row.target_id">
                {{ row.target_name || row.target_id }}
              </span>
              <span v-if="row.status === 'failed'" class="timeline-item__status-failed">失败</span>
              <span v-if="row.changes_json?.length" class="timeline-item__badge" @click.stop="openDetail(row)">
                {{ row.changes_json.length }} 字段变更
              </span>
            </div>
            <div v-if="row.details" class="timeline-item__detail">{{ row.details }}</div>
            <div class="timeline-item__time">{{ fmt(row.timestamp) }}</div>
          </div>
        </a-timeline-item>
      </a-timeline>

      <!-- 表格视图 -->
      <table v-else class="audit-table">
        <thead>
          <tr>
            <th style="width: 160px">时间</th>
            <th style="width: 100px">用户</th>
            <th style="width: 120px">操作类型</th>
            <th style="width: 100px">对象类型</th>
            <th>目标对象</th>
            <th style="min-width: 200px">详情</th>
            <th style="width: 80px; text-align: center">变更</th>
            <th style="width: 60px; text-align: center">状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in pagedList" :key="row.id" class="audit-row" @click="openDetail(row)">
            <td class="audit-time">{{ fmt(row.timestamp) }}</td>
            <td class="audit-user">{{ row.user_name || '系统' }}</td>
            <td>
              <span
                class="audit-action"
                :style="{
                  background: actionMeta(row.action).color + '1F',
                  color: actionMeta(row.action).color,
                }"
              >
                {{ actionMeta(row.action).label }}
              </span>
            </td>
            <td>
              <span class="audit-type">{{ typeLabel(row.target_type) }}</span>
            </td>
            <td class="audit-name">
              <span class="audit-name__text">{{ row.target_name || row.target_id }}</span>
              <code class="audit-name__id">{{ row.target_id }}</code>
            </td>
            <td class="audit-details">{{ row.details || '—' }}</td>
            <td style="text-align: center">
              <span v-if="row.changes_json?.length" class="audit-changes-badge">{{ row.changes_json.length }}</span>
              <span v-else class="audit-muted">—</span>
            </td>
            <td style="text-align: center">
              <CheckCircleFilled v-if="row.status !== 'failed'" style="color: #10b981; font-size: 14px" />
              <CloseCircleFilled v-else style="color: #EF4444; font-size: 14px" />
            </td>
          </tr>
        </tbody>
      </table>

      <div class="audit-pagination">
        <span class="audit-pagination__info">共 {{ total }} 条 · 第 {{ page }} / {{ totalPages }} 页</span>
        <div class="audit-pagination__btns">
          <a-button size="small" :disabled="page <= 1" @click="goPage(page - 1)">上一页</a-button>
          <a-button size="small" :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</a-button>
        </div>
      </div>
    </PageState>

    <!-- 详情抽屉 -->
    <a-drawer v-model:open="drawerOpen" title="变更详情" width="480" placement="right">
      <template v-if="selected">
        <div class="detail-meta">
          <div class="detail-meta__row"><span>时间</span><span>{{ fmt(selected.timestamp) }}</span></div>
          <div class="detail-meta__row">
            <span>操作</span>
            <span
              class="audit-action"
              :style="{
                background: actionMeta(selected.action).color + '1F',
                color: actionMeta(selected.action).color,
              }"
            >
              {{ actionMeta(selected.action).label }}
            </span>
          </div>
          <div class="detail-meta__row"><span>对象</span><span>{{ typeLabel(selected.target_type) }} · {{ selected.target_name || selected.target_id }}</span></div>
          <div class="detail-meta__row"><span>操作人</span><span>{{ selected.user_name || '系统' }}</span></div>
          <div class="detail-meta__row">
            <span>状态</span>
            <span :style="{ color: selected.status === 'failed' ? '#EF4444' : '#10b981', fontWeight: 600 }">
              {{ selected.status === 'failed' ? '失败' : '成功' }}
            </span>
          </div>
        </div>

        <div v-if="selected.details" class="detail-section">
          <h4>操作详情</h4>
          <p class="detail-section__text">{{ selected.details }}</p>
        </div>

        <div v-if="selected.changes_json?.length" class="detail-changes">
          <h4>字段变更</h4>
          <table class="changes-table">
            <thead><tr><th>字段</th><th>变更前</th><th>变更后</th></tr></thead>
            <tbody>
              <tr v-for="(c, i) in selected.changes_json" :key="i">
                <td><code>{{ c.field }}</code></td>
                <td class="changes-old">{{ formatVal(c.old) }}</td>
                <td class="changes-new">{{ formatVal(c.new) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="!selected.details" class="detail-empty">无字段变更记录</div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  ExclamationCircleOutlined,
  SearchOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  CloseCircleOutlined,
  UnorderedListOutlined,
  TableOutlined,
} from '@ant-design/icons-vue'
import { h } from 'vue'
import PageState from '../../components/common/PageState.vue'
import { get } from '../../api/client'

interface AuditChange { field: string; old: unknown; new: unknown }

interface AuditLogItem {
  id: string
  timestamp: string
  user_id: string | null
  user_name: string | null
  action: string
  target_type: string
  target_id: string
  target_name: string
  details: string | null
  status: string
  changes_json: AuditChange[] | null
}

const ACTION_META: Record<string, { label: string; color: string }> = {
  // html 项目原生操作类型
  execute_strategy: { label: '执行策略', color: '#10b981' },
  modify_rule:      { label: '修改规则', color: '#f59e0b' },
  approve_evolution:{ label: '审批演化', color: '#8B5CF6' },
  create_object:    { label: '创建对象', color: '#4a9eff' },
  export_report:    { label: '导出报告', color: '#94a3b8' },
  run_strategy:     { label: '运行管线', color: '#00d9ff' },
  edit_ontology:    { label: '编辑本体', color: '#f97316' },
  // 通用 CRUD
  create:           { label: '创建',     color: '#10b981' },
  update:           { label: '更新',     color: '#4a9eff' },
  delete:           { label: '删除',     color: '#EF4444' },
  execute:          { label: '执行',     color: '#10b981' },
  rollback:         { label: '回滚',     color: '#f59e0b' },
  evaluate:         { label: '评估',     color: '#8B5CF6' },
  login:            { label: '登录',     color: '#10b981' },
  login_failed:     { label: '登录失败', color: '#EF4444' },
}

const TYPE_LABEL: Record<string, string> = {
  entity: '实体',
  attribute: '属性',
  relation: '关系',
  rule: '规则',
  action: '动作',
  strategy: '策略',
  function: '函数',
  attribute_mapping: '属性映射',
  Evolution: '演化',
  BusinessRule: '业务规则',
}

const loading = ref(true)
const list = ref<AuditLogItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const keyword = ref('')
const actionFilter = ref<string>('all')
const targetTypeFilter = ref<string | undefined>(undefined)
const viewMode = ref<'timeline' | 'table'>('timeline')

const drawerOpen = ref(false)
const selected = ref<AuditLogItem | null>(null)

const viewOptions = [
  { value: 'timeline', label: '时间线', icon: () => h(UnorderedListOutlined) },
  { value: 'table',    label: '表格',   icon: () => h(TableOutlined) },
]

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const actionOptions = computed(() => {
  const set = new Set<string>()
  list.value.forEach(r => set.add(r.action))
  return Array.from(set).map(a => ({ value: a, label: actionMeta(a).label }))
})

const filteredList = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return list.value.filter(r => {
    if (actionFilter.value !== 'all' && r.action !== actionFilter.value) return false
    if (kw) {
      const blob = `${r.details ?? ''} ${r.target_name ?? ''} ${r.target_id ?? ''} ${r.user_name ?? ''}`.toLowerCase()
      if (!blob.includes(kw)) return false
    }
    return true
  })
})

const pagedList = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredList.value.slice(start, start + pageSize)
})

function actionMeta(action: string) {
  return ACTION_META[action] ?? { label: action, color: '#94a3b8' }
}

function typeLabel(t: string) {
  return TYPE_LABEL[t] ?? t
}

function fmt(d: string) {
  if (!d) return '-'
  const t = new Date(d)
  if (Number.isNaN(t.getTime())) return d.replace('T', ' ').slice(0, 19)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(t.getMonth() + 1)}-${pad(t.getDate())} ${pad(t.getHours())}:${pad(t.getMinutes())}:${pad(t.getSeconds())}`
}

function formatVal(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'object') {
    try { return JSON.stringify(v) } catch { return String(v) }
  }
  return String(v)
}

function parseTarget(r: AuditLogItem): { objectType: string; label: string } | null {
  if (!r.target_id) return null
  const parts = r.target_id.split('/')
  if (parts.length === 2) return { objectType: parts[0], label: r.target_name || parts[1] }
  if (r.target_id.startsWith('rule_') || r.target_id.startsWith('BR_')) return { objectType: 'BusinessRule', label: r.target_name || r.target_id }
  if (r.target_id.startsWith('EVO-')) return { objectType: 'Evolution', label: r.target_name || r.target_id }
  return null
}

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: 1, page_size: 100 }
    if (targetTypeFilter.value) params.target_type = targetTypeFilter.value
    const res = await get<{ items: AuditLogItem[]; total: number }>('/governance/audit-logs', { params })
    list.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function doSearch() {
  page.value = 1
  fetchList()
}

function onKeywordChange() {
  page.value = 1
}

function goPage(p: number) {
  page.value = p
}

function openDetail(row: AuditLogItem) {
  selected.value = row
  drawerOpen.value = true
}

onMounted(fetchList)
</script>

<style scoped>
.audit-page { padding: 24px; height: 100%; overflow: auto; }

/* 顶部告警条 */
.audit-banner {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 16px; padding: 8px 14px;
  border-radius: 8px;
  background: #FEF2F2; border: 1px solid #fecaca;
  font-size: 11px;
}
.audit-banner__icon { color: #DC2626; }
.audit-banner__label { color: #991B1B; font-weight: 600; }
.audit-banner__desc { color: #B91C1C; }

/* 工具条 */
.audit-toolbar {
  display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;
}
.audit-toolbar__search { width: 260px; border-radius: 8px; }
.audit-toolbar__select { width: 150px; }
.audit-toolbar__spacer { flex: 1; }

/* 时间线视图 */
.audit-timeline { padding-top: 8px; }
.timeline-item { padding-bottom: 4px; }
.timeline-item__head {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.timeline-item__user {
  font-size: 13px; font-weight: 600; color: var(--neutral-900, #111827);
}
.timeline-item__action {
  display: inline-block;
  font-size: 10px; line-height: 16px;
  border-radius: 4px; padding: 0 5px; margin: 0;
  font-weight: 500;
}
.timeline-item__target {
  font-size: 12px; color: var(--neutral-500, #6b7280);
}
.timeline-item__target--link {
  color: #4a9eff; cursor: pointer; text-decoration: underline dotted;
}
.timeline-item__status-failed {
  font-size: 10px; line-height: 16px; padding: 0 6px; border-radius: 4px;
  background: #FEE2E2; color: #DC2626; font-weight: 600;
}
.timeline-item__badge {
  font-size: 10px; line-height: 16px; padding: 0 6px; border-radius: 4px;
  background: rgba(74, 158, 255, 0.12); color: #4a9eff; cursor: pointer; font-weight: 600;
}
.timeline-item__detail {
  font-size: 12px; color: var(--neutral-500, #6b7280); margin-top: 4px; line-height: 1.5;
}
.timeline-item__time {
  font-size: 11px; color: var(--neutral-400, #9ca3af); margin-top: 2px;
}

/* 表格视图 */
.audit-table {
  width: 100%; border-collapse: collapse; font-size: var(--text-body-size, 13px);
  background: var(--neutral-0, #fff); border-radius: 8px; overflow: hidden;
}
.audit-table th {
  text-align: left; padding: 8px 12px;
  background: var(--neutral-50, #f9fafb);
  border-bottom: 2px solid var(--neutral-200, #e5e7eb);
  font-weight: 600; font-size: var(--text-caption-size, 12px);
  color: var(--neutral-600, #4b5563); white-space: nowrap;
}
.audit-table td {
  padding: 8px 12px; border-bottom: 1px solid var(--neutral-100, #f3f4f6);
  vertical-align: middle;
}
.audit-row { cursor: pointer; transition: background 0.1s; }
.audit-row:hover { background: var(--neutral-25, #fafbfc); }

.audit-time { font-size: 12px; color: var(--neutral-500, #6b7280); white-space: nowrap; font-family: ui-monospace, SFMono-Regular, monospace; }
.audit-action {
  display: inline-block; padding: 0 6px; border-radius: 4px;
  font-size: 11px; line-height: 18px; font-weight: 500;
}
.audit-type {
  font-size: 12px; color: var(--neutral-600, #4b5563);
  background: var(--neutral-100, #f3f4f6);
  padding: 2px 8px; border-radius: 4px;
}
.audit-name { display: flex; flex-direction: column; gap: 2px; }
.audit-name__text { font-size: 13px; color: var(--neutral-800, #1f2937); }
.audit-name__id { font-size: 11px; color: var(--neutral-400, #9ca3af); }
.audit-user { font-size: 13px; color: var(--neutral-600, #4b5563); font-weight: 500; }
.audit-details {
  font-size: 12px; color: var(--neutral-500, #6b7280);
  max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.audit-changes-badge {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%;
  background: rgba(74, 158, 255, 0.12); color: #4a9eff;
  font-size: 11px; font-weight: 700;
}
.audit-muted { color: var(--neutral-300, #d1d5db); }

/* 分页 */
.audit-pagination {
  display: flex; align-items: center; justify-content: space-between; margin-top: 12px;
}
.audit-pagination__info { font-size: 12px; color: var(--neutral-400, #9ca3af); }
.audit-pagination__btns { display: flex; gap: 8px; }

/* 详情抽屉 */
.detail-meta {
  display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px;
  padding: 16px; background: var(--neutral-50, #f9fafb); border-radius: 8px;
}
.detail-meta__row {
  display: flex; justify-content: space-between; font-size: 13px; align-items: center;
}
.detail-meta__row span:first-child { color: var(--neutral-500, #6b7280); }

.detail-section { margin-bottom: 16px; }
.detail-section h4 { font-size: 14px; font-weight: 600; color: var(--neutral-700, #374151); margin: 0 0 8px; }
.detail-section__text {
  font-size: 13px; line-height: 1.6; color: var(--neutral-700, #374151);
  background: var(--neutral-50, #f9fafb); padding: 10px 12px; border-radius: 6px; margin: 0;
}

.detail-changes h4 { font-size: 14px; font-weight: 600; color: var(--neutral-700, #374151); margin: 0 0 10px; }
.changes-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.changes-table th {
  text-align: left; padding: 6px 10px;
  background: var(--neutral-50, #f9fafb);
  border-bottom: 2px solid var(--neutral-200, #e5e7eb);
  font-size: 12px; color: var(--neutral-600, #4b5563);
}
.changes-table td { padding: 6px 10px; border-bottom: 1px solid var(--neutral-100, #f3f4f6); }
.changes-old { color: #EF4444; text-decoration: line-through; }
.changes-new { color: #10b981; }
.detail-empty { color: var(--neutral-400, #9ca3af); font-size: 13px; padding: 20px 0; text-align: center; }
</style>
