<template>
  <div class="detail">
    <OntologyBreadcrumb :items="breadcrumbs" />

    <div class="detail__header">
      <div class="detail__title-row">
        <div class="detail__icon" :class="`detail__icon--tier${entity.tier}`">
          {{ entity.name.charAt(0) }}
        </div>
        <div>
          <h1 class="text-h1">{{ entity.name }}</h1>
          <div class="detail__tags">
            <span class="detail__tag-cn">{{ entity.nameCn }}</span>
            <span class="tier-tag" :class="`tier-tag--tier${entity.tier}`">Tier {{ entity.tier }} · {{ tierLabel }}</span>
            <span class="status-badge" :class="`status-badge--${entity.status}`">● {{ statusLabel }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 指标行 -->
    <div class="detail__metrics">
      <MetricCard
        v-for="m in metrics"
        :key="m.label"
        :value="m.value"
        :label="m.label"
        :trend="m.trend"
        trend-label="较上月"
        :clickable="true"
      />
    </div>

    <!-- Tabs -->
    <div class="detail__tabs">
      <button
        v-for="tab in tabs"
        :key="tab"
        class="detail__tab"
        :class="{ 'detail__tab--active': activeTab === tab }"
        @click="activeTab = tab"
      >{{ tab }}</button>
    </div>

    <!-- 属性表格 -->
    <div class="detail__content">
      <template v-if="activeTab === '属性'">
        <table class="data-table">
          <thead>
            <tr>
              <th>属性名称</th>
              <th>类型</th>
              <th>描述</th>
              <th>必填</th>
              <th>示例值</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="attr in attrs" :key="attr.name">
              <td><code class="text-code">{{ attr.name }}</code></td>
              <td><span class="type-tag">{{ attr.type }}</span></td>
              <td class="text-body">{{ attr.desc }}</td>
              <td>
                <span class="status-dot" :class="attr.required ? 'status-dot--success' : 'status-dot--muted'"></span>
              </td>
              <td class="text-caption" style="font-family: var(--font-mono);">{{ attr.example }}</td>
            </tr>
          </tbody>
        </table>
      </template>

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
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import OntologyBreadcrumb from '../../components/common/OntologyBreadcrumb.vue'
import MetricCard from '../../components/common/MetricCard.vue'

const route = useRoute()
const activeTab = ref('属性')
const tabs = ['属性', '关系', '规则', '动作', '血缘']

const entity = computed(() => ({
  id: route.params.id as string,
  name: 'FTTRSubscription',
  nameCn: 'FTTR续约订阅',
  tier: 3 as const,
  attrs: 18,
  relations: 5,
  rules: 3,
  actions: 2,
  status: 'active' as const,
}))

const tierLabel = computed(() => ({ 1: '核心对象', 2: '领域对象', 3: '场景对象' }[entity.value.tier]))
const statusLabel = computed(() => ({ active: '活跃', warning: '警告', error: '异常' }[entity.value.status]))

const breadcrumbs = computed(() => [
  { label: '本体管理', path: '/ontology' },
  { label: '对象类型', path: '/ontology' },
  { label: `Tier ${entity.value.tier} 场景`, tier: entity.value.tier },
  { label: entity.value.name },
])

const metrics = computed(() => [
  { label: '属性', value: entity.value.attrs,     trend:  2.1 },
  { label: '关系', value: entity.value.relations, trend:  0   },
  { label: '规则', value: entity.value.rules,     trend: -1.5 },
  { label: '动作', value: entity.value.actions,   trend:  5.0 },
])

const attrs = [
  { name: 'subscription_id', type: 'string', desc: '订阅唯一标识', required: true, example: 'sub_20240101_001' },
  { name: 'customer_id', type: 'ref', desc: '关联客户 → Customer', required: true, example: 'cust_10086' },
  { name: 'product_id', type: 'ref', desc: '关联产品 → Product', required: true, example: 'prod_fttr_200m' },
  { name: 'expire_date', type: 'date', desc: '到期日期', required: true, example: '2024-03-31' },
  { name: 'days_to_expire', type: 'computed', desc: '距到期天数（实时计算）', required: false, example: '28' },
  { name: 'monthly_fee', type: 'number', desc: '月费（元）', required: true, example: '299.00' },
  { name: 'bandwidth', type: 'string', desc: '带宽规格', required: true, example: '200M' },
  { name: 'contract_years', type: 'number', desc: '合同年限', required: true, example: '2' },
  { name: 'auto_renew', type: 'boolean', desc: '是否自动续约', required: false, example: 'false' },
  { name: 'churn_risk', type: 'computed', desc: '流失风险评分 (0-1)', required: false, example: '0.73' },
]
</script>

<style scoped>
.detail {
  padding: 24px;
  max-width: 1000px;
}

.detail__header { margin: 16px 0 20px; }
.detail__title-row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.detail__icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.detail__icon--tier1 { background: var(--tier1-primary); }
.detail__icon--tier2 { background: var(--tier2-primary); }
.detail__icon--tier3 { background: var(--tier3-primary); }

.detail__tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.detail__tag-cn {
  font-size: 13px;
  color: var(--neutral-600);
}
.tier-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}
.tier-tag--tier1 { background: var(--tier1-bg); color: var(--tier1-text); }
.tier-tag--tier2 { background: var(--tier2-bg); color: var(--tier2-text); }
.tier-tag--tier3 { background: var(--tier3-bg); color: var(--tier3-text); }

.status-badge {
  font-size: 11px;
  font-weight: 500;
}
.status-badge--active { color: var(--status-success); }
.status-badge--warning { color: var(--status-warning); }
.status-badge--error { color: var(--status-error); }

.detail__metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.detail__tabs {
  display: flex;
  border-bottom: 2px solid var(--neutral-200);
  margin-bottom: 20px;
}
.detail__tab {
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
.detail__tab:hover { color: var(--neutral-800); }
.detail__tab--active { color: var(--semantic-600); border-bottom-color: var(--semantic-600); }

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
.status-dot--muted { background: var(--neutral-300); }

.placeholder-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  gap: 12px;
  color: var(--neutral-400);
}
</style>
