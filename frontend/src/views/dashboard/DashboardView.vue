<template>
  <div class="dashboard">
    <div class="dashboard__header">
      <div>
        <h1 class="text-display">数据看板</h1>
        <p class="text-caption" style="margin-top: 4px;">本体平台运行概览 · 实时更新</p>
      </div>
      <div class="dashboard__header-actions">
        <span class="live-badge">
          <span class="live-badge__dot"></span>
          实时
        </span>
        <button class="btn-secondary">导出报告</button>
      </div>
    </div>

    <!-- KPI 卡片行 -->
    <div class="dashboard__kpi-row">
      <div class="kpi-card" v-for="kpi in kpis" :key="kpi.label" :class="`kpi-card--${kpi.color}`">
        <div class="kpi-card__icon" v-html="kpi.icon"></div>
        <div class="kpi-card__body">
          <div class="kpi-card__value">{{ kpi.value }}</div>
          <div class="kpi-card__label">{{ kpi.label }}</div>
          <div class="kpi-card__trend" :class="kpi.trend > 0 ? 'trend--up' : 'trend--down'">
            {{ kpi.trend > 0 ? '↑' : '↓' }} {{ Math.abs(kpi.trend) }}% 较上周
          </div>
        </div>
      </div>
    </div>

    <!-- 中间两列 -->
    <div class="dashboard__mid-row">
      <!-- 对象类型分布 -->
      <div class="dash-card">
        <div class="dash-card__header">
          <h3 class="text-h3">对象类型分布</h3>
          <span class="text-caption">按 Tier 层级</span>
        </div>
        <div class="tier-dist">
          <div class="tier-dist__item" v-for="t in tierDist" :key="t.tier">
            <div class="tier-dist__label">
              <span class="tier-dot" :class="`tier-dot--${t.tier}`"></span>
              <span>Tier {{ t.tier }} {{ t.name }}</span>
            </div>
            <div class="tier-dist__bar-wrap">
              <div class="tier-dist__bar" :class="`tier-dist__bar--${t.tier}`" :style="{ width: t.pct + '%' }"></div>
            </div>
            <span class="tier-dist__count">{{ t.count }}</span>
          </div>
        </div>
      </div>

      <!-- 近期活动 -->
      <div class="dash-card">
        <div class="dash-card__header">
          <h3 class="text-h3">近期活动</h3>
          <span class="text-caption">最近 7 天</span>
        </div>
        <div class="activity-list">
          <div class="activity-item" v-for="a in activities" :key="a.id">
            <div class="activity-item__icon" :class="`activity-icon--${a.type}`" v-html="a.icon"></div>
            <div class="activity-item__body">
              <p class="text-body-medium">{{ a.title }}</p>
              <p class="text-caption">{{ a.description }}</p>
            </div>
            <span class="activity-item__time text-caption">{{ a.time }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 状态总览 -->
    <div class="dash-card">
      <div class="dash-card__header">
        <h3 class="text-h3">对象健康状态</h3>
        <span class="text-caption">全部 {{ allObjects.length }} 个对象</span>
      </div>
      <div class="health-grid">
        <div
          class="health-item"
          v-for="obj in allObjects"
          :key="obj.name"
          :class="`health-item--${obj.status}`"
          :title="obj.name"
        >
          <span class="health-item__name">{{ obj.name }}</span>
          <span class="health-item__tier">T{{ obj.tier }}</span>
        </div>
      </div>
    </div>

    <!-- 推理链示例 -->
    <div class="dash-card">
      <div class="dash-card__header">
        <h3 class="text-h3">推理链追溯</h3>
        <span class="text-caption">策略推荐全链路可解释</span>
      </div>
      <ReasoningChain title="高价值续约策略 #strategy_001" :steps="reasoningSteps" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import ReasoningChain from '../../components/common/ReasoningChain.vue'
import type { ReasoningStep } from '../../components/common/ReasoningChain.vue'
import { dashboardApi } from '../../api/dashboard'

const reasoningSteps: ReasoningStep[] = [
  { type: 'ontology', title: '本体查询: CustomerSegment', source: 'BSS系统 (CRM_CUSTOMER)', result: '筛选出 2,847 名高价值用户' },
  { type: 'ml', title: 'ML预测: churn_prediction_model', source: '输入: arpu, tenure, complaint_count', result: 'churn_probability = 0.73' },
  { type: 'rule', title: '规则匹配: rule_007_high_value_renewal', source: '条件: arpu >= 100 AND tenure >= 12', result: '触发"续约优惠+设备升级"策略' },
  { type: 'output', title: '策略输出: strategy_recommend', source: '产品: FTTR千兆升级包', result: '预测转化率: 3.2%，触点: APP推送(优先) + 短信(备选)' },
]

// 从 API 加载的数据
const stats = ref<Record<string, unknown>>({})
const loading = ref(true)

onMounted(async () => {
  try {
    stats.value = await dashboardApi.stats() as unknown as Record<string, unknown>
  } finally {
    loading.value = false
  }
})

const kpiIcons = {
  entity: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="5" r="3" stroke="currentColor" stroke-width="1.5"/><circle cx="4" cy="15" r="3" stroke="currentColor" stroke-width="1.5"/><circle cx="16" cy="15" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M10 8v4M10 12L4 12.5M10 12l6 .5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  rule: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M4 10h12M4 6h8M4 14h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  relation: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M3 14l4-4 3 3 4-5 3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  active: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.5"/><path d="M10 6v4l3 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
}

const kpis = computed(() => [
  { label: '对象类型', value: String(stats.value.entity_count ?? '-'), trend: 0, color: 'semantic', icon: kpiIcons.entity },
  { label: '活跃规则', value: String(stats.value.active_rule_count ?? '-'), trend: 0, color: 'kinetic', icon: kpiIcons.rule },
  { label: '关系数量', value: String(stats.value.relation_count ?? '-'), trend: 0, color: 'dynamic', icon: kpiIcons.relation },
  { label: '总规则数', value: String(stats.value.rule_count ?? '-'), trend: 0, color: 'warning', icon: kpiIcons.active },
])

const tierDist = computed(() => (stats.value.tier_distribution as { tier: number; name: string; count: number; pct: number }[]) ?? [])

const activityIcons: Record<string, string> = {
  create: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  update: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7a5 5 0 0110 0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M10 5l2 2-2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  execute: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M4 2l8 5-8 5V2z" fill="currentColor"/></svg>`,
  warning: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2l5.5 10H1.5L7 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M7 6v3M7 10.5v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  delete: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  rollback: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7a5 5 0 0110 0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
}

const activities = computed(() =>
  ((stats.value.recent_activities as { id: string; type: string; title: string; description: string; time: string }[]) ?? []).map(a => ({
    ...a,
    icon: activityIcons[a.type] ?? activityIcons.update,
  }))
)

const allObjects = computed(() =>
  (stats.value.health_status as { id: string; name: string; tier: number; status: string }[]) ?? []
)
</script>

<style scoped>
.dashboard {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.dashboard__header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.live-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--status-success-bg);
  color: var(--status-success);
  font-size: 12px;
  font-weight: 600;
}
.live-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--status-success);
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.btn-secondary {
  padding: 6px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--neutral-300);
  background: var(--neutral-0);
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-700);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.btn-secondary:hover {
  border-color: var(--semantic-400);
  color: var(--semantic-600);
}

