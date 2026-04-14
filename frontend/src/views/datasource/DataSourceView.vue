<template>
  <div class="ds-page">
    <div class="ds-page__header">
      <div>
        <h1 class="text-display">数据源管理</h1>
        <p class="text-caption" style="margin-top: 4px;">连接配置 · 状态监控 · 数据接入</p>
      </div>
      <div class="ds-page__actions">
        <button class="btn-primary" @click="openCreate">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新建数据源
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="ds-page__stats">
      <div class="stat-card stat-card--semantic">
        <div class="stat-card__value">{{ store.stats.total }}</div>
        <div class="stat-card__label">总数据源</div>
      </div>
      <div class="stat-card stat-card--dynamic">
        <div class="stat-card__value">{{ store.stats.enabled }}</div>
        <div class="stat-card__label">运行中</div>
      </div>
      <div class="stat-card stat-card--kinetic">
        <div class="stat-card__value">{{ store.stats.stopped }}</div>
        <div class="stat-card__label">已停止</div>
      </div>
      <div class="stat-card stat-card--error">
        <div class="stat-card__value">{{ store.stats.error }}</div>
        <div class="stat-card__label">异常</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="ds-page__filter">
      <input v-model="search" class="ds-search" placeholder="搜索数据源名称..." @input="onSearch" />
      <div class="ds-filter-tags">
        <button v-for="f in typeFilters" :key="f.value" class="filter-tag" :class="{ 'filter-tag--active': activeType === f.value }" @click="setTypeFilter(f.value)">{{ f.label }}</button>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="ds-page__table-wrap">
      <table class="ds-table">
        <thead>
          <tr>
            <th>数据源名称</th>
            <th>类型</th>
            <th>连接地址</th>
            <th>数据库</th>
            <th>表数量</th>
            <th>管道状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ds in store.items" :key="ds.id">
            <td class="text-body-medium">{{ ds.name }}</td>
            <td><span class="ds-type-badge">{{ ds.type }}</span></td>
            <td class="text-code">{{ ds.host }}:{{ ds.port }}</td>
            <td>{{ ds.database || '-' }}</td>
            <td>{{ ds.table_count }}</td>
            <td>
              <button class="ds-toggle" :class="ds.enabled ? 'ds-toggle--on' : 'ds-toggle--off'" @click="handleToggle(ds)" :disabled="toggling === ds.id">
                <span class="ds-toggle__dot"></span>
                <span class="ds-toggle__label">{{ ds.enabled ? '运行中' : '已停止' }}</span>
              </button>
            </td>
            <td class="text-caption">{{ formatTime(ds.created_at) }}</td>
            <td class="ds-table__actions">
              <button class="btn-sm-sync" @click="handleRefresh(ds)" :disabled="refreshing === ds.id">
                {{ refreshing === ds.id ? '同步中...' : '同步' }}
              </button>
              <button class="btn-sm-detail" @click="openDetail(ds)">详情</button>
              <button class="btn-sm-edit" @click="openEdit(ds)">编辑</button>
              <button class="btn-sm-del" @click="handleDelete(ds)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="store.items.length === 0 && !store.loading" class="ds-empty">
        <p class="text-caption">暂无数据源，点击「新建数据源」添加</p>
      </div>
    </div>

    <!-- 新建/编辑弹窗 -->
    <ModalDialog :visible="showModal" :title="editingId ? '编辑数据源' : '新建数据源'" width="560px" @close="showModal = false">
      <form class="ds-form" @submit.prevent="handleSave">
        <div class="form-row">
          <label class="form-label">数据源名称</label>
          <input v-model="form.name" class="form-input" placeholder="如：业务主库" required />
        </div>
        <div class="form-row-inline">
          <div class="form-row" style="flex:1">
            <label class="form-label">类型</label>
            <select v-model="form.type" class="form-input" required>
              <option v-for="t in dsTypes" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div class="form-row" style="flex:1">
            <label class="form-label">端口</label>
            <input v-model.number="form.port" class="form-input" type="number" required />
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">主机地址</label>
          <input v-model="form.host" class="form-input form-input--code" placeholder="如：192.168.1.100" required />
        </div>
        <div class="form-row-inline">
          <div class="form-row" style="flex:1">
            <label class="form-label">数据库名</label>
            <input v-model="form.database" class="form-input" placeholder="可选" />
          </div>
        </div>
        <div class="form-row-inline">
          <div class="form-row" style="flex:1">
            <label class="form-label">用户名</label>
            <input v-model="form.username" class="form-input" />
          </div>
          <div class="form-row" style="flex:1">
            <label class="form-label">密码</label>
            <input v-model="form.password" class="form-input" type="password" />
          </div>
        </div>
        <div class="form-row">
          <label class="form-label">描述</label>
          <input v-model="form.description" class="form-input" placeholder="可选" />
        </div>
        <div class="ds-form__footer">
          <button type="button" class="btn-secondary" @click="showModal = false">取消</button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </form>
    </ModalDialog>

    <!-- 详情弹窗 -->
    <ModalDialog :visible="showDetail" :title="detailName + ' — ' + (previewTable ? previewTable : '表列表')" width="800px" @close="closeDetail">
      <!-- 表列表视图 -->
      <div v-if="!previewTable">
        <div v-if="detailLoading" class="ds-detail-loading">加载中...</div>
        <div v-else-if="tableList.length === 0" class="ds-detail-empty">
          <p class="text-caption">未获取到表（请检查连接权限）</p>
        </div>
        <div v-else class="ds-detail-tables">
          <div v-for="t in tableList" :key="t" class="ds-detail-table-item" @click="loadPreview(t)">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="2" width="12" height="10" rx="1.5" stroke="currentColor" stroke-width="1.2"/><path d="M1 5.5h12M5 5.5V12" stroke="currentColor" stroke-width="1.2"/></svg>
            <span>{{ t }}</span>
          </div>
        </div>
      </div>
      <!-- 数据预览视图 -->
      <div v-else>
        <div class="ds-preview-header">
          <button class="btn-secondary btn-sm-back" @click="previewTable = null">← 返回表列表</button>
          <span class="text-caption">前 20 条数据</span>
        </div>
        <div v-if="previewLoading" class="ds-detail-loading">加载中...</div>
        <div v-else class="ds-preview-table-wrap">
          <table class="ds-table ds-preview-table">
            <thead>
              <tr>
                <th v-for="col in previewColumns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in previewRows" :key="i">
                <td v-for="(cell, j) in row" :key="j">{{ cell ?? '-' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="previewRows.length === 0" class="ds-detail-empty">
            <p class="text-caption">该表暂无数据</p>
          </div>
        </div>
      </div>
    </ModalDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useDataSourceStore } from '../../store/datasource'
import ModalDialog from '../../components/common/ModalDialog.vue'
import * as api from '../../api/datasource'
import type { DataSource, DataSourceCreate } from '../../types/datasource'

const store = useDataSourceStore()

const search = ref('')
const activeType = ref('')
const showModal = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)
const toggling = ref<string | null>(null)
const refreshing = ref<string | null>(null)

