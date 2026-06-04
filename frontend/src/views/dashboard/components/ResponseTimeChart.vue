<template>
  <a-card :bordered="false">
    <template #title>
      <div class="chart-header">
        <span>服务响应时间</span>
        <div class="header-controls">
          <a-radio-group v-model:value="timeRange" size="small" @change="onRangeChange">
            <a-radio-button value="1">近1小时</a-radio-button>
            <a-radio-button value="6">近6小时</a-radio-button>
            <a-radio-button value="24">近24小时</a-radio-button>
            <a-radio-button value="custom">自定义</a-radio-button>
          </a-radio-group>
          <a-range-picker
            v-if="timeRange === 'custom'"
            v-model:value="customRange"
            size="small"
            show-time
            format="MM-DD HH:mm"
            :placeholder="['开始时间', '结束时间']"
            @change="fetchCustomData"
            style="margin-left: 8px;"
          />
        </div>
      </div>
    </template>
    <div ref="chartEl" style="height: 260px;"></div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import type { Dayjs } from 'dayjs'
import * as echarts from 'echarts'
import { monitorApi, type ResponseHistoryPoint } from '../../../api/monitor'
import { buildResponseTimeChartData } from './responseTimeChartData'

const chartEl = ref<HTMLElement>()
const timeRange = ref('1')
const customRange = ref<[Dayjs, Dayjs] | null>(null)
let chart: echarts.ECharts | null = null

const SERVICE_COLORS: Record<string, string> = {
  '后端API': '#5c7cfa', '数据库': '#20c997', '规则引擎': '#7950f2',
  '函数运行时': '#f59f00', 'Agent 服务': '#339af0', '本体引擎': '#fa5252',
  '图数据库': '#e64980', '大模型网关': '#fab005', 'MinIO': '#40c057', 'Redis': '#fd7e14',
}

function onRangeChange() {
  if (timeRange.value !== 'custom') {
    fetchData()
  }
}

async function fetchData() {
  const hours = parseInt(timeRange.value)
  if (isNaN(hours)) return
  const data = await monitorApi.responseHistory(hours)
  renderChart(data)
}

async function fetchCustomData() {
  if (!customRange.value) return
  const [start, end] = customRange.value
  const hours = Math.ceil((end.valueOf() - start.valueOf()) / (1000 * 60 * 60))
  if (hours <= 0) return
  const data = await monitorApi.responseHistory(hours)
  // Filter data to custom range
  const startTime = start.toISOString()
  const endTime = end.toISOString()
  const filtered = data.filter(d => d.collected_at >= startTime && d.collected_at <= endTime)
  renderChart(filtered)
}

function renderChart(data: ResponseHistoryPoint[]) {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)

  const chartData = buildResponseTimeChartData(data)

  const series = chartData.series.map(({ name, points }) => ({
    name,
    type: 'line' as const,
    smooth: true,
    data: points.map(([time, value]) => [toChartTime(time), value]),
    showSymbol: false,
    symbol: 'circle',
    symbolSize: 5,
    lineStyle: { width: 2 },
    itemStyle: { color: SERVICE_COLORS[name] || '#999' },
    connectNulls: false,
  }))

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        label: {
          formatter: (params: { value: string | number }) => formatCollectedAt(String(params.value)),
        },
      },
    },
    legend: { top: 0, right: 0, type: 'scroll' },
    grid: { top: 40, right: 20, bottom: 30, left: 50 },
    xAxis: {
      type: 'time',
      axisLabel: {
        fontSize: 11,
        formatter: (value: string | number) => formatCollectedAt(String(value)),
      },
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

function toChartTime(value: string) {
  return value.endsWith('Z') ? value : `${value}Z`
}

function formatCollectedAt(value: string) {
  const date = new Date(/^\d+$/.test(value) ? Number(value) : toChartTime(value))
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Shanghai',
  })
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
  flex-wrap: wrap;
  gap: 8px;
}
.header-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
