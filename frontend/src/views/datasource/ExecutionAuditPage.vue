<template>
  <div class="ea-page">
    <div class="ea-page__header">
      <h1 class="ea-page__title">数据接入 · 执行审计</h1>
      <p class="ea-page__subtitle">所有 SQL 必经的执行闸口（/execute）审计日志：谁、为何、查了哪个 Asset、跑多久、有没有命中缓存、是否被拦截</p>
    </div>

    <!-- 24h 统计 -->
    <div class="ea-stats">
      <a-statistic title="24h 执行总数" :value="store.stats?.total ?? 0" />
      <a-statistic title="缓存命中率"
                   :value="((store.stats?.cache_hit_rate ?? 0) * 100).toFixed(1)"
                   suffix="%" :value-style="{ color: '#10b981' }" />
      <a-statistic title="拒绝率"
                   :value="((store.stats?.blocked_rate ?? 0) * 100).toFixed(2)"
                   suffix="%" :value-style="{ color: '#ef4444' }" />
      <a-statistic title="平均延迟"
                   :value="(store.stats?.avg_duration_ms ?? 0).toFixed(0)"
                   suffix="ms" />
      <span class="ea-spacer" />
      <a-button @click="refresh">刷新</a-button>
    </div>

    <!-- 过滤 -->
    <div class="ea-toolbar">
      <a-input v-model:value="filters.purpose" placeholder="purpose 过滤..." style="width:200px" allow-clear @change="reload" />
      <a-input v-model:value="filters.asset_id" placeholder="asset_id 过滤..." style="width:240px" allow-clear @change="reload" />
      <a-segmented v-model:value="filters.bucket" :options="bucketOptions" @change="reload" />
    </div>

    <!-- 列表 -->
    <a-table size="middle" :columns="columns" :data-source="store.items"
             :loading="store.loading" :pagination="{ pageSize: 30 }"
             row-key="id" @row-click="openDetail">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'purpose'">
          <a-tag :color="purposeColor(record.purpose)">{{ record.purpose }}</a-tag>
        </template>
        <template v-else-if="column.key === 'asset_id'">
          <code class="ea-mono">{{ record.asset_id?.slice(0, 8) || '—' }}...</code>
        </template>
        <template v-else-if="column.key === 'duration_ms'">
          <span :style="{ color: durationColor(record.duration_ms) }">{{ record.duration_ms }}ms</span>
        </template>
        <template v-else-if="column.key === 'cache_hit'">
          <a-tag v-if="record.cache_hit" color="green">命中</a-tag>
          <span v-else class="ea-muted">—</span>
        </template>
        <template v-else-if="column.key === 'blocked'">
          <a-tag v-if="record.blocked" color="red">{{ record.block_reason }}</a-tag>
          <a-tag v-else color="default">OK</a-tag>
        </template>
        <template v-else-if="column.key === 'started_at'">
          <span class="ea-mono">{{ fmt(record.started_at) }}</span>
        </template>
        <template v-else-if="column.key === 'sql_preview'">
          <code class="ea-mono ea-truncate">{{ record.sql_preview || '—' }}</code>
        </template>
      </template>
    </a-table>

    <!-- 详情抽屉 -->
    <a-drawer :open="!!detail.id" title="执行记录详情" width="640"
              @update:open="detail.id = ''">
      <div v-if="detail.log">
        <a-descriptions size="small" bordered :column="2">
          <a-descriptions-item label="开始">{{ fmt(detail.log.started_at) }}</a-descriptions-item>
          <a-descriptions-item label="耗时">{{ detail.log.duration_ms }}ms</a-descriptions-item>
          <a-descriptions-item label="purpose">{{ detail.log.purpose }}</a-descriptions-item>
          <a-descriptions-item label="返回行数">{{ detail.log.rows_returned }}</a-descriptions-item>
          <a-descriptions-item label="资产">{{ detail.log.asset_id || '—' }}</a-descriptions-item>
          <a-descriptions-item label="连接">{{ detail.log.connection_id || '—' }}</a-descriptions-item>
          <a-descriptions-item label="缓存">{{ detail.log.cache_hit ? '命中' : '未命中' }}</a-descriptions-item>
          <a-descriptions-item label="状态">{{ detail.log.blocked ? '被拒绝：' + detail.log.block_reason : '正常' }}</a-descriptions-item>
          <a-descriptions-item label="用户">{{ detail.log.user_id || '匿名' }}</a-descriptions-item>
          <a-descriptions-item label="SQL hash">
            <code class="ea-mono">{{ detail.log.sql_hash.slice(0, 16) }}...</code>
          </a-descriptions-item>
        </a-descriptions>
        <h5 class="ea-subtitle">SQL（前 500 字符）</h5>
        <pre class="ea-pre">{{ detail.log.sql_preview }}</pre>
        <h5 class="ea-subtitle">参数（已脱敏）</h5>
        <pre class="ea-pre">{{ JSON.stringify(detail.log.params_redacted, null, 2) }}</pre>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import {
  Button as AButton, Descriptions as ADescriptions,
  DescriptionsItem as ADescriptionsItem, Drawer as ADrawer,
  Input as AInput, Segmented as ASegmented, Statistic as AStatistic,
  Table as ATable, Tag as ATag,
} from 'ant-design-vue'
import { useExecutionStore } from '../../store/execution'
import type { ExecutionLog } from '../../types/execution'

