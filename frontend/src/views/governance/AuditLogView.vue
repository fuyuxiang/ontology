<template>
  <div class="audit-page">
    <div class="audit-header">
      <h2 class="audit-header__title">审计日志</h2>
      <p class="audit-header__desc">记录所有实体、关系、规则的创建/修改/删除操作</p>
    </div>

    <!-- 过滤栏 -->
    <div class="audit-filters">
      <a-select v-model:value="filters.action" placeholder="操作类型" allow-clear size="small" style="width:120px" @change="doSearch">
        <a-select-option value="create">创建</a-select-option>
        <a-select-option value="update">更新</a-select-option>
        <a-select-option value="delete">删除</a-select-option>
      </a-select>
      <a-select v-model:value="filters.target_type" placeholder="对象类型" allow-clear size="small" style="width:140px" @change="doSearch">
        <a-select-option value="entity">实体</a-select-option>
        <a-select-option value="relation">关系</a-select-option>
        <a-select-option value="rule">规则</a-select-option>
        <a-select-option value="attribute_mapping">属性映射</a-select-option>
      </a-select>
      <a-input v-model:value="filters.user_name" placeholder="操作人" allow-clear size="small" style="width:120px" @press-enter="doSearch" />
      <a-button size="small" type="primary" @click="doSearch">查询</a-button>
      <a-button size="small" @click="resetFilters">重置</a-button>
      <span class="audit-filters__total">共 {{ total }} 条记录</span>
    </div>

    <PageState :loading="loading" :empty="!loading && list.length === 0" empty-text="暂无审计日志">
      <table class="audit-table">
        <thead>
          <tr>
            <th style="width:160px">时间</th>
            <th style="width:80px">操作</th>
            <th style="width:100px">对象类型</th>
            <th>对象名称</th>
            <th style="width:100px">操作人</th>
            <th style="width:60px">变更</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in list" :key="row.id" class="audit-row" @click="openDetail(row)">
            <td class="audit-time">{{ fmt(row.timestamp) }}</td>
            <td>
              <span class="audit-action" :class="`audit-action--${row.action}`">{{ actionLabel(row.action) }}</span>
            </td>
            <td>
              <span class="audit-type">{{ typeLabel(row.target_type) }}</span>
            </td>
            <td class="audit-name">
              <span class="audit-name__text">{{ row.target_name || row.target_id }}</span>
              <code class="audit-name__id">{{ row.target_id }}</code>
            </td>
            <td class="audit-user">{{ row.user_name || '-' }}</td>
            <td>
              <span v-if="row.changes_json?.length" class="audit-changes-badge">{{ row.changes_json.length }}</span>
              <span v-else class="audit-muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="audit-pagination">
        <span class="audit-pagination__info">第 {{ page }} / {{ totalPages }} 页</span>
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
          <div class="detail-meta__row"><span>操作</span><span class="audit-action" :class="`audit-action--${selected.action}`">{{ actionLabel(selected.action) }}</span></div>
          <div class="detail-meta__row"><span>对象</span><span>{{ typeLabel(selected.target_type) }} · {{ selected.target_name }}</span></div>
          <div class="detail-meta__row"><span>操作人</span><span>{{ selected.user_name || '-' }}</span></div>
        </div>
        <div v-if="selected.changes_json?.length" class="detail-changes">
          <h4>字段变更</h4>
          <table class="changes-table">
            <thead><tr><th>字段</th><th>变更前</th><th>变更后</th></tr></thead>
            <tbody>
              <tr v-for="(c, i) in selected.changes_json" :key="i">
                <td><code>{{ c.field }}</code></td>
                <td class="changes-old">{{ c.old ?? '—' }}</td>
                <td class="changes-new">{{ c.new ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="detail-empty">无字段变更记录</div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import PageState from '../../components/common/PageState.vue'
import { get } from '../../api/client'

interface AuditLogItem {
  id: string
  timestamp: string
  user_id: string | null
  user_name: string | null
  action: string
  target_type: string
  target_id: string
  target_name: string
  changes_json: { field: string; old: unknown; new: unknown }[] | null
}

const loading = ref(true)
const list = ref<AuditLogItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const drawerOpen = ref(false)
const selected = ref<AuditLogItem | null>(null)

const filters = reactive({ action: undefined as string | undefined, target_type: undefined as string | undefined, user_name: '' })

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function fmt(d: string) {
  return d ? d.replace('T', ' ').slice(0, 19) : '-'
}

function actionLabel(a: string) {
  return { create: '创建', update: '更新', delete: '删除' }[a] || a
}

function typeLabel(t: string) {
  return { entity: '实体', relation: '关系', rule: '规则', attribute_mapping: '属性映射' }[t] || t
}

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize }
    if (filters.action) params.action = filters.action
    if (filters.target_type) params.target_type = filters.target_type
    if (filters.user_name) params.user_name = filters.user_name
    const res = await get<{ items: AuditLogItem[]; total: number }>('/governance/audit-logs', { params })
    list.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function doSearch() { page.value = 1; fetchList() }
function goPage(p: number) { page.value = p; fetchList() }
function resetFilters() { filters.action = undefined; filters.target_type = undefined; filters.user_name = ''; doSearch() }

function openDetail(row: AuditLogItem) { selected.value = row; drawerOpen.value = true }

onMounted(fetchList)
</script>

<style scoped>
.audit-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
.audit-header { margin-bottom: 20px; }
.audit-header__title { font-size: 18px; font-weight: 700; color: var(--neutral-900); margin: 0 0 4px; }
.audit-header__desc { font-size: var(--text-caption-size); color: var(--neutral-500); margin: 0; }

.audit-filters { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.audit-filters__total { font-size: var(--text-caption-size); color: var(--neutral-400); margin-left: 8px; }

.audit-table { width: 100%; border-collapse: collapse; font-size: var(--text-body-size); }
.audit-table th { text-align: left; padding: 8px 12px; background: var(--neutral-50); border-bottom: 2px solid var(--neutral-200); font-weight: 600; font-size: var(--text-caption-size); color: var(--neutral-600); white-space: nowrap; }
.audit-table td { padding: 8px 12px; border-bottom: 1px solid var(--neutral-100); vertical-align: middle; }
.audit-row { cursor: pointer; transition: background 0.1s; }
.audit-row:hover { background: var(--neutral-25, #fafbfc); }

.audit-time { font-size: var(--text-code-size); color: var(--neutral-500); white-space: nowrap; }
.audit-action { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--text-caption-size); font-weight: 600; }
.audit-action--create { background: var(--status-success-bg); color: var(--status-success); }
.audit-action--update { background: var(--status-info-bg); color: var(--status-info); }
.audit-action--delete { background: var(--status-error-bg); color: var(--status-error); }
.audit-type { font-size: var(--text-caption-size); color: var(--neutral-600); background: var(--neutral-100); padding: 2px 8px; border-radius: var(--radius-sm); }
.audit-name { display: flex; flex-direction: column; gap: 2px; }
.audit-name__text { font-size: var(--text-body-size); color: var(--neutral-800); }
.audit-name__id { font-size: 11px; color: var(--neutral-400); }
.audit-user { font-size: var(--text-body-size); color: var(--neutral-600); }
.audit-changes-badge { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 50%; background: var(--semantic-100); color: var(--semantic-600); font-size: 11px; font-weight: 700; }
.audit-muted { color: var(--neutral-300); }

.audit-pagination { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; }
.audit-pagination__info { font-size: var(--text-caption-size); color: var(--neutral-400); }
.audit-pagination__btns { display: flex; gap: 8px; }

/* 详情抽屉 */
.detail-meta { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; padding: 16px; background: var(--neutral-50); border-radius: var(--radius-md); }
.detail-meta__row { display: flex; justify-content: space-between; font-size: var(--text-body-size); }
.detail-meta__row span:first-child { color: var(--neutral-500); }
.detail-changes h4 { font-size: 14px; font-weight: 600; color: var(--neutral-700); margin: 0 0 10px; }
.changes-table { width: 100%; border-collapse: collapse; font-size: var(--text-body-size); }
.changes-table th { text-align: left; padding: 6px 10px; background: var(--neutral-50); border-bottom: 2px solid var(--neutral-200); font-size: var(--text-caption-size); color: var(--neutral-600); }
.changes-table td { padding: 6px 10px; border-bottom: 1px solid var(--neutral-100); }
.changes-old { color: var(--status-error); text-decoration: line-through; }
.changes-new { color: var(--status-success); }
.detail-empty { color: var(--neutral-400); font-size: var(--text-body-size); padding: 20px 0; text-align: center; }
</style>
