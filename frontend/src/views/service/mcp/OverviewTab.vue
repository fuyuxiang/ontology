<template>
  <div class="overview">
    <!-- 顶部 Banner -->
    <div class="page-banner">
      <div class="page-banner__content">
        <h1 class="page-banner__title">本体服务</h1>
        <p class="page-banner__desc">基于 MCP 协议对外暴露本体查询、数据探索和 Python 运行时能力，支持 Claude Desktop、Cursor 等 AI 客户端直接接入</p>
      </div>
      <div class="page-banner__right">
        <div class="page-banner__status">
          <span class="status-dot"></span>
          <span>服务运行中</span>
        </div>
        <div class="page-banner__endpoint">
          <code>{{ endpoint }}</code>
          <button class="copy-btn" @click="copyEndpoint">复制</button>
        </div>
        <div class="page-banner__meta">
          <span class="meta-tag">v1.0.0</span>
          <span class="meta-tag">MCP · streamable-http</span>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="overview__stats">
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--calls">📈</div>
        <div class="stat-card__body">
          <div class="stat-card__value">
            {{ overview.total_calls_today.toLocaleString() }}
            <span
              v-if="callsTrend !== null"
              class="stat-card__trend"
              :class="callsTrend >= 0 ? 'trend--up' : 'trend--down'"
            >{{ callsTrend >= 0 ? '↑' : '↓' }} {{ Math.abs(callsTrend).toFixed(1) }}%</span>
          </div>
          <span class="stat-card__label">今日调用</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--speed">⚡</div>
        <div class="stat-card__body">
          <div class="stat-card__value">
            {{ overview.avg_response_ms }}<small>ms</small>
          </div>
          <span class="stat-card__label">平均响应</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--error">⚠</div>
        <div class="stat-card__body">
          <div class="stat-card__value">
            {{ (overview.error_rate * 100).toFixed(2) }}<small>%</small>
          </div>
          <span class="stat-card__label">错误率</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--conn">🔗</div>
        <div class="stat-card__body">
          <div class="stat-card__value">{{ overview.active_connections }}</div>
          <span class="stat-card__label">活跃连接</span>
        </div>
      </div>
    </div>

    <!-- 图表区 -->
    <div class="overview__charts">
      <div class="chart-panel chart-panel--main">
        <div class="chart-panel__header">
          <h3>调用趋势</h3>
          <div class="range-btns">
            <button
              v-for="r in ranges"
              :key="r"
              :class="{ active: trendRange === r }"
              @click="changeRange(r)"
            >{{ r }}</button>
          </div>
        </div>
        <div ref="trendEl" class="chart-panel__canvas"></div>
      </div>
      <div class="chart-panel chart-panel--side">
        <div class="chart-panel__header">
          <h3>工具分布</h3>
        </div>
        <div ref="pieEl" class="chart-panel__canvas"></div>
      </div>
    </div>

    <!-- 工具健康表格 -->
    <div class="overview__table">
      <h3 class="section-title">工具健康</h3>
      <table class="tool-table">
        <thead>
          <tr>
            <th>工具名称</th>
            <th>描述</th>
            <th>调用次数</th>
            <th>平均耗时</th>
            <th>错误数</th>
            <th>最近调用</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stat in toolStats" :key="stat.tool_name">
            <td><code>{{ stat.tool_name }}</code></td>
            <td>{{ toolDesc(stat.tool_name) }}</td>
            <td>{{ stat.call_count.toLocaleString() }}</td>
            <td>{{ stat.avg_ms }} ms</td>
            <td :class="{ 'text-error': stat.error_count > 0 }">{{ stat.error_count }}</td>
            <td>{{ formatTime(stat.last_called) }}</td>
          </tr>
          <tr v-if="!toolStats.length">
            <td colspan="6" style="text-align: center; color: var(--neutral-400);">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  getMcpOverview,
  getMcpTrend,
  getMcpToolStats,
  getMcpTools,
  type McpOverview,
  type McpToolStat,
  type McpToolSchema,
} from '../../../api/mcp'

