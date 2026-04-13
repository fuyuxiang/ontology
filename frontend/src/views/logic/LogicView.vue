<template>
  <div class="logic-page">
    <div class="logic-page__header">
      <div>
        <h1 class="text-display">业务逻辑</h1>
        <p class="text-caption" style="margin-top: 4px;">规则引擎管理 · 条件匹配 · 动作执行</p>
      </div>
      <div class="logic-page__actions">
        <button class="btn-primary" @click="showAdd = true">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新建规则
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="logic-page__stats">
      <div class="stat-card stat-card--semantic">
        <div class="stat-card__value">{{ rules.length }}</div>
        <div class="stat-card__label">总规则数</div>
      </div>
      <div class="stat-card stat-card--dynamic">
        <div class="stat-card__value">{{ rules.filter(r => r.status === 'active').length }}</div>
        <div class="stat-card__label">活跃规则</div>
      </div>
      <div class="stat-card stat-card--kinetic">
        <div class="stat-card__value">{{ rules.filter(r => r.status === 'warning').length }}</div>
        <div class="stat-card__label">需关注</div>
      </div>
      <div class="stat-card stat-card--error">
        <div class="stat-card__value">{{ rules.filter(r => r.status === 'disabled').length }}</div>
        <div class="stat-card__label">已禁用</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="logic-page__filter">
      <input v-model="search" class="logic-search" placeholder="搜索规则名称或条件..." />
      <div class="logic-filter-tags">
        <button
          v-for="f in filters"
          :key="f.value"
          class="filter-tag"
          :class="{ 'filter-tag--active': activeFilter === f.value }"
          @click="activeFilter = f.value"
        >{{ f.label }}</button>
      </div>
    </div>

    <!-- 规则列表 -->
    <div class="logic-page__list">
      <div
        v-for="rule in filteredRules"
        :key="rule.id"
        class="rule-card"
        :class="{ 'rule-card--expanded': expandedId === rule.id }"
        @click="expandedId = expandedId === rule.id ? null : rule.id"
      >
        <div class="rule-card__header">
          <span class="rule-card__status" :class="`rule-card__status--${rule.status}`"></span>
          <code class="rule-card__id text-code">{{ rule.id }}</code>
          <span class="rule-card__name text-body-medium">{{ rule.name }}</span>
          <span class="rule-card__entity text-caption">{{ rule.entity }}</span>
          <span class="rule-card__priority" :class="`priority--${rule.priority}`">{{ rule.priority }}</span>
        </div>
        <div v-if="expandedId === rule.id" class="rule-card__detail">
          <div class="rule-detail-row">
            <span class="rule-detail-label">触发条件</span>
            <code class="text-code">{{ rule.condition }}</code>
          </div>
          <div class="rule-detail-row">
            <span class="rule-detail-label">执行动作</span>
            <span>{{ rule.action }}</span>
          </div>
          <div class="rule-detail-row">
            <span class="rule-detail-label">触发次数</span>
            <span>{{ rule.triggerCount }} 次（近30天）</span>
          </div>
          <div class="rule-detail-row">
            <span class="rule-detail-label">最后触发</span>
            <span>{{ rule.lastTriggered }}</span>
          </div>
        </div>
      </div>
      <div v-if="filteredRules.length === 0" class="logic-empty">
        <p class="text-caption">无匹配规则</p>
      </div>
    </div>

    <!-- 新建规则弹窗 -->
    <Teleport to="body">
      <div v-if="showAdd" class="modal-overlay" @click.self="showAdd = false">
        <div class="modal-panel">
          <h3 class="text-h2" style="margin-bottom: 16px;">新建业务规则</h3>
          <p class="text-caption" style="margin-bottom: 20px;">功能开发中，敬请期待</p>
          <button class="btn-primary" @click="showAdd = false">关闭</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const search = ref('')
const activeFilter = ref('all')
const expandedId = ref<string | null>(null)
const showAdd = ref(false)

const filters = [
  { label: '全部', value: 'all' },
  { label: '活跃', value: 'active' },
  { label: '需关注', value: 'warning' },
  { label: '已禁用', value: 'disabled' },
]

interface Rule {
  id: string; name: string; entity: string; condition: string; action: string
  status: 'active' | 'warning' | 'disabled'; priority: 'high' | 'medium' | 'low'
  triggerCount: number; lastTriggered: string
}

