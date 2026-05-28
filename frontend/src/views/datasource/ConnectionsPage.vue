<template>
  <div class="cp-page">
    <div class="cp-page__header">
      <h1 class="cp-page__title">数据接入</h1>
      <p class="cp-page__subtitle">统一管理数据源连接、凭据与访问权限。支持数据库 / 对象存储 / 文件传输 / 消息队列 / API。</p>
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
        <template #icon><PlusOutlined /></template>新增数据源
      </a-button>
    </div>

    <!-- 工具栏 -->
    <div class="cp-toolbar">
      <a-input-search v-model:value="search" placeholder="搜索连接名称 / 主机..." style="width:300px"
                      allow-clear @search="onSearch" @change="onSearch" />
      <a-segmented v-model:value="categoryFilter" :options="categoryFilters" @change="onSearch" />
    </div>

    <!-- 表格 -->
    <a-table size="middle" :columns="columns" :data-source="store.items"
             :loading="store.loading" :pagination="{ pageSize: 20 }" row-key="id">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'category'">
          <a-tag :color="categoryColor(record.category)">{{ categoryLabel(record.category) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'type'">
          <a-tag :color="typeColor(record.type)">{{ record.type }}</a-tag>
        </template>
        <template v-else-if="column.key === 'endpoint'">
          <code class="cp-mono">{{ endpointBrief(record) }}</code>
        </template>
        <template v-else-if="column.key === 'status'">
          <span class="cp-status">
            <span class="cp-status__dot" :style="{ background: statusColor(record) }" />
            <span :style="{ color: statusColor(record) }">{{ statusLabel(record) }}</span>
            <SyncOutlined v-if="testing === record.id" spin style="margin-left:4px;color:#f59e0b" />
          </span>
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
            <a-button type="link" size="small" @click="openBrowser(record)">
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
        <a-empty description="暂无数据源，点击「新增数据源」添加" />
      </template>
    </a-table>

    <!-- 第一步：选大类（仅新建时显示） -->
    <a-modal :open="picker.open" title="选择数据源类型" width="720" :footer="null"
             @update:open="(v) => picker.open = v" destroy-on-close>
      <div class="cp-cat-grid">
        <div v-for="cat in CATEGORIES" :key="cat.key" class="cp-cat-card"
             :class="{ 'cp-cat-card--disabled': !(capabilities[cat.key] && capabilities[cat.key].length) }"
             @click="selectCategory(cat.key)">
          <div class="cp-cat-card__icon" :style="{ background: cat.color }">{{ cat.glyph }}</div>
          <div class="cp-cat-card__title">{{ cat.label }}</div>
          <div class="cp-cat-card__sub">{{ (capabilities[cat.key] || []).join(' · ') || '后端未启用' }}</div>
          <div class="cp-cat-card__hint">{{ cat.hint }}</div>
        </div>
      </div>
    </a-modal>

    <!-- 第二步：表单抽屉（新建/编辑共用） -->
    <a-drawer :open="modal.open" :title="modalTitle" width="560"
              @update:open="(v) => modal.open = v" destroy-on-close>
      <a-form layout="vertical">
        <a-form-item label="连接名称 *">
          <a-input v-model:value="form.name" placeholder="example_conn" :disabled="!!modal.editingId" />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="分类">
              <a-input :value="categoryLabel(form.category)" disabled />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="具体类型 *">
              <a-select v-model:value="form.type" :options="typeOptionsForCategory" :disabled="!!modal.editingId" />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- ─── 数据库 ─── -->
        <template v-if="form.category === 'database'">
          <a-row :gutter="12">
            <a-col :span="16">
              <a-form-item label="主机 *"><a-input v-model:value="form.host" placeholder="127.0.0.1" /></a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="端口"><a-input-number v-model:value="form.port" style="width:100%" /></a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="数据库 / Schema"><a-input v-model:value="form.database" /></a-form-item>
          <a-row :gutter="12">
            <a-col :span="12"><a-form-item label="用户名 *"><a-input v-model:value="form.username" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item :label="modal.editingId ? '密码（留空不改）' : '密码 *'">
              <a-input-password v-model:value="form.password" /></a-form-item></a-col>
          </a-row>
        </template>

        <!-- ─── 对象存储 (S3/OSS/...) ─── -->
        <template v-else-if="form.category === 'object_storage'">
          <a-form-item label="Endpoint">
            <a-input v-model:value="paramStr.endpoint" placeholder="https://s3.amazonaws.com 或留空走 AWS 默认" />
          </a-form-item>
          <a-row :gutter="12">
            <a-col :span="12">
              <a-form-item label="Region"><a-input v-model:value="paramStr.region" placeholder="us-east-1" /></a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="Bucket *"><a-input v-model:value="paramStr.bucket" /></a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="Path-Style 寻址">
            <a-switch v-model:checked="paramBool.path_style" />
            <span class="cp-hint">非 AWS 兼容服务（MinIO 等）通常需要打开</span>
          </a-form-item>
          <a-row :gutter="12">
            <a-col :span="12"><a-form-item label="Access Key *">
              <a-input v-model:value="credStr.access_key" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item :label="modal.editingId ? 'Secret Key（留空不改）' : 'Secret Key *'">
              <a-input-password v-model:value="credStr.secret_key" /></a-form-item></a-col>
          </a-row>
        </template>

        <!-- ─── 文件传输 (FTP/SFTP) ─── -->
        <template v-else-if="form.category === 'file_transfer'">
          <a-row :gutter="12">
            <a-col :span="16"><a-form-item label="主机 *"><a-input v-model:value="paramStr.host" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="端口"><a-input-number v-model:value="paramNum.port"
                                                                       :placeholder="form.type === 'sftp' ? '22' : '21'"
                                                                       style="width:100%" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="根目录"><a-input v-model:value="paramStr.root_path" placeholder="/" /></a-form-item>
          <a-form-item v-if="form.type === 'ftp'" label="启用 FTPS">
            <a-switch v-model:checked="paramBool.use_tls" />
          </a-form-item>
          <a-row :gutter="12">
            <a-col :span="12"><a-form-item label="用户名">
              <a-input v-model:value="credStr.username" placeholder="anonymous" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item :label="modal.editingId ? '密码（留空不改）' : '密码'">
              <a-input-password v-model:value="credStr.password" /></a-form-item></a-col>
          </a-row>
        </template>

        <!-- ─── 消息队列 (Kafka) ─── -->
        <template v-else-if="form.category === 'message_queue'">
          <a-form-item label="Brokers *">
            <a-input v-model:value="paramStr.brokers" placeholder="host1:9092,host2:9092" />
          </a-form-item>
          <a-form-item label="Security Protocol">
            <a-select v-model:value="paramStr.security_protocol" :options="kafkaSecurityOptions" />
          </a-form-item>
          <a-row v-if="paramStr.security_protocol && paramStr.security_protocol !== 'PLAINTEXT'" :gutter="12">
            <a-col :span="12"><a-form-item label="SASL 用户">
              <a-input v-model:value="credStr.username" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item :label="modal.editingId ? 'SASL 密码（留空不改）' : 'SASL 密码'">
              <a-input-password v-model:value="credStr.password" /></a-form-item></a-col>
          </a-row>
        </template>

        <!-- ─── HTTP API ─── -->
        <template v-else-if="form.category === 'api'">
          <a-form-item label="Base URL *">
            <a-input v-model:value="paramStr.base_url" placeholder="https://api.example.com/v1" />
          </a-form-item>
          <a-form-item label="探测路径">
            <a-input v-model:value="paramStr.probe_path" placeholder="/health 或 /" />
          </a-form-item>
          <a-form-item label="认证方式">
            <a-select v-model:value="paramStr.auth_type" :options="apiAuthOptions" />
          </a-form-item>
          <a-form-item v-if="paramStr.auth_type === 'bearer'" :label="modal.editingId ? 'Bearer Token（留空不改）' : 'Bearer Token'">
            <a-input-password v-model:value="credStr.token" />
          </a-form-item>
          <a-row v-else-if="paramStr.auth_type === 'basic'" :gutter="12">
            <a-col :span="12"><a-form-item label="用户名"><a-input v-model:value="credStr.username" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item :label="modal.editingId ? '密码（留空不改）' : '密码'">
              <a-input-password v-model:value="credStr.password" /></a-form-item></a-col>
          </a-row>
          <template v-else-if="paramStr.auth_type === 'api_key'">
            <a-form-item label="Header 名称">
              <a-input v-model:value="credStr.key" placeholder="X-API-Key" />
            </a-form-item>
            <a-form-item :label="modal.editingId ? 'API Key 值（留空不改）' : 'API Key 值'">
              <a-input-password v-model:value="credStr.value" />
            </a-form-item>
          </template>
        </template>

        <!-- ─── 通用：限流 / 描述 ─── -->
        <a-divider />
        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="池容量"><a-input-number v-model:value="form.pool_size" :min="1" :max="32" style="width:100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="QPS 限流"><a-input-number v-model:value="form.rate_limit_qps" :min="1" :max="500" style="width:100%" /></a-form-item>
          </a-col>
          <a-col :span="8" v-if="form.category === 'database'">
            <a-form-item label="允许写入"><a-switch v-model:checked="form.writable" /></a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="描述"><a-textarea v-model:value="form.description" :rows="2" /></a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="saving" @click="save">保存</a-button>
        </a-form-item>
      </a-form>
    </a-drawer>

    <!-- 浏览弹窗（按 category 切换内容） -->
    <a-modal :open="browser.open" :title="`浏览：${browser.title}`" width="720" :footer="null"
             @update:open="(v) => browser.open = v">
      <a-spin :spinning="browser.loading">
        <!-- 批量操作工具条（除 API 外通用） -->
        <div v-if="browser.category !== 'api'" class="cp-bulk-bar">
          <a-checkbox :checked="allSelected" :indeterminate="someSelected" @change="toggleAll">
            全选 <span class="cp-muted">（已选 {{ browser.selected.length }}/{{ totalRows }}）</span>
          </a-checkbox>
          <span class="cp-spacer" />
          <a-button type="primary" :disabled="browser.selected.length === 0"
                    :loading="bulkSaving" @click="bulkRegister">
            批量注册为 Asset（{{ browser.selected.length }}）
          </a-button>
        </div>

        <!-- 数据库 -->
        <a-tabs v-if="browser.category === 'database'">
          <a-tab-pane key="dbs" tab="数据库">
            <a-list size="small" :data-source="browser.databases">
              <template #renderItem="{ item }"><a-list-item>{{ item }}</a-list-item></template>
            </a-list>
          </a-tab-pane>
          <a-tab-pane key="tables" :tab="`表（${browser.tables.length}）`">
            <a-list size="small" :data-source="browser.tables">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-checkbox :checked="browser.selected.includes(item)" @change="toggleOne(item)">
                    {{ item }}
                  </a-checkbox>
                  <a-button type="link" size="small" @click="registerAsAsset(item)">注册为 Asset</a-button>
                </a-list-item>
              </template>
            </a-list>
          </a-tab-pane>
        </a-tabs>

        <!-- 对象存储 -->
        <div v-else-if="browser.category === 'object_storage'">
          <a-input-search v-model:value="browser.prefix" placeholder="prefix 前缀" enter-button="筛选"
                          @search="reloadBrowser" style="margin-bottom:12px" />
          <a-list size="small" :data-source="browser.objects">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-checkbox :checked="browser.selected.includes(item.key)" @change="toggleOne(item.key)">
                  <code class="cp-mono">{{ item.key }}</code>
                  <span class="cp-muted" style="margin-left:8px">{{ formatSize(item.size) }}</span>
                </a-checkbox>
                <a-button type="link" size="small" @click="registerObjectAsAsset(item)">注册为 Asset</a-button>
              </a-list-item>
            </template>
          </a-list>
        </div>

        <!-- 文件传输 -->
        <div v-else-if="browser.category === 'file_transfer'">
          <a-input-search v-model:value="browser.path" placeholder="路径" enter-button="进入"
                          @search="reloadBrowser" style="margin-bottom:12px" />
          <a-list size="small" :data-source="browser.paths">
            <template #renderItem="{ item }">
              <a-list-item>
                <span style="display:flex;align-items:center;gap:8px;flex:1">
                  <a-checkbox v-if="!item.is_dir"
                              :checked="browser.selected.includes(item.name)"
                              @change="toggleOne(item.name)" />
                  <span :style="item.is_dir ? 'color:#3b82f6;cursor:pointer' : ''"
                        @click="item.is_dir && enterPath(item.name)">
                    {{ item.is_dir ? '📁' : '📄' }} {{ item.name }}
                  </span>
                  <span class="cp-muted" style="margin-left:8px">{{ formatSize(item.size) }}</span>
                </span>
                <a-button v-if="!item.is_dir" type="link" size="small" @click="registerPathAsAsset(item)">
                  注册为 Asset
                </a-button>
              </a-list-item>
            </template>
          </a-list>
        </div>

        <!-- 消息队列 -->
        <div v-else-if="browser.category === 'message_queue'">
          <a-list size="small" :data-source="browser.topics">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-checkbox :checked="browser.selected.includes(item)" @change="toggleOne(item)">
                  <code class="cp-mono">{{ item }}</code>
                </a-checkbox>
                <a-button type="link" size="small" @click="registerTopicAsAsset(item)">注册为 Asset</a-button>
              </a-list-item>
            </template>
          </a-list>
        </div>

        <!-- API -->
        <div v-else-if="browser.category === 'api'" class="cp-empty">
          <p>API 类型暂不支持自动列举端点。</p>
          <p>请直接在「资产目录」中注册为 document 资产，关联此连接。</p>
        </div>
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  Button as AButton, Checkbox as ACheckbox, Col as ACol, Divider as ADivider, Drawer as ADrawer, Empty as AEmpty,
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
import {
  getCapabilities, listObjects, listPaths, listTablesOfConnection, listTopics,
} from '../../api/connection'
import type {
  Capabilities, Connection, ConnectionCategory,
  ObjectEntry, PathEntry,
} from '../../types/connection'

const store = useConnectionStore()
const assetStore = useAssetStore()
const search = ref('')
const categoryFilter = ref<string>('all')
const capabilities = ref<Capabilities>({} as Capabilities)

const CATEGORIES: { key: ConnectionCategory; label: string; glyph: string; color: string; hint: string }[] = [
  { key: 'database',       label: '数据库',     glyph: 'DB',  color: '#3b82f6', hint: '关系数据库 / 数仓' },
  { key: 'object_storage', label: '对象存储',   glyph: 'S3',  color: '#10b981', hint: 'S3 / OSS / MinIO' },
  { key: 'file_transfer',  label: '文件传输',   glyph: 'FTP', color: '#f59e0b', hint: 'FTP / SFTP / HDFS' },
  { key: 'message_queue',  label: '消息队列',   glyph: 'MQ',  color: '#8b5cf6', hint: 'Kafka / Pulsar' },
  { key: 'api',            label: 'HTTP API',   glyph: 'API', color: '#ec4899', hint: 'REST / GraphQL' },
]

const categoryFilters = computed(() => [
  { label: '全部', value: 'all' },
  ...CATEGORIES.map(c => ({ label: c.label, value: c.key })),
])

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '分类', key: 'category', width: 110 },
  { title: '类型', key: 'type', width: 110 },
  { title: '端点', key: 'endpoint', ellipsis: true },
  { title: '权限', key: 'writable', width: 80 },
  { title: '状态', key: 'status', width: 110 },
  { title: '操作', key: 'actions', width: 280 },
]