const overview = ref<McpOverview>({
  total_calls_today: 0,
  total_calls_yesterday: 0,
  avg_response_ms: 0,
  error_rate: 0,
  active_connections: 0,
})
const toolStats = ref<McpToolStat[]>([])
const tools = ref<McpToolSchema[]>([])

const ranges = ['1h', '24h', '7d'] as const
const trendRange = ref<'1h' | '24h' | '7d'>('24h')

const endpoint = `${window.location.origin}/api/v1/mcp`

const trendEl = ref<HTMLElement | null>(null)
const pieEl = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null

const callsTrend = computed<number | null>(() => {
  const y = overview.value.total_calls_yesterday
  if (!y) return null
  return ((overview.value.total_calls_today - y) / y) * 100
})

function toolDesc(name: string): string {
  return tools.value.find(t => t.name === name)?.description || '-'
}

function formatTime(t: string | null): string {
  if (!t) return '-'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  return d.toLocaleString('zh-CN', { hour12: false })
}

async function copyEndpoint() {
  try {
    await navigator.clipboard.writeText(endpoint)
  } catch { /* ignore */ }
}

function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
}

async function loadTrend() {
  try {
    const res = await getMcpTrend(trendRange.value)
    trendChart?.setOption({
      xAxis: { data: res.data.map(p => p.time) },
      series: [{ data: res.data.map(p => p.count) }],
    })
  } catch { /* ignore */ }
}

async function changeRange(r: '1h' | '24h' | '7d') {
  trendRange.value = r
  await loadTrend()
}

async function loadPie() {
  try {
    const stats = await getMcpToolStats()
    toolStats.value = stats
    pieChart?.setOption({
      series: [{
        data: stats.map(s => ({ name: s.tool_name, value: s.call_count })),
      }],
    })
  } catch { /* ignore */ }
}

function initCharts() {
  if (trendEl.value) {
    trendChart = echarts.init(trendEl.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { top: 10, right: 16, bottom: 24, left: 40 },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f3f4f6' } } },
      series: [{
        type: 'line', smooth: true, symbol: 'none',
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(99,102,241,0.3)' }, { offset: 1, color: 'rgba(99,102,241,0.02)' }] } },
        lineStyle: { color: '#6366f1', width: 2 },
        data: [],
      }],
    })
  }
  if (pieEl.value) {
    pieChart = echarts.init(pieEl.value)
    pieChart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: ['45%', '70%'],
        label: { fontSize: 10 },
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
        data: [],
      }],
    })
  }
}

