<template>
  <div class="ql-tab">
    <a-row :gutter="16" class="ql-layout">
      <!-- 左：资产列表 -->
      <a-col :span="8">
        <div class="ql-card">
          <div class="ql-card__title">资产列表</div>
          <a-input-search v-model:value="search" placeholder="搜索资产..." allow-clear style="margin: 8px 0" />
          <a-list size="small" :data-source="filteredAssets" :pagination="false" class="ql-asset-list">
            <template #renderItem="{ item }">
              <a-list-item :class="{ active: selected?.id === item.id }" @click="select(item)">
                <div class="ql-asset">
                  <span class="ql-asset__name">{{ item.name }}</span>
                  <a-tag size="small" :color="kindColor(item.kind)">{{ item.kind }}</a-tag>
                </div>
              </a-list-item>
            </template>
          </a-list>
        </div>
      </a-col>

      <!-- 右：探针指标 -->
      <a-col :span="16">
        <div v-if="!selected" class="ql-card ql-empty">
          <a-empty description="选择左侧资产查看质量指标" />
        </div>
        <template v-else>
          <div class="ql-card">
            <div class="ql-row">
              <div>
                <div class="ql-card__title">{{ selected.name }}</div>
                <div class="ql-card__sub">{{ selected.kind }} · {{ locatorBrief(selected) }}</div>
              </div>
              <a-space>
                <a-button :loading="running.row_count" @click="run('row_count')">行数</a-button>
                <a-button :loading="running.schema_drift" @click="run('schema_drift')">Schema 漂移</a-button>
                <a-dropdown v-if="columnOptions.length">
                  <a-button>列指标 <DownOutlined /></a-button>
                  <template #overlay>
                    <a-menu>
                      <a-menu-item v-for="c in columnOptions" :key="c.value"
                                   @click="runWithColumn('null_ratio', c.value)">
                        {{ c.label }} - 空值率
                      </a-menu-item>
                      <a-menu-divider />
                      <a-menu-item v-for="c in columnOptions" :key="'d-'+c.value"
                                   @click="runWithColumn('distinct_count', c.value)">
                        {{ c.label }} - 去重计数
                      </a-menu-item>
                    </a-menu>
                  </template>
                </a-dropdown>
              </a-space>
            </div>

            <a-row :gutter="16" class="ql-metrics">
              <a-col :span="6">
                <a-statistic title="行数（最新）" :value="latestNumeric('row_count')" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="主键唯一性"
                             :value="(latestNumeric('pk_uniqueness') ?? 0) === 0 ? '✓' : `重复 ${latestNumeric('pk_uniqueness')}`"
                             :value-style="{ color: latestNumeric('pk_uniqueness') === 0 ? '#10b981' : '#ef4444' }" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="Schema 漂移"
                             :value="schemaDriftLabel"
                             :value-style="{ color: schemaDriftSeverity === 'error' ? '#ef4444' : schemaDriftSeverity === 'warning' ? '#f59e0b' : '#10b981' }" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="探针记录数" :value="metrics.length" />
              </a-col>
            </a-row>
          </div>

          <!-- 历史 -->
          <div class="ql-card">
            <div class="ql-card__title">探针历史</div>
            <a-empty v-if="metrics.length === 0" description="暂无探针记录" />
            <a-table v-else size="small" :columns="historyCols" :data-source="metrics"
                     :pagination="{ pageSize: 12 }" row-key="id" />
          </div>
        </template>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  Button as AButton, Col as ACol, Dropdown as ADropdown, Empty as AEmpty,
  InputSearch as AInputSearch, List as AList, ListItem as AListItem,
  Menu as AMenu, MenuItem as AMenuItem, MenuDivider as AMenuDivider,
  Row as ARow, Space as ASpace, Statistic as AStatistic, Table as ATable,
  Tag as ATag, message,
} from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import { useAssetStore } from '../../../store/asset'
import { runProbe, listAssetProbes } from '../../../api/probe'
import type { Asset, AssetKind } from '../../../types/asset'
import type { QualityKind, QualityMetric } from '../../../types/quality'

