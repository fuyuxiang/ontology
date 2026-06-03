<template>
  <a-card :bordered="false">
    <template #title>
      <div class="chart-header">
        <span>服务响应时间</span>
        <a-radio-group v-model:value="timeRange" size="small" @change="fetchData">
          <a-radio-button value="1">近1小时</a-radio-button>
          <a-radio-button value="6">近6小时</a-radio-button>
          <a-radio-button value="24">近24小时</a-radio-button>
        </a-radio-group>
      </div>
    </template>
    <div ref="chartEl" style="height: 260px;"></div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { monitorApi, type ResponseHistoryPoint } from '../../../api/monitor'

const chartEl = ref<HTMLElement>()
const timeRange = ref('1')
let chart: echarts.ECharts | null = null

const SERVICE_COLORS: Record<string, string> = {
  '后端API': '#5c7cfa', '数据库': '#20c997', '规则引擎': '#7950f2',
  '函数运行时': '#f59f00', 'Agent 服务': '#339af0', '本体引擎': '#fa5252',
  '图数据库': '#e64980', '大模型网关': '#fab005', 'MinIO': '#40c057', 'Redis': '#fd7e14',
}

async function fetchData() {
  const hours = parseInt(timeRange.value)
  const data = await monitorApi.responseHistory(hours)
  renderChart(data)
}

function renderChart(data: ResponseHistoryPoint[]) {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)

  const byService: Record<string, { times: string[]; values: (number | null)[] }> = {}
  for (const p of data) {
    if (!byService[p.service_name]) byService[p.service_name] = { times: [], values: [] }
    byService[p.service_name].times.push(p.collected_at)
    byService[p.service_name].values.push(p.response_ms)
  }

  const series = Object.entries(byService).map(([name, d]) => ({
    name,
    type: 'line' as const,
    smooth: true,
    data: d.values,
    lineStyle: { width: 2 },
    itemStyle: { color: SERVICE_COLORS[name] || '#999' },
    connectNulls: false,
  }))

  const allTimes = [...new Set(data.map(d => d.collected_at))].sort()

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0, type: 'scroll' },
    grid: { top: 40, right: 20, bottom: 30, left: 50 },
    xAxis: {
      type: 'category',
      data: allTimes.map(t => t.substring(11, 19)),
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: 'ms',
      axisLabel: { fontSize: 11 },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    series,
  }, true)
}

onMounted(() => {
  nextTick(fetchData)
  window.addEventListener('resize', () => chart?.resize())
})
</script>

<style scoped>
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
