<template>
  <a-card title="最近告警" :bordered="false">
    <template #extra>
      <a-badge :count="unresolvedCount" :offset="[0, 0]">
        <span style="font-size: 12px; color: #888;">未处理</span>
      </a-badge>
    </template>
    <a-table :dataSource="alerts" :columns="columns" :pagination="false"
             size="small" :scroll="{ y: 320 }" row-key="id">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'level'">
          <a-tag :color="levelColor(record.level)">{{ levelLabel(record.level) }}</a-tag>
        </template>
        <template v-if="column.key === 'time'">
          {{ formatTime(record.created_at) }}
        </template>
        <template v-if="column.key === 'action'">
          <a v-if="!record.resolved" @click="$emit('resolve', record.id)" style="color: #5c7cfa;">处理</a>
          <span v-else style="color: #aaa;">已处理</span>
        </template>
      </template>
    </a-table>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AlertItem } from '../../../api/monitor'

const props = defineProps<{ alerts: AlertItem[] }>()
defineEmits<{ resolve: [id: number] }>()

const unresolvedCount = computed(() => props.alerts.filter(a => !a.resolved).length)

const columns = [
  { key: 'level', title: '级别', width: 70 },
  { key: 'message', title: '告警内容', ellipsis: true },
  { key: 'service_name', title: '服务', width: 100 },
  { key: 'time', title: '时间', width: 120 },
  { key: 'action', title: '操作', width: 70 },
]

function levelColor(level: string) {
  return { critical: 'red', warning: 'orange', info: 'blue' }[level] || 'default'
}
function levelLabel(level: string) {
  return { critical: '严重', warning: '警告', info: '提示' }[level] || level
}
function formatTime(iso: string) {
  if (!iso) return ''
  return iso.substring(11, 19)
}
</script>
