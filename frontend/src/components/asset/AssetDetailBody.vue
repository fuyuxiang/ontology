<template>
  <div v-if="!asset" class="adb-empty">
    <a-spin v-if="loading" />
    <a-empty v-else description="选择一个资产查看详情" />
  </div>
  <div v-else class="adb">
    <!-- 顶部摘要 -->
    <div class="adb-header">
      <div class="adb-meta">
        <span class="adb-label">连接</span>
        <span class="adb-value">{{ asset.connection_id || '—' }}</span>
        <span class="adb-label">所有者</span>
        <span class="adb-value">{{ asset.owner || '—' }}</span>
        <span class="adb-label">领域</span>
        <span class="adb-value">{{ asset.domain || '—' }}</span>
        <span class="adb-label">缓存 TTL</span>
        <span class="adb-value">{{ asset.cache_ttl_seconds }}s</span>
        <span class="adb-label">同步时间</span>
        <span class="adb-value">{{ asset.schema_synced_at || '从未' }}</span>
      </div>
      <a-tag v-for="t in (asset.tags || [])" :key="t" color="default">{{ t }}</a-tag>
    </div>

    <a-row :gutter="16" class="adb-body">
      <!-- 左：DE 视角 -->
      <a-col :span="14">
        <h4 class="adb-title">数据视角</h4>

        <!-- table / sql_view -->
        <template v-if="asset.kind !== 'document'">
          <div class="adb-actions">
            <a-button size="small" :loading="syncing" @click="onSyncSchema">同步 Schema</a-button>
            <a-button size="small" :loading="profiling" @click="onProfile">跑 Profile</a-button>
          </div>
          <h5 class="adb-subtitle">Schema 快照（{{ (asset.schema_snapshot || []).length }} 列）</h5>
          <a-table
            v-if="(asset.schema_snapshot || []).length"
            size="small"
            :columns="schemaCols"
            :data-source="asset.schema_snapshot || []"
            :pagination="false"
            row-key="name"
          />
          <a-empty v-else description="尚无 schema，点击「同步 Schema」" />

          <h5 class="adb-subtitle">Profile</h5>
          <a-descriptions v-if="asset.profile" size="small" bordered :column="2">
            <a-descriptions-item label="行数">{{ asset.profile.row_count ?? '—' }}</a-descriptions-item>
            <a-descriptions-item label="采样时间">{{ asset.profile.sampled_at || '—' }}</a-descriptions-item>
            <a-descriptions-item label="新鲜度">{{ asset.profile.max_updated_at || '—' }}</a-descriptions-item>
          </a-descriptions>
          <a-empty v-else description="尚无 profile，点击「跑 Profile」" :image-style="{ height: '40px' }" />

          <h5 class="adb-subtitle">数据预览（前 20 行）</h5>
          <a-table
            v-if="preview && preview.columns && preview.rows"
            size="small"
            :columns="(preview.columns || []).map(c => ({ title: c, dataIndex: c, key: c }))"
            :data-source="(preview.rows || []).map((row) => Object.fromEntries((preview!.columns || []).map((c, j) => [c, row[j]])).valueOf() as any)"
            :pagination="false"
            :scroll="{ x: 'max-content' }"
            row-key="$rowIdx"
          />
          <a-empty v-else description="预览失败或暂无数据" />
        </template>

        <!-- document -->
        <template v-else>
          <h5 class="adb-subtitle">非结构化资产 · {{ asset.document_source_type }}</h5>
          <a-descriptions size="small" bordered :column="1">
            <a-descriptions-item label="locator">
              <pre class="adb-pre">{{ JSON.stringify(asset.locator, null, 2) }}</pre>
            </a-descriptions-item>
            <a-descriptions-item label="摘要 / 抽样">
              <pre class="adb-pre">{{ asset.parsed_summary || '（无解析摘要）' }}</pre>
            </a-descriptions-item>
            <a-descriptions-item v-if="preview && preview.files" label="文件清单">
              <a-list size="small" :data-source="preview.files" :pagination="false">
                <template #renderItem="{ item }">
                  <a-list-item>{{ item }}</a-list-item>
                </template>
              </a-list>
            </a-descriptions-item>
            <a-descriptions-item v-if="preview && preview.note" label="提示">
              {{ preview.note }}
            </a-descriptions-item>
          </a-descriptions>
        </template>

        <!-- 质量历史 -->
        <h5 class="adb-subtitle">最近质量探针</h5>
        <a-empty v-if="metrics.length === 0" description="暂无探针记录" :image-style="{ height: '40px' }" />
        <a-table
          v-else
          size="small"
          :columns="metricCols"
          :data-source="metrics.slice(0, 8)"
          :pagination="false"
          row-key="id"
        />
      </a-col>

      <!-- 右：建模视角 + usage -->
      <a-col :span="10">
        <h4 class="adb-title">建模 / 使用</h4>
        <a-button type="primary" size="small" @click="onNavigateToBinding">
          在 ObjectType 编辑器中绑定
        </a-button>

        <a-descriptions size="small" :column="1" class="adb-usage">
          <a-descriptions-item label="被绑定的 ObjectType">
            <a-tag v-for="b in (usage?.usage.bindings || [])" :key="b.id" color="blue">
              {{ b.id.slice(0, 8) }} · {{ b.note || '' }}
            </a-tag>
            <span v-if="!(usage?.usage.bindings || []).length" class="adb-muted">—</span>
          </a-descriptions-item>
          <a-descriptions-item label="构建会话引用">
            <a-tag v-for="s in (usage?.usage.builder_sessions || [])" :key="s.id">
              {{ s.id.slice(0, 8) }}
            </a-tag>
            <span v-if="!(usage?.usage.builder_sessions || []).length" class="adb-muted">—</span>
          </a-descriptions-item>
          <a-descriptions-item label="规则引用">
            <span v-if="!(usage?.usage.rules || []).length" class="adb-muted">—</span>
            <a-tag v-for="r in (usage?.usage.rules || [])" :key="r.id">{{ r.id.slice(0, 8) }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="动作引用">
            <span v-if="!(usage?.usage.actions || []).length" class="adb-muted">—</span>
            <a-tag v-for="a in (usage?.usage.actions || [])" :key="a.id">{{ a.id.slice(0, 8) }}</a-tag>
          </a-descriptions-item>
        </a-descriptions>

        <h5 class="adb-subtitle">敏感度标签</h5>
        <a-empty
          v-if="!asset.sensitivity_tags || Object.keys(asset.sensitivity_tags).length === 0"
          description="未标记"
          :image-style="{ height: '32px' }"
        />
        <div v-else class="adb-sensitivity">
          <a-tag v-for="(level, col) in asset.sensitivity_tags" :key="col" :color="level === 'pii' ? 'red' : 'orange'">
            {{ col }}：{{ level }}
          </a-tag>
        </div>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import {
  Button as AButton, Col as ACol, Descriptions as ADescriptions,
  DescriptionsItem as ADescriptionsItem, Empty as AEmpty, List as AList,
  ListItem as AListItem, Row as ARow, Spin as ASpin, Table as ATable, Tag as ATag,
} from 'ant-design-vue'
import type { Asset, AssetWithUsage, PreviewResult } from '../../types/asset'
import type { QualityMetric } from '../../types/quality'

defineProps<{
  asset: Asset | null
  usage: AssetWithUsage | null
  preview: PreviewResult | null
  metrics: QualityMetric[]
  loading: boolean
  syncing: boolean
  profiling: boolean
  onSyncSchema: () => void
  onProfile: () => void
  onNavigateToBinding: () => void
}>()

const schemaCols = [
  { title: '列名', dataIndex: 'name', key: 'name' },
  { title: '类型', dataIndex: 'type', key: 'type' },
  {
    title: '主键', dataIndex: 'is_pk', key: 'is_pk',
    customRender: ({ value }: any) => (value ? '✓' : ''),
  },
  {
    title: '可空', dataIndex: 'nullable', key: 'nullable',
    customRender: ({ value }: any) => (value ? '✓' : ''),
  },
  { title: '注释', dataIndex: 'comment', key: 'comment' },
]

const metricCols = [
  { title: '类型', dataIndex: 'kind', key: 'kind' },
  { title: '列', dataIndex: 'column_name', key: 'column_name' },
  {
    title: '值', dataIndex: 'value_numeric', key: 'value_numeric',
    customRender: ({ record }: any) => record.value_numeric ?? record.value_text ?? '—',
  },
  { title: '严重度', dataIndex: 'severity', key: 'severity' },
  { title: '时间', dataIndex: 'measured_at', key: 'measured_at' },
]
</script>

<style scoped>
.adb-empty { padding: 32px; text-align: center; }
.adb { display: flex; flex-direction: column; gap: 12px; }
.adb-header {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 8px 12px; background: var(--neutral-50, #f8f9fa); border-radius: 6px;
}
.adb-meta { display: flex; gap: 12px; flex-wrap: wrap; font-size: 12px; }
.adb-label { color: var(--neutral-500, #6b7280); margin-right: 4px; }
.adb-value { color: var(--neutral-900, #111827); font-weight: 500; }
.adb-body { margin-top: 12px; }
.adb-title { margin: 0 0 8px; font-size: 14px; color: var(--neutral-700, #374151); }
.adb-subtitle { margin: 16px 0 8px; font-size: 12px; color: var(--neutral-500, #6b7280); }
.adb-actions { display: flex; gap: 8px; margin-bottom: 8px; }
.adb-pre {
  font-family: var(--font-mono, 'Menlo', 'Consolas', monospace);
  font-size: 11px; white-space: pre-wrap; word-break: break-all;
  margin: 0; max-height: 220px; overflow-y: auto;
}
.adb-usage { margin-top: 12px; }
.adb-muted { color: var(--neutral-400, #9ca3af); font-size: 12px; }
.adb-sensitivity { display: flex; flex-wrap: wrap; gap: 4px; }
</style>
