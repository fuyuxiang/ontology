<template>
  <div class="traces-view">
    <header class="traces-view__header">
      <h2>运行追踪</h2>
      <p class="traces-view__desc">Agent 调用历史记录，包含输入输出、耗时和状态</p>
    </header>

    <div class="traces-view__filters">
      <a-select v-model:value="filters.agent_id" placeholder="全部 Agent" allow-clear style="width: 200px" @change="fetchTraces">
        <a-select-option v-for="a in agents" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
      </a-select>
      <a-select v-model:value="filters.status" placeholder="全部状态" allow-clear style="width: 120px" @change="fetchTraces">
        <a-select-option value="ok">成功</a-select-option>
        <a-select-option value="error">失败</a-select-option>
      </a-select>
      <a-range-picker v-model:value="dateRange" @change="onDateChange" />
    </div>

    <a-table
      :columns="columns"
      :data-source="traces"
      :loading="loading"
      :pagination="pagination"
      row-key="id"
      :expandable="{ expandedRowRender }"
      @change="onTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="record.status === 'ok' ? 'green' : 'red'">{{ record.status === 'ok' ? '成功' : '失败' }}</a-tag>
        </template>
        <template v-if="column.key === 'latency_ms'">
          {{ record.latency_ms != null ? `${record.latency_ms}ms` : '-' }}
        </template>
        <template v-if="column.key === 'created_at'">
          {{ formatTime(record.created_at) }}
        </template>
      </template>
      <template #expandedRowRender="{ record }">
        <div class="traces-view__detail">
          <div class="traces-view__detail-block">
            <strong>输入：</strong>
            <pre>{{ expandedData[record.id]?.input_text || record.input_text }}</pre>
          </div>
          <div class="traces-view__detail-block">
            <strong>输出：</strong>
            <pre>{{ expandedData[record.id]?.output_text || record.output_text }}</pre>
          </div>
        </div>
      </template>
    </a-table>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { tracesApi, type TraceItem } from '../../api/ops'
import { agentsApi } from '../../api/agents'
import type { Dayjs } from 'dayjs'

const agents = ref<{ id: string; name: string }[]>([])
const traces = ref<TraceItem[]>([])
const loading = ref(false)
const expandedData = ref<Record<string, TraceItem>>({})
const dateRange = ref<[Dayjs, Dayjs] | null>(null)

const filters = reactive({
  agent_id: undefined as string | undefined,
  status: undefined as string | undefined,
  date_from: undefined as string | undefined,
  date_to: undefined as string | undefined,
})

const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const columns = [
  { title: 'Agent', dataIndex: 'agent_name', key: 'agent_name', width: 160 },
  { title: '输入', dataIndex: 'input_text', key: 'input_text', ellipsis: true },
  { title: '状态', key: 'status', width: 80 },
  { title: '耗时', key: 'latency_ms', width: 100 },
  { title: '时间', key: 'created_at', width: 170 },
]

function formatTime(iso: string | null) {
  if (!iso) return '-'
  return iso.replace('T', ' ').slice(0, 19)
}

function onDateChange(dates: [Dayjs, Dayjs] | null) {
  if (dates) {
    filters.date_from = dates[0].format('YYYY-MM-DD')
    filters.date_to = dates[1].format('YYYY-MM-DD') + 'T23:59:59'
  } else {
    filters.date_from = undefined
    filters.date_to = undefined
  }
  fetchTraces()
}

function onTableChange(pag: any) {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchTraces()
}

async function fetchTraces() {
  loading.value = true
  try {
    const res = await tracesApi.list({
      ...filters,
      page: pagination.current,
      page_size: pagination.pageSize,
    })
    traces.value = res.items
    pagination.total = res.total
  } finally {
    loading.value = false
  }
}

async function loadFullTrace(record: TraceItem) {
  if (!expandedData.value[record.id]) {
    const full = await tracesApi.get(record.id)
    expandedData.value[record.id] = full
  }
}

onMounted(async () => {
  const list = await agentsApi.list()
  agents.value = list.map((a: any) => ({ id: a.id, name: a.name }))
  fetchTraces()
})
</script>

<style scoped>
.traces-view { padding: 24px; }
.traces-view__header h2 { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
.traces-view__desc { color: var(--text-secondary, #666); font-size: 13px; margin-bottom: 16px; }
.traces-view__filters { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.traces-view__detail { padding: 12px 0; }
.traces-view__detail-block { margin-bottom: 12px; }
.traces-view__detail-block pre { margin: 4px 0 0; white-space: pre-wrap; word-break: break-all; font-size: 12px; background: var(--bg-secondary, #f5f5f5); padding: 8px 12px; border-radius: 6px; max-height: 300px; overflow-y: auto; }
</style>
