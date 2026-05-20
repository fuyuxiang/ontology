<template>
  <div class="health-tab">
    <a-spin v-if="loading" size="large" class="health-tab__loading" />

    <template v-else>
      <!-- 实时连接 / Mock 数据指示 -->
      <div class="health-tab__status">
        <span class="health-tab__dot" :class="{ 'is-live': realtime }"></span>
        <a-typography-text type="secondary" style="font-size:12px">
          {{ realtime ? '实时连接' : 'Mock 数据' }}
          <span v-if="lastRefresh" style="margin-left:8px;color:#bbb">
            上次刷新: {{ lastRefresh.toLocaleTimeString() }}
          </span>
        </a-typography-text>
      </div>

      <!-- 顶部 4 张卡片 -->
      <a-row :gutter="[16, 16]" class="health-tab__row">
        <a-col :xs="24" :lg="6" class="health-tab__col">
          <a-card class="health-tab__card" :body-style="{ padding: '12px 16px', display: 'flex', alignItems: 'center' }">
            <div class="health-tab__drift">
              <DriftGauge :value="dashboard.drift_score" />
              <div>
                <a-typography-text type="secondary" style="font-size:12px">本体漂移分数</a-typography-text>
                <div :style="{ fontSize: '10px', marginTop: '4px', color: dashboard.trend === 'improving' ? '#52c41a' : '#ff4d4f' }">
                  {{ dashboard.trend === 'improving' ? '↓ 趋势改善' : '↑ 趋势恶化' }}
                </div>
              </div>
            </div>
          </a-card>
        </a-col>

        <a-col :xs="24" :lg="6" class="health-tab__col">
          <a-card class="health-tab__card" :body-style="{ padding: '12px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }">
            <a-typography-text type="secondary" style="font-size:12px">
              <AlertOutlined /> 待处理告警
            </a-typography-text>
            <div class="health-tab__metric-row">
              <span class="health-tab__metric-num" :style="{ color: dashboard.pending_alerts > 0 ? '#ff4d4f' : '#52c41a' }">
                {{ dashboard.pending_alerts }}<span class="health-tab__metric-unit">条</span>
              </span>
              <Sparkline :data="sparkline.alerts" color="#ff4d4f" />
            </div>
          </a-card>
        </a-col>

        <a-col :xs="24" :lg="6" class="health-tab__col">
          <a-card class="health-tab__card" :body-style="{ padding: '12px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }">
            <a-typography-text type="secondary" style="font-size:12px">
              <RiseOutlined /> 本周演化
            </a-typography-text>
            <div class="health-tab__metric-row">
              <span class="health-tab__metric-num">
                {{ dashboard.weekly_evolutions }}<span class="health-tab__metric-unit">次</span>
              </span>
              <Sparkline :data="sparkline.evolutions" color="#1677ff" />
            </div>
            <a-typography-text type="secondary" style="font-size:11px">
              对比上周 <span style="color:#52c41a">+{{ dashboard.weekly_evolutions_delta }}</span>
            </a-typography-text>
          </a-card>
        </a-col>

        <a-col :xs="24" :lg="6" class="health-tab__col">
          <a-card class="health-tab__card" :body-style="{ padding: '12px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }">
            <a-typography-text type="secondary" style="font-size:12px">
              <HeartOutlined /> 模型健康度
            </a-typography-text>
            <div class="health-tab__metric-row">
              <span class="health-tab__metric-num" :style="{ color: dashboard.model_health > 80 ? '#52c41a' : '#faad14' }">
                {{ dashboard.model_health }}<span class="health-tab__metric-unit">%</span>
              </span>
              <Sparkline :data="sparkline.health" color="#52c41a" />
            </div>
            <a-typography-text type="secondary" style="font-size:11px">3 个模型综合</a-typography-text>
          </a-card>
        </a-col>
      </a-row>

      <!-- 第二行：分群偏差矩阵 + 触点效果排名 -->
      <a-row :gutter="[16, 16]" class="health-tab__row" style="margin-top:16px">
        <a-col :xs="24" :lg="14" class="health-tab__col">
          <a-card class="health-tab__card" :body-style="{ padding: '12px 16px' }">
            <template #title>
              <SyncOutlined /> 分群偏差矩阵
            </template>
            <div style="overflow-x:auto">
              <table class="health-tab__seg-table">
                <thead>
                  <tr>
                    <th style="text-align:left">分群</th>
                    <th>预测</th>
                    <th>实际</th>
                    <th style="min-width:120px">偏差</th>
                    <th>样本</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="seg in segments" :key="seg.id">
                    <td><a-typography-text strong style="font-size:13px">{{ seg.name }}</a-typography-text></td>
                    <td style="text-align:center">{{ seg.predicted }}%</td>
                    <td style="text-align:center">{{ seg.actual }}%</td>
                    <td style="text-align:center">
                      <DeviationBar :deviation="seg.deviation" />
                    </td>
                    <td style="text-align:center;color:#999;font-size:12px">{{ seg.sample_size.toLocaleString() }}</td>
                    <td style="text-align:center">
                      <span class="health-tab__status-dot" :style="{ background: statusColor(seg.status) }"></span>
                      <a-typography-text :style="{ fontSize: '12px', color: statusColor(seg.status) }">
                        {{ statusLabel(seg.status) }}
                      </a-typography-text>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </a-card>
        </a-col>

        <a-col :xs="24" :lg="10" class="health-tab__col">
          <a-card title="触点效果排名" class="health-tab__card" :body-style="{ padding: '12px 16px' }">
            <div v-for="(t, i) in sortedTouchpoints" :key="t.name" class="health-tab__tp">
              <div class="health-tab__tp-row">
                <a-space :size="6">
                  <span class="health-tab__tp-rank" :class="{ 'is-top': i === 0 }">{{ i + 1 }}</span>
                  <a-typography-text strong style="font-size:14px">{{ t.name }}</a-typography-text>
                </a-space>
                <a-space :size="16">
                  <span style="font-size:12px;color:#999">触达 {{ t.reach_rate }}%</span>
                  <a-typography-text strong :style="{ fontSize: '16px', color: tpColor(t.conversion) }">
                    {{ t.conversion }}%
                  </a-typography-text>
                </a-space>
              </div>
              <div class="health-tab__tp-bar">
                <div class="health-tab__tp-bar-inner"
                  :style="{ width: (t.conversion / maxConv * 100) + '%', background: `linear-gradient(90deg, ${tpColor(t.conversion)}88, ${tpColor(t.conversion)})` }">
                </div>
              </div>
              <div class="health-tab__tp-cost">
                <a-typography-text type="secondary" style="font-size:11px">成本效益比 {{ t.cost_ratio }}</a-typography-text>
              </div>
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 实时告警流 -->
      <a-card title="实时告警流" class="health-tab__card health-tab__alerts" :body-style="{ padding: '8px 16px' }">
        <div v-for="(alert, i) in alerts" :key="i" class="health-tab__alert" :class="{ 'is-last': i === alerts.length - 1 }">
          <div class="health-tab__alert-icon">
            <component :is="alertIcon(alert.level)" :style="{ color: alertColor(alert.level) }" />
          </div>
          <div style="flex:1">
            <a-typography-text style="font-size:13px">{{ alert.content }}</a-typography-text>
          </div>
          <a-typography-text type="secondary" style="font-size:11px;white-space:nowrap;flex-shrink:0">
            <ClockCircleOutlined style="margin-right:3px" />{{ alert.time }}
          </a-typography-text>
        </div>
      </a-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  AlertOutlined,
  RiseOutlined,
  HeartOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons-vue'
