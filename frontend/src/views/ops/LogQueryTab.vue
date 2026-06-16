<template>
  <div class="log-tab">
    <!-- 筛选工具栏 -->
    <div class="log-tab__toolbar">
      <div class="log-tab__filters">
        <a-range-picker
          v-model:value="dateRange"
          :placeholder="['开始时间', '结束时间']"
          format="YYYY-MM-DD HH:mm"
          :show-time="{ format: 'HH:mm' }"
          style="width: 300px"
          allow-clear
          @change="handleSearch"
        />
        <div class="log-tab__level-group">
          <label
            v-for="level in levels"
            :key="level.value"
            class="log-tab__level-check"
            :class="{ 'log-tab__level-check--active': selectedLevels.includes(level.value) }"
          >
            <input
              type="checkbox"
              :value="level.value"
              v-model="selectedLevels"
              @change="handleSearch"
              hidden
            />
            <span class="log-tab__level-dot" :style="{ background: level.color }"></span>
            {{ level.label }}
          </label>
        </div>
        <a-select
          v-model:value="filterSource"
          placeholder="全部来源"
          allow-clear
          style="width: 140px"
          :options="sourceOptions"
          @change="handleSearch"
        />
        <a-input-search
          v-model:value="filterKeyword"
          placeholder="搜索日志内容"
          style="flex: 1; min-width: 200px"
          allow-clear
          @search="handleSearch"
          @change="(e: Event) => { if (!(e.target as HTMLInputElement).value) handleSearch() }"
        />
      </div>
      <div class="log-tab__toolbar-right">
        <label class="log-tab__realtime-toggle">
          <a-switch v-model:checked="realtimeEnabled" size="small" />
          <span class="log-tab__realtime-label">
            <span v-if="realtimeEnabled" class="log-tab__live-dot"></span>
            实时
          </span>
        </label>
      </div>
    </div>

    <!-- 统计条 -->
    <div class="log-tab__stats" v-if="stats.total > 0">
      <div class="log-tab__stats-left">
        <span class="log-tab__stats-total">共 {{ stats.total.toLocaleString() }} 条</span>
        <span class="log-tab__stats-sep">│</span>
        <span v-for="level in levels" :key="level.value" class="log-tab__stats-item" :style="{ color: level.color }">
          <span class="log-tab__stats-dot" :style="{ background: level.color }"></span>
          {{ stats[level.value] || 0 }}
        </span>
      </div>
      <div class="log-tab__stats-right">
        <span class="log-tab__stats-time">更新于 {{ lastUpdate }}</span>
      </div>
    </div>

    <!-- 日志列表 -->
    <div class="log-tab__list" ref="listRef">
      <!-- 实时流指示条 -->
      <div v-if="realtimeEnabled" class="log-tab__live-bar">
        <span class="log-tab__live-dot-animated"></span>
        实时接收中...
      </div>

      <template v-if="logs.length">
        <div
          v-for="log in logs"
          :key="log.id"
          class="log-entry"
          :class="[
            `log-entry--${log.level}`,
            { 'log-entry--expanded': expandedId === log.id }
          ]"
          @click="toggleExpand(log.id)"
        >
          <!-- 第一行：时间 + 级别 + 来源 + 消息 -->
          <div class="log-entry__row1">
            <span class="log-entry__time">{{ formatTime(log.timestamp) }}</span>
            <span class="log-entry__level" :class="`log-entry__level--${log.level}`">
              <span class="log-entry__level-dot" :style="{ background: getLevelColor(log.level) }"></span>
              {{ log.level }}
            </span>
            <span class="log-entry__source">{{ log.source }}</span>
            <span class="log-entry__message">{{ log.message }}</span>
          </div>
          <!-- 第二行：上下文标签 -->
          <div class="log-entry__row2" v-if="log.user || log.ip || log.duration_ms !== undefined || log.status_code">
            <span v-if="log.user" class="log-entry__tag">
              <span class="log-entry__tag-icon">👤</span>{{ log.user }}
            </span>
            <span v-if="log.ip" class="log-entry__tag">
              <span class="log-entry__tag-icon">🌐</span>{{ log.ip }}
            </span>
            <span v-if="log.status_code" class="log-entry__tag" :class="log.status_code < 400 ? 'log-entry__tag--ok' : 'log-entry__tag--err'">
              HTTP {{ log.status_code }}
            </span>
            <span v-if="log.duration_ms !== undefined && log.duration_ms !== null" class="log-entry__tag">
              ⏱ {{ log.duration_ms }}ms
            </span>
            <span v-if="log.resolved !== undefined" class="log-entry__tag" :class="log.resolved ? 'log-entry__tag--ok' : 'log-entry__tag--err'">
              {{ log.resolved ? '✓ 已处理' : '✗ 未处理' }}
            </span>
          </div>
          <!-- 展开详情 -->
          <div v-if="expandedId === log.id" class="log-entry__detail">
            <div class="log-entry__detail-grid">
              <div v-if="log.user" class="log-entry__detail-item">
                <span class="log-entry__detail-label">操作用户</span>
                <span class="log-entry__detail-value">{{ log.user }}</span>
              </div>
              <div v-if="log.ip" class="log-entry__detail-item">
                <span class="log-entry__detail-label">来源 IP</span>
                <span class="log-entry__detail-value log-entry__mono">{{ log.ip }}</span>
              </div>
              <div v-if="log.source" class="log-entry__detail-item">
                <span class="log-entry__detail-label">来源模块</span>
                <span class="log-entry__detail-value">{{ log.source }}</span>
              </div>
              <div class="log-entry__detail-item">
                <span class="log-entry__detail-label">时间</span>
                <span class="log-entry__detail-value log-entry__mono">{{ formatTime(log.timestamp) }}</span>
              </div>
              <div v-if="log.duration_ms !== undefined && log.duration_ms !== null" class="log-entry__detail-item">
                <span class="log-entry__detail-label">耗时</span>
                <span class="log-entry__detail-value">{{ log.duration_ms }}ms</span>
              </div>
              <div v-if="log.resolved !== undefined" class="log-entry__detail-item">
                <span class="log-entry__detail-label">状态</span>
                <span class="log-entry__detail-value">{{ log.resolved ? '已处理' : '未处理' }}</span>
              </div>
            </div>
            <div v-if="log.raw" class="log-entry__raw">
              <pre>{{ log.raw }}</pre>
            </div>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-else-if="!loading" class="log-tab__empty">
        <div class="log-tab__empty-icon">🔍</div>
        <p class="log-tab__empty-title">未找到匹配日志</p>
        <p class="log-tab__empty-desc">尝试调整时间范围或筛选条件</p>
        <button class="log-tab__empty-btn" @click="handleReset">重置筛选</button>
      </div>

      <!-- 骨架屏 -->
      <div v-if="loading" class="log-tab__skeleton">
        <div v-for="i in 6" :key="i" class="skeleton-log">
          <div class="skeleton skeleton--w160"></div>
          <div class="skeleton skeleton--w50"></div>
          <div class="skeleton skeleton--w100"></div>
          <div class="skeleton skeleton--flex"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import {
  RangePicker as ARangePicker,
  Select as ASelect,
  InputSearch as AInputSearch,
  Switch as ASwitch,
} from 'ant-design-vue'
import type { Dayjs } from 'dayjs'
import { monitorApi, type AlertItem } from '../../api/monitor'
import { tracesApi, type TraceItem } from '../../api/ops'