const store = useExecutionStore()

const filters = reactive({
  purpose: '', asset_id: '', bucket: 'all' as string,
})

const bucketOptions = [
  { label: '全部', value: 'all' },
  { label: '正常', value: 'ok' },
  { label: '被拒绝', value: 'blocked' },
  { label: '缓存命中', value: 'cache' },
]

const detail = reactive({ id: '', log: null as ExecutionLog | null })

const columns = [
  { title: '时间', key: 'started_at', width: 160 },
  { title: 'purpose', key: 'purpose', width: 160 },
  { title: 'asset_id', key: 'asset_id', width: 110 },
  { title: 'SQL', key: 'sql_preview', ellipsis: true },
  { title: '行数', dataIndex: 'rows_returned', key: 'rows_returned', width: 70 },
  { title: '耗时', key: 'duration_ms', width: 80 },
  { title: '缓存', key: 'cache_hit', width: 70 },
  { title: '状态', key: 'blocked', width: 110 },
]

async function reload() {
  const f: any = { limit: 200 }
  if (filters.purpose) f.purpose = filters.purpose
  if (filters.asset_id) f.asset_id = filters.asset_id
  if (filters.bucket === 'blocked') f.blocked = true
  if (filters.bucket === 'ok') f.blocked = false
  await Promise.all([store.fetchList(f), store.fetchStats()])
  if (filters.bucket === 'cache') {
    store.items = store.items.filter(l => l.cache_hit)
  }
}
function refresh() { reload() }

async function openDetail(record: ExecutionLog) {
  detail.id = record.id
  try {
    detail.log = await store.getOne(record.id)
  } catch {
    detail.log = record
  }
}

function fmt(s: string | null) {
  if (!s) return '—'
  const d = new Date(s)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.toTimeString().slice(0, 8)}`
}
function purposeColor(p: string) {
  if (p.startsWith('mnp')) return 'blue'
  if (p.startsWith('scene')) return 'cyan'
  if (p.startsWith('probe')) return 'gold'
  if (p.startsWith('builder')) return 'purple'
  if (p.startsWith('action')) return 'red'
  return 'default'
}
function durationColor(ms: number) {
  if (ms > 2000) return '#ef4444'
  if (ms > 500) return '#f59e0b'
  return '#10b981'
}

onMounted(reload)
</script>

<style scoped>
.ea-page { padding: 24px; }
.ea-page__header { margin-bottom: 16px; }
.ea-page__title { font-size: 24px; font-weight: 600; color: #111827; margin: 0; }
.ea-page__subtitle { font-size: 13px; color: #6b7280; margin-top: 4px; }
.ea-stats { display: flex; gap: 32px; padding: 16px; background: #fff; border-radius: 8px; margin-bottom: 12px; }
.ea-spacer { flex: 1; }
.ea-toolbar { display: flex; gap: 12px; padding: 12px 16px; background: #fff; border-radius: 8px; margin-bottom: 12px; }
.ea-mono { font-family: 'Menlo','Consolas',monospace; font-size: 11px; color: #4b5563; }
.ea-truncate { display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ea-muted { color: #9ca3af; }
.ea-subtitle { margin: 12px 0 6px; font-size: 12px; color: #6b7280; }
.ea-pre {
  font-family: 'Menlo','Consolas',monospace; font-size: 11px;
  white-space: pre-wrap; padding: 8px 12px;
  background: #f9fafb; border-radius: 6px; max-height: 240px; overflow-y: auto;
}
</style>
