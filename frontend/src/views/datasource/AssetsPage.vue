<template>
  <div class="ap-page">
    <div class="ap-page__header">
      <h1 class="ap-page__title">数据接入 · 资产目录</h1>
      <p class="ap-page__subtitle">本平台所有可用的结构化与非结构化资产；本体绑定、AI 召回、规则、动作均从此选取</p>
    </div>

    <!-- KPI -->
    <div class="ap-stats">
      <a-statistic title="资产总数" :value="store.stats.total" />
      <a-statistic title="表" :value="store.stats.tables" :value-style="{ color: '#3b82f6' }" />
      <a-statistic title="SQL 视图" :value="store.stats.views" :value-style="{ color: '#06b6d4' }" />
      <a-statistic title="文档" :value="store.stats.documents" :value-style="{ color: '#f59e0b' }" />
      <span class="ap-spacer" />
      <a-dropdown>
        <a-button type="primary">
          <template #icon><PlusOutlined /></template>
          新建资产 <DownOutlined />
        </a-button>
        <template #overlay>
          <a-menu>
            <a-menu-item @click="openCreate('table')">表 / SQL 视图</a-menu-item>
            <a-menu-divider />
            <a-menu-item @click="openDoc('file')">文档：上传文件</a-menu-item>
            <a-menu-item @click="openDoc('oss')">文档：对象存储 OSS</a-menu-item>
            <a-menu-item @click="openDoc('directory')">文档：目录扫描</a-menu-item>
            <a-menu-item @click="openDoc('api')">文档：HTTP API</a-menu-item>
            <a-menu-item @click="openDoc('mq')">文档：MQ topic</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>

    <!-- 二级 tab -->
    <a-tabs v-model:activeKey="activeKind" class="ap-tabs" @change="reload">
      <a-tab-pane key="all" tab="全部" />
      <a-tab-pane key="table" tab="表" />
      <a-tab-pane key="sql_view" tab="SQL 视图" />
      <a-tab-pane key="document" tab="文档" />
    </a-tabs>

    <!-- 文档 source_type 子过滤 -->
    <a-segmented v-if="activeKind === 'document'" v-model:value="docSubFilter"
                 :options="docFilterOptions" class="ap-doc-filter" @change="reload" />

    <!-- 工具栏 -->
    <div class="ap-toolbar">
      <a-input-search v-model:value="search" placeholder="搜索资产名称 / 别名 / 描述..." style="width:340px"
                      allow-clear @search="reload" @change="reload" />
      <a-select v-model:value="domainFilter" placeholder="按 domain 过滤" allow-clear style="width:200px"
                :options="domainOptions" @change="reload" />
    </div>

    <!-- 列表 -->
    <a-table size="middle" :columns="columns" :data-source="store.items"
             :loading="store.loading" :pagination="{ pageSize: 20 }" row-key="id">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <a class="ap-name" @click="openDetail(record)">{{ record.name }}</a>
          <a-tag v-if="record.alias" color="purple" style="margin-left:8px">@{{ record.alias }}</a-tag>
        </template>
        <template v-else-if="column.key === 'kind'">
          <a-tag :color="kindColor(record.kind)">{{ kindLabel(record) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'locator'">
          <code class="ap-mono">{{ locatorBrief(record) }}</code>
        </template>
        <template v-else-if="column.key === 'connection'">
          {{ connectionName(record.connection_id) }}
        </template>
        <template v-else-if="column.key === 'profile'">
          <span v-if="record.profile?.row_count != null">{{ record.profile.row_count }} 行</span>
          <span v-else class="ap-muted">—</span>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space :size="4" wrap>
            <a-button type="link" size="small" @click="openDetail(record)">详情</a-button>
            <a-button type="link" size="small"
                      :disabled="record.kind === 'document'" @click="syncOne(record)">
              同步 Schema
            </a-button>
            <a-button type="link" size="small"
                      :disabled="record.kind === 'document'" @click="profileOne(record)">
              Profile
            </a-button>
            <a-popconfirm :title="`确认删除「${record.name}」？被引用时会被拒绝。`" @confirm="del(record)">
              <a-button type="link" size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
      <template #emptyText>
        <a-empty description="暂无资产，点击「新建资产」开始登记" />
      </template>
    </a-table>

    <!-- 详情抽屉 -->
    <AssetDetailDrawer
      v-model:visible="detail.visible"
      :asset-id="detail.assetId"
      @navigate-to-binding="onNavigateToBinding"
    />

    <!-- 新建结构化资产 -->
    <CreateTableAssetDrawer
      v-model:open="createTable.open"
      @success="reload"
    />

    <!-- 5 种文档接入 -->
    <CreateDocumentAssetDrawer
      v-model:open="createDoc.open"
      :source-type="createDoc.kind"
      @success="reload"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  Button as AButton, Dropdown as ADropdown, Empty as AEmpty,
  InputSearch as AInputSearch, Menu as AMenu, MenuItem as AMenuItem,
  MenuDivider as AMenuDivider, Popconfirm as APopconfirm,
  Segmented as ASegmented, Select as ASelect, Space as ASpace,
  Statistic as AStatistic, TabPane as ATabPane, Tabs as ATabs,
  Table as ATable, Tag as ATag, message,
} from 'ant-design-vue'
import { DownOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { useAssetStore } from '../../store/asset'
import { useConnectionStore } from '../../store/connection'
import type { Asset, AssetKind, DocumentSourceType } from '../../types/asset'
import AssetDetailDrawer from '../../components/asset/AssetDetailDrawer.vue'
import CreateTableAssetDrawer from './components/CreateTableAssetDrawer.vue'
import CreateDocumentAssetDrawer from './components/CreateDocumentAssetDrawer.vue'

const store = useAssetStore()
const connStore = useConnectionStore()

const activeKind = ref<string>('all')
const docSubFilter = ref<string>('all')
const search = ref('')
const domainFilter = ref<string | undefined>(undefined)

const docFilterOptions = [
  { label: '全部', value: 'all' },
  { label: '文件', value: 'file' },
  { label: '对象存储', value: 'oss' },
  { label: '目录', value: 'directory' },
  { label: 'API', value: 'api' },
  { label: 'MQ', value: 'mq' },
]

const detail = reactive({ visible: false, assetId: null as string | null })
const createTable = reactive({ open: false })
const createDoc = reactive({ open: false, kind: 'file' as DocumentSourceType })

const columns = [
  { title: '名称', key: 'name' },
  { title: '类型', key: 'kind', width: 130 },
  { title: '位置', key: 'locator', ellipsis: true },
  { title: '连接', key: 'connection', width: 160, ellipsis: true },
  { title: '统计', key: 'profile', width: 100 },
  { title: '状态', key: 'status', width: 100 },
  { title: '操作', key: 'actions', width: 280 },
]

const domainOptions = computed(() => {
  const s = new Set<string>()
  for (const a of store.items) if (a.domain) s.add(a.domain)
  return Array.from(s).map(d => ({ label: d, value: d }))
})

async function reload() {
  await Promise.all([
    store.fetchList(buildFilters()),
    connStore.items.length === 0 ? connStore.fetchList() : Promise.resolve(),
  ])
}
function buildFilters() {
  const f: any = {}
  if (activeKind.value !== 'all') f.kind = activeKind.value
  if (activeKind.value === 'document' && docSubFilter.value !== 'all') {
    f.document_source_type = docSubFilter.value
  }
  if (search.value) f.q = search.value
  if (domainFilter.value) f.domain = domainFilter.value
  return f
}

function openDetail(record: Asset) {
  detail.assetId = record.id
  detail.visible = true
}

function openCreate(_kind: string) { createTable.open = true }
function openDoc(kind: DocumentSourceType) { createDoc.kind = kind; createDoc.open = true }

async function syncOne(record: Asset) {
  try {
    const r = await store.syncSchema(record.id)
    const { added, removed, type_changed } = r.diff
    const msg = `Schema 同步完成，新增 ${added.length} / 删除 ${removed.length} / 类型变更 ${type_changed.length}`
    if (added.length || removed.length || type_changed.length) message.warning(msg)
    else message.success(msg)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  }
}

async function profileOne(record: Asset) {
  try {
    const r = await store.profile(record.id)
    message.success(`Profile 完成：${r.row_count} 行`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  }
}

async function del(record: Asset) {
  try {
    await store.remove(record.id)
    message.success('已删除')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败（可能被引用）')
  }
}

function onNavigateToBinding(assetId: string) {
  // 跳转到本体建模 BindingTab。由调用方实现路由跳转；这里做兜底提示。
  message.info('请前往本体建模模块的 ObjectType 编辑器进行绑定')
}

function kindLabel(a: Asset) {
  if (a.kind === 'table') return '表'
  if (a.kind === 'sql_view') return 'SQL 视图'
  return `文档 · ${a.document_source_type}`
}
function kindColor(k: AssetKind) {
  return ({ table: 'blue', sql_view: 'cyan', document: 'gold' } as Record<AssetKind, string>)[k]
}
function statusColor(s: string) {
  return ({ active: 'green', deprecated: 'orange', broken: 'red' } as any)[s] || 'default'
}
function locatorBrief(a: Asset) {
  const loc: any = a.locator || {}
  if (a.kind === 'table') return loc.table || '—'
  if (a.kind === 'sql_view') return ((loc.sql || '') as string).slice(0, 80) + (loc.sql && (loc.sql as string).length > 80 ? '...' : '')
  return loc.source_type === 'file' ? loc.file_path
    : loc.source_type === 'oss' ? `oss://${loc.bucket}/${loc.prefix || ''}`
    : loc.source_type === 'directory' ? loc.directory_path
    : loc.source_type === 'api' ? loc.api_url
    : loc.source_type === 'mq' ? `${loc.host}:${loc.port}/${loc.topic}`
    : ''
}
function connectionName(id: string | null) {
  if (!id) return '—'
  const c = connStore.items.find(c => c.id === id)
  return c ? c.name : id.slice(0, 8) + '...'
}

onMounted(reload)
</script>

<style scoped>
.ap-page { padding: 24px; }
.ap-page__header { margin-bottom: 16px; }
.ap-page__title { font-size: 24px; font-weight: 600; color: #111827; margin: 0; }
.ap-page__subtitle { font-size: 13px; color: #6b7280; margin-top: 4px; }
.ap-stats {
  display: flex; align-items: center; gap: 32px; padding: 16px;
  background: #fff; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 12px;
}
.ap-spacer { flex: 1; }
.ap-tabs { background: #fff; padding: 0 16px; border-radius: 8px; margin-bottom: 12px; }
.ap-doc-filter { margin-bottom: 12px; }
.ap-toolbar { display: flex; gap: 12px; padding: 12px 16px; background: #fff; border-radius: 8px; margin-bottom: 12px; }
.ap-name { color: #1d4ed8; cursor: pointer; }
.ap-name:hover { text-decoration: underline; }
.ap-mono { font-family: 'Menlo','Consolas',monospace; font-size: 11px; color: #4b5563; }
.ap-muted { color: #9ca3af; }
</style>
