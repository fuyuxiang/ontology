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
          <a-space>
            <a v-if="!record.resolved" @click="$emit('resolve', record.id)" style="color: #5c7cfa;">处理</a>
            <a @click="showDetail(record)" style="color: #888;">详情</a>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 详情弹窗 -->
    <a-modal v-model:open="detailVisible" title="告警详情" :footer="null" width="480px">
      <div v-if="detailAlert" class="alert-detail">
        <div class="detail-row">
          <span class="detail-label">级别</span>
          <a-tag :color="levelColor(detailAlert.level)">{{ levelLabel(detailAlert.level) }}</a-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">服务</span>
          <span>{{ detailAlert.service_name }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">时间</span>
          <span>{{ formatTimeFull(detailAlert.created_at) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">状态</span>
          <a-tag :color="detailAlert.resolved ? 'green' : 'red'">{{ detailAlert.resolved ? '已处理' : '未处理' }}</a-tag>
        </div>
        <div class="detail-row" v-if="detailAlert.resolved_at">
          <span class="detail-label">处理时间</span>
          <span>{{ formatTimeFull(detailAlert.resolved_at) }}</span>
        </div>
        <div class="detail-msg">
          <span class="detail-label">告警内容</span>
          <p>{{ detailAlert.message }}</p>
        </div>
      </div>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { AlertItem } from '../../../api/monitor'

const props = defineProps<{ alerts: AlertItem[] }>()
defineEmits<{ resolve: [id: number] }>()

const unresolvedCount = computed(() => props.alerts.filter(a => !a.resolved).length)

const detailVisible = ref(false)
const detailAlert = ref<AlertItem | null>(null)

function showDetail(alert: AlertItem) {
  detailAlert.value = alert
  detailVisible.value = true
}

const columns = [
  { key: 'level', dataIndex: 'level', title: '级别', width: 70 },
  { key: 'message', dataIndex: 'message', title: '告警内容', ellipsis: true },
  { key: 'service_name', dataIndex: 'service_name', title: '服务', width: 100 },
  { key: 'time', dataIndex: 'created_at', title: '时间', width: 120 },
  { key: 'action', title: '操作', width: 100 },
]

function levelColor(level: string) {
  return { critical: 'red', warning: 'orange', info: 'blue' }[level] || 'default'
}
function levelLabel(level: string) {
  return { critical: '严重', warning: '警告', info: '提示' }[level] || level
}
function formatTime(iso: string) {
  if (!iso) return ''
  // 后端返回的是 UTC 时间（无 Z 后缀），需要加 Z 表示 UTC
  const d = new Date(iso + 'Z')
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: 'Asia/Shanghai' })
}

function formatTimeFull(iso: string) {
  if (!iso) return ''
  const d = new Date(iso + 'Z')
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: 'Asia/Shanghai' })
}
</script>

<style scoped>
.alert-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.detail-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.detail-label {
  font-size: 13px;
  color: var(--color-text-secondary, #888);
  min-width: 70px;
  flex-shrink: 0;
}
.detail-msg {
  margin-top: 8px;
}
.detail-msg p {
  margin: 4px 0 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary, #333);
}
</style>
