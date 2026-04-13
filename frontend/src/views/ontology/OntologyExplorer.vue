<template>
  <div class="explorer">
    <!-- 左侧对象列表面板 -->
    <aside class="explorer__panel">
      <div class="explorer__search">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" class="explorer__search-icon">
          <circle cx="6" cy="6" r="4" stroke="currentColor" stroke-width="1.5"/>
          <path d="M9 9l2.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <input v-model="searchQuery" class="explorer__search-input" placeholder="搜索对象类型..." />
      </div>

      <div class="explorer__tier-group" v-for="group in filteredGroups" :key="group.tier">
        <div class="explorer__tier-header">
          <TierBadge :tier="group.tier" />
          <span class="explorer__tier-label">{{ group.label }}</span>
          <span class="explorer__tier-count">{{ group.entities.length }}</span>
        </div>
        <EntityCard
          v-for="entity in group.entities"
          :key="entity.id"
          :entity="entity"
          :selected="selectedId === entity.id"
          @click="selectEntity"
        />
      </div>
    </aside>

    <!-- 右侧详情区 -->
    <div class="explorer__content">
      <template v-if="selected">
        <!-- 标题区 -->
        <div class="explorer__detail-header">
          <div class="explorer__detail-title">
            <TierBadge :tier="selected.tier" />
            <div>
              <h1 class="text-h1">{{ selected.name }}</h1>
              <p class="text-caption">{{ selected.nameCn }} · Tier {{ selected.tier }} {{ tierLabel(selected.tier) }}</p>
            </div>
          </div>
        </div>

        <!-- 指标卡片行 -->
        <div class="explorer__metrics">
          <div class="metric-card" v-for="m in metrics" :key="m.label">
            <span class="metric-card__value">{{ m.value }}</span>
            <span class="metric-card__label">{{ m.label }}</span>
          </div>
        </div>

        <!-- Tab 内容 -->
        <div class="explorer__tabs">
          <button
            v-for="tab in tabs"
            :key="tab"
            class="explorer__tab"
            :class="{ 'explorer__tab--active': activeTab === tab }"
            @click="activeTab = tab"
          >{{ tab }}</button>
        </div>

        <div class="explorer__tab-content">
          <!-- 属性列表 -->
          <template v-if="activeTab === '属性'">
            <table class="data-table">
              <thead>
                <tr>
                  <th>属性名称</th>
                  <th>类型</th>
                  <th>描述</th>
                  <th>必填</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="attr in selectedAttrs" :key="attr.name">
                  <td><code class="text-code">{{ attr.name }}</code></td>
                  <td><span class="type-tag">{{ attr.type }}</span></td>
                  <td class="text-body">{{ attr.desc }}</td>
                  <td>
                    <span class="status-dot" :class="attr.required ? 'status-dot--success' : 'status-dot--muted'"></span>
                  </td>
                </tr>
              </tbody>
            </table>
          </template>

          <!-- 关系列表 -->
          <template v-else-if="activeTab === '关系'">
            <div class="relation-list">
              <div class="relation-item" v-for="rel in selectedRelations" :key="rel.name">
                <div class="relation-item__from">
                  <TierBadge :tier="selected.tier" />
                  <span>{{ selected.name }}</span>
                </div>
                <div class="relation-item__arrow">
                  <span class="relation-item__type">{{ rel.type }}</span>
                  <svg width="40" height="12" viewBox="0 0 40 12" fill="none">
                    <path d="M0 6h36M30 2l6 4-6 4" stroke="var(--neutral-400)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <div class="relation-item__to">
                  <TierBadge :tier="rel.targetTier" />
                  <span>{{ rel.target }}</span>
                </div>
              </div>
            </div>
          </template>

          <!-- 规则列表 -->
          <template v-else-if="activeTab === '规则'">
            <table class="data-table">
              <thead>
                <tr>
                  <th>规则ID</th>
                  <th>规则名称</th>
                  <th>触发条件</th>
                  <th>执行动作</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rule in selectedRules" :key="rule.id">
                  <td><code class="text-code">{{ rule.id }}</code></td>
                  <td class="text-body-medium">{{ rule.name }}</td>
                  <td><code class="text-code">{{ rule.condition }}</code></td>
                  <td class="text-body">{{ rule.action }}</td>
                  <td>
                    <span class="status-dot" :class="rule.status === 'active' ? 'status-dot--success' : 'status-dot--warning'"></span>
                  </td>
                </tr>
              </tbody>
            </table>
          </template>

          <!-- 动作列表 -->
          <template v-else-if="activeTab === '动作'">
            <div class="action-list">
              <div class="action-item" v-for="act in selectedActions" :key="act.id">
                <div class="action-item__info">
                  <span class="action-item__name text-body-medium">{{ act.name }}</span>
                  <span class="action-item__type text-caption">{{ act.type }}</span>
                </div>
                <span class="action-status" :class="`action-status--${act.status}`">{{ act.status }}</span>
                <button class="action-exec-btn">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M3 1.5l7 4.5-7 4.5V1.5z" fill="currentColor"/>
                  </svg>
                  执行
                </button>
              </div>
            </div>
          </template>

          <!-- 血缘占位 -->
          <template v-else>
            <div class="placeholder-tab">
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                <rect x="8" y="8" width="24" height="24" rx="4" stroke="var(--neutral-300)" stroke-width="2"/>
                <path d="M14 20h12M14 15h8M14 25h6" stroke="var(--neutral-300)" stroke-width="2" stroke-linecap="round"/>
              </svg>
              <p class="text-caption">{{ activeTab }}内容待开发</p>
            </div>
          </template>
        </div>
      </template>

      <!-- 未选中状态 -->
      <template v-else>
        <div class="explorer__empty">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="20" r="8" stroke="var(--neutral-300)" stroke-width="2"/>
            <circle cx="14" cy="48" r="8" stroke="var(--neutral-300)" stroke-width="2"/>
            <circle cx="50" cy="48" r="8" stroke="var(--neutral-300)" stroke-width="2"/>
            <path d="M32 28v8M32 36L14 40M32 36l18 4" stroke="var(--neutral-300)" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <p class="text-h3" style="color: var(--neutral-500); margin-top: 16px;">选择左侧对象类型查看详情</p>
          <p class="text-caption" style="margin-top: 6px;">共 {{ totalEntities }} 个对象类型，覆盖 3 个 Tier 层级</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import EntityCard, { type Entity } from '../../components/common/EntityCard.vue'
