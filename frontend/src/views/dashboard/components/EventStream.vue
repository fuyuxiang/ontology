<template>
  <a-card title="系统事件" :bordered="false">
    <template #extra>
      <a-select v-model:value="filter" size="small" style="width: 100px;">
        <a-select-option value="all">全部</a-select-option>
        <a-select-option value="deploy">部署</a-select-option>
        <a-select-option value="config">配置</a-select-option>
        <a-select-option value="user">用户</a-select-option>
        <a-select-option value="asset">资产</a-select-option>
        <a-select-option value="binding">绑定</a-select-option>
        <a-select-option value="execution">执行</a-select-option>
      </a-select>
    </template>
    <p v-if="error" role="alert">{{ error }} <button @click="$emit('retry')">重试</button></p>
    <p v-else>{{ connected ? '实时事件已连接' : '正在连接实时事件…' }}</p>
    <div class="event-list">
      <div v-for="(ev, i) in filteredEvents" :key="i" class="event-item">
        <span class="event-time">{{ formatPlatformDateTime(ev.time) }}</span>
        <a-tag :color="tagColor(ev.type)" size="small">{{ ev.type }}</a-tag>
        <span class="event-desc">{{ ev.description }}</span>
      </div>
      <a-empty v-if="filteredEvents.length === 0" description="暂无系统事件" />
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { formatPlatformDateTime } from '../../../utils/platformTime'
import { ref, computed } from 'vue'

interface SystemEvent {
  time: string
  type: string
  description: string
}

const props = defineProps<{ events: SystemEvent[]; error?:string; connected?:boolean }>()
defineEmits<{ (event:'retry'):void }>()
const filter = ref('all')

const filteredEvents = computed(() => {
  if (filter.value === 'all') return props.events
  return props.events.filter(e => e.type === filter.value)
})

function tagColor(type: string) {
  return { deploy: 'blue', config: 'purple', user: 'green', alert: 'red' }[type] || 'default'
}
</script>

<style scoped>
.event-list {
  min-height: 320px;
  max-height: 400px;
  overflow-y: auto;
}
.event-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--neutral-200, #e5e7eb);
}
.event-time {
  font-family: monospace;
  font-size: 12px;
  color: var(--neutral-600, #6b7280);
  flex-shrink: 0;
}
.event-desc {
  font-size: 13px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
