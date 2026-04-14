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

      <!-- 关系 -->
      <template v-else-if="activeTab === '关系'">
        <div class="relation-list">
          <div class="relation-item" v-for="rel in relations" :key="rel.name">
            <span class="relation-item__from">{{ entity.name }}</span>
            <span class="relation-item__arrow">
              <span class="relation-item__type">{{ rel.type }}</span>
              →
            </span>
            <span class="relation-item__to">{{ rel.target }}</span>
            <span class="relation-item__card">{{ rel.cardinality }}</span>
          </div>
        </div>
      </template>

      <!-- 规则 -->
      <template v-else-if="activeTab === '规则'">
        <table class="data-table">
          <thead>
            <tr><th>规则ID</th><th>规则名称</th><th>触发条件</th><th>执行动作</th><th>状态</th></tr>
          </thead>
          <tbody>
            <tr v-for="rule in rules" :key="rule.id">
              <td><code class="text-code">{{ rule.id }}</code></td>
              <td class="text-body-medium">{{ rule.name }}</td>
              <td><code class="text-code">{{ rule.condition }}</code></td>
              <td class="text-body">{{ rule.action }}</td>
              <td><span class="status-dot" :class="rule.status === 'active' ? 'status-dot--success' : 'status-dot--warning'"></span></td>
            </tr>
          </tbody>
        </table>
      </template>

      <!-- 动作 -->
      <template v-else-if="activeTab === '动作'">
        <div class="action-list">
          <div class="action-item" v-for="act in actions" :key="act.id">
            <div class="action-item__info">
              <span class="action-item__name text-body-medium">{{ act.name }}</span>
              <span class="action-item__type text-caption">{{ act.type }}</span>
            </div>
            <span class="action-status" :class="`action-status--${act.status}`">{{ act.status }}</span>
            <button class="action-exec-btn">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 1.5l7 4.5-7 4.5V1.5z" fill="currentColor"/></svg>
              执行
            </button>
          </div>
        </div>
      </template>

      <!-- 血缘 -->
      <template v-else-if="activeTab === '血缘'">
        <EntityLineageGraph :entity-id="entityId" />
      </template>

      <!-- 其他占位 -->
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import OntologyBreadcrumb from '../../components/common/OntologyBreadcrumb.vue'
import MetricCard from '../../components/common/MetricCard.vue'
import EntityLineageGraph from '../../components/canvas/EntityLineageGraph.vue'
import { useOntologyStore } from '../../store/ontology'

const route = useRoute()
const store = useOntologyStore()
const activeTab = ref('属性')
const tabs = ['属性', '关系', '规则', '动作', '血缘']

const entityId = computed(() => route.params.id as string)

onMounted(() => { store.fetchEntity(entityId.value) })
watch(entityId, (id) => { if (id) store.fetchEntity(id) })

const detail = computed(() => store.currentEntity)

const entity = computed(() => detail.value ? {
  id: detail.value.id,
  name: detail.value.name,
  nameCn: detail.value.name_cn,
  tier: detail.value.tier as 1 | 2 | 3,
  attrs: detail.value.attributes.length,
  relations: detail.value.relations.length,
  rules: detail.value.rules.length,
  actions: detail.value.actions.length,
  status: detail.value.status as 'active' | 'warning' | 'error',
} : { id: '', name: '加载中...', nameCn: '', tier: 1 as const, attrs: 0, relations: 0, rules: 0, actions: 0, status: 'active' as const })

const tierLabel = computed(() => ({ 1: '核心对象', 2: '领域对象', 3: '场景对象' }[entity.value.tier]))
const statusLabel = computed(() => ({ active: '活跃', warning: '警告', error: '异常' }[entity.value.status]))

const breadcrumbs = computed(() => [
  { label: '本体管理', path: '/ontology' },
  { label: '对象类型', path: '/ontology' },
  { label: `Tier ${entity.value.tier} ${tierLabel.value}`, tier: entity.value.tier },
  { label: entity.value.name },
])

const metrics = computed(() => [
  { label: '属性', value: entity.value.attrs, trend: 0 },
  { label: '关系', value: entity.value.relations, trend: 0 },
  { label: '规则', value: entity.value.rules, trend: 0 },
  { label: '动作', value: entity.value.actions, trend: 0 },
])

const attrs = computed(() =>
  detail.value?.attributes.map(a => ({
    name: a.name, type: a.type, desc: a.description, required: a.required, example: a.example || '',
  })) ?? []
)

const relations = computed(() =>
  detail.value?.relations.map(r => ({
    name: r.name, type: r.rel_type,
    target: r.to_entity_name || r.from_entity_name,
    cardinality: r.cardinality,
  })) ?? []
)

const rules = computed(() =>
  detail.value?.rules.map(r => ({
    id: r.id, name: r.name,
    condition: r.condition_expr, action: r.action_desc, status: r.status,
  })) ?? []
)

const actions = computed(() =>
  detail.value?.actions.map(a => ({
    id: a.id, name: a.name, type: a.type, status: a.status,
  })) ?? []
)
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
.status-dot--warning { background: var(--status-warning); }
.status-dot--muted { background: var(--neutral-300); }

/* 关系列表 */
.relation-list { display: flex; flex-direction: column; gap: 8px; }
.relation-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 16px; background: var(--neutral-0);
  border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
}
.relation-item__from, .relation-item__to { font-size: 13px; font-weight: 500; color: var(--neutral-800); }
.relation-item__arrow { font-size: 11px; color: var(--neutral-400); display: flex; flex-direction: column; align-items: center; }
.relation-item__type { font-size: 10px; font-weight: 600; text-transform: uppercase; color: var(--neutral-500); }
.relation-item__card { font-size: 10px; font-weight: 500; color: var(--neutral-500); background: var(--neutral-50); padding: 1px 6px; border-radius: 3px; margin-left: auto; }

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
  font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: var(--radius-full);
}
.action-status--active { background: var(--status-success-bg); color: var(--status-success); }
.action-status--warning { background: var(--status-warning-bg); color: var(--status-warning); }
.action-exec-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 5px 12px; border-radius: var(--radius-md); border: none;
  background: var(--kinetic-500); color: #fff; font-size: 12px;
  font-weight: 500; cursor: pointer; transition: background var(--transition-fast);
}
.action-exec-btn:hover { background: var(--kinetic-600); }

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