// 详情弹窗状态
const showDetail = ref(false)
const detailId = ref<string | null>(null)
const detailName = ref('')
const detailLoading = ref(false)
const tableList = ref<string[]>([])
const previewTable = ref<string | null>(null)
const previewLoading = ref(false)
const previewColumns = ref<string[]>([])
const previewRows = ref<unknown[][]>([])

const dsTypes = ['mysql', 'postgresql', 'oracle', 'sqlserver', 'clickhouse', 'hive', 'kafka', 'elasticsearch', 'api']

const defaultPort: Record<string, number> = {
  mysql: 3306, postgresql: 5432, oracle: 1521, sqlserver: 1433,
  clickhouse: 8123, hive: 10000, kafka: 9092, elasticsearch: 9200, api: 443,
}

const emptyForm = (): DataSourceCreate => ({
  name: '', type: 'mysql', host: '', port: 3306, database: '', username: '', password: '', description: '',
})

const form = ref<DataSourceCreate>(emptyForm())

const typeFilters = [
  { label: '全部', value: '' },
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgresql' },
  { label: 'Oracle', value: 'oracle' },
  { label: 'ClickHouse', value: 'clickhouse' },
  { label: 'Kafka', value: 'kafka' },
]

onMounted(() => store.fetchList())

function statusLabel(s: string) {
  return s === 'active' ? '正常' : s === 'inactive' ? '未启用' : '异常'
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function setTypeFilter(v: string) {
  activeType.value = v
  store.fetchList({ type: v || undefined, q: search.value || undefined })
}

function onSearch() {
  store.fetchList({ type: activeType.value || undefined, q: search.value || undefined })
}

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  showModal.value = true
}

