<template>
  <a-card title="资源使用率" :bordered="false">
    <div class="gauges-row">
      <div class="gauge-item">
        <div class="gauge-chart">
          <svg viewBox="0 0 100 60" class="gauge-svg" aria-hidden="true">
            <path class="gauge-track" d="M10 50 A40 40 0 0 1 90 50" fill="none" stroke="#f1f3f5" stroke-width="10" stroke-linecap="round" />
            <path class="gauge-progress"
              d="M10 50 A40 40 0 0 1 90 50"
              fill="none"
              :stroke="gaugeColor(cpuPercent)"
              :stroke-dasharray="gaugeDashArray(cpuPercent)"
              stroke-width="10"
              stroke-linecap="round"
            />
          </svg>
          <span class="gauge-value" :style="{ color: gaugeColor(cpuPercent) }">{{ formatPercent(cpuPercent) }}</span>
        </div>
        <div class="gauge-label">CPU</div>
        <div class="gauge-detail">{{ data ? data.cpu_percent.toFixed(1) + '%' : '-' }}</div>
      </div>
      <div class="gauge-item">
        <div class="gauge-chart">
          <svg viewBox="0 0 100 60" class="gauge-svg" aria-hidden="true">
            <path class="gauge-track" d="M10 50 A40 40 0 0 1 90 50" fill="none" stroke="#f1f3f5" stroke-width="10" stroke-linecap="round" />
            <path class="gauge-progress"
              d="M10 50 A40 40 0 0 1 90 50"
              fill="none"
              :stroke="gaugeColor(memoryPercent)"
              :stroke-dasharray="gaugeDashArray(memoryPercent)"
              stroke-width="10"
              stroke-linecap="round"
            />
          </svg>
          <span class="gauge-value" :style="{ color: gaugeColor(memoryPercent) }">{{ formatPercent(memoryPercent) }}</span>
        </div>
        <div class="gauge-label">内存</div>
        <div class="gauge-detail">{{ data ? data.memory_used_gb + 'G / ' + data.memory_total_gb + 'G' : '-' }}</div>
      </div>
      <div class="gauge-item">
        <div class="gauge-chart">
          <svg viewBox="0 0 100 60" class="gauge-svg" aria-hidden="true">
            <path class="gauge-track" d="M10 50 A40 40 0 0 1 90 50" fill="none" stroke="#f1f3f5" stroke-width="10" stroke-linecap="round" />
            <path class="gauge-progress"
              d="M10 50 A40 40 0 0 1 90 50"
              fill="none"
              :stroke="gaugeColor(diskPercent)"
              :stroke-dasharray="gaugeDashArray(diskPercent)"
              stroke-width="10"
              stroke-linecap="round"
            />
          </svg>
          <span class="gauge-value" :style="{ color: gaugeColor(diskPercent) }">{{ formatPercent(diskPercent) }}</span>
        </div>
        <div class="gauge-label">磁盘</div>
        <div class="gauge-detail">{{ data ? data.disk_used_gb + 'G / ' + data.disk_total_gb + 'G' : '-' }}</div>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ResourceMetrics } from '../../../api/monitor'
import { clampPercent, gaugeColor, gaugeDashArray } from './resourceGaugeData'

const props = defineProps<{ data: ResourceMetrics | null }>()

const cpuPercent = computed(() => clampPercent(props.data?.cpu_percent ?? 0))
const memoryPercent = computed(() => clampPercent(props.data?.memory_percent ?? 0))
const diskPercent = computed(() => clampPercent(props.data?.disk_percent ?? 0))

function formatPercent(value: number): string {
  return `${Math.round(clampPercent(value))}%`
}
</script>

<style scoped>
.gauges-row {
  display: flex;
  justify-content: space-around;
  gap: 16px;
}
.gauge-item {
  flex: 1 1 0;
  min-width: 0;
  text-align: center;
}
.gauge-chart {
  position: relative;
  width: min(100%, 160px);
  height: 108px;
  margin: 0 auto;
}
.gauge-svg {
  display: block;
  width: 100%;
  height: 100%;
}
.gauge-value {
  position: absolute;
  left: 50%;
  bottom: 12px;
  transform: translateX(-50%);
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
}
.gauge-label {
  font-size: 14px;
  font-weight: 500;
  margin-top: 4px;
}
.gauge-detail {
  font-size: 12px;
  color: var(--color-text-secondary, #888);
  white-space: nowrap;
}

@media (max-width: 640px) {
  .gauges-row {
    flex-direction: column;
  }
  .gauge-chart {
    width: 160px;
  }
}
</style>