import { harnessApi, type HarnessDashboard, type DriftSegment, type DriftTouchpoint, type DriftAlert } from '../../../api/harness'
import DriftGauge from '../components/DriftGauge.vue'
import Sparkline from '../components/Sparkline.vue'
import DeviationBar from '../components/DeviationBar.vue'

const loading = ref(true)
const realtime = ref(false)
const lastRefresh = ref<Date | null>(null)
const dashboard = ref<HarnessDashboard>({
  drift_score: 0, trend: 'improving', pending_alerts: 0, weekly_evolutions: 0, weekly_evolutions_delta: 0, model_health: 0,
})
const segments = ref<DriftSegment[]>([])
const touchpoints = ref<DriftTouchpoint[]>([])
const alerts = ref<DriftAlert[]>([])

const sparkline = computed(() => ({
  drift: [31, 28, 27, 25, 24, 23.5, dashboard.value.drift_score ?? 23.5],
  alerts: [5, 4, 3, 3, 2, 2, dashboard.value.pending_alerts ?? 2],
  evolutions: [1, 2, 3, 2, 4, 4, dashboard.value.weekly_evolutions ?? 5],
  health: [79, 80, 82, 83, 84, 84.7, dashboard.value.model_health ?? 84.7],
}))

const sortedTouchpoints = computed(() => [...touchpoints.value].sort((a, b) => b.conversion - a.conversion))
const maxConv = computed(() => sortedTouchpoints.value[0]?.conversion || 1)

