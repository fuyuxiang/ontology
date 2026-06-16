<template>
  <a-modal
    :open="visible"
    :title="title"
    width="780"
    @update:open="(v: boolean) => emit('update:visible', v)"
    @ok="confirm"
  >
    <div class="ap-toolbar">
      <a-segmented v-model:value="activeKind" :options="kindOptions" />
      <a-input-search v-model:value="search" placeholder="搜索资产..." style="flex: 1" allow-clear />
    </div>

    <a-table
      class="ap-table"
      size="small"
      :columns="columns"
      :data-source="filtered"
      :loading="loading"
      :pagination="{ pageSize: 8 }"
      :row-selection="rowSelection"
      row-key="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'kind'">
          <a-tag :color="kindColor(record.kind)">{{ kindLabel(record) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'locator'">
          <code class="ap-mono">{{ locatorBrief(record) }}</code>
        </template>
        <template v-else-if="column.key === 'profile'">
          <span v-if="record.profile?.row_count != null">{{ record.profile.row_count }} 行</span>
          <span v-else class="ap-muted">—</span>
        </template>
      </template>
    </a-table>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  InputSearch as AInputSearch, Modal as AModal, Segmented as ASegmented,
  Table as ATable, Tag as ATag,
} from 'ant-design-vue'
import { useAssetStore } from '../../store/asset'
import type { Asset, AssetKind } from '../../types/asset'

const props = withDefaults(defineProps<{
  visible: boolean
  title?: string
  kinds?: AssetKind[]
  multiSelect?: boolean
  preselected?: string[]
}>(), {
  title: '选择资产',
  multiSelect: false,
  preselected: () => [],
})

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'confirm', selected: Asset[]): void
}>()

const store = useAssetStore()
const search = ref('')
const activeKind = ref<string>('all')
const selectedIds = ref<string[]>([...props.preselected])

const kindOptions = computed(() => {
  const base = [{ label: '全部', value: 'all' }]
  const allowed = props.kinds || ['table', 'sql_view', 'document']
  if (allowed.includes('table')) base.push({ label: '表', value: 'table' })
  if (allowed.includes('sql_view')) base.push({ label: 'SQL 视图', value: 'sql_view' })
  if (allowed.includes('document')) base.push({ label: '文档', value: 'document' })
  return base
})

watch(() => props.visible, async (v) => {
  if (v && !store.items.length) {
    await store.fetchList()
  }
  if (v) selectedIds.value = [...props.preselected]
})

const filtered = computed(() => {
  let rows = store.items.filter(a => a.status === 'active')
  if (props.kinds && props.kinds.length) {
    rows = rows.filter(a => props.kinds!.includes(a.kind))
  }
  if (activeKind.value !== 'all') {
    rows = rows.filter(a => a.kind === activeKind.value)
  }
  const kw = search.value.trim().toLowerCase()
  if (kw) {
    rows = rows.filter(a => (a.name || '').toLowerCase().includes(kw)
      || (a.alias || '').toLowerCase().includes(kw)
      || (a.description || '').toLowerCase().includes(kw))
  }
  return rows
})

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '类型', key: 'kind', width: 120 },
  { title: '位置', key: 'locator', ellipsis: true },
  { title: '统计', key: 'profile', width: 100 },
]

const rowSelection = computed(() => ({
  type: props.multiSelect ? 'checkbox' : 'radio',
  selectedRowKeys: selectedIds.value,
  onChange: (keys: string[]) => { selectedIds.value = keys },
}))

function kindLabel(record: Asset) {
  if (record.kind === 'table') return '表'
  if (record.kind === 'sql_view') return 'SQL 视图'
  return `文档 · ${record.document_source_type}`
}
function kindColor(k: AssetKind) {
  return ({ table: 'blue', sql_view: 'cyan', document: 'gold' } as Record<AssetKind, string>)[k]
}
function locatorBrief(a: Asset) {
  const loc: any = a.locator || {}
  if (a.kind === 'table') return loc.table || '—'
  if (a.kind === 'sql_view') return (loc.sql || '').slice(0, 80) + '...'
  return loc.source_type === 'file' ? loc.file_path
    : loc.source_type === 'oss' ? `oss://${loc.bucket}/${loc.prefix || ''}`
    : loc.source_type === 'directory' ? loc.directory_path
    : loc.source_type === 'api' ? loc.api_url
    : loc.source_type === 'mq' ? `${loc.host}:${loc.port}/${loc.topic}`
    : ''
}

function confirm() {
  const map = new Map(store.items.map(a => [a.id, a]))
  const sel = selectedIds.value.map(id => map.get(id)).filter(Boolean) as Asset[]
  emit('confirm', sel)
  emit('update:visible', false)
}
</script>

<style scoped>
.ap-toolbar { display: flex; gap: 12px; margin-bottom: 12px; }
.ap-table { background: #fff; }
.ap-mono { font-family: var(--font-mono, 'Menlo', 'Consolas', monospace); font-size: 11px; }
.ap-muted { color: var(--neutral-400, #9ca3af); }
</style>