const testing = ref<string | null>(null)
const saving = ref(false)

const picker = reactive({ open: false })
const modal = reactive({ open: false, editingId: '' as string })
type FormShape = {
  name: string
  category: ConnectionCategory
  type: string
  host: string
  port: number
  database: string
  username: string
  password: string
  pool_size: number
  rate_limit_qps: number
  writable: boolean
  description: string
}
const form = reactive<FormShape>({
  name: '', category: 'database', type: 'mysql',
  host: '', port: 3306, database: '',
  username: '', password: '',
  pool_size: 4, rate_limit_qps: 20, writable: false, description: '',
})
// params 拆三组以方便 v-model（字符串/数字/布尔）
const paramStr = reactive<Record<string, string>>({})
const paramNum = reactive<Record<string, number>>({})
const paramBool = reactive<Record<string, boolean>>({})
const credStr = reactive<Record<string, string>>({})

const browser = reactive({
  open: false, loading: false, connId: '', category: 'database' as ConnectionCategory,
  title: '',
  databases: [] as string[],
  tables: [] as string[],
  objects: [] as ObjectEntry[],
  paths: [] as PathEntry[],
  topics: [] as string[],
  prefix: '',
  path: '/',
  selected: [] as string[],
})
const bulkSaving = ref(false)

const totalRows = computed(() => {
  if (browser.category === 'database') return browser.tables.length
  if (browser.category === 'object_storage') return browser.objects.length
  if (browser.category === 'file_transfer') return browser.paths.filter(p => !p.is_dir).length
  if (browser.category === 'message_queue') return browser.topics.length
  return 0
})

