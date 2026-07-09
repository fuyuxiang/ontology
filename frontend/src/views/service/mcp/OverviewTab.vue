<template>
  <div class="overview">
    <!-- Hero 区 -->
    <div class="overview__hero">
      <div class="hero__left">
        <h2 class="hero__title">本体 MCP 服务</h2>
        <div class="hero__meta">
          <span class="hero__version">v1.0.0</span>
          <span class="hero__protocol">MCP · streamable-http</span>
        </div>
      </div>
      <div class="hero__right">
        <div class="hero__status">
          <span class="status-dot"></span>
          <span class="hero__status-text">运行中</span>
        </div>
        <div class="hero__endpoint">
          <code>{{ endpoint }}</code>
          <button class="copy-btn" @click="copyEndpoint">复制</button>
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
.overview__hero {
  background: linear-gradient(135deg, #1a1a2e 0%, #4a3f8a 100%);
  padding: 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
}
.hero__title { font-size: 20px; font-weight: 700; margin: 0; }
.hero__meta { display: flex; gap: 12px; margin-top: 8px; }
.hero__version, .hero__protocol { font-size: 12px; background: rgba(255,255,255,0.15); padding: 2px 8px; border-radius: 4px; }
.hero__right { text-align: right; }
.hero__status { display: flex; align-items: center; gap: 6px; justify-content: flex-end; font-size: 12px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #4ade80; display: inline-block; animation: pulse 2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.hero__endpoint { margin-top: 8px; display: flex; align-items: center; justify-content: flex-end; }
.hero__endpoint code { font-size: 12px; background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 4px; }
.copy-btn { margin-left: 8px; font-size: 11px; background: rgba(255,255,255,0.2); border: none; color: #fff; padding: 3px 8px; border-radius: 4px; cursor: pointer; }
.copy-btn:hover { background: rgba(255,255,255,0.3); }

.overview__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 20px 24px; }
.stat-card { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); display: flex; align-items: center; gap: 12px; }
.stat-card__icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
.stat-card__icon--calls { background: #eef2ff; color: #6366f1; }
.stat-card__icon--speed { background: #ecfdf5; color: #10b981; }
.stat-card__icon--error { background: #fef2f2; color: #ef4444; }
.stat-card__icon--conn { background: #fffbeb; color: #f59e0b; }
.stat-card__body { flex: 1; }
.stat-card__value { font-size: 22px; font-weight: 700; color: var(--neutral-900); }
.stat-card__value small { font-size: 12px; font-weight: 400; color: var(--neutral-500); margin-left: 2px; }
.stat-card__label { display: block; font-size: 12px; color: var(--neutral-500); margin-top: 2px; }
.stat-card__trend { font-size: 11px; font-weight: 600; }
.trend--up { color: #10b981; }
.trend--down { color: #ef4444; }

.overview__charts { display: flex; gap: 16px; padding: 0 24px 20px; }
.chart-panel { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.chart-panel--main { flex: 2; }
.chart-panel--side { flex: 1; }
.chart-panel__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.chart-panel__header h3 { font-size: 13px; font-weight: 600; color: var(--neutral-800); margin: 0; }
.range-btns { display: flex; gap: 4px; }
.range-btns button { font-size: 11px; padding: 3px 8px; border: 1px solid var(--neutral-200); border-radius: 4px; background: #fff; cursor: pointer; color: var(--neutral-600); }
.range-btns button.active { background: var(--semantic-600); color: #fff; border-color: var(--semantic-600); }
.chart-panel__canvas { height: 240px; }

.overview__table { padding: 0 24px 24px; }
.section-title { font-size: 13px; font-weight: 600; color: var(--neutral-800); margin: 0 0 12px; }
.tool-table { width: 100%; border-collapse: collapse; font-size: 12px; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.tool-table th { text-align: left; padding: 10px 12px; background: var(--neutral-50); color: var(--neutral-600); font-weight: 600; border-bottom: 1px solid var(--neutral-200); }
.tool-table td { padding: 10px 12px; border-bottom: 1px solid var(--neutral-100); color: var(--neutral-700); }
.tool-table code { font-size: 11px; background: var(--neutral-100); padding: 1px 4px; border-radius: 3px; }
.text-error { color: #ef4444; font-weight: 600; }
</style>
