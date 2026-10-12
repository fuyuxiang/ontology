<template>
  <div class="ap-page">
    <div class="ap-page__header">
      <div>
      <h1 class="ap-page__title">{{ text("资产目录") }}</h1>
      <p class="ap-page__subtitle">{{ text("统一管理可用数据资产") }}</p>
      </div>
      <a-dropdown>
        <a-button type="primary" :disabled="!canEdit">{{ text("新建资产") }} <DownOutlined /></a-button>
        <template #overlay>
          <a-menu @click="onCreateAsset">
            <a-menu-item key="table">{{ text("表 / SQL 视图") }}</a-menu-item>
            <a-menu-divider />
            <a-menu-item key="file">{{ text("上传文件") }}</a-menu-item>
            <a-menu-item key="oss">{{ text("对象存储") }}</a-menu-item>
            <a-menu-item key="directory">{{ text("本地目录") }}</a-menu-item>
            <a-menu-item key="api">HTTP API</a-menu-item>
            <a-menu-item key="mq">{{ text("消息队列") }}</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>

    <!-- KPI -->
    <div class="ap-stats">
      <a-statistic :title="text('资产总数')" :value="store.stats.total" />
      <a-statistic :title="text('结构化')" :value="store.stats.structured" :value-style="{ color: '#3b82f6' }" />
      <a-statistic :title="text('非结构化')" :value="store.stats.unstructured" :value-style="{ color: '#f59e0b' }" />
    </div>

    <!-- 二级 tab：结构化 / 非结构化 -->
    <a-tabs v-model:active-key="activeCategory" class="ap-tabs" @change="onCategoryChange">
      <a-tab-pane key="all" :tab="text('全部')" />
      <a-tab-pane key="structured" :tab="text('结构化')" />
      <a-tab-pane key="unstructured" :tab="text('非结构化')" />
    </a-tabs>

    <!-- 非结构化 source_type 子过滤 -->
    <a-segmented v-if="activeCategory === 'unstructured'" v-model:value="docSubFilter"
                 :options="docFilterOptions" class="ap-doc-filter" @change="reload" />

    <!-- 工具栏 -->
    <div class="ap-toolbar">
      <a-input-search v-model:value="search" :placeholder="text('搜索资产名称 / 别名 / 描述...')" style="width:340px"
                      allow-clear @search="reload" @change="reload" />
      <a-select v-model:value="domainFilter" :placeholder="text('按 domain 过滤')" allow-clear style="width:200px"
                :options="domainOptions" @change="reload" />
      <span style="flex:1" />
      <a-segmented v-model:value="viewMode" :options="viewModeOptions" />
    </div>
    <a-alert v-if="store.error" type="error" show-icon :message="text('资产加载失败')"
             :description="store.error" class="ap-load-error">
      <template #action><a-button size="small" @click="reload">{{ text("重试") }}</a-button></template>
    </a-alert>

    <!-- 卡片网格视图 -->
    <a-spin v-if="viewMode === 'grid'" :spinning="store.loading" :tip="text('正在加载资产…')">
      <a-empty v-if="!store.loading && !store.error && store.items.length === 0"
               :description="hasFilters ? text('没有匹配的资产，请调整搜索或筛选条件') : text('暂无资产，点击「新建资产」开始登记')" style="padding:64px 0" />
      <a-row v-else :gutter="[16, 16]">
        <a-col v-for="record in store.items" :key="record.id" :xs="24" :sm="12" :lg="8" :xl="6">
          <a-card hoverable class="ap-card" :body-style="{ padding: '16px' }" @click="openDetail(record)">
            <!-- 第一行：名称 + 类型 + 别名 + 状态 -->
            <div class="ap-card__row">
              <button type="button" class="ap-card__name" :title="record.name" @click.stop="openDetail(record)">
                {{ record.name }}
              </button>
              <a-tag :color="kindColor(record.kind)" class="ap-card__tag">{{ kindLabel(record) }}</a-tag>
            </div>

            <div class="ap-card__row" style="margin-top:6px">
              <a-tag v-if="record.alias" color="purple" class="ap-card__tag" :title="record.alias">@{{ record.alias }}</a-tag>
              <a-tag :color="statusColor(record.status)" class="ap-card__tag">{{ statusLabel(record.status) }}</a-tag>
            </div>

            <!-- 描述（2 行省略） -->
            <a-tooltip :title="record.description || locatorBrief(record) || undefined">
              <p class="ap-card__desc">{{ record.description || locatorBrief(record) || '—' }}</p>
            </a-tooltip>

            <!-- 标签 -->
            <div v-if="(record.tags || []).length" class="ap-card__tags">
              <a-tag v-for="t in (record.tags || []).slice(0, 4)" :key="t" class="ap-card__tag-sm" :title="t">{{ t }}</a-tag>
              <span v-if="(record.tags || []).length > 4" class="ap-muted">+{{ (record.tags || []).length - 4 }}</span>
            </div>

            <!-- 底部：行数 / 刷新策略 / owner -->
            <div class="ap-card__meta">
              <span>
                <span class="ap-muted">{{ text("记录:") }}</span>
                <span class="ap-card__num">{{ record.profile?.row_count?.toLocaleString() || '—' }}</span>
              </span>
              <span>
                <span class="ap-muted">{{ text("刷新:") }}</span>
                <span>{{ refreshPolicyLabel(record.refresh_policy) }}</span>
              </span>
            </div>
            <div class="ap-card__owner">
              <span class="ap-muted">{{ text("连接:") }}</span> {{ connectionName(record.connection_id) }}
              <span v-if="record.owner" style="margin-left:12px">· {{ record.owner }}</span>
            </div>

            <!-- 卡片悬停操作（点击不冒泡）-->
            <div class="ap-card__actions" @click.stop>
              <a-button type="link" size="small"
                        :disabled="!canEdit || record.kind === 'document' || !!pendingActions[record.id]" :loading="pendingActions[record.id] === 'sync'" @click="syncOne(record)"> {{ text("同步 Schema") }} </a-button>
              <a-button type="link" size="small"
                        :disabled="!canEdit || record.kind === 'document' || !!pendingActions[record.id]" :loading="pendingActions[record.id] === 'profile'" @click="profileOne(record)">
                Profile
              </a-button>
              <a-popconfirm :title="text('确认删除「{name}」？', { name: record.name })" :ok-text="text('删除')" :cancel-text="text('取消')" :ok-button-props="{ danger: true }" :overlay-style="{ maxWidth: 'min(480px, calc(100vw - 32px))' }" @confirm="del(record)">
                <a-button type="link" size="small" danger :disabled="!canDelete || !!pendingActions[record.id]" :loading="pendingActions[record.id] === 'delete'">{{ text("删除") }}</a-button>
              </a-popconfirm>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <!-- 列表视图（保留兼容） -->
    <a-table v-else size="middle" :columns="columns" :data-source="store.items"
             :loading="store.loading" :pagination="{ current: currentPage, pageSize: 20, onChange: (page: number) => currentPage = page }" :scroll="{ x: 1060 }" row-key="id">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <button type="button" class="ap-name" :title="record.name" @click="openDetail(record as Asset)">{{ record.name }}</button>
          <a-tag v-if="record.alias" color="purple" style="margin-left:8px">@{{ record.alias }}</a-tag>
        </template>
        <template v-else-if="column.key === 'kind'">
          <a-tag :color="kindColor((record as Asset).kind)">{{ kindLabel(record as Asset) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'locator'">
          <code class="ap-mono">{{ locatorBrief(record as Asset) }}</code>
        </template>
        <template v-else-if="column.key === 'connection'">
          {{ connectionName(record.connection_id) }}
        </template>
        <template v-else-if="column.key === 'profile'">
          <span v-if="record.profile?.row_count != null">{{ record.profile.row_count }} {{ text("行") }}</span>
          <span v-else class="ap-muted">—</span>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space :size="4" wrap>
            <a-button type="link" size="small" @click="openDetail(record as Asset)">{{ text("详情") }}</a-button>
            <a-button type="link" size="small"
                      :disabled="!canEdit || record.kind === 'document' || !!pendingActions[record.id]" :loading="pendingActions[record.id] === 'sync'" @click="syncOne(record as Asset)"> {{ text("同步 Schema") }} </a-button>
            <a-button type="link" size="small"
                      :disabled="!canEdit || record.kind === 'document' || !!pendingActions[record.id]" :loading="pendingActions[record.id] === 'profile'" @click="profileOne(record as Asset)">
              Profile
            </a-button>
            <a-popconfirm :title="text('确认删除「{name}」？被引用时会被拒绝。', { name: record.name })" :ok-text="text('删除')" :cancel-text="text('取消')" :ok-button-props="{ danger: true }" :overlay-style="{ maxWidth: 'min(480px, calc(100vw - 32px))' }" @confirm="del(record as Asset)">
              <a-button type="link" size="small" danger :disabled="!canDelete || !!pendingActions[record.id]" :loading="pendingActions[record.id] === 'delete'">{{ text("删除") }}</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
      <template #emptyText>
        <a-empty v-if="!store.error" :description="hasFilters ? text('没有匹配的资产，请调整搜索或筛选条件') : text('暂无资产，点击「新建资产」开始登记')" />
      </template>
    </a-table>

    <!-- 详情抽屉 -->
    <AssetDetailDrawer
      v-model:visible="detail.visible"
      :asset-id="detail.assetId"
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
import { useProductText } from "../../composables/useProductText"
const { text } = useProductText()

import { useManagementPermission } from '../../composables/useManagementPermission'
const { canEdit, canDelete } = useManagementPermission('entity:write')
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  Alert as AAlert, Button as AButton, Card as ACard, Col as ACol, Dropdown as ADropdown,
  Empty as AEmpty, InputSearch as AInputSearch,
  Popconfirm as APopconfirm, Row as ARow, Segmented as ASegmented,
  Menu as AMenu, MenuItem as AMenuItem, MenuDivider as AMenuDivider,
  Select as ASelect, Space as ASpace, Spin as ASpin, Statistic as AStatistic,
  TabPane as ATabPane, Tabs as ATabs, Table as ATable, Tag as ATag, Tooltip as ATooltip,
  message,
} from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import { useAssetStore } from '../../store/asset'
import { useConnectionStore } from '../../store/connection'
import type { Asset, AssetKind, DocumentSourceType } from '../../types/asset'
import AssetDetailDrawer from '../../components/asset/AssetDetailDrawer.vue'
import CreateTableAssetDrawer from './components/CreateTableAssetDrawer.vue'
import CreateDocumentAssetDrawer from './components/CreateDocumentAssetDrawer.vue'

const store = useAssetStore()
const connStore = useConnectionStore()

type AssetCategory = 'all' | 'structured' | 'unstructured'
const activeCategory = ref<AssetCategory>('all')
const docSubFilter = ref<string>('all')
const search = ref('')
const domainFilter = ref<string | undefined>(undefined)
const viewMode = ref<'grid' | 'list'>('grid')
const currentPage = ref(1)
const pendingActions = reactive<Record<string, 'sync' | 'profile' | 'delete'>>({})
const knownDomains = ref<string[]>([])
const hasFilters = computed(() => !!search.value || !!domainFilter.value || activeCategory.value !== 'all')

const viewModeOptions = computed(() => [
  { label: text("卡片"), value: 'grid' },
  { label: text("列表"), value: 'list' },
])

const docFilterOptions = computed(() => [
  { label: text("全部"), value: 'all' },
  { label: text("文件"), value: 'file' },
  { label: text("对象存储"), value: 'oss' },
  { label: text("目录"), value: 'directory' },
  { label: 'API', value: 'api' },
  { label: 'MQ', value: 'mq' },
])

const detail = reactive({ visible: false, assetId: null as string | null })
const createTable = reactive({ open: false })
const createDoc = reactive({ open: false, kind: 'file' as DocumentSourceType })

const columns = computed(() => [
  { title: text("名称"), key: 'name', width: 210, ellipsis: true },
  { title: text("类型"), key: 'kind', width: 130 },
  { title: text("位置"), key: 'locator', width: 210, ellipsis: true },
  { title: text("连接"), key: 'connection', width: 160, ellipsis: true },
  { title: text("统计"), key: 'profile', width: 100 },
  { title: text("状态"), key: 'status', width: 100 },
  { title: text("操作"), key: 'actions', width: 280, fixed: 'right' as const },
])

const domainOptions = computed(() => {
  const s = new Set(knownDomains.value)
  if (domainFilter.value) s.add(domainFilter.value)
  return Array.from(s).map(d => ({ label: d, value: d }))
})

async function reload() {
  currentPage.value = 1
  await Promise.all([
    store.fetchList(buildFilters()),
    connStore.items.length === 0 ? connStore.fetchList() : Promise.resolve(),
  ])
}
watch(() => store.items, (items) => {
  knownDomains.value = [...new Set([...knownDomains.value, ...items.flatMap(a => a.domain ? [a.domain] : [])])]
}, { immediate: true })

function onCreateAsset({ key }: { key: string | number }) {
  if (key === 'table') createTable.open = true
  else {
    createDoc.kind = key as DocumentSourceType
    createDoc.open = true
  }
}
function buildFilters() {
  const f: any = {}
  if (activeCategory.value === 'structured') {
    f.kinds = 'table,sql_view'
  } else if (activeCategory.value === 'unstructured') {
    f.kind = 'document'
    if (docSubFilter.value !== 'all') f.document_source_type = docSubFilter.value
  }
  if (search.value) f.q = search.value
  if (domainFilter.value) f.domain = domainFilter.value
  return f
}

function onCategoryChange() {
  if (activeCategory.value !== 'unstructured') docSubFilter.value = 'all'
  reload()
}

function openDetail(record: Asset) {
  detail.assetId = record.id
  detail.visible = true
}

async function syncOne(record: Asset) {
  if (pendingActions[record.id]) return
  pendingActions[record.id] = 'sync'
  try {
    const r = await store.syncSchema(record.id)
    const { added, removed, type_changed } = r.diff
    const msg = text('Schema 同步完成，新增 {added} / 删除 {removed} / 类型变更 {changed}', { added: added.length, removed: removed.length, changed: type_changed.length })
    if (added.length || removed.length || type_changed.length) message.warning(msg)
    else message.success(msg)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally {
    delete pendingActions[record.id]
  }
}

async function profileOne(record: Asset) {
  if (pendingActions[record.id]) return
  pendingActions[record.id] = 'profile'
  try {
    const r = await store.profile(record.id)
    message.success(text('Profile 完成：{count} 行', { count: r.row_count }))
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally {
    delete pendingActions[record.id]
  }
}

async function del(record: Asset) {
  if (pendingActions[record.id]) return
  pendingActions[record.id] = 'delete'
  try {
    await store.remove(record.id)
    message.success(text("已删除"))
  } catch (e: any) {
    message.error(e.response?.data?.detail || text("删除失败（可能被引用）"))
  } finally {
    delete pendingActions[record.id]
  }
}

function kindLabel(a: Asset) {
  if (a.kind === 'table') return text("表")
  if (a.kind === 'sql_view') return text("SQL 视图")
  const labels: Record<string, string> = { file: text("文件"), oss: text("对象存储"), s3: text("对象存储"), directory: text("目录"), api: 'API', mq: text("消息队列") }
  return a.document_source_type ? text('文档 · {type}', { type: labels[a.document_source_type] || a.document_source_type }) : text("文档")
}
function kindColor(k: AssetKind) {
  return ({ table: 'blue', sql_view: 'cyan', document: 'gold' } as Record<AssetKind, string>)[k]
}
function statusColor(s: string) {
  return ({ active: 'green', deprecated: 'orange', broken: 'red' } as any)[s] || 'default'
}
function statusLabel(status: string) {
  return ({ active: text("可用"), deprecated: text("已弃用"), broken: text("异常") } as Record<string, string>)[status] || status
}
function refreshPolicyLabel(policy: string) {
  return ({ on_demand: text("按需"), hourly: text("每小时"), daily: text("每日") } as Record<string, string>)[policy] || policy
}
function locatorBrief(a: Asset) {
  const loc: any = a.locator || {}
  if (a.kind === 'table') return loc.table || '—'
  if (a.kind === 'sql_view') return ((loc.sql || '') as string).slice(0, 80) + (loc.sql && (loc.sql as string).length > 80 ? '...' : '')
  return loc.source_type === 'file' ? loc.file_path || loc.path || ''
    : loc.source_type === 's3' ? loc.key || ''
    : loc.source_type === 'oss' ? `oss://${loc.bucket}/${loc.prefix || ''}`
    : loc.source_type === 'directory' ? loc.directory_path
    : loc.source_type === 'api' ? loc.api_url || loc.path || ''
    : loc.source_type === 'mq' ? loc.host ? `${loc.host}:${loc.port || 9092}/${loc.topic}` : loc.topic || ''
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
.ap-page__header { margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.ap-page__title { font-size: 24px; font-weight: 600; color: var(--neutral-900, #111827); margin: 0; }
.ap-page__subtitle { font-size: 13px; color: var(--neutral-600, #6b7280); margin-top: 4px; }
.ap-stats {
  display: flex; align-items: center; gap: 32px; padding: 16px;
  background: var(--neutral-0, #fff); border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 12px;
}
.ap-spacer { flex: 1; }
.ap-tabs { background: var(--neutral-0, #fff); padding: 0 16px; border-radius: 8px; margin-bottom: 12px; }
.ap-doc-filter { margin-bottom: 12px; }
.ap-toolbar { display: flex; flex-wrap: wrap; gap: 12px; padding: 12px 16px; background: var(--neutral-0, #fff); border-radius: 8px; margin-bottom: 12px; align-items: center; }
.ap-load-error { margin-bottom: 16px; }
.ap-name { color: var(--semantic-600, #1d4ed8); cursor: pointer; border: 0; background: none; padding: 0; font: inherit; text-align: left; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ap-name:hover { text-decoration: underline; }
.ap-mono { font-family: 'Menlo','Consolas',monospace; font-size: 11px; color: var(--neutral-700, #4b5563); }
.ap-muted { color: var(--neutral-600, #6b7280); font-size: 12px; }

/* 卡片网格视图 */
.ap-card {
  height: 100%;
  border: 1px solid var(--neutral-100, #e5e7eb);
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.ap-card:hover {
  border-color: var(--semantic-300, #93c5fd);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
  transform: translateY(-1px);
}
.ap-card__row {
  display: flex; align-items: center; gap: 6px;
  flex-wrap: wrap;
}
.ap-card__name {
  font-size: 14px; flex: 1; color: var(--neutral-900, #111827);
  min-width: 0; border: 0; padding: 0; background: none; text-align: left; font-weight: 600;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer;
}
.ap-card__tag { font-size: 11px; }
.ap-card__tag-sm { font-size: 11px; line-height: 1.4; }
.ap-card__desc {
  margin: 8px 0 !important;
  font-size: 12px;
  color: var(--neutral-600, #4b5563);
  min-height: 36px;
  line-height: 18px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}
.ap-card__tags {
  display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;
  min-height: 22px;
}
.ap-card__meta {
  display: flex; justify-content: space-between;
  font-size: 12px; color: var(--neutral-700, #374151);
  padding-top: 8px;
  border-top: 1px dashed var(--neutral-100, #e5e7eb);
}
.ap-card__num { font-weight: 600; color: var(--neutral-900, #111827); margin-left: 4px; }
.ap-card__owner {
  font-size: 11px; color: var(--neutral-500, #6b7280); margin-top: 4px;
  overflow-wrap: anywhere;
}
.ap-card__actions {
  display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--neutral-100, #e5e7eb);
}
.ap-card__tag, .ap-card__tag-sm { max-width: 100%; overflow: hidden; text-overflow: ellipsis; }
.ap-card__name:focus-visible, .ap-name:focus-visible { outline: 2px solid var(--primary, #2563eb); outline-offset: 3px; border-radius: 2px; }
</style>