interface LogEntry {
  id: string
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR'
  source: string
  message: string
  user?: string
  ip?: string
  status_code?: number
  duration_ms?: number | null
  resolved?: boolean
  raw?: string
}

const levels = [
  { value: 'DEBUG', label: 'DEBUG', color: 'var(--neutral-500, #868e96)' },
  { value: 'INFO', label: 'INFO', color: 'var(--status-info, #339af0)' },
  { value: 'WARN', label: 'WARN', color: 'var(--status-warning, #f59f00)' },
  { value: 'ERROR', label: 'ERROR', color: 'var(--status-error, #fa5252)' },
]

const sourceOptions = [
  { label: '系统告警', value: 'alert' },
  { label: '智能体执行', value: 'trace' },
]

const logs = ref<LogEntry[]>([])
const loading = ref(false)
const expandedId = ref<string | null>(null)
const listRef = ref<HTMLElement | null>(null)
const lastUpdate = ref('--:--')

const dateRange = ref<[Dayjs, Dayjs] | null>(null)
const selectedLevels = ref<string[]>(['DEBUG', 'INFO', 'WARN', 'ERROR'])
const filterSource = ref<string | undefined>(undefined)
const filterKeyword = ref('')
const realtimeEnabled = ref(false)

const stats = reactive({ total: 0, DEBUG: 0, INFO: 0, WARN: 0, ERROR: 0 })