import TierBadge from '../../components/common/TierBadge.vue'

const searchQuery = ref('')
const selectedId = ref<string | null>(null)
const activeTab = ref('属性')
const tabs = ['属性', '关系', '规则', '动作', '血缘']

const allEntities: Entity[] = [
  { id: 'customer', name: 'Customer', nameCn: '客户', tier: 1, attrs: 24, relations: 11, rules: 8, status: 'active' },
  { id: 'order', name: 'Order', nameCn: '订单', tier: 1, attrs: 18, relations: 7, rules: 5, status: 'active' },
  { id: 'product', name: 'Product', nameCn: '产品', tier: 1, attrs: 15, relations: 6, rules: 4, status: 'active' },
  { id: 'touchpoint', name: 'Touchpoint', nameCn: '触点', tier: 1, attrs: 12, relations: 5, rules: 3, status: 'warning' },
  { id: 'channel', name: 'Channel', nameCn: '渠道', tier: 1, attrs: 10, relations: 4, rules: 2, status: 'active' },
  { id: 'agent', name: 'Agent', nameCn: '坐席', tier: 1, attrs: 9, relations: 3, rules: 2, status: 'active' },
  { id: 'contract', name: 'Contract', nameCn: '合同', tier: 1, attrs: 14, relations: 5, rules: 6, status: 'active' },
  { id: 'campaign', name: 'Campaign', nameCn: '营销活动', tier: 2, attrs: 16, relations: 8, rules: 7, status: 'active' },
  { id: 'segment', name: 'CustomerSegment', nameCn: '客户分群', tier: 2, attrs: 11, relations: 4, rules: 5, status: 'active' },
  { id: 'strategy', name: 'Strategy', nameCn: '策略', tier: 2, attrs: 13, relations: 6, rules: 9, status: 'warning' },
  { id: 'rule', name: 'RuleSet', nameCn: '规则集', tier: 2, attrs: 8, relations: 3, rules: 12, status: 'active' },
  { id: 'fttr-sub', name: 'FTTRSubscription', nameCn: 'FTTR续约订阅', tier: 3, attrs: 18, relations: 5, rules: 3, status: 'active' },
  { id: 'fttr-strat', name: 'FTTRStrategy', nameCn: 'FTTR续约策略', tier: 3, attrs: 14, relations: 4, rules: 6, status: 'active' },
]

const groups = [
  { tier: 1 as const, label: 'Tier 1 核心对象', entities: allEntities.filter(e => e.tier === 1) },
  { tier: 2 as const, label: 'Tier 2 领域对象', entities: allEntities.filter(e => e.tier === 2) },
  { tier: 3 as const, label: 'Tier 3 场景对象', entities: allEntities.filter(e => e.tier === 3) },
]

const filteredGroups = computed(() => {
  if (!searchQuery.value) return groups
  const q = searchQuery.value.toLowerCase()
  return groups.map(g => ({
    ...g,
    entities: g.entities.filter(e =>
      e.name.toLowerCase().includes(q) || e.nameCn.includes(q)
    )
  })).filter(g => g.entities.length > 0)
})