const allSelected = computed(() => totalRows.value > 0 && browser.selected.length === totalRows.value)
const someSelected = computed(() => browser.selected.length > 0 && browser.selected.length < totalRows.value)

function selectableKeys(): string[] {
  if (browser.category === 'database') return [...browser.tables]
  if (browser.category === 'object_storage') return browser.objects.map(o => o.key)
  if (browser.category === 'file_transfer') return browser.paths.filter(p => !p.is_dir).map(p => p.name)
  if (browser.category === 'message_queue') return [...browser.topics]
  return []
}

function toggleAll() {
  if (allSelected.value) browser.selected = []
  else browser.selected = selectableKeys()
}

function toggleOne(key: string) {
  const i = browser.selected.indexOf(key)
  if (i >= 0) browser.selected.splice(i, 1)
  else browser.selected.push(key)
}

const modalTitle = computed(() => (modal.editingId ? '编辑数据源' : '新增数据源'))

const typeOptionsForCategory = computed(() => {
  const types = capabilities.value[form.category] || []
  return types.map(t => ({ label: t.toUpperCase(), value: t }))
})

const kafkaSecurityOptions = [
  { label: 'PLAINTEXT', value: 'PLAINTEXT' },
  { label: 'SASL_PLAINTEXT', value: 'SASL_PLAINTEXT' },
  { label: 'SASL_SSL', value: 'SASL_SSL' },
]