function statusColor(s: string) { return s === 'alert' ? '#ff4d4f' : s === 'warning' ? '#faad14' : '#52c41a' }
function statusLabel(s: string) { return s === 'alert' ? '告警' : s === 'warning' ? '关注' : '正常' }
function tpColor(c: number) { return c > 10 ? '#52c41a' : c > 5 ? '#1677ff' : '#faad14' }
function alertIcon(level: string) {
  return level === 'error' ? WarningOutlined
    : level === 'warning' ? AlertOutlined
    : level === 'success' ? CheckCircleOutlined
    : InfoCircleOutlined
}
function alertColor(level: string) {
  return level === 'error' ? '#ff4d4f'
    : level === 'warning' ? '#faad14'
    : level === 'success' ? '#52c41a'
    : '#1677ff'
}

let timer: any = null
async function loadAll() {
  try {
    const [d, drift, tel] = await Promise.all([
      harnessApi.getDashboard(),
      harnessApi.getDrift(),
      harnessApi.getTelemetrySummary(),
    ])
    if (d) {
      dashboard.value = d
      realtime.value = true
    }
    if (drift?.segments) segments.value = drift.segments
    if (drift?.touchpoints) touchpoints.value = drift.touchpoints
    if (tel?.alerts) alerts.value = tel.alerts
    lastRefresh.value = new Date()
  } catch {
    realtime.value = false
  }
}

onMounted(async () => {
  await loadAll()
  loading.value = false
  timer = setInterval(loadAll, 30000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.health-tab { display: flex; flex-direction: column; gap: 0; }
.health-tab__loading { display: flex; align-items: center; justify-content: center; height: 100%; padding: 60px 0; }
.health-tab__status { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.health-tab__dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #ff4d4f; box-shadow: 0 0 6px #ff4d4f60;
  display: inline-block;
}
.health-tab__dot.is-live { background: #52c41a; box-shadow: 0 0 6px #52c41a60; }
.health-tab__row { display: flex; align-items: stretch; }
.health-tab__col { display: flex; }
.health-tab__card { border-radius: 12px; width: 100%; }
.health-tab__drift { display: flex; align-items: center; gap: 12px; }
.health-tab__metric-row { display: flex; align-items: flex-end; justify-content: space-between; margin-top: 8px; }
.health-tab__metric-num { font-size: 32px; font-weight: 700; line-height: 1; }
.health-tab__metric-unit { font-size: 14px; font-weight: 400; color: #999; margin-left: 4px; }
.health-tab__seg-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.health-tab__seg-table thead tr { border-bottom: 2px solid #f0f0f0; }
.health-tab__seg-table th { text-align: center; padding: 8px 6px; font-weight: 600; color: #666; }
.health-tab__seg-table tbody tr { border-bottom: 1px solid #fafafa; }
.health-tab__seg-table td { padding: 8px 6px; }
.health-tab__status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
.health-tab__tp { margin-bottom: 14px; }
.health-tab__tp-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.health-tab__tp-rank {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%;
  background: #fafafa; font-size: 11px; font-weight: 600; color: #999;
}
.health-tab__tp-rank.is-top { background: #f6ffed; color: #52c41a; }
.health-tab__tp-bar { height: 6px; background: #f5f5f5; border-radius: 3px; overflow: hidden; }
.health-tab__tp-bar-inner { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.health-tab__tp-cost { display: flex; justify-content: flex-end; margin-top: 2px; }
.health-tab__alerts { margin-top: 16px; border-radius: 12px; }
.health-tab__alert { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid #fafafa; }
.health-tab__alert.is-last { border-bottom: none; }
.health-tab__alert-icon { margin-top: 2px; }
</style>
