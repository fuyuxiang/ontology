<template>
  <div class="monitor-page">
    <div class="monitor-page__header">
      <h1 class="text-display">运维监控</h1>
      <p class="text-caption" style="margin-top: 4px;">系统资源 · 服务状态 · 安全事件</p>
    </div>

    <div class="monitor-tabs">
      <button v-for="tab in tabs" :key="tab.key" class="monitor-tab" :class="{ 'monitor-tab--active': activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
    </div>

    <!-- 资源概览 -->
    <div v-if="activeTab === 'resources'" class="monitor-section">
      <div class="resource-grid">
        <div class="resource-card">
          <div class="resource-card__header">CPU</div>
          <div class="resource-card__gauge">
            <svg viewBox="0 0 100 50" class="gauge-svg">
              <path d="M10 45 A35 35 0 0 1 90 45" fill="none" stroke="var(--neutral-200)" stroke-width="8" stroke-linecap="round"/>
              <path d="M10 45 A35 35 0 0 1 90 45" fill="none" :stroke="gaugeColor(resources.cpu_percent)" stroke-width="8" stroke-linecap="round" :stroke-dasharray="`${resources.cpu_percent * 1.1} 200`"/>
            </svg>
            <span class="gauge-value">{{ resources.cpu_percent.toFixed(1) }}%</span>
          </div>
        </div>
        <div class="resource-card">
          <div class="resource-card__header">内存</div>
          <div class="resource-card__gauge">
            <svg viewBox="0 0 100 50" class="gauge-svg">
              <path d="M10 45 A35 35 0 0 1 90 45" fill="none" stroke="var(--neutral-200)" stroke-width="8" stroke-linecap="round"/>
              <path d="M10 45 A35 35 0 0 1 90 45" fill="none" :stroke="gaugeColor(resources.memory_percent)" stroke-width="8" stroke-linecap="round" :stroke-dasharray="`${resources.memory_percent * 1.1} 200`"/>
            </svg>
            <span class="gauge-value">{{ resources.memory_percent.toFixed(1) }}%</span>
          </div>
          <div class="resource-card__detail">{{ resources.memory_used_gb }}GB / {{ resources.memory_total_gb }}GB</div>
        </div>
        <div class="resource-card">
          <div class="resource-card__header">磁盘</div>
          <div class="resource-card__gauge">
            <svg viewBox="0 0 100 50" class="gauge-svg">
              <path d="M10 45 A35 35 0 0 1 90 45" fill="none" stroke="var(--neutral-200)" stroke-width="8" stroke-linecap="round"/>
              <path d="M10 45 A35 35 0 0 1 90 45" fill="none" :stroke="gaugeColor(resources.disk_percent)" stroke-width="8" stroke-linecap="round" :stroke-dasharray="`${resources.disk_percent * 1.1} 200`"/>
            </svg>
            <span class="gauge-value">{{ resources.disk_percent.toFixed(1) }}%</span>
          </div>
          <div class="resource-card__detail">{{ resources.disk_used_gb }}GB / {{ resources.disk_total_gb }}GB</div>
        </div>
      </div>
      <div class="system-info" v-if="systemInfo">
        <h3 class="text-body-medium" style="margin-bottom:12px;">系统信息</h3>
        <div class="info-grid">
          <div class="info-item" v-for="(val, key) in systemInfo" :key="key">
            <span class="info-label">{{ key }}</span>
            <span class="info-value">{{ val }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 服务状态 -->
    <div v-if="activeTab === 'services'" class="monitor-section">
      <div class="service-list">
        <div v-for="svc in services" :key="svc.name" class="service-item">
          <span class="service-dot" :class="svc.status === 'healthy' ? 'service-dot--ok' : 'service-dot--err'"></span>
          <span class="service-name">{{ svc.name }}</span>
          <span class="service-status">{{ svc.status === 'healthy' ? '正常' : '异常' }}</span>
          <span v-if="svc.response_ms" class="service-rt">{{ svc.response_ms }}ms</span>
        </div>
      </div>
    </div>

    <!-- 安全事件 -->
    <div v-if="activeTab === 'security'" class="monitor-section">
      <table class="data-table" v-if="securityEvents.length">
        <thead>
          <tr><th>时间</th><th>事件类型</th><th>用户</th><th>目标</th><th>严重度</th></tr>
        </thead>
        <tbody>
          <tr v-for="evt in securityEvents" :key="evt.id">
            <td class="text-caption">{{ evt.timestamp?.slice(0, 19).replace('T', ' ') }}</td>
            <td><code class="text-code">{{ evt.event_type }}</code></td>
            <td>{{ evt.user_name || '—' }}</td>
            <td class="text-caption">{{ evt.target }}</td>
            <td><span class="severity-tag" :class="`severity--${evt.severity}`">{{ evt.severity }}</span></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="monitor-empty">暂无安全事件</div>
    </div>

    <!-- 链路追踪 -->
    <div v-if="activeTab === 'tracing'" class="monitor-section">
      <div class="monitor-empty">
        <p>链路追踪功能开发中</p>
        <p class="text-caption">将支持跨服务请求调用链、数据血缘追踪</p>
      </div>
    </div>

    <!-- 容灾状态 -->
    <div v-if="activeTab === 'disaster'" class="monitor-section">
      <div class="monitor-empty">
        <p>容灾监控功能开发中</p>
        <p class="text-caption">将支持组件冗余部署状态、数据副本一致性监控</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { monitorApi, type ResourceMetrics, type ServiceStatus, type SecurityEvent } from '../../api/monitor'

const activeTab = ref('resources')
const tabs = [
  { key: 'resources', label: '资源概览' },
  { key: 'services', label: '服务状态' },
  { key: 'security', label: '安全事件' },
  { key: 'tracing', label: '链路追踪' },
  { key: 'disaster', label: '容灾状态' },
]

const resources = ref<ResourceMetrics>({ cpu_percent: 0, memory_percent: 0, memory_used_gb: 0, memory_total_gb: 0, disk_percent: 0, disk_used_gb: 0, disk_total_gb: 0 })
const services = ref<ServiceStatus[]>([])
const securityEvents = ref<SecurityEvent[]>([])
const systemInfo = ref<Record<string, any> | null>(null)

let timer: ReturnType<typeof setInterval> | null = null

function gaugeColor(pct: number) {
  if (pct < 60) return 'var(--status-success, #22c55e)'
  if (pct < 80) return 'var(--status-warning, #f59e0b)'
  return 'var(--status-error, #ef4444)'
}

async function fetchData() {
  try {
    const overview = await monitorApi.overview()
    resources.value = overview.resources
    services.value = overview.services
    securityEvents.value = overview.security_events
    systemInfo.value = overview.system_info
  } catch { /* ignore */ }
}

onMounted(() => {
  fetchData()
  timer = setInterval(fetchData, 15000)
})

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.monitor-page { padding: 24px 32px; max-width: 1200px; }
.monitor-page__header { margin-bottom: 24px; }
.monitor-tabs { display: flex; gap: 4px; margin-bottom: 24px; border-bottom: 1px solid var(--neutral-100); padding-bottom: 0; }
.monitor-tab { padding: 10px 18px; border: none; background: transparent; font-size: 13px; color: var(--neutral-500); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.15s; }
.monitor-tab:hover { color: var(--neutral-800); }
.monitor-tab--active { color: var(--semantic-600); border-bottom-color: var(--semantic-600); font-weight: 500; }
.monitor-section { animation: fadeIn 0.2s; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

.resource-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 32px; }
.resource-card { background: var(--neutral-0); border: 1px solid var(--neutral-100); border-radius: 12px; padding: 20px; text-align: center; }
.resource-card__header { font-size: 14px; font-weight: 600; color: var(--neutral-700); margin-bottom: 12px; }
.resource-card__gauge { position: relative; width: 120px; height: 60px; margin: 0 auto; }
.gauge-svg { width: 100%; height: 100%; }
.gauge-value { position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); font-size: 18px; font-weight: 700; color: var(--neutral-800); }
.resource-card__detail { font-size: 12px; color: var(--neutral-500); margin-top: 8px; }