let pollTimer: ReturnType<typeof setInterval> | null = null

function toggleExpand(id: string) {
  expandedId.value = expandedId.value === id ? null : id
}

function handleSearch() {
  fetchData()
}

function handleReset() {
  dateRange.value = null
  selectedLevels.value = ['DEBUG', 'INFO', 'WARN', 'ERROR']
  filterSource.value = undefined
  filterKeyword.value = ''
  fetchData()
}

function formatTime(ts: string) {
  if (!ts) return '-'
  return ts.replace('T', ' ').slice(0, 19)
}

function getLevelColor(level: string) {
  const map: Record<string, string> = {
    DEBUG: 'var(--neutral-500, #868e96)',
    INFO: 'var(--status-info, #339af0)',
    WARN: 'var(--status-warning, #f59f00)',
    ERROR: 'var(--status-error, #fa5252)',
  }
  return map[level] || 'var(--neutral-500)'
}

function alertToLog(a: AlertItem): LogEntry {
  const levelMap: Record<string, LogEntry['level']> = {
    critical: 'ERROR', high: 'ERROR', medium: 'WARN', warning: 'WARN', low: 'INFO', info: 'INFO',
    error: 'ERROR', debug: 'DEBUG', ERROR: 'ERROR', WARN: 'WARN', INFO: 'INFO', DEBUG: 'DEBUG',
  }
  return {
    id: `alert-${a.id}`,
    timestamp: a.created_at,
    level: levelMap[a.level.toLowerCase()] || 'INFO',
    source: a.service_name || '系统',
    message: a.message,
    resolved: a.resolved,
    raw: `告警 ID: ${a.id}\n服务: ${a.service_name}\n级别: ${a.level}\n状态: ${a.resolved ? '已处理' : '未处理'}${a.resolved_at ? `\n处理时间: ${formatTime(a.resolved_at)}` : ''}`,
  }
}

function traceToLog(t: TraceItem): LogEntry {
  const level: LogEntry['level'] = t.status === 'error' ? 'ERROR' : t.status === 'timeout' ? 'WARN' : 'DEBUG'
  return {
    id: `trace-${t.id}`,
    timestamp: t.created_at || '',
    level,
    source: t.agent_name || '智能体引擎',
    message: truncate(t.input_text || '无输入', 80),
    duration_ms: t.latency_ms,
    status_code: t.status === 'error' ? 500 : 200,
    raw: `Trace ID: ${t.id}\n智能体: ${t.agent_name || t.agent_id}\n状态: ${t.status}\n耗时: ${t.latency_ms ?? '-'}ms\nToken 消耗: ${t.tokens_used ?? '-'}\n\n--- 输入 ---\n${t.input_text || '(空)'}\n\n--- 输出 ---\n${t.output_text || '(空)'}`,
  }
}

function truncate(str: string, len: number) {
  return str.length > len ? str.slice(0, len) + '...' : str
}

