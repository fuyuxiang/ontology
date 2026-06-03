<template>
  <a-card title="资源使用率" :bordered="false">
    <div class="gauges-row">
      <div v-for="(g, i) in gauges" :key="g.label" class="gauge-item">
        <div class="gauge-chart" :ref="el => { if (el) chartEls[i] = el as HTMLElement }"></div>
        <div class="gauge-label">{{ g.label }}</div>
        <div class="gauge-detail">{{ g.detail }}</div>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ResourceMetrics } from '../../../api/monitor'

const props = defineProps<{ data: ResourceMetrics | null }>()

const chartEls = ref<HTMLElement[]>([])
const chartInstances: echarts.ECharts[] = []

function getGauges() {
  if (!props.data) return []
  return [
    { label: 'CPU', value: props.data.cpu_percent, detail: `${props.data.cpu_percent.toFixed(1)}%` },
    { label: '内存', value: props.data.memory_percent, detail: `${props.data.memory_used_gb}G / ${props.data.memory_total_gb}G` },
    { label: '磁盘', value: props.data.disk_percent, detail: `${props.data.disk_used_gb}G / ${props.data.disk_total_gb}G` },
  ]
}

function getColor(value: number): string {
  if (value < 60) return '#20c997'
  if (value < 85) return '#f59f00'
  return '#fa5252'
}

function initCharts() {
  chartInstances.forEach(c => c.dispose())
  chartInstances.length = 0

  const gauges = getGauges()
  chartEls.value.forEach((el, i) => {
    if (!el || !gauges[i]) return
    const chart = echarts.init(el)
    const g = gauges[i]
    chart.setOption({
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
          color: getColor(g.value),
        },
        data: [{ value: Math.round(g.value) }],
      }],
    })
    chartInstances.push(chart)
  })
}

watch(() => props.data, () => { nextTick(initCharts) }, { deep: true })

onMounted(() => { nextTick(initCharts) })
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
