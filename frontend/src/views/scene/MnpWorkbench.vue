<template>
  <div class="workbench">
    <!-- Header -->
    <div class="workbench__header">
      <div>
        <h1 class="text-display">携号转网预警系统</h1>
        <p class="text-caption" style="margin-top: 4px;">风险识别 → 关系扩散 → 维挽执行 → 效果验证</p>
      </div>
    </div>

    <!-- KPI 卡片 -->
    <div class="workbench__kpis">
      <div class="kpi-card kpi-card--danger">
        <div class="kpi-card__value">{{ stats.high }}</div>
        <div class="kpi-card__label">高风险</div>
      </div>
      <div class="kpi-card kpi-card--warning">
        <div class="kpi-card__value">{{ stats.medium }}</div>
        <div class="kpi-card__label">中风险</div>
      </div>
      <div class="kpi-card kpi-card--info">
        <div class="kpi-card__value">{{ stats.low }}</div>
        <div class="kpi-card__label">低风险</div>
      </div>
      <div class="kpi-card kpi-card--success">
        <div class="kpi-card__value">{{ stats.retained }}</div>
        <div class="kpi-card__label">已维挽</div>
      </div>
      <div class="kpi-card kpi-card--muted">
        <div class="kpi-card__value">{{ stats.ported }}</div>
        <div class="kpi-card__label">已携转</div>
      </div>
    </div>

    <!-- 主体 -->
    <div class="workbench__body">
      <!-- 左侧：风险用户列表 -->
      <RiskUserList
        :users="riskUsers"
        :selected-id="selectedUserId"
        :filter="filter"
        @select="onSelectUser"
        @filter="filter = $event"
      />

      <!-- 右侧：详情区 -->
      <div class="workbench__detail">
        <template v-if="selectedUser">
          <!-- 用户画像 -->
          <UserProfile :user="selectedUser" />

          <!-- 关系图谱 -->
          <RiskGraph :entity-id="selectedUser.entityId" />

          <!-- 推理链 + 维挽动作 -->
          <ReasoningPanel :user="selectedUser" :signals="userSignals" :actions="userActions" />

          <!-- 状态时间线 -->
          <StatusTimeline :logs="statusLogs" />
        </template>
        <div v-else class="workbench__empty">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><circle cx="24" cy="24" r="20" stroke="#dee2e6" stroke-width="1.5" stroke-dasharray="4 3"/><path d="M18 24h12M24 18v12" stroke="#ced4da" stroke-width="1.5" stroke-linecap="round"/></svg>
          <p>选择左侧风险用户查看详情</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { entityApi } from '../../api/ontology'
import RiskUserList from '../../components/mnp/RiskUserList.vue'
import UserProfile from '../../components/mnp/UserProfile.vue'
import RiskGraph from '../../components/mnp/RiskGraph.vue'
import ReasoningPanel from '../../components/mnp/ReasoningPanel.vue'
import StatusTimeline from '../../components/mnp/StatusTimeline.vue'

export interface RiskUser {
  entityId: string
  name: string
  phone: string
  riskLevel: 'high' | 'medium' | 'low' | 'safe'
  riskScore: number
  arpu: number
  arpuTrend: 'rising' | 'stable' | 'declining'
  tenure: number
  complaints: number
  competitorQueries: number
  mnpStatus: string
}

export interface Signal { type: string; time: string; detail: string; weight: number }
export interface Action { type: string; status: string; time: string; effect?: string; scoreBefore?: number; scoreAfter?: number }
export interface StatusLog { time: string; fromLevel: string; toLevel: string; reason: string; triggeredBy: string }

const filter = ref('all')
const selectedUserId = ref<string | null>(null)
const riskUsers = ref<RiskUser[]>([])
const userSignals = ref<Signal[]>([])
const userActions = ref<Action[]>([])
const statusLogs = ref<StatusLog[]>([])

const stats = computed(() => {
  const u = riskUsers.value
  return {
    high: u.filter(x => x.riskLevel === 'high').length,
    medium: u.filter(x => x.riskLevel === 'medium').length,
    low: u.filter(x => x.riskLevel === 'low').length,
    retained: u.filter(x => x.mnpStatus === '已挽留').length,
    ported: u.filter(x => x.mnpStatus === '已携转').length,
  }
})

const selectedUser = computed(() => riskUsers.value.find(u => u.entityId === selectedUserId.value) || null)

onMounted(async () => {
  // 从后端加载 MNP 实体，用 MnpRiskUser 的属性构造 mock 风险用户
  try {
    const entities = await entityApi.list({ namespace: 'mnp' })
    const riskEntity = entities.find(e => e.name === 'MnpRiskUser')
    if (riskEntity) {
      // 生成演示数据
      riskUsers.value = generateDemoUsers(riskEntity.id)
    }
  } catch { /* fallback to demo */ }
  if (riskUsers.value.length === 0) riskUsers.value = generateDemoUsers('mnp_MnpRiskUser')
})