const apiAuthOptions = [
  { label: '无', value: 'none' },
  { label: 'Bearer Token', value: 'bearer' },
  { label: 'Basic', value: 'basic' },
  { label: 'API Key (Header)', value: 'api_key' },
]

async function load() { await store.fetchList(buildFilters()) }
function buildFilters() {
  const f: Record<string, string> = {}
  if (search.value) f.q = search.value
  if (categoryFilter.value !== 'all') f.category = categoryFilter.value
  return f
}
function onSearch() { load() }

function openCreate() {
  modal.editingId = ''
  picker.open = true
}

function selectCategory(cat: ConnectionCategory) {
  if (!(capabilities.value[cat] && capabilities.value[cat].length)) return
  resetForm()
  form.category = cat
  form.type = capabilities.value[cat][0]
  // 默认端口
  if (cat === 'database') form.port = ({ mysql: 3306, postgresql: 5432, oracle: 1521, sqlserver: 1433 } as any)[form.type] || 3306
  picker.open = false
  modal.open = true
}

function resetForm() {
  Object.assign(form, {
    name: '', category: 'database', type: 'mysql',
    host: '', port: 3306, database: '',
    username: '', password: '',
    pool_size: 4, rate_limit_qps: 20, writable: false, description: '',
  })
  for (const k of Object.keys(paramStr)) delete paramStr[k]
  for (const k of Object.keys(paramNum)) delete paramNum[k]
  for (const k of Object.keys(paramBool)) delete paramBool[k]
  for (const k of Object.keys(credStr)) delete credStr[k]
}