const store = useAssetStore()
const search = ref('')
const selected = ref<Asset | null>(null)
const metrics = ref<QualityMetric[]>([])
const running = reactive<Record<QualityKind | string, boolean>>({})

const filteredAssets = computed(() => {
  let rows = store.items.filter(a => a.kind !== 'document')
  const kw = search.value.trim().toLowerCase()
  if (kw) rows = rows.filter(a => a.name.toLowerCase().includes(kw))
  return rows
})

const columnOptions = computed(() => {
  const cols = selected.value?.schema_snapshot || []
  return cols.map(c => ({ label: c.name, value: c.name }))
})

const historyCols = [
  { title: '类型', dataIndex: 'kind', key: 'kind' },
  { title: '列', dataIndex: 'column_name', key: 'column_name' },
  {
    title: '值', dataIndex: 'value_numeric', key: 'value_numeric',
    customRender: ({ record }: any) => record.value_numeric ?? record.value_text ?? '—',
  },
  { title: '严重度', dataIndex: 'severity', key: 'severity' },
  { title: '时间', dataIndex: 'measured_at', key: 'measured_at' },
]

async function reload() {
  await store.fetchList()
}

async function select(asset: Asset) {
  selected.value = asset
  metrics.value = await listAssetProbes(asset.id, {})
}

async function run(kind: QualityKind, column?: string) {
  if (!selected.value) return
  running[kind] = true
  try {
    await runProbe(kind, { asset_id: selected.value.id, column: column || null })
    metrics.value = await listAssetProbes(selected.value.id, {})
    message.success(`探针「${kind}」已完成`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || e.message)
  } finally {
    running[kind] = false
  }
}

async function runWithColumn(kind: QualityKind, column: string) {
  await run(kind, column)
}

function latestNumeric(kind: QualityKind): number | null {
  const m = metrics.value.find(x => x.kind === kind)
  return m?.value_numeric ?? null
}

const schemaDriftSeverity = computed(() => {
  const m = metrics.value.find(x => x.kind === 'schema_drift')
  return m?.severity || 'ok'
})

const schemaDriftLabel = computed(() => {
  const sev = schemaDriftSeverity.value
  if (sev === 'error') return '存在差异'
  if (sev === 'warning') return '新增列'
  return '稳定'
})

function kindColor(k: AssetKind) {
  return ({ table: 'blue', sql_view: 'cyan', document: 'gold' } as Record<AssetKind, string>)[k]
}
function locatorBrief(a: Asset) {
  const loc: any = a.locator || {}
  if (a.kind === 'table') return loc.table
  if (a.kind === 'sql_view') return (loc.sql || '').slice(0, 60) + '...'
  return ''
}

onMounted(reload)
</script>

<style scoped>
.ql-tab { padding: 16px; }
.ql-layout { min-height: 70vh; }
.ql-card {
  background: #fff; border-radius: 8px; padding: 16px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 12px;
}
.ql-card__title { font-size: 14px; font-weight: 600; color: #111827; }
.ql-card__sub { font-size: 12px; color: #6b7280; margin-top: 2px; }
.ql-row { display: flex; align-items: flex-start; justify-content: space-between; }
.ql-metrics { margin-top: 16px; }
.ql-asset-list :deep(.ant-list-item) { cursor: pointer; padding: 8px 12px; }
.ql-asset-list :deep(.ant-list-item:hover) { background: #f3f4f6; }
.ql-asset-list :deep(.ant-list-item.active) { background: #e0f2fe; }
.ql-asset { display: flex; align-items: center; gap: 8px; width: 100%; }
.ql-asset__name { flex: 1; font-size: 13px; }
.ql-empty { display: flex; align-items: center; justify-content: center; min-height: 360px; }
</style>