const totalEntities = allEntities.length
const selected = computed(() => allEntities.find(e => e.id === selectedId.value) ?? null)

const metrics = computed(() => selected.value ? [
  { label: '属性', value: selected.value.attrs },
  { label: '关系', value: selected.value.relations },
  { label: '规则', value: selected.value.rules },
  { label: '动作', value: 2 },
] : [])

const tierLabel = (t: number) => ({ 1: '核心对象', 2: '领域对象', 3: '场景对象' }[t] ?? '')

function selectEntity(entity: Entity) {
  selectedId.value = entity.id
  activeTab.value = '属性'
}

const attrMap: Record<string, { name: string; type: string; desc: string; required: boolean }[]> = {
  customer: [
    { name: 'customer_id', type: 'string', desc: '客户唯一标识', required: true },
    { name: 'name', type: 'string', desc: '客户姓名', required: true },
    { name: 'phone', type: 'string', desc: '联系电话', required: true },
    { name: 'segment', type: 'ref', desc: '所属分群 → CustomerSegment', required: false },
    { name: 'ltv_score', type: 'number', desc: '生命周期价值评分', required: false },
    { name: 'churn_risk', type: 'computed', desc: '流失风险概率 (0-1)', required: false },
    { name: 'created_at', type: 'date', desc: '创建时间', required: true },
  ],
  'fttr-sub': [
    { name: 'subscription_id', type: 'string', desc: '订阅唯一标识', required: true },
    { name: 'customer_id', type: 'ref', desc: '关联客户 → Customer', required: true },
    { name: 'product_id', type: 'ref', desc: '关联产品 → Product', required: true },
    { name: 'expire_date', type: 'date', desc: '到期日期', required: true },
    { name: 'days_to_expire', type: 'computed', desc: '距到期天数', required: false },
    { name: 'monthly_fee', type: 'number', desc: '月费（元）', required: true },
  ],
}

const selectedAttrs = computed(() =>
  attrMap[selectedId.value ?? ''] ?? [
    { name: 'id', type: 'string', desc: '唯一标识', required: true },
    { name: 'name', type: 'string', desc: '名称', required: true },
    { name: 'created_at', type: 'date', desc: '创建时间', required: true },
    { name: 'updated_at', type: 'date', desc: '更新时间', required: false },
  ]
)

const selectedRelations = computed(() => [
  { name: 'belongs_to', type: 'belongs_to', target: 'Customer', targetTier: 1 as const },
  { name: 'has_product', type: 'has_one', target: 'Product', targetTier: 1 as const },
  { name: 'in_campaign', type: 'many_to_many', target: 'Campaign', targetTier: 2 as const },
])

const ruleMap: Record<string, { id: string; name: string; condition: string; action: string; status: string }[]> = {
  customer: [
    { id: 'rule_001', name: '高价值客户识别', condition: 'ltv_score >= 80 AND tenure >= 12', action: '标记为高价值', status: 'active' },
    { id: 'rule_002', name: '流失预警', condition: 'churn_risk >= 0.7', action: '触发挽留策略', status: 'active' },
    { id: 'rule_003', name: '沉默客户唤醒', condition: 'last_active_days > 90', action: '推送唤醒活动', status: 'active' },
  ],
  'fttr-sub': [
    { id: 'rule_005', name: '到期续约提醒', condition: 'days_to_expire <= 30', action: '发送续约提醒', status: 'active' },
    { id: 'rule_006', name: '欠费预警', condition: 'overdue_days > 7', action: '发送催缴通知', status: 'warning' },
  ],
  campaign: [
    { id: 'rule_004', name: '预算超限预警', condition: 'spend > budget * 0.9', action: '通知负责人', status: 'active' },
  ],
}
const selectedRules = computed(() =>
  ruleMap[selectedId.value ?? ''] ?? [
    { id: 'rule_default', name: '默认校验规则', condition: 'id IS NOT NULL', action: '拒绝空值', status: 'active' },
  ]
)

const actionMap: Record<string, { id: string; name: string; type: string; status: string }[]> = {
  customer: [
    { id: 'act_001', name: '发送续约优惠', type: 'campaign', status: 'active' },
    { id: 'act_002', name: '升级FTTR套餐', type: 'upsell', status: 'active' },
  ],
  'fttr-sub': [
    { id: 'act_003', name: '自动续约', type: 'automation', status: 'active' },
    { id: 'act_004', name: '到期提醒短信', type: 'notification', status: 'active' },
  ],
  campaign: [
    { id: 'act_005', name: '启动活动', type: 'lifecycle', status: 'active' },
  ],
}
const selectedActions = computed(() =>
  actionMap[selectedId.value ?? ''] ?? [
    { id: 'act_default', name: '查看详情', type: 'navigation', status: 'active' },
  ]
)
</script>