function openEdit(record: Connection) {
  resetForm()
  modal.editingId = record.id
  Object.assign(form, {
    name: record.name, category: record.category, type: record.type,
    host: record.host, port: record.port, database: record.database,
    username: '', password: '',
    pool_size: record.pool_size, rate_limit_qps: record.rate_limit_qps,
    writable: record.writable, description: record.description || '',
  })
  // 把 params JSON 拆回三个 reactive map
  const p = (record.params || {}) as Record<string, unknown>
  for (const [k, v] of Object.entries(p)) {
    if (typeof v === 'boolean') paramBool[k] = v
    else if (typeof v === 'number') paramNum[k] = v
    else paramStr[k] = String(v ?? '')
  }
  modal.open = true
}

function buildParams(): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(paramStr)) if (v !== '' && v !== undefined) out[k] = v
  for (const [k, v] of Object.entries(paramNum)) if (v !== undefined && v !== null && !Number.isNaN(v)) out[k] = v
  for (const [k, v] of Object.entries(paramBool)) if (typeof v === 'boolean') out[k] = v
  return out
}

function buildCredential(): Record<string, unknown> | null {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(credStr)) if (v !== '' && v !== undefined) out[k] = v
  return Object.keys(out).length ? out : null
}

async function save() {
  saving.value = true
  try {
    if (modal.editingId) {
      const payload: Record<string, unknown> = {
        host: form.host, port: form.port, database: form.database,
        params: buildParams(),
        pool_size: form.pool_size, rate_limit_qps: form.rate_limit_qps,
        writable: form.writable, description: form.description,
      }
      const cred = buildCredential()
      if (cred) payload.credential = cred
      // DB 类的密码改用顶级 username/password 兼容旧接口
      if (form.category === 'database') {
        if (form.username) payload.username = form.username
        if (form.password) payload.password = form.password
      }
      await store.update(modal.editingId, payload as any)
      message.success('已更新')
    } else {
      if (!form.name) { message.error('请填写连接名称'); return }
      const payload: Record<string, unknown> = {
        name: form.name, category: form.category, type: form.type,
        host: form.host || '', port: form.port || 0,
        database: form.database, params: buildParams(),
        pool_size: form.pool_size, rate_limit_qps: form.rate_limit_qps,
        writable: form.writable, description: form.description,
      }
      const cred = buildCredential()
      if (cred) payload.credential = cred
      if (form.category === 'database') {
        payload.username = form.username
        payload.password = form.password
      }
      await store.create(payload as any)
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

async function openBrowser(record: Connection) {
  Object.assign(browser, {
    open: true, loading: true, connId: record.id, category: record.category,
    title: record.name,
    databases: [], tables: [], objects: [], paths: [], topics: [],
    prefix: '', path: '/', selected: [],
  })
  await reloadBrowser()
}

async function reloadBrowser() {
  browser.loading = true
  browser.selected = []
  try {
    if (browser.category === 'database') {
      browser.databases = []
      const conn = store.items.find(c => c.id === browser.connId)
      if (conn?.database) browser.databases = [conn.database]
      browser.tables = await listTablesOfConnection(browser.connId)
    } else if (browser.category === 'object_storage') {
      browser.objects = await listObjects(browser.connId, browser.prefix, 200)
    } else if (browser.category === 'file_transfer') {
      browser.paths = await listPaths(browser.connId, browser.path || '/', 200)
    } else if (browser.category === 'message_queue') {
      browser.topics = await listTopics(browser.connId)
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally {
    browser.loading = false
  }
}

function enterPath(name: string) {
  const base = browser.path.endsWith('/') ? browser.path : browser.path + '/'
  browser.path = base + name
  reloadBrowser()
}

async function registerAsAsset(table: string) {
  try {
    await assetStore.create({ name: table, kind: 'table', connection_id: browser.connId, locator: { table } })
    message.success(`已注册资产：${table}`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  }
}

async function registerObjectAsAsset(obj: ObjectEntry) {
  try {
    await assetStore.create({
      name: obj.key, kind: 'document', connection_id: browser.connId,
      locator: { source_type: 's3', key: obj.key },
    } as any)
    message.success(`已注册资产：${obj.key}`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  }
}

async function registerPathAsAsset(p: PathEntry) {
  try {
    const fullPath = (browser.path.endsWith('/') ? browser.path : browser.path + '/') + p.name
    await assetStore.create({
      name: p.name, kind: 'document', connection_id: browser.connId,
      locator: { source_type: 'file', path: fullPath },
    } as any)
    message.success(`已注册资产：${p.name}`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  }
}

async function registerTopicAsAsset(topic: string) {
  try {
    await assetStore.create({
      name: topic, kind: 'document', connection_id: browser.connId,
      locator: { source_type: 'mq', topic },
    } as any)
    message.success(`已注册资产：${topic}`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  }
}

async function bulkRegister() {
  if (browser.selected.length === 0) return
  bulkSaving.value = true
  let ok = 0
  const failed: { key: string; reason: string }[] = []
  for (const sel of [...browser.selected]) {
    try {
      const payload = buildAssetPayload(sel)
      if (!payload) continue
      await assetStore.create(payload as any)
      ok += 1
    } catch (e: any) {
      failed.push({ key: sel, reason: e.response?.data?.detail || e.message || '未知错误' })
    }
  }
  // 成功的从 selected 移除；失败的保留
  browser.selected = failed.map(f => f.key)
  bulkSaving.value = false
  if (failed.length === 0) {
    message.success(`已批量注册 ${ok} 个资产`)
  } else if (ok > 0) {
    message.warning(`成功 ${ok}，失败 ${failed.length}：${failed.slice(0, 3).map(f => f.key).join('、')}${failed.length > 3 ? ' ...' : ''}`)
  } else {
    message.error(`全部失败：${failed[0].reason}`)
  }
}

function buildAssetPayload(sel: string): Record<string, unknown> | null {
  if (browser.category === 'database') {
    return { name: sel, kind: 'table', connection_id: browser.connId, locator: { table: sel } }
  }
  if (browser.category === 'object_storage') {
    return { name: sel, kind: 'document', connection_id: browser.connId,
             locator: { source_type: 's3', key: sel } }
  }
  if (browser.category === 'file_transfer') {
    const fullPath = (browser.path.endsWith('/') ? browser.path : browser.path + '/') + sel
    return { name: sel, kind: 'document', connection_id: browser.connId,
             locator: { source_type: 'file', path: fullPath } }
  }
  if (browser.category === 'message_queue') {
    return { name: sel, kind: 'document', connection_id: browser.connId,
             locator: { source_type: 'mq', topic: sel } }
  }
  return null
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
function categoryLabel(cat: string) {
  return CATEGORIES.find(c => c.key === cat)?.label || cat
}
function categoryColor(cat: string) {
  return ({ database: 'blue', object_storage: 'green', file_transfer: 'orange',
            message_queue: 'purple', api: 'magenta' } as any)[cat] || 'default'
}
function typeColor(t: string) {
  return ({
    mysql: 'blue', postgresql: 'cyan', oracle: 'red',
    sqlserver: 'purple', hive: 'orange', clickhouse: 'gold',
    s3: 'green', oss: 'green', ftp: 'orange', sftp: 'gold',
    kafka: 'purple', rest: 'magenta',
  } as any)[t] || 'default'
}

function endpointBrief(c: Connection) {
  const p = (c.params || {}) as Record<string, any>
  if (c.category === 'database') return `${c.host}:${c.port}/${c.database || '-'}`
  if (c.category === 'object_storage') return `${p.endpoint || 'aws'}/${p.bucket || '-'}`
  if (c.category === 'file_transfer') return `${c.type}://${p.host || ''}:${p.port || ''}${p.root_path || ''}`
  if (c.category === 'message_queue') return p.brokers || '-'
  if (c.category === 'api') return p.base_url || '-'
  return '-'
}

function formatSize(n: number) {
  if (!n) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`
}

watch(() => form.type, (t) => {
  if (form.category === 'database') {
    const def: Record<string, number> = { mysql: 3306, postgresql: 5432, oracle: 1521, sqlserver: 1433 }
    if (def[t] && !modal.editingId) form.port = def[t]
  }
})

onMounted(async () => {
  try {
    capabilities.value = await getCapabilities()
  } catch {
    capabilities.value = {} as Capabilities
  }
  await load()
})
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
.cp-muted { color: #9ca3af; font-size: 12px; }
.cp-hint { color: #9ca3af; font-size: 11px; margin-left: 8px; }
.cp-empty { padding: 32px; text-align: center; color: #6b7280; font-size: 13px; line-height: 1.7; }

.cp-bulk-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 12px; margin-bottom: 8px;
  background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px;
}

.cp-cat-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
}
.cp-cat-card {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 18px 12px; border: 1px solid #e5e7eb; border-radius: 10px;
  cursor: pointer; transition: all 0.15s; background: #fff;
}
.cp-cat-card:not(.cp-cat-card--disabled):hover {
  border-color: #3b82f6; box-shadow: 0 4px 12px rgba(59,130,246,0.1);
  transform: translateY(-1px);
}
.cp-cat-card--disabled { opacity: 0.45; cursor: not-allowed; }
.cp-cat-card__icon {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 14px;
}
.cp-cat-card__title { font-weight: 600; font-size: 14px; color: #111827; }
.cp-cat-card__sub { font-size: 11px; color: #6b7280; }
.cp-cat-card__hint { font-size: 11px; color: #9ca3af; }
</style>
