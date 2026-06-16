<template>
  <div class="ap-page">
    <div class="ap-page__header">
      <h1 class="ap-page__title">资产目录</h1>
      <p class="ap-page__subtitle">统一管理可用数据资产</p>
    </div>

    <!-- KPI -->
    <div class="ap-stats">
      <a-statistic title="资产总数" :value="store.stats.total" />
      <a-statistic title="结构化" :value="store.stats.structured" :value-style="{ color: '#3b82f6' }" />
      <a-statistic title="非结构化" :value="store.stats.unstructured" :value-style="{ color: '#f59e0b' }" />
    </div>

    <!-- 二级 tab：结构化 / 非结构化 -->
    <a-tabs v-model:activeKey="activeCategory" class="ap-tabs" @change="onCategoryChange">
      <a-tab-pane key="all" tab="全部" />
      <a-tab-pane key="structured" tab="结构化" />
      <a-tab-pane key="unstructured" tab="非结构化" />
    </a-tabs>

    <!-- 非结构化 source_type 子过滤 -->
    <a-segmented v-if="activeCategory === 'unstructured'" v-model:value="docSubFilter"
                 :options="docFilterOptions" class="ap-doc-filter" @change="reload" />

    <!-- 工具栏 -->
    <div class="ap-toolbar">
      <a-input-search v-model:value="search" placeholder="搜索资产名称 / 别名 / 描述..." style="width:340px"
                      allow-clear @search="reload" @change="reload" />
      <a-select v-model:value="domainFilter" placeholder="按 domain 过滤" allow-clear style="width:200px"
                :options="domainOptions" @change="reload" />
      <span style="flex:1" />
      <a-segmented v-model:value="viewMode" :options="viewModeOptions" />
    </div>

    <!-- 卡片网格视图 -->
    <div v-if="viewMode === 'grid'">
      <a-empty v-if="!store.loading && store.items.length === 0"
               description="暂无资产，点击「新建资产」开始登记" style="padding:64px 0" />
      <a-row v-else :gutter="[16, 16]">
        <a-col v-for="record in store.items" :key="record.id" :xs="24" :sm="12" :lg="8" :xl="6">
          <a-card hoverable class="ap-card" :body-style="{ padding: '16px' }" @click="openDetail(record)">
            <!-- 第一行：名称 + 类型 + 别名 + 状态 -->
            <div class="ap-card__row">
              <a-typography-text strong class="ap-card__name" :ellipsis="{ tooltip: record.name }">
                {{ record.name }}
              </a-typography-text>
              <a-tag :color="kindColor(record.kind)" class="ap-card__tag">{{ kindLabel(record) }}</a-tag>
            </div>

            <div class="ap-card__row" style="margin-top:6px">
              <a-tag v-if="record.alias" color="purple" class="ap-card__tag">@{{ record.alias }}</a-tag>
              <a-tag :color="statusColor(record.status)" class="ap-card__tag">{{ record.status }}</a-tag>
            </div>

            <!-- 描述（2 行省略） -->
            <a-typography-paragraph type="secondary" class="ap-card__desc"
                                    :ellipsis="{ rows: 2, tooltip: record.description }">
              {{ record.description || locatorBrief(record) || '—' }}
            </a-typography-paragraph>

            <!-- 标签 -->
            <div v-if="(record.tags || []).length" class="ap-card__tags">
              <a-tag v-for="t in (record.tags || []).slice(0, 4)" :key="t" class="ap-card__tag-sm">{{ t }}</a-tag>
              <span v-if="(record.tags || []).length > 4" class="ap-muted">+{{ (record.tags || []).length - 4 }}</span>
            </div>

            <!-- 底部：行数 / 刷新策略 / owner -->
            <div class="ap-card__meta">
              <span>
                <span class="ap-muted">记录:</span>
                <span class="ap-card__num">{{ record.profile?.row_count?.toLocaleString() || '—' }}</span>
              </span>
              <span>
                <span class="ap-muted">刷新:</span>
                <span>{{ record.refresh_policy }}</span>
              </span>
            </div>
            <div class="ap-card__owner">
              <span class="ap-muted">连接:</span> {{ connectionName(record.connection_id) }}
              <span v-if="record.owner" style="margin-left:12px">· {{ record.owner }}</span>
            </div>

            <!-- 卡片悬停操作（点击不冒泡）-->
            <div class="ap-card__actions" @click.stop>
              <a-button type="link" size="small"
                        :disabled="record.kind === 'document'" @click="syncOne(record)">
                同步 Schema
              </a-button>
              <a-button type="link" size="small"
                        :disabled="record.kind === 'document'" @click="profileOne(record)">
                Profile
              </a-button>
              <a-popconfirm :title="`确认删除「${record.name}」？`" @confirm="del(record)">
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </div>

    <!-- 列表视图（保留兼容） -->
    <a-table v-else size="middle" :columns="columns" :data-source="store.items"
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
  Button as AButton, Card as ACard, Col as ACol,
  Empty as AEmpty, InputSearch as AInputSearch,
  Popconfirm as APopconfirm, Row as ARow, Segmented as ASegmented,
  Select as ASelect, Space as ASpace, Statistic as AStatistic,
  TabPane as ATabPane, Tabs as ATabs, Table as ATable, Tag as ATag,
  Typography, message,
} from 'ant-design-vue'
import { useAssetStore } from '../../store/asset'
import { useConnectionStore } from '../../store/connection'
import type { Asset, AssetKind, DocumentSourceType } from '../../types/asset'
import AssetDetailDrawer from '../../components/asset/AssetDetailDrawer.vue'
import CreateTableAssetDrawer from './components/CreateTableAssetDrawer.vue'
import CreateDocumentAssetDrawer from './components/CreateDocumentAssetDrawer.vue'

const ATypographyText = Typography.Text
const ATypographyParagraph = Typography.Paragraph

const store = useAssetStore()
const connStore = useConnectionStore()

type AssetCategory = 'all' | 'structured' | 'unstructured'
const activeCategory = ref<AssetCategory>('all')
const docSubFilter = ref<string>('all')
const search = ref('')
const domainFilter = ref<string | undefined>(undefined)
const viewMode = ref<'grid' | 'list'>('grid')

const viewModeOptions = [
  { label: '卡片', value: 'grid' },
  { label: '列表', value: 'list' },
]

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

function onNavigateToBinding(_assetId: string) {
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
.ap-toolbar { display: flex; gap: 12px; padding: 12px 16px; background: #fff; border-radius: 8px; margin-bottom: 12px; align-items: center; }
.ap-name { color: #1d4ed8; cursor: pointer; }
.ap-name:hover { text-decoration: underline; }
.ap-mono { font-family: 'Menlo','Consolas',monospace; font-size: 11px; color: #4b5563; }
.ap-muted { color: #9ca3af; font-size: 12px; }

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
  font-size: 14px; flex: 1; color: #111827;
  min-width: 0;
}
.ap-card__tag { font-size: 11px; }
.ap-card__tag-sm { font-size: 11px; line-height: 1.4; }
.ap-card__desc {
  margin: 8px 0 !important;
  font-size: 12px;
  color: var(--neutral-600, #4b5563);
  min-height: 36px;
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
.ap-card__num { font-weight: 600; color: #111827; margin-left: 4px; }
.ap-card__owner {
  font-size: 11px; color: var(--neutral-500, #6b7280); margin-top: 4px;
}
.ap-card__actions {
  display: flex; gap: 4px; margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--neutral-100, #e5e7eb);
  opacity: 0;
  transition: opacity 0.15s;
}
.ap-card:hover .ap-card__actions { opacity: 1; }
</style>
