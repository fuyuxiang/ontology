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
    <a-alert v-if="loadError" type="error" show-icon :message="loadError" style="margin-bottom:12px">
      <template #action><a-button size="small" @click="reload">重试</a-button></template>
    </a-alert>
    <div class="chart-content">
      <div ref="chartEl" style="height: 260px;"></div>
      <a-empty v-if="isEmpty && !loadError" class="chart-empty" :description="timeRange === 'custom' && !customRange ? '请选择开始和结束时间' : '该时间范围暂无响应记录'" />
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { Alert as AAlert, Button as AButton, Empty as AEmpty } from 'ant-design-vue'
import type { Dayjs } from 'dayjs'
import * as echarts from 'echarts'
import { monitorApi, type ResponseHistoryPoint } from '../../../api/monitor'
import { buildResponseTimeChartData } from './responseTimeChartData'

const chartEl = ref<HTMLElement>()
const timeRange = ref('1')
const customRange = ref<[Dayjs, Dayjs] | null>(null)
let chart: echarts.ECharts | null = null
let requestId = 0
let disposed = false
let resizeObserver: ResizeObserver | null = null
const loadError = ref('')
const isEmpty = ref(false)

const SERVICE_COLORS: Record<string, string> = {
  '后端API': '#5c7cfa', '数据库': '#20c997', '规则引擎': '#7950f2',
  '函数运行时': '#f59f00', 'Agent 服务': '#339af0', '本体引擎': '#fa5252',
  '图数据库': '#e64980', '大模型网关': '#fab005', 'MinIO': '#40c057', 'Redis': '#fd7e14',
}

function onRangeChange() {
  if (timeRange.value !== 'custom') {
    fetchData()
  } else {
    ++requestId
    chart?.hideLoading()
    if (customRange.value) fetchCustomData()
    else { chart?.clear(); isEmpty.value = true; loadError.value = '' }
  }
}

async function fetchData() {
  const hours = parseInt(timeRange.value)
  if (isNaN(hours)) return
  await loadHistory(hours)
}

async function fetchCustomData() {
  if (!customRange.value) return
  const [start, end] = customRange.value
  if (end.valueOf() <= start.valueOf()) return
  // API 按“距现在多少小时”取记录，历史自定义范围需要从其开始时间查询。
  const hours = Math.max(1, Math.ceil((Date.now() - start.valueOf()) / (1000 * 60 * 60)))
  await loadHistory(hours, [start.valueOf(), end.valueOf()])
}

function reload() { return timeRange.value === 'custom' ? fetchCustomData() : fetchData() }

async function loadHistory(hours: number, range?: [number, number]) {
  const request = ++requestId
  loadError.value = ''
  chart?.showLoading('default', { text: '加载中…' })
  try {
    const data = await monitorApi.responseHistory(hours)
    if (disposed || request !== requestId) return
    const filtered = range ? data.filter(point => {
      const time = new Date(toChartTime(point.collected_at)).getTime()
      return time >= range[0] && time <= range[1]
    }) : data
    renderChart(filtered)
    isEmpty.value = filtered.length === 0
  } catch (e: any) {
    if (!disposed && request === requestId) loadError.value = e.response?.data?.detail || '响应记录加载失败，请重试'
  } finally {
    if (request === requestId) chart?.hideLoading()
  }
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
  return /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`
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
  if (chartEl.value) {
    chart = echarts.init(chartEl.value)
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(chartEl.value)
  }
  nextTick(fetchData)
})

onBeforeUnmount(() => {
  disposed = true
  ++requestId
  resizeObserver?.disconnect()
  chart?.dispose()
  chart = null
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
  flex-wrap: wrap;
}
.chart-content { position: relative; }
.chart-empty { position: absolute; inset: 30px 0 0; background: var(--neutral-0, #fff); padding-top: 24px; }
</style>