async function openEdit(ds: DataSource) {
  editingId.value = ds.id
  try {
    const detail = await api.getDataSource(ds.id)
    form.value = { name: detail.name, type: detail.type, host: detail.host, port: detail.port, database: detail.database, username: detail.username, password: detail.password, description: detail.description }
  } catch {
    form.value = { name: ds.name, type: ds.type, host: ds.host, port: ds.port, database: ds.database, username: ds.username, password: ds.password, description: ds.description }
  }
  showModal.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingId.value) {
      await api.updateDataSource(editingId.value, form.value)
    } else {
      await api.createDataSource(form.value)
    }
    showModal.value = false
    store.fetchList({ type: activeType.value || undefined, q: search.value || undefined })
  } catch (e: any) {
    alert(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleToggle(ds: DataSource) {
  toggling.value = ds.id
  try {
    await api.toggleDataSource(ds.id)
    store.fetchList({ type: activeType.value || undefined, q: search.value || undefined })
  } catch {
    alert('操作失败')
  } finally {
    toggling.value = null
  }
}

async function handleDelete(ds: DataSource) {
  if (!confirm(`确认删除数据源「${ds.name}」？`)) return
  try {
    await api.deleteDataSource(ds.id)
    store.fetchList({ type: activeType.value || undefined, q: search.value || undefined })
  } catch {
    alert('删除失败')
  }
}

async function handleRefresh(ds: DataSource) {
  refreshing.value = ds.id
  try {
    const res = await api.refreshTables(ds.id)
    if (res.table_count === 0) {
      alert('同步完成，但未获取到表（请检查数据库连接权限）')
    } else {
      alert(`同步完成，共 ${res.table_count} 张表`)
    }
    store.fetchList({ type: activeType.value || undefined, q: search.value || undefined })
  } catch {
    alert('同步失败')
  } finally {
    refreshing.value = null
  }
}

async function openDetail(ds: DataSource) {
  detailId.value = ds.id
  detailName.value = ds.name
  tableList.value = []
  previewTable.value = null
  previewColumns.value = []
  previewRows.value = []
  showDetail.value = true
  detailLoading.value = true
  try {
    const res = await api.getTableList(ds.id)
    tableList.value = res.tables
  } catch {
    alert('获取表列表失败，请检查连接')
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  showDetail.value = false
  detailId.value = null
  previewTable.value = null
}

async function loadPreview(tableName: string) {
  previewTable.value = tableName
  previewLoading.value = true
  previewColumns.value = []
  previewRows.value = []
  try {
    const res = await api.getTablePreview(detailId.value!, tableName)
    previewColumns.value = res.columns
    previewRows.value = res.rows
  } catch {
    alert('查询数据失败')
  } finally {
    previewLoading.value = false
  }
}
</script>

<style scoped>
.ds-page { padding: 28px 32px; max-width: 1200px; }
.ds-page__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.ds-page__actions { display: flex; gap: 8px; }

.ds-page__stats { display: flex; gap: 12px; margin-bottom: 20px; }
.stat-card { flex: 1; padding: 16px; border-radius: var(--radius-lg); border: 1px solid var(--neutral-100); background: var(--neutral-0); }
.stat-card__value { font-size: 24px; font-weight: 700; }
.stat-card__label { font-size: 12px; color: var(--neutral-500); margin-top: 2px; }
.stat-card--semantic .stat-card__value { color: var(--semantic-600); }
.stat-card--dynamic .stat-card__value { color: var(--dynamic-600); }
.stat-card--kinetic .stat-card__value { color: var(--kinetic-600); }
.stat-card--error .stat-card__value { color: var(--status-error); }

.ds-page__filter { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.ds-search { padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: 13px; width: 240px; color: var(--neutral-800); background: var(--neutral-0); outline: none; }
.ds-search:focus { border-color: var(--semantic-500); }
.ds-filter-tags { display: flex; gap: 6px; }
.filter-tag { padding: 4px 12px; border-radius: var(--radius-full); border: 1px solid var(--neutral-200); background: var(--neutral-0); font-size: 12px; color: var(--neutral-600); cursor: pointer; }
.filter-tag--active { background: var(--semantic-600); color: #fff; border-color: var(--semantic-600); }

.ds-page__table-wrap { border: 1px solid var(--neutral-100); border-radius: var(--radius-lg); overflow: hidden; background: var(--neutral-0); }
.ds-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ds-table th { text-align: left; padding: 10px 14px; font-size: 12px; font-weight: 600; color: var(--neutral-500); background: var(--neutral-50); border-bottom: 1px solid var(--neutral-100); }
.ds-table td { padding: 12px 14px; border-bottom: 1px solid var(--neutral-50); color: var(--neutral-800); }
.ds-table tbody tr:hover { background: var(--neutral-25, var(--neutral-50)); }
.ds-table tbody tr:last-child td { border-bottom: none; }

.ds-type-badge { display: inline-block; padding: 2px 8px; border-radius: var(--radius-full); font-size: 11px; font-weight: 600; background: var(--semantic-50); color: var(--semantic-600); text-transform: uppercase; }
.ds-status { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 500; }
.ds-status::before { content: ''; width: 6px; height: 6px; border-radius: 50%; }
.ds-status--active { color: var(--dynamic-600); }
.ds-status--active::before { background: var(--dynamic-500); }
.ds-status--inactive { color: var(--neutral-500); }
.ds-status--inactive::before { background: var(--neutral-400); }
.ds-status--error { color: var(--status-error); }
.ds-status--error::before { background: var(--status-error); }

.ds-table__actions { display: flex; gap: 6px; }
.btn-sm-sync, .btn-sm-detail, .btn-sm-edit, .btn-sm-del { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: var(--radius-md); font-size: 11px; font-weight: 500; cursor: pointer; border: 1px solid; }
.btn-sm-sync { border-color: var(--kinetic-400); background: var(--kinetic-50); color: var(--kinetic-700); }
.btn-sm-sync:hover { background: var(--kinetic-500); color: #fff; }
.btn-sm-sync:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-sm-detail { border-color: var(--semantic-400); background: var(--semantic-50); color: var(--semantic-600); }
.btn-sm-detail:hover { background: var(--semantic-500); color: #fff; }
.btn-sm-edit { border-color: var(--semantic-400); background: var(--semantic-50); color: var(--semantic-600); }
.btn-sm-edit:hover { background: var(--semantic-500); color: #fff; }
.btn-sm-del { border-color: var(--status-error); background: var(--status-error-bg); color: var(--status-error); }
.btn-sm-del:hover { background: var(--status-error); color: #fff; }

.ds-toggle { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: var(--radius-full); font-size: 12px; font-weight: 500; cursor: pointer; border: none; transition: all var(--transition-fast); }
.ds-toggle:disabled { opacity: 0.6; cursor: not-allowed; }
.ds-toggle__dot { width: 8px; height: 8px; border-radius: 50%; transition: background var(--transition-fast); }
.ds-toggle--on { background: var(--dynamic-50); color: var(--dynamic-700); }
.ds-toggle--on .ds-toggle__dot { background: var(--dynamic-500); }
.ds-toggle--on:hover { background: var(--dynamic-100); }
.ds-toggle--off { background: var(--neutral-100); color: var(--neutral-500); }
.ds-toggle--off .ds-toggle__dot { background: var(--neutral-400); }
.ds-toggle--off:hover { background: var(--neutral-200); }

.ds-empty { padding: 48px; text-align: center; }

.ds-form { display: flex; flex-direction: column; gap: 14px; }
.ds-form__footer { display: flex; justify-content: flex-end; gap: 8px; padding-top: 8px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-row-inline { display: flex; gap: 12px; }
.form-label { font-size: 12px; font-weight: 500; color: var(--neutral-600); }
.form-input { padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: 13px; color: var(--neutral-800); background: var(--neutral-0); outline: none; }
.form-input:focus { border-color: var(--semantic-500); }
.form-input--code { font-family: var(--font-mono); font-size: 12px; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: var(--radius-md); border: none; background: var(--semantic-600); color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-primary:hover { background: var(--semantic-700); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { padding: 8px 16px; border-radius: var(--radius-md); border: 1px solid var(--neutral-200); background: var(--neutral-0); color: var(--neutral-700); font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-secondary:hover { background: var(--neutral-50); }

.ds-detail-loading { padding: 32px; text-align: center; color: var(--neutral-500); font-size: 13px; }
.ds-detail-empty { padding: 32px; text-align: center; }
.ds-detail-tables { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
.ds-detail-table-item { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border: 1px solid var(--neutral-100); border-radius: var(--radius-md); cursor: pointer; font-size: 13px; color: var(--neutral-700); transition: all var(--transition-fast); }
.ds-detail-table-item:hover { background: var(--semantic-50); border-color: var(--semantic-300); color: var(--semantic-700); }
.ds-detail-table-item svg { color: var(--neutral-400); flex-shrink: 0; }
.ds-detail-table-item:hover svg { color: var(--semantic-500); }

.ds-preview-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.btn-sm-back { font-size: 12px; padding: 4px 12px; }
.ds-preview-table-wrap { overflow-x: auto; max-height: 400px; overflow-y: auto; }
.ds-preview-table { font-size: 12px; }
.ds-preview-table th { white-space: nowrap; position: sticky; top: 0; z-index: 1; }
.ds-preview-table td { white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
</style>