.system-info { background: var(--neutral-0); border: 1px solid var(--neutral-100); border-radius: 12px; padding: 20px; }
.info-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.info-item { display: flex; flex-direction: column; gap: 2px; }
.info-label { font-size: 11px; color: var(--neutral-500); text-transform: capitalize; }
.info-value { font-size: 13px; color: var(--neutral-800); font-family: var(--font-mono); }

.service-list { display: flex; flex-direction: column; gap: 8px; }
.service-item { display: flex; align-items: center; gap: 12px; padding: 14px 18px; background: var(--neutral-0); border: 1px solid var(--neutral-100); border-radius: 10px; }
.service-dot { width: 10px; height: 10px; border-radius: 50%; }
.service-dot--ok { background: var(--status-success); }
.service-dot--err { background: var(--status-error); }
.service-name { flex: 1; font-size: 14px; font-weight: 500; }
.service-status { font-size: 12px; color: var(--neutral-500); }
.service-rt { font-size: 12px; color: var(--neutral-400); font-family: var(--font-mono); }

.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--neutral-200); color: var(--neutral-600); font-weight: 500; font-size: 12px; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid var(--neutral-50); }
.severity-tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.severity--low { background: var(--neutral-100); color: var(--neutral-600); }
.severity--medium { background: var(--status-warning-bg, #fef3c7); color: var(--status-warning); }
.severity--high { background: var(--status-error-bg, #fef2f2); color: var(--status-error); }

.monitor-empty { text-align: center; padding: 60px 20px; color: var(--neutral-400); }
</style>