/* KPI 卡片 */
.dashboard__kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.kpi-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-xl);
  padding: 20px;
  display: flex;
  gap: 16px;
  align-items: flex-start;
  box-shadow: var(--shadow-xs);
  transition: box-shadow var(--transition-fast), transform var(--transition-fast);
}
.kpi-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.kpi-card__icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.kpi-card--semantic .kpi-card__icon { background: var(--semantic-50); color: var(--semantic-600); }
.kpi-card--kinetic .kpi-card__icon { background: var(--kinetic-50); color: var(--kinetic-600); }
.kpi-card--dynamic .kpi-card__icon { background: var(--dynamic-50); color: var(--dynamic-600); }
.kpi-card--warning .kpi-card__icon { background: var(--status-warning-bg); color: var(--status-warning); }

.kpi-card__value {
  font-size: 28px;
  font-weight: 700;
  color: var(--neutral-900);
  line-height: 1;
  margin-bottom: 4px;
}
.kpi-card__label {
  font-size: 12px;
  color: var(--neutral-500);
  margin-bottom: 6px;
}
.kpi-card__trend {
  font-size: 11px;
  font-weight: 500;
}
.trend--up { color: var(--status-success); }
.trend--down { color: var(--status-error); }

/* 中间两列 */
.dashboard__mid-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* 通用卡片 */
.dash-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-xl);
  padding: 20px;
  box-shadow: var(--shadow-xs);
}
.dash-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

/* Tier 分布 */
.tier-dist { display: flex; flex-direction: column; gap: 14px; }
.tier-dist__item { display: flex; align-items: center; gap: 12px; }
.tier-dist__label {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 120px;
  font-size: 12px;
  color: var(--neutral-700);
  flex-shrink: 0;
}
.tier-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}
.tier-dot--1 { background: var(--tier1-primary); }
.tier-dot--2 { background: var(--tier2-primary); }
.tier-dot--3 { background: var(--tier3-primary); }

.tier-dist__bar-wrap {
  flex: 1;
  height: 8px;
  background: var(--neutral-100);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.tier-dist__bar {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 600ms ease-out;
}
.tier-dist__bar--1 { background: var(--tier1-primary); }
.tier-dist__bar--2 { background: var(--tier2-primary); }
.tier-dist__bar--3 { background: var(--tier3-primary); }
.tier-dist__count {
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-700);
  width: 20px;
  text-align: right;
}

/* 活动列表 */
.activity-list { display: flex; flex-direction: column; gap: 12px; }
.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.activity-item__icon {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.activity-icon--create { background: var(--dynamic-50); color: var(--dynamic-600); }
.activity-icon--update { background: var(--semantic-50); color: var(--semantic-600); }
.activity-icon--execute { background: var(--kinetic-50); color: var(--kinetic-600); }
.activity-icon--warning { background: var(--status-warning-bg); color: var(--status-warning); }

.activity-item__body { flex: 1; }
.activity-item__time { flex-shrink: 0; padding-top: 2px; }

/* 健康状态网格 */
.health-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.health-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--neutral-200);
  font-size: 12px;
  font-weight: 500;
  transition: all var(--transition-fast);
}
.health-item--active { background: var(--status-success-bg); border-color: var(--status-success); color: var(--status-success); }
.health-item--warning { background: var(--status-warning-bg); border-color: var(--status-warning); color: var(--status-warning); }
.health-item--error { background: var(--status-error-bg); border-color: var(--status-error); color: var(--status-error); }
.health-item__name { color: var(--neutral-800); }
.health-item__tier {
  font-size: 10px;
  font-weight: 600;
  opacity: 0.7;
}
</style>
