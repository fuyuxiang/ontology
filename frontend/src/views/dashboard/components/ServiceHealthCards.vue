<template>
  <a-card :bordered="false" class="health-card">
    <div class="health-grid">
      <div v-for="svc in services" :key="svc.name" class="health-item"
           :class="{ unhealthy: svc.status === 'unhealthy', warning: svc.status === 'warning' }">
        <span class="status-dot" :class="svc.status"></span>
        <div class="info">
          <span class="name">{{ svc.name }}</span>
          <span class="latency">{{ svc.response_ms != null ? svc.response_ms.toFixed(0) + 'ms' : (svc.status === 'healthy' ? '正常' : '不可达') }}</span>
        </div>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
defineProps<{
  services: Array<{ name: string; status: string; response_ms: number | null }>
}>()
</script>

<style scoped>
.health-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.health-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 6px;
  background: var(--color-bg-container, #fafafa);
  min-width: 140px;
  transition: background 0.2s;
}
.health-item:hover {
  background: var(--color-bg-elevated, #f0f0f0);
}
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.healthy { background: #12b886; }
.status-dot.warning { background: #f59f00; animation: pulse 1.5s infinite; }
.status-dot.unhealthy { background: #fa5252; animation: pulse 1.5s infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.info {
  display: flex;
  flex-direction: column;
}
.name { font-size: 13px; font-weight: 500; }
.latency { font-size: 11px; color: var(--color-text-secondary, #888); }
</style>