onMounted(async () => {
  await nextTick()
  initCharts()
  window.addEventListener('resize', handleResize)
  try {
    overview.value = await getMcpOverview()
  } catch { /* ignore */ }
  try {
    const res = await getMcpTools()
    tools.value = res.tools || []
  } catch { /* ignore */ }
  await loadTrend()
  await loadPie()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
  trendChart = null
  pieChart = null
})
</script>
<style scoped>
.page-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32px;
  background: linear-gradient(135deg, #e8f4fd 0%, #dbeafe 50%, #eff6ff 100%);
  border-radius: var(--radius-lg, 12px);
  margin: 0 24px 24px;
}
.page-banner__title { font-size: 24px; font-weight: 700; color: var(--neutral-900, #111); margin: 0 0 8px; }
.page-banner__desc { font-size: 13px; color: var(--neutral-600, #555); margin: 0; max-width: 480px; line-height: 1.5; }
.page-banner__right { text-align: right; }
.page-banner__status { display: flex; align-items: center; gap: 6px; justify-content: flex-end; font-size: 13px; color: #16a34a; font-weight: 500; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #16a34a; display: inline-block; animation: pulse 2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.page-banner__endpoint { margin-top: 8px; display: flex; align-items: center; justify-content: flex-end; }
.page-banner__endpoint code { font-size: 12px; background: rgba(37,99,235,0.08); color: var(--primary, #2563eb); padding: 4px 10px; border-radius: 4px; }
.copy-btn { margin-left: 8px; font-size: 11px; background: var(--primary, #2563eb); border: none; color: #fff; padding: 4px 10px; border-radius: 4px; cursor: pointer; }
.copy-btn:hover { opacity: 0.9; }
.page-banner__meta { display: flex; gap: 8px; margin-top: 8px; justify-content: flex-end; }
.meta-tag { font-size: 11px; background: rgba(37,99,235,0.08); color: var(--primary, #2563eb); padding: 2px 8px; border-radius: 4px; }

.overview__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 0 24px 24px; }
.stat-card { background: var(--neutral-0, #fff); border: 1px solid var(--neutral-100, #f0f0f0); border-radius: var(--radius-lg, 12px); padding: 16px; display: flex; align-items: center; gap: 12px; transition: box-shadow 0.15s, border-color 0.15s; }
.stat-card:hover { border-color: var(--primary, #2563eb); box-shadow: 0 4px 16px rgba(37, 99, 235, 0.08); }
.stat-card__icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
.stat-card__icon--calls { background: #eff6ff; }
.stat-card__icon--speed { background: #ecfdf5; }
.stat-card__icon--error { background: #fef2f2; }
.stat-card__icon--conn { background: #fffbeb; }
.stat-card__body { flex: 1; }
.stat-card__value { font-size: 22px; font-weight: 700; color: var(--neutral-900, #111); }
.stat-card__value small { font-size: 12px; font-weight: 400; color: var(--neutral-500, #888); margin-left: 2px; }
.stat-card__label { display: block; font-size: 12px; color: var(--neutral-500, #888); margin-top: 2px; }
.stat-card__trend { font-size: 11px; font-weight: 600; margin-left: 6px; }
.trend--up { color: #16a34a; }
.trend--down { color: #dc2626; }

.overview__charts { display: flex; gap: 16px; padding: 0 24px 24px; }
.chart-panel { background: var(--neutral-0, #fff); border: 1px solid var(--neutral-100, #f0f0f0); border-radius: var(--radius-lg, 12px); padding: 16px; }
.chart-panel--main { flex: 2; }
.chart-panel--side { flex: 1; }
.chart-panel__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.chart-panel__header h3 { font-size: 13px; font-weight: 600; color: var(--neutral-800, #333); margin: 0; }
.range-btns { display: flex; gap: 4px; }
.range-btns button { font-size: 11px; padding: 4px 10px; border: 1px solid var(--neutral-200, #e5e5e5); border-radius: 6px; background: var(--neutral-0, #fff); cursor: pointer; color: var(--neutral-600, #555); transition: all 0.15s; }
.range-btns button:hover { border-color: var(--primary, #2563eb); color: var(--primary, #2563eb); }
.range-btns button.active { background: var(--primary, #2563eb); color: #fff; border-color: var(--primary, #2563eb); }
.chart-panel__canvas { height: 240px; }

.overview__table { padding: 0 24px 24px; }
.section-title { font-size: 14px; font-weight: 600; color: var(--neutral-800, #333); margin: 0 0 12px; }
.tool-table { width: 100%; border-collapse: collapse; font-size: 12px; background: var(--neutral-0, #fff); border-radius: var(--radius-lg, 12px); overflow: hidden; border: 1px solid var(--neutral-100, #f0f0f0); }
.tool-table th { text-align: left; padding: 10px 12px; background: var(--neutral-50, #fafafa); color: var(--neutral-600, #555); font-weight: 600; border-bottom: 1px solid var(--neutral-200, #e5e5e5); }
.tool-table td { padding: 10px 12px; border-bottom: 1px solid var(--neutral-100, #f0f0f0); color: var(--neutral-700, #333); }
.tool-table code { font-size: 11px; background: var(--neutral-100, #f0f0f0); padding: 1px 4px; border-radius: 3px; }
.text-error { color: #dc2626; font-weight: 600; }
</style>