function generateDemoUsers(entityId: string): RiskUser[] {
  return [
    { entityId, name: '张明华', phone: '138****6721', riskLevel: 'high', riskScore: 92, arpu: 89, arpuTrend: 'declining', tenure: 36, complaints: 3, competitorQueries: 5, mnpStatus: '预警中' },
    { entityId, name: '李秀英', phone: '139****3345', riskLevel: 'high', riskScore: 87, arpu: 128, arpuTrend: 'declining', tenure: 24, complaints: 2, competitorQueries: 4, mnpStatus: '维挽中' },
    { entityId, name: '王建国', phone: '136****8890', riskLevel: 'medium', riskScore: 72, arpu: 68, arpuTrend: 'stable', tenure: 48, complaints: 1, competitorQueries: 3, mnpStatus: '预警中' },
    { entityId, name: '赵丽娟', phone: '137****2156', riskLevel: 'medium', riskScore: 65, arpu: 156, arpuTrend: 'declining', tenure: 12, complaints: 0, competitorQueries: 2, mnpStatus: '监控中' },
    { entityId, name: '陈志强', phone: '135****7743', riskLevel: 'low', riskScore: 45, arpu: 98, arpuTrend: 'stable', tenure: 60, complaints: 0, competitorQueries: 1, mnpStatus: '监控中' },
    { entityId, name: '刘美玲', phone: '138****9012', riskLevel: 'safe', riskScore: 15, arpu: 188, arpuTrend: 'rising', tenure: 72, complaints: 0, competitorQueries: 0, mnpStatus: '已挽留' },
    { entityId, name: '孙伟', phone: '136****4567', riskLevel: 'high', riskScore: 95, arpu: 45, arpuTrend: 'declining', tenure: 6, complaints: 5, competitorQueries: 8, mnpStatus: '已携转' },
  ]
}

function onSelectUser(user: RiskUser) {
  selectedUserId.value = user.entityId + user.name
  // 生成该用户的信号、动作、状态日志
  userSignals.value = [
    { type: 'ARPU下降', time: '2026-03-15', detail: `月均ARPU从¥${user.arpu + 40}降至¥${user.arpu}，降幅${Math.round(40/(user.arpu+40)*100)}%`, weight: 0.3 },
    ...(user.complaints > 0 ? [{ type: '投诉', time: '2026-03-20', detail: `近3月投诉${user.complaints}次，涉及网络质量和资费问题`, weight: 0.25 }] : []),
    ...(user.competitorQueries > 0 ? [{ type: '竞品查询', time: '2026-04-01', detail: `查询竞品套餐${user.competitorQueries}次，主要关注移动/联通低价套餐`, weight: 0.2 }] : []),
    { type: '家庭成员携转', time: '2026-04-05', detail: '配偶已于3月携转至中国移动', weight: 0.25 },
  ]
  userActions.value = user.mnpStatus === '维挽中' || user.mnpStatus === '已挽留' ? [
    { type: '发送专属优惠', status: '已完成', time: '2026-04-06', effect: user.mnpStatus === '已挽留' ? '有效' : '待评估', scoreBefore: user.riskScore, scoreAfter: user.mnpStatus === '已挽留' ? user.riskScore - 40 : undefined },
    { type: '客户经理回访', status: user.mnpStatus === '已挽留' ? '已完成' : '执行中', time: '2026-04-08' },
  ] : []
  statusLogs.value = [
    { time: '2026-03-01', fromLevel: '安全', toLevel: '低风险', reason: 'ARPU开始下降', triggeredBy: '规则引擎' },
    { time: '2026-03-20', fromLevel: '低风险', toLevel: '中风险', reason: '投诉次数增加', triggeredBy: '规则引擎' },
    { time: '2026-04-05', fromLevel: '中风险', toLevel: '高风险', reason: '配偶已携转，家庭风险传导', triggeredBy: '关系传导' },
    ...(user.mnpStatus === '维挽中' ? [{ time: '2026-04-06', fromLevel: '高风险', toLevel: '高风险', reason: '维挽动作已执行，等待效果评估', triggeredBy: '维挽生效' }] : []),
    ...(user.mnpStatus === '已挽留' ? [{ time: '2026-04-20', fromLevel: '高风险', toLevel: '低风险', reason: '维挽方案生效，用户续约成功', triggeredBy: '维挽生效' }] : []),
  ]
}
</script>

<style scoped>
.workbench { display: flex; flex-direction: column; height: 100%; background: var(--neutral-50, #f8f9fa); }
.workbench__header { padding: 20px 24px 0; }
.workbench__kpis { display: flex; gap: 12px; padding: 16px 24px; }
.kpi-card { flex: 1; padding: 14px 16px; border-radius: 10px; background: #fff; border: 1px solid #e9ecef; }
.kpi-card__value { font-size: 28px; font-weight: 700; line-height: 1; }
.kpi-card__label { font-size: 12px; color: #868e96; margin-top: 4px; }
.kpi-card--danger .kpi-card__value { color: #fa5252; }
.kpi-card--warning .kpi-card__value { color: #f59f00; }
.kpi-card--info .kpi-card__value { color: #339af0; }
.kpi-card--success .kpi-card__value { color: #12b886; }
.kpi-card--muted .kpi-card__value { color: #adb5bd; }
.workbench__body { display: flex; flex: 1; overflow: hidden; padding: 0 24px 24px; gap: 16px; }
.workbench__detail { flex: 1; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }
.workbench__empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: #adb5bd; font-size: 14px; }
</style>