const rules: Rule[] = [
  { id: 'rule_001', name: '高价值客户识别', entity: 'Customer', condition: 'ltv_score >= 80 AND tenure >= 12', action: '标记为高价值客户', status: 'active', priority: 'high', triggerCount: 1247, lastTriggered: '2小时前' },
  { id: 'rule_002', name: '流失预警', entity: 'Customer', condition: 'churn_risk >= 0.7', action: '触发挽留策略', status: 'active', priority: 'high', triggerCount: 892, lastTriggered: '30分钟前' },
  { id: 'rule_003', name: '大额订单审批', entity: 'Order', condition: 'amount >= 5000', action: '触发人工审批流程', status: 'active', priority: 'medium', triggerCount: 156, lastTriggered: '1天前' },
  { id: 'rule_004', name: '预算超限预警', entity: 'Campaign', condition: 'spend > budget * 0.9', action: '通知活动负责人', status: 'warning', priority: 'high', triggerCount: 23, lastTriggered: '3小时前' },
  { id: 'rule_005', name: '到期续约提醒', entity: 'FTTRSubscription', condition: 'days_to_expire <= 30', action: '发送续约提醒', status: 'active', priority: 'high', triggerCount: 2847, lastTriggered: '1小时前' },
  { id: 'rule_006', name: '欠费预警', entity: 'FTTRSubscription', condition: 'overdue_days > 7', action: '发送催缴通知', status: 'warning', priority: 'medium', triggerCount: 67, lastTriggered: '5小时前' },
  { id: 'rule_007', name: '高价值续约', entity: 'FTTRSubscription', condition: 'monthly_fee >= 200 AND churn_risk >= 0.5', action: '触发专属优惠', status: 'active', priority: 'high', triggerCount: 534, lastTriggered: '45分钟前' },
  { id: 'rule_008', name: '沉默客户唤醒', entity: 'Customer', condition: 'last_active_days > 90', action: '推送唤醒活动', status: 'active', priority: 'medium', triggerCount: 312, lastTriggered: '2天前' },
  { id: 'rule_009', name: '策略效果评估', entity: 'FTTRStrategy', condition: 'actual_conversion < predicted * 0.5', action: '暂停策略并通知', status: 'active', priority: 'low', triggerCount: 8, lastTriggered: '1周前' },
  { id: 'rule_010', name: '旧版分群规则（废弃）', entity: 'CustomerSegment', condition: 'segment_version < 2', action: '迁移至新版', status: 'disabled', priority: 'low', triggerCount: 0, lastTriggered: '—' },
]

const filteredRules = computed(() => {
  let list = rules as Rule[]
  if (activeFilter.value !== 'all') list = list.filter(r => r.status === activeFilter.value)
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(r => r.name.includes(q) || r.id.includes(q) || r.condition.toLowerCase().includes(q))
  }
  return list
})
</script>

<style scoped>
.logic-page { padding: 24px; }
.logic-page__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.logic-page__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }

.stat-card { padding: 16px; border-radius: var(--radius-lg); text-align: center; border: 1px solid var(--neutral-200); background: var(--neutral-0); }
.stat-card__value { font-size: 28px; font-weight: 700; line-height: 1; }
.stat-card__label { font-size: 11px; color: var(--neutral-600); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.3px; }
.stat-card--semantic .stat-card__value { color: var(--semantic-600); }
.stat-card--dynamic .stat-card__value { color: var(--dynamic-600); }
.stat-card--kinetic .stat-card__value { color: var(--kinetic-600); }
.stat-card--error .stat-card__value { color: var(--neutral-400); }

.logic-page__filter { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.logic-search { flex: 1; padding: 8px 12px; border: 1px solid var(--neutral-200); border-radius: var(--radius-md); font-size: 13px; background: var(--neutral-0); color: var(--neutral-700); outline: none; }
.logic-search:focus { border-color: var(--semantic-500); }
.logic-filter-tags { display: flex; gap: 6px; }
.filter-tag { padding: 5px 12px; border-radius: var(--radius-full); border: 1px solid var(--neutral-200); background: var(--neutral-0); font-size: 12px; color: var(--neutral-600); cursor: pointer; transition: all var(--transition-fast); }
.filter-tag:hover { border-color: var(--semantic-400); color: var(--semantic-600); }
.filter-tag--active { background: var(--semantic-50); border-color: var(--semantic-500); color: var(--semantic-600); font-weight: 500; }

.logic-page__list { display: flex; flex-direction: column; gap: 6px; }
.rule-card { background: var(--neutral-0); border: 1px solid var(--neutral-200); border-radius: var(--radius-md); cursor: pointer; transition: border-color var(--transition-fast), box-shadow var(--transition-fast); }
.rule-card:hover { border-color: var(--semantic-300); }
.rule-card--expanded { border-color: var(--semantic-400); box-shadow: var(--shadow-sm); }
.rule-card__header { display: flex; align-items: center; gap: 10px; padding: 12px 16px; }
.rule-card__status { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.rule-card__status--active { background: var(--status-success); }
.rule-card__status--warning { background: var(--status-warning); }
.rule-card__status--disabled { background: var(--neutral-300); }
.rule-card__id { font-size: 11px; color: var(--neutral-500); }
.rule-card__name { flex: 1; font-size: 13px; }
.rule-card__entity { font-size: 11px; color: var(--neutral-500); }
.rule-card__priority { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: var(--radius-full); text-transform: uppercase; }
.priority--high { background: var(--status-error-bg); color: var(--status-error); }
.priority--medium { background: var(--status-warning-bg); color: var(--kinetic-700); }
.priority--low { background: var(--neutral-100); color: var(--neutral-500); }
.rule-card__detail { padding: 0 16px 16px; border-top: 1px solid var(--neutral-100); padding-top: 12px; }
.rule-detail-row { display: flex; gap: 12px; padding: 4px 0; font-size: 12px; color: var(--neutral-700); }
.rule-detail-label { width: 80px; flex-shrink: 0; font-weight: 500; color: var(--neutral-500); }
.logic-empty { padding: 40px; text-align: center; }

.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: var(--radius-md); border: none; background: var(--semantic-600); color: #fff; font-size: 13px; font-weight: 500; cursor: pointer; transition: background var(--transition-fast); }
.btn-primary:hover { background: var(--semantic-700); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-panel { background: var(--neutral-0); border-radius: var(--radius-xl); padding: 24px; min-width: 360px; box-shadow: var(--shadow-xl); }
</style>