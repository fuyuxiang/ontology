<template>
  <a-card title="系统事件" :bordered="false">
    <template #extra>
      <a-select v-model:value="filter" size="small" style="width: 100px;">
        <a-select-option value="all">全部</a-select-option>
        <a-select-option value="deploy">部署</a-select-option>
        <a-select-option value="config">配置</a-select-option>
        <a-select-option value="user">用户</a-select-option>
      </a-select>
    </template>
    <div class="event-list">
      <div v-for="(ev, i) in filteredEvents" :key="i" class="event-item">
        <span class="event-time">{{ ev.time }}</span>
        <a-tag :color="tagColor(ev.type)" size="small">{{ ev.type }}</a-tag>
        <span class="event-desc">{{ ev.description }}</span>
      </div>
      <a-empty v-if="filteredEvents.length === 0" description="暂无系统事件" />
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface SystemEvent {
  time: string
  type: string
  description: string
}

const props = defineProps<{ events: SystemEvent[] }>()
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
  border-bottom: 1px solid var(--color-border-secondary, #f0f0f0);
}
.event-time {
  font-family: monospace;
  font-size: 12px;
  color: var(--color-text-secondary, #888);
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
