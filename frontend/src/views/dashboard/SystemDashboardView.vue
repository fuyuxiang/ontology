<template>
  <div class="dashboard-container">
    <!-- Header -->
    <div class="dashboard-header">
      <h2>系统看板</h2>
      <div class="header-right">
        <span class="last-update">最后更新: {{ lastUpdate }}</span>
        <a-dropdown>
          <a-button size="small">
            <template #icon><ReloadOutlined /></template>
            {{ autoRefreshLabel }}
          </a-button>
          <template #overlay>
            <a-menu @click="onRefreshChange">
              <a-menu-item key="30">30秒</a-menu-item>
              <a-menu-item key="60">60秒</a-menu-item>
              <a-menu-item key="0">关闭</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
        <a-button size="small" @click="fetchAll" :loading="loading">
          <template #icon><ReloadOutlined /></template>
        </a-button>
      </div>
    </div>

    <!-- Service Health -->
    <ServiceHealthCards :services="services" />

    <!-- Resource + Response Time -->
    <a-row :gutter="16" style="margin-top: 16px;" class="middle-row">
      <a-col :xs="24" :lg="10" class="middle-col">
        <ResourceGauges :data="resources" />
      </a-col>
      <a-col :xs="24" :lg="14" class="middle-col">
        <ResponseTimeChart />
      </a-col>
    </a-row>

    <!-- Stats Row - 6 cards -->
    <a-row :gutter="16" style="margin-top: 16px;">
      <a-col :xs="12" :sm="8" :lg="4">
        <OntologyStats :data="ontologyStats" />
      </a-col>
      <a-col :xs="12" :sm="8" :lg="4">
        <LLMCallStats :data="llmStats" />
      </a-col>
      <a-col :xs="12" :sm="8" :lg="4">
        <AgentActivity :data="agentActivity" />
      </a-col>
      <a-col :xs="12" :sm="8" :lg="4">
        <DataStats :data="platformStats" />
      </a-col>
      <a-col :xs="12" :sm="8" :lg="4">
        <RuleStats :data="platformStats" />
      </a-col>
      <a-col :xs="12" :sm="8" :lg="4">
        <PipelineStats :data="platformStats" />
      </a-col>
    </a-row>

    <!-- Alerts + Events -->
    <a-row :gutter="16" style="margin-top: 16px;" class="bottom-row">
      <a-col :xs="24" :lg="12" class="bottom-col">
        <AlertTable :alerts="mergedAlerts" @resolve="onResolveAlert" />
      </a-col>
      <a-col :xs="24" :lg="12" class="bottom-col">
        <EventStream :events="wsEvents" />
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { monitorApi } from '../../api/monitor'
import type { ResourceMetrics, ServiceStatus, AlertItem, LLMStatsResponse, OntologyStatsResponse, AgentActivityResponse, PlatformStatsResponse } from '../../api/monitor'
import { useMonitorWS } from '../../composables/useMonitorWS'

import ServiceHealthCards from './components/ServiceHealthCards.vue'
import ResourceGauges from './components/ResourceGauges.vue'
import ResponseTimeChart from './components/ResponseTimeChart.vue'
import AlertTable from './components/AlertTable.vue'
import EventStream from './components/EventStream.vue'
import OntologyStats from './components/OntologyStats.vue'
import LLMCallStats from './components/LLMCallStats.vue'
import AgentActivity from './components/AgentActivity.vue'
import DataStats from './components/DataStats.vue'
import RuleStats from './components/RuleStats.vue'
import PipelineStats from './components/PipelineStats.vue'

const loading = ref(false)
const resources = ref<ResourceMetrics | null>(null)
const services = ref<ServiceStatus[]>([])
const alerts = ref<AlertItem[]>([])
const llmStats = ref<LLMStatsResponse | null>(null)
const ontologyStats = ref<OntologyStatsResponse | null>(null)
const agentActivity = ref<AgentActivityResponse | null>(null)
const platformStats = ref<PlatformStatsResponse | null>(null)
const lastUpdate = ref('--:--:--')
const autoRefreshSec = ref(30)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const { alerts: wsAlerts } = useMonitorWS()

// Merge WS alerts into table
const mergedAlerts = computed(() => {
  const ws = wsAlerts.value.map(a => ({ ...a, resolved: false }))
  const existing = alerts.value
  const ids = new Set(ws.map((a: any) => a.id))
  const merged = [...ws, ...existing.filter(a => !ids.has(a.id))]
  return merged.sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 20)
})

// Events from WS messages
const wsEvents = ref<Array<{ time: string; type: string; description: string }>>([])

const autoRefreshLabel = computed(() => {
  if (autoRefreshSec.value === 0) return '关闭'
  return `${autoRefreshSec.value}s`
})

async function fetchAll() {
  loading.value = true
  try {
    const [res, svc, alt, llm, ont, agent, platform] = await Promise.all([
      monitorApi.resources(),
      monitorApi.services(),
      monitorApi.alerts(20),
      monitorApi.llmStats(),
      monitorApi.ontologyStats(),
      monitorApi.agentActivity(),
      monitorApi.platformStats(),
    ])
    resources.value = res
    services.value = svc
    alerts.value = alt
    llmStats.value = llm
    ontologyStats.value = ont
    agentActivity.value = agent
    platformStats.value = platform
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  } catch (e) {
    console.error('Dashboard fetch error:', e)
  } finally {
    loading.value = false
  }
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer)
  if (autoRefreshSec.value > 0) {
    refreshTimer = setInterval(fetchAll, autoRefreshSec.value * 1000)
  }
}

function onRefreshChange({ key }: { key: string }) {
  autoRefreshSec.value = parseInt(key)
  startAutoRefresh()
}

async function onResolveAlert(id: number) {
  try {
    await monitorApi.resolveAlert(id)
    const idx = alerts.value.findIndex(a => a.id === id)
    if (idx >= 0) alerts.value[idx].resolved = true
  } catch (e) {
    console.error('Resolve alert error:', e)
  }
}

onMounted(() => {
  fetchAll()
  startAutoRefresh()
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.dashboard-container {
  padding: 24px 32px;
}
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.dashboard-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.last-update {
  font-size: 13px;
  color: var(--color-text-secondary, #888);
}
.middle-row,
.bottom-row {
  display: flex;
  align-items: stretch;
}
.middle-col,
.bottom-col {
  display: flex;
}
.middle-col > *,
.bottom-col > * {
  flex: 1;
}
</style>