async function fetchData() {
  loading.value = true
  try {
    const promises: Promise<unknown>[] = []
    if (!filterSource.value || filterSource.value === 'alert') {
      promises.push(monitorApi.alerts(100).catch(() => [] as AlertItem[]))
    } else {
      promises.push(Promise.resolve([] as AlertItem[]))
    }
    if (!filterSource.value || filterSource.value === 'trace') {
      promises.push(tracesApi.list({ page_size: 50 }).catch(() => ({ items: [] as TraceItem[] })))
    } else {
      promises.push(Promise.resolve({ items: [] as TraceItem[] }))
    }
    const [alerts, traceRes] = await Promise.all(promises) as [AlertItem[], { items: TraceItem[] }]
    let allLogs: LogEntry[] = [
      ...alerts.map(alertToLog),
      ...(traceRes.items || []).map(traceToLog),
    ]
    allLogs.sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''))
    allLogs = allLogs.filter(l => selectedLevels.value.includes(l.level))
    if (filterKeyword.value) {
      const kw = filterKeyword.value.toLowerCase()
      allLogs = allLogs.filter(l =>
        l.message.toLowerCase().includes(kw) || l.source.toLowerCase().includes(kw) || (l.user && l.user.toLowerCase().includes(kw))
      )
    }
    logs.value = allLogs
    stats.total = allLogs.length
    stats.DEBUG = allLogs.filter(l => l.level === 'DEBUG').length
    stats.INFO = allLogs.filter(l => l.level === 'INFO').length
    stats.WARN = allLogs.filter(l => l.level === 'WARN').length
    stats.ERROR = allLogs.filter(l => l.level === 'ERROR').length
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    logs.value = []; stats.total = 0
  } finally {
    loading.value = false
  }
}

function startRealtime() {
  pollTimer = setInterval(() => {
    if (realtimeEnabled.value) fetchData()
  }, 10000)
}

onMounted(() => { fetchData(); startRealtime() })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.log-tab__toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.log-tab__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  flex: 1;
}
.log-tab__toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 级别多选 */
.log-tab__level-group {
  display: flex;
  gap: 4px;
}
.log-tab__level-check {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid var(--neutral-200);
  color: var(--neutral-500);
  transition: all 0.2s;
  user-select: none;
}
.log-tab__level-check:hover {
  border-color: var(--neutral-300);
  background: var(--neutral-50);
}
.log-tab__level-check--active {
  border-color: var(--neutral-300);
  background: var(--neutral-50);
  color: var(--neutral-700);
  font-weight: 500;
}
.log-tab__level-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* 实时开关 */
.log-tab__realtime-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.log-tab__realtime-label {
  font-size: 13px;
  color: var(--neutral-600);
  display: flex;
  align-items: center;
  gap: 6px;
}
.log-tab__live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--status-success, #10b981);
  animation: pulse 1.5s infinite;
}

/* 统计条 */
.log-tab__stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--neutral-50);
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
}
.log-tab__stats-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.log-tab__stats-total {
  font-weight: 600;
  color: var(--neutral-700);
}
.log-tab__stats-sep {
  color: var(--neutral-200);
}
.log-tab__stats-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
}
.log-tab__stats-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.log-tab__stats-right {
  display: flex;
  align-items: center;
}
.log-tab__stats-time {
  font-size: 12px;
  color: var(--neutral-400);
}

/* 实时流指示条 */
.log-tab__live-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(32, 201, 151, 0.06);
  border-bottom: 1px solid rgba(32, 201, 151, 0.15);
  font-size: 13px;
  color: var(--status-success, #10b981);
  font-weight: 500;
}
.log-tab__live-dot-animated {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-success, #10b981);
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.8); }
}