<style scoped>
.explorer {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* 左侧面板 */
.explorer__panel {
  width: 280px;
  min-width: 280px;
  background: var(--neutral-0);
  border-right: 1px solid var(--neutral-200);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.explorer__search {
  position: relative;
  padding: 12px;
  border-bottom: 1px solid var(--neutral-100);
  flex-shrink: 0;
}
.explorer__search-icon {
  position: absolute;
  left: 22px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--neutral-500);
}
.explorer__search-input {
  width: 100%;
  padding: 7px 10px 7px 32px;
  border-radius: var(--radius-md);
  border: 1px solid var(--neutral-200);
  background: var(--neutral-50);
  font-size: 13px;
  color: var(--neutral-800);
  outline: none;
  transition: border-color var(--transition-fast);
}
.explorer__search-input:focus {
  border-color: var(--semantic-400);
  background: var(--neutral-0);
}
.explorer__search-input::placeholder { color: var(--neutral-400); }

.explorer__tier-group {
  padding: 8px 8px 4px;
  overflow-y: auto;
}
.explorer__tier-group + .explorer__tier-group {
  border-top: 1px solid var(--neutral-100);
}

.explorer__tier-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 6px 8px;
}
.explorer__tier-label {
  flex: 1;
  font-size: 11px;
  font-weight: 600;
  color: var(--neutral-600);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.explorer__tier-count {
  font-size: 11px;
  color: var(--neutral-500);
  background: var(--neutral-100);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.explorer__tier-group .entity-card {
  margin-bottom: 4px;
}

/* 右侧内容区 */
.explorer__content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.explorer__detail-header {
  margin-bottom: 20px;
}
.explorer__detail-title {
  display: flex;
  align-items: center;
  gap: 14px;
}
.explorer__detail-title .tier-badge {
  width: 40px;
  height: 40px;
  font-size: 14px;
  border-radius: var(--radius-lg);
}

/* 指标卡片 */
.explorer__metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.metric-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: var(--shadow-xs);
}
.metric-card__value {
  font-size: 28px;
  font-weight: 700;
  color: var(--neutral-900);
  line-height: 1;
}
.metric-card__label {
  font-size: 12px;
  color: var(--neutral-500);
}

/* Tabs */
.explorer__tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--neutral-200);
  margin-bottom: 20px;
}
.explorer__tab {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-600);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: color var(--transition-fast), border-color var(--transition-fast);
}
.explorer__tab:hover { color: var(--neutral-800); }
.explorer__tab--active {
  color: var(--semantic-600);
  border-bottom-color: var(--semantic-600);
}

/* 表格 */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  text-align: left;
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--neutral-500);
  border-bottom: 1px solid var(--neutral-200);
}
.data-table td {
  padding: 10px 12px;
  color: var(--neutral-700);
  border-bottom: 1px solid var(--neutral-100);
}
.data-table tr:nth-child(even) td { background: var(--neutral-50); }
.data-table tr:hover td { background: var(--semantic-50); }

.type-tag {
  display: inline-block;
  padding: 1px 7px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
  background: var(--neutral-100);
  color: var(--neutral-700);
  font-family: var(--font-mono);
}

.status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: var(--radius-full);
}
.status-dot--success { background: var(--status-success); }
.status-dot--warning { background: var(--status-warning); }
.status-dot--muted { background: var(--neutral-300); }

/* 动作列表 */
.action-list { display: flex; flex-direction: column; gap: 8px; }
.action-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 16px; background: var(--neutral-0);
  border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
  transition: border-color var(--transition-fast);
}
.action-item:hover { border-color: var(--kinetic-400); }
.action-item__info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.action-item__name { font-size: 13px; }
.action-item__type { font-size: 11px; color: var(--neutral-500); }
.action-status {
  font-size: 11px; font-weight: 500; padding: 2px 8px;
  border-radius: var(--radius-full);
}
.action-status--active { background: var(--status-success-bg); color: var(--status-success); }
.action-status--inactive { background: var(--neutral-100); color: var(--neutral-500); }
.action-status--warning { background: var(--status-warning-bg); color: var(--status-warning); }
.action-exec-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 5px 12px; border-radius: var(--radius-md); border: none;
  background: var(--kinetic-500); color: #fff; font-size: 12px;
  font-weight: 500; cursor: pointer; transition: background var(--transition-fast);
}
.action-exec-btn:hover { background: var(--kinetic-600); }

/* 关系列表 */
.relation-list { display: flex; flex-direction: column; gap: 12px; }
.relation-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
}
.relation-item__from, .relation-item__to {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-800);
}
.relation-item__arrow {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.relation-item__type {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--neutral-500);
}

/* 占位 */
.placeholder-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  gap: 12px;
  color: var(--neutral-400);
}

/* 空状态 */
.explorer__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
  text-align: center;
}
</style>
