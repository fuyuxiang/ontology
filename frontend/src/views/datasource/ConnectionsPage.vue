<template>
  <div class="cp-page">
    <div class="cp-page__header">
      <h1 class="cp-page__title">数据接入 · 连接</h1>
      <p class="cp-page__subtitle">配置到数据仓库 / 业务库的物理连接，凭据加密引用，全平台读写源数据的统一入口</p>
    </div>

    <!-- 统计 -->
    <div class="cp-stats">
      <a-statistic title="连接总数" :value="store.stats.total">
        <template #prefix><DatabaseOutlined style="color:#3b82f6" /></template>
      </a-statistic>
      <a-statistic title="在线" :value="store.stats.enabled" :value-style="{ color: '#10b981' }">
        <template #prefix><CheckCircleOutlined style="color:#10b981" /></template>
      </a-statistic>
      <a-statistic title="离线" :value="store.stats.stopped" :value-style="{ color: '#6b7280' }" />
      <a-statistic v-if="store.stats.error > 0" title="异常" :value="store.stats.error"
                   :value-style="{ color: '#ef4444' }" />
      <span class="cp-spacer" />
      <a-button type="primary" @click="openCreate">
        <template #icon><PlusOutlined /></template>新增连接
      </a-button>
    </div>

    <!-- 工具栏 -->
    <div class="cp-toolbar">
      <a-input-search v-model:value="search" placeholder="搜索连接名称 / 主机..." style="width:300px"
                      allow-clear @search="onSearch" @change="onSearch" />
      <a-segmented v-model:value="typeFilter" :options="typeFilters" @change="onSearch" />
    </div>

    <!-- 表格 -->
    <a-table size="middle" :columns="columns" :data-source="store.items"
             :loading="store.loading" :pagination="{ pageSize: 20 }" row-key="id">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'type'">
          <a-tag :color="typeColor(record.type)">{{ record.type }}</a-tag>
        </template>
        <template v-else-if="column.key === 'status'">
          <span class="cp-status">
            <span class="cp-status__dot" :style="{ background: statusColor(record) }" />
            <span :style="{ color: statusColor(record) }">{{ statusLabel(record) }}</span>
            <SyncOutlined v-if="testing === record.id" spin style="margin-left:4px;color:#f59e0b" />
          </span>
        </template>
        <template v-else-if="column.key === 'host'">
          <code class="cp-mono">{{ record.host }}:{{ record.port }}</code>
        </template>
        <template v-else-if="column.key === 'writable'">
          <a-tag v-if="record.writable" color="orange">可写</a-tag>
          <a-tag v-else color="default">只读</a-tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space :size="4" wrap>
            <a-button type="link" size="small" :loading="testing === record.id" @click="testOne(record)">
              <template #icon><LinkOutlined /></template>测试
            </a-button>
            <a-button type="link" size="small" @click="openTables(record)">
              <template #icon><TableOutlined /></template>列表
            </a-button>
            <a-button type="link" size="small" @click="openEdit(record)">编辑</a-button>
            <a-popconfirm :title="`确认删除「${record.name}」？资产被引用时会被拒绝。`" @confirm="del(record)">
              <a-button type="link" size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
      <template #emptyText>
        <a-empty description="暂无连接，点击「新增连接」添加" />
      </template>
    </a-table>

    <!-- 新建/编辑 抽屉 -->
    <a-drawer :open="modal.open" :title="modal.editingId ? '编辑连接' : '新增连接'"
              width="520" @update:open="(v) => modal.open = v" destroy-on-close>
      <a-form layout="vertical">
        <a-form-item label="连接名称 *">
          <a-input v-model:value="form.name" placeholder="如：bb_audit_db" :disabled="!!modal.editingId" />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="数据库类型">
              <a-select v-model:value="form.type" :options="typeOptions" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="端口">
              <a-input-number v-model:value="form.port" style="width:100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="主机">
          <a-input v-model:value="form.host" placeholder="192.168.1.100" />
        </a-form-item>
        <a-form-item label="数据库 / Schema">
          <a-input v-model:value="form.database" placeholder="可选" />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="用户名">
              <a-input v-model:value="form.username" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item :label="modal.editingId ? '密码（留空不改）' : '密码'">
              <a-input-password v-model:value="form.password" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="池容量">
              <a-input-number v-model:value="form.pool_size" :min="1" :max="32" style="width:100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="QPS 限流">
              <a-input-number v-model:value="form.rate_limit_qps" :min="1" :max="500" style="width:100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="允许写入">
              <a-switch v-model:checked="form.writable" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="2" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="saving" @click="save">保存</a-button>
        </a-form-item>
      </a-form>
    </a-drawer>

    <!-- 浏览库表 -->
    <a-modal :open="browser.open" title="浏览库表" width="640" :footer="null"
             @update:open="(v) => browser.open = v">
      <a-spin :spinning="browser.loading">
        <a-tabs>
          <a-tab-pane key="dbs" tab="数据库">
            <a-list size="small" :data-source="browser.databases">
              <template #renderItem="{ item }"><a-list-item>{{ item }}</a-list-item></template>
            </a-list>
          </a-tab-pane>
          <a-tab-pane key="tables" tab="表">
            <a-list size="small" :data-source="browser.tables">
              <template #renderItem="{ item }">
                <a-list-item>
                  {{ item }}
                  <a-button type="link" size="small" @click="registerAsAsset(item)">
                    注册为 Asset
                  </a-button>
                </a-list-item>
              </template>
            </a-list>
          </a-tab-pane>
        </a-tabs>
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  Button as AButton, Col as ACol, Drawer as ADrawer, Empty as AEmpty,
  Form as AForm, FormItem as AFormItem, Input as AInput, InputNumber as AInputNumber,
  InputPassword as AInputPassword, InputSearch as AInputSearch, List as AList,
  ListItem as AListItem, Modal as AModal, Popconfirm as APopconfirm, Row as ARow,
  Segmented as ASegmented, Select as ASelect, Space as ASpace, Spin as ASpin,
  Statistic as AStatistic, Switch as ASwitch, Table as ATable, Tabs as ATabs,
  TabPane as ATabPane, Tag as ATag, Textarea as ATextarea, message,
} from 'ant-design-vue'
import {
  CheckCircleOutlined, DatabaseOutlined, LinkOutlined, PlusOutlined,
  SyncOutlined, TableOutlined,
} from '@ant-design/icons-vue'
import { useConnectionStore } from '../../store/connection'
import { useAssetStore } from '../../store/asset'
import { listDatabases, listTablesOfConnection } from '../../api/connection'
import type { Connection, ConnectionType } from '../../types/connection'

const store = useConnectionStore()
const assetStore = useAssetStore()
const search = ref('')
const typeFilter = ref<string>('all')

const typeOptions = [
  { label: 'MySQL', value: 'mysql' }, { label: 'PostgreSQL', value: 'postgresql' },
  { label: 'Oracle', value: 'oracle' }, { label: 'SQL Server', value: 'sqlserver' },
  { label: 'Hive', value: 'hive' }, { label: 'ClickHouse', value: 'clickhouse' },
]
const typeFilters = computed(() => [{ label: '全部', value: 'all' }, ...typeOptions])

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '类型', key: 'type', width: 110 },
  { title: '主机:端口', key: 'host', width: 200 },
  { title: '数据库', dataIndex: 'database', key: 'database' },
  { title: '权限', key: 'writable', width: 80 },
  { title: '状态', key: 'status', width: 110 },
  { title: '操作', key: 'actions', width: 280 },
]

const testing = ref<string | null>(null)
const saving = ref(false)
const modal = reactive({ open: false, editingId: '' as string })
const form = reactive({
  name: '', type: 'mysql' as ConnectionType, host: '', port: 3306, database: '',
  username: '', password: '',
  pool_size: 4, rate_limit_qps: 20, writable: false, description: '',
})

const browser = reactive({
  open: false, loading: false, connId: '',
  databases: [] as string[], tables: [] as string[],
})

async function load() { await store.fetchList(buildFilters()) }
function buildFilters() {
  const f: any = {}
  if (search.value) f.q = search.value
  if (typeFilter.value !== 'all') f.type = typeFilter.value
  return f
}
function onSearch() { load() }

function openCreate() {
  modal.editingId = ''
  Object.assign(form, {
    name: '', type: 'mysql', host: '', port: 3306, database: '',
    username: '', password: '', pool_size: 4, rate_limit_qps: 20, writable: false, description: '',
  })
  modal.open = true
}
function openEdit(record: Connection) {
  modal.editingId = record.id
  Object.assign(form, {
    name: record.name, type: record.type, host: record.host, port: record.port,
    database: record.database, username: '', password: '',
    pool_size: record.pool_size, rate_limit_qps: record.rate_limit_qps,
    writable: record.writable, description: record.description || '',
  })
  modal.open = true
}

async function save() {
  saving.value = true
  try {
    if (modal.editingId) {
      const payload: any = { ...form }
      if (!form.password) delete payload.password
      if (!form.username) delete payload.username
      await store.update(modal.editingId, payload)
      message.success('已更新')
    } else {
      if (!form.name || !form.host || !form.username) {
        message.error('请填写名称 / 主机 / 用户名'); return
      }
      await store.create({ ...form })
      message.success('已创建')
    }
    modal.open = false
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally {
    saving.value = false
  }
}

async function testOne(record: Connection) {
  testing.value = record.id
  try {
    const r = await store.test(record.id)
    if (r.success) message.success(`连接成功（${r.latency_ms}ms）`)
    else message.error(r.message)
    await load()
  } finally { testing.value = null }
}

async function del(record: Connection) {
  try {
    await store.remove(record.id); message.success('已删除')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

async function openTables(record: Connection) {
  browser.connId = record.id; browser.open = true; browser.loading = true
  try {
    const [dbs, ts] = await Promise.all([
      listDatabases(record.id).catch(() => []),
      listTablesOfConnection(record.id),
    ])
    browser.databases = dbs; browser.tables = ts
  } catch (e: any) {
    message.error(e.message)
  } finally {
    browser.loading = false
  }
}

async function registerAsAsset(table: string) {
  try {
    await assetStore.create({
      name: table, kind: 'table',
      connection_id: browser.connId,
      locator: { table },
    })
    message.success(`已注册资产：${table}`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  }
}

function statusColor(c: Connection) {
  if (!c.enabled) return '#9ca3af'
  if (c.status === 'error') return '#ef4444'
  if (c.last_test_ok) return '#10b981'
  return '#3b82f6'
}
function statusLabel(c: Connection) {
  if (!c.enabled) return '已禁用'
  if (c.status === 'error') return '异常'
  if (c.last_test_ok) return '在线'
  return '待测试'
}
function typeColor(t: string) {
  return ({
    mysql: 'blue', postgresql: 'cyan', oracle: 'red',
    sqlserver: 'purple', hive: 'orange', clickhouse: 'gold',
  } as any)[t] || 'default'
}

onMounted(load)
</script>

<style scoped>
.cp-page { padding: 24px; }
.cp-page__header { margin-bottom: 16px; }
.cp-page__title { font-size: 24px; font-weight: 600; color: #111827; margin: 0; }
.cp-page__subtitle { font-size: 13px; color: #6b7280; margin-top: 4px; }
.cp-stats {
  display: flex; align-items: center; gap: 32px; padding: 16px;
  background: #fff; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  margin-bottom: 12px;
}
.cp-spacer { flex: 1; }
.cp-toolbar {
  display: flex; gap: 12px; align-items: center; padding: 12px 16px;
  background: #fff; border-radius: 8px; margin-bottom: 12px;
}
.cp-status { display: inline-flex; align-items: center; gap: 6px; }
.cp-status__dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.cp-mono { font-family: 'Menlo','Consolas',monospace; font-size: 12px; color: #4b5563; }
</style>