/* 日志列表 */
.log-tab__list {
  max-height: calc(100vh - 400px);
  min-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--neutral-100);
  border-radius: 10px;
  background: var(--neutral-0);
}
.log-entry {
  padding: 12px 16px;
  border-bottom: 1px solid var(--neutral-100);
  cursor: pointer;
  transition: all 0.15s ease;
  border-left: 3px solid transparent;
}
.log-entry:hover {
  background: var(--neutral-50);
}
.log-entry:last-child {
  border-bottom: none;
}
.log-entry--ERROR { border-left-color: var(--status-error, #fa5252); }
.log-entry--WARN  { border-left-color: var(--status-warning, #f59f00); }
.log-entry--INFO  { border-left-color: var(--status-info, #339af0); }
.log-entry--DEBUG { border-left-color: var(--neutral-300); }

/* 第一行 */
.log-entry__row1 {
  display: flex;
  align-items: center;
  gap: 10px;
}
.log-entry__time {
  width: 180px;
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--neutral-500);
}
.log-entry__level {
  width: 70px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}
.log-entry__level-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.log-entry__level--DEBUG { color: var(--neutral-500); }
.log-entry__level--INFO  { color: #339af0; }
.log-entry__level--WARN  { color: #f59f00; }
.log-entry__level--ERROR { color: #fa5252; }
.log-entry__source {
  width: 100px;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--neutral-600);
  background: var(--neutral-50);
  padding: 2px 8px;
  border-radius: 4px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.log-entry__message {
  flex: 1;
  font-size: 13px;
  color: var(--neutral-800);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 第二行：上下文标签 */
.log-entry__row2 {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  padding-left: 280px;
}
.log-entry__tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--neutral-600);
  background: var(--neutral-50);
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--neutral-100);
}
.log-entry__tag-icon {
  font-size: 11px;
}
.log-entry__tag--ok {
  color: var(--status-success, #10b981);
  background: rgba(16, 185, 129, 0.06);
  border-color: rgba(16, 185, 129, 0.15);
}
.log-entry__tag--err {
  color: var(--status-error, #fa5252);
  background: rgba(250, 82, 82, 0.06);
  border-color: rgba(250, 82, 82, 0.15);
}

/* 展开详情 */
.log-entry--expanded .log-entry__message {
  white-space: normal;
}
.log-entry__detail {
  margin-top: 12px;
  padding: 14px 16px;
  background: var(--neutral-50);
  border-radius: 8px;
  border: 1px solid var(--neutral-100);
}
.log-entry__detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.log-entry__detail-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.log-entry__detail-label {
  font-size: 11px;
  color: var(--neutral-400);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.log-entry__detail-value {
  font-size: 13px;
  color: var(--neutral-800);
}
.log-entry__mono {
  font-family: var(--font-mono);
  font-size: 12px;
}
.log-entry__raw {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  padding: 14px;
  border-radius: 6px;
  overflow-x: auto;
}
.log-entry__raw pre {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--neutral-700);
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
}

/* 空状态 */
.log-tab__empty {
  text-align: center;
  padding: 60px 20px;
}
.log-tab__empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.8;
}
.log-tab__empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--neutral-700);
  margin-bottom: 6px;
}
.log-tab__empty-desc {
  font-size: 13px;
  color: var(--neutral-400);
  margin-bottom: 16px;
}
.log-tab__empty-btn {
  padding: 8px 20px;
  border: 1px solid var(--neutral-200);
  background: var(--neutral-0);
  border-radius: 6px;
  font-size: 13px;
  color: var(--neutral-600);
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.log-tab__empty-btn:hover {
  border-color: var(--semantic-400);
  color: var(--semantic-600);
}

/* 骨架屏 */
.log-tab__skeleton {
  display: flex;
  flex-direction: column;
}
.skeleton-log {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--neutral-100);
}
.skeleton {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--neutral-100) 25%, var(--neutral-50) 50%, var(--neutral-100) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skeleton--w160 { width: 160px; }
.skeleton--w50 { width: 50px; }
.skeleton--w100 { width: 100px; }
.skeleton--flex { flex: 1; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }

/* 响应式 */
@media (max-width: 1440px) {
  .log-entry__row1 { flex-wrap: wrap; }
  .log-entry__time { width: auto; }
  .log-entry__source { width: auto; }
  .log-entry__message { flex-basis: 100%; margin-top: 4px; }
  .log-entry__row2 { padding-left: 0; }
}
</style>
