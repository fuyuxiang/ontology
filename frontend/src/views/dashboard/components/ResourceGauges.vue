<template>
  <a-card title="资源使用率" :bordered="false">
    <div class="gauges-row">
      <div class="gauge-item">
        <div ref="cpuEl" class="gauge-chart"></div>
        <div class="gauge-label">CPU</div>
        <div class="gauge-detail">{{ data ? data.cpu_percent.toFixed(1) + '%' : '-' }}</div>
      </div>
      <div class="gauge-item">
        <div ref="memEl" class="gauge-chart"></div>
        <div class="gauge-label">内存</div>
        <div class="gauge-detail">{{ data ? data.memory_used_gb + 'G / ' + data.memory_total_gb + 'G' : '-' }}</div>
      </div>
      <div class="gauge-item">
        <div ref="diskEl" class="gauge-chart"></div>
        <div class="gauge-label">磁盘</div>
        <div class="gauge-detail">{{ data ? data.disk_used_gb + 'G / ' + data.disk_total_gb + 'G' : '-' }}</div>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ResourceMetrics } from '../../../api/monitor'

const props = defineProps<{ data: ResourceMetrics | null }>()

const cpuEl = ref<HTMLElement>()
const memEl = ref<HTMLElement>()
const diskEl = ref<HTMLElement>()
let cpuChart: echarts.ECharts | null = null
let memChart: echarts.ECharts | null = null
let diskChart: echarts.ECharts | null = null

function getColor(value: number): string {
  if (value < 60) return '#20c997'
  if (value < 85) return '#f59f00'
  return '#fa5252'
}

function makeOption(value: number) {
  return {
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      min: 0,
      max: 100,
      radius: '90%',
      progress: { show: true, width: 12 },
      axisLine: { lineStyle: { width: 12, color: [[1, '#f1f3f5']] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      pointer: { show: false },
      title: { show: false },
      detail: {
        valueAnimation: true,
        fontSize: 28,
        fontWeight: 700,
        formatter: '{value}%',
        offsetCenter: [0, '10%'],
        color: getColor(value),
      },
      data: [{ value: Math.round(value) }],
    }],
  }
}

function updateCharts() {
  if (!props.data) return
  const d = props.data

  if (cpuEl.value) {
    if (!cpuChart) cpuChart = echarts.init(cpuEl.value)
    cpuChart.setOption(makeOption(d.cpu_percent))
  }
  if (memEl.value) {
    if (!memChart) memChart = echarts.init(memEl.value)
    memChart.setOption(makeOption(d.memory_percent))
  }
  if (diskEl.value) {
    if (!diskChart) diskChart = echarts.init(diskEl.value)
    diskChart.setOption(makeOption(d.disk_percent))
  }
}

watch(() => props.data, () => { nextTick(updateCharts) }, { deep: true })

onMounted(() => { nextTick(updateCharts) })
</script>

<style scoped>
.gauges-row {
  display: flex;
  justify-content: space-around;
  gap: 16px;
}
.gauge-item {
  text-align: center;
  flex: 1;
}
.gauge-chart {
  width: 100%;
  height: 160px;
}
.gauge-label {
  font-size: 14px;
  font-weight: 500;
  margin-top: 4px;
}
.gauge-detail {
  font-size: 12px;
  color: var(--color-text-secondary, #888);
}
</style>
