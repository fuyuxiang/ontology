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
            <span v-if="dsInfo" class="ds-link-tag" :title="`数据源: ${dsInfo.datasource_name} · 表: ${dsInfo.table_name}`">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 3.5A1.5 1.5 0 013.5 2h5A1.5 1.5 0 0110 3.5v0A1.5 1.5 0 018.5 5h-5A1.5 1.5 0 012 3.5zm0 5A1.5 1.5 0 013.5 7h5A1.5 1.5 0 0110 8.5v0A1.5 1.5 0 018.5 10h-5A1.5 1.5 0 012 8.5z" stroke="currentColor" stroke-width="1"/></svg>
              {{ dsInfo.datasource_name }} · {{ dsInfo.table_name }}
            </span>
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

      <!-- 数据实例 -->
      <template v-else-if="activeTab === '数据实例'">
        <div v-if="instanceLoading" class="instance-loading">
          <svg class="spin" width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="8" stroke="var(--neutral-300)" stroke-width="2"/><path d="M10 2a8 8 0 018 8" stroke="var(--semantic-500)" stroke-width="2" stroke-linecap="round"/></svg>
          <span class="text-caption">加载数据实例...</span>
        </div>
        <div v-else-if="!instancePreview || !instancePreview.table_name" class="placeholder-tab">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <rect x="8" y="8" width="24" height="24" rx="4" stroke="var(--neutral-300)" stroke-width="2"/>
            <path d="M14 20h12M14 15h8M14 25h6" stroke="var(--neutral-300)" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <p class="text-caption">该实体尚未映射数据源，请先在「本体映射」中配置字段映射</p>
        </div>
        <template v-else>
          <!-- 数据源信息头 -->
          <div class="instance-header">
            <div class="instance-source-info">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 4A2 2 0 014 2h6a2 2 0 012 2v0a2 2 0 01-2 2H4a2 2 0 01-2-2zm0 6a2 2 0 012-2h6a2 2 0 012 2v0a2 2 0 01-2 2H4a2 2 0 01-2-2z" stroke="var(--status-info)" stroke-width="1.2"/></svg>
              <span class="instance-source-label">数据源</span>
              <code class="instance-source-name">{{ instancePreview.datasource_name }}</code>
              <span class="instance-source-sep">·</span>
              <span class="instance-source-label">表</span>
              <code class="instance-source-name">{{ instancePreview.table_name }}</code>
              <span class="instance-total">共 {{ instancePreview.total_rows }} 条记录</span>
            </div>
            <!-- 字段覆盖率 -->
            <div class="instance-coverage" v-if="instanceFields.length">
              <span class="instance-coverage-label">字段映射覆盖率</span>
              <div class="instance-coverage-bar">
                <div class="instance-coverage-fill" :style="{ width: coveragePct + '%' }"></div>
              </div>
              <span class="instance-coverage-pct">{{ coveragePct }}%</span>
            </div>
          </div>

          <!-- 数据表格 -->
          <div class="instance-table-wrap">
            <table class="data-table instance-table">
              <thead>
                <tr>
                  <th v-for="col in instancePreview.columns" :key="col">
                    <div class="instance-col-head">
                      <span class="instance-col-field">{{ col }}</span>
                      <span v-if="fieldAttrMap[col]" class="instance-col-attr">{{ fieldAttrMap[col] }}</span>
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in instancePreview.rows" :key="i">
                  <td v-for="(col, ci) in instancePreview.columns" :key="col">
                    <span class="instance-cell">{{ row[ci] ?? '—' }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 分页 -->
          <div class="instance-pagination" v-if="instancePreview.total_rows > instancePreview.page_size">
            <button class="page-btn" :disabled="instancePage === 1" @click="instancePage--">‹ 上一页</button>
            <span class="page-info">第 {{ instancePage }} 页 / 共 {{ Math.ceil(instancePreview.total_rows / instancePreview.page_size) }} 页</span>
            <button class="page-btn" :disabled="instancePage >= Math.ceil(instancePreview.total_rows / instancePreview.page_size)" @click="instancePage++">下一页 ›</button>
          </div>
        </template>
      </template>

      <!-- 智能体 -->
      <template v-else-if="activeTab === '智能体'">
        <div v-if="agentLoading" class="instance-loading">
          <svg class="spin" width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="8" stroke="var(--neutral-300)" stroke-width="2"/><path d="M10 2a8 8 0 018 8" stroke="var(--semantic-500)" stroke-width="2" stroke-linecap="round"/></svg>
          <span class="text-caption">加载智能体...</span>
        </div>
        <div v-else-if="linkedAgents.length === 0" class="placeholder-tab">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <path d="M20 8L34 16v8L20 32 6 24v-8L20 8z" stroke="var(--neutral-300)" stroke-width="2" stroke-linejoin="round"/>
            <path d="M20 16v8M14 19l6 3 6-3" stroke="var(--neutral-300)" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <p class="text-caption">暂无智能体引用该本体对象</p>
        </div>
        <div v-else class="agent-chain-list">
          <div v-for="agent in linkedAgents" :key="agent.id" class="agent-chain-card">
            <!-- 链路头 -->
            <div class="agent-chain-header">
              <div class="agent-chain-icon">{{ agent.name.charAt(0) }}</div>
              <div class="agent-chain-meta">
                <span class="agent-chain-name">{{ agent.name }}</span>
                <span class="agent-chain-desc">{{ agent.description }}</span>
              </div>
              <span class="agent-chain-status" :class="agent.status === 'published' ? 'agent-chain-status--pub' : 'agent-chain-status--draft'">
                {{ agent.status === 'published' ? '已发布' : '草稿' }}
              </span>
            </div>
            <!-- 链路可视化: 本体 → 智能体 → 结论 -->
            <div class="agent-chain-flow">
              <div class="agent-chain-step agent-chain-step--ont">
                <span class="agent-chain-step-icon">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                </span>
                <span>{{ entity.nameCn }}</span>
              </div>
              <svg class="agent-chain-arrow" width="24" height="12" viewBox="0 0 24 12"><path d="M0 6h20M16 2l4 4-4 4" stroke="var(--neutral-300)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <div class="agent-chain-step agent-chain-step--agent">
                <span class="agent-chain-step-icon">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 4v4l-6 4-6-4V6l6-4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
                </span>
                <span>{{ agent.name }}</span>
              </div>
              <svg class="agent-chain-arrow" width="24" height="12" viewBox="0 0 24 12"><path d="M0 6h20M16 2l4 4-4 4" stroke="var(--neutral-300)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <div class="agent-chain-step agent-chain-step--result">
                <span class="agent-chain-step-icon">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3 8l4 4 6-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </span>
                <span>{{ agent.conclusionLabel }}</span>
              </div>
            </div>
            <!-- 节点列表 -->
            <div class="agent-chain-nodes" v-if="agent.nodes.length">
              <span v-for="n in agent.nodes" :key="n.id" class="agent-chain-node-tag" :style="{ borderColor: n.color + '60', color: n.color, background: n.color + '12' }">{{ n.label }}</span>
            </div>
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
import { useRoute, useRouter } from 'vue-router'
import OntologyBreadcrumb from '../../components/common/OntologyBreadcrumb.vue'
import MetricCard from '../../components/common/MetricCard.vue'
import EntityLineageGraph from '../../components/canvas/EntityLineageGraph.vue'
import { useOntologyStore } from '../../store/ontology'
import { resolutionApi } from '../../api/resolution'
import { get } from '../../api/client'
import type { SourceDataPreview, SourceField } from '../../api/resolution'

const route = useRoute()
const router = useRouter()
const store = useOntologyStore()
const activeTab = ref('属性')
const tabs = ['属性', '关系', '规则', '动作', '数据实例', '智能体', '血缘']

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

const dsInfo = computed(() => {
  const sj = detail.value?.schema_json
  if (!sj || !sj.datasource_id) return null
  return { datasource_id: sj.datasource_id, datasource_name: sj.datasource_name || '未知', table_name: sj.table_name || '' }
})

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

// 数据实例
const instancePreview = ref<SourceDataPreview | null>(null)
const instanceFields = ref<SourceField[]>([])
const instanceLoading = ref(false)
const instancePage = ref(1)

async function loadInstances() {
  if (!entityId.value) return
  instanceLoading.value = true
  try {
    const [preview, fields] = await Promise.all([
      resolutionApi.preview(entityId.value, { page: instancePage.value }),
      resolutionApi.getFields(entityId.value),
    ])
    instancePreview.value = preview
    instanceFields.value = fields
  } catch {
    instancePreview.value = null
  } finally {
    instanceLoading.value = false
  }
}

watch(instancePage, () => { if (activeTab.value === '数据实例') loadInstances() })

const fieldAttrMap = computed(() => {
  const map: Record<string, string> = {}
  for (const f of instanceFields.value) {
    if (f.source_field && f.attribute_name) map[f.source_field] = f.attribute_name
  }
  return map
})

const coveragePct = computed(() => {
  if (!instanceFields.value.length) return 0
  const mapped = instanceFields.value.filter(f => f.source_field).length
  return Math.round((mapped / instanceFields.value.length) * 100)
})

// 智能体链路
const linkedAgents = ref<any[]>([])
const agentLoading = ref(false)

const nodeColorMap: Record<string, string> = {
  'ontology-query': '#3b82f6', 'ontology-relation': '#6366f1', 'rule-evaluate': '#f59e0b',
  'datasource': '#8b5cf6', 'llm-inference': '#10b981', 'ml-model': '#06b6d4',
  'voice-audit': '#7c3aed', 'condition': '#a855f7', 'merge': '#0ea5e9',
  'rule-engine': '#f59e0b', 'notification': '#ef4444', 'human-approval': '#f97316',
  'write-back': '#64748b', 'api-response': '#22c55e',
}

async function loadAgents() {
  agentLoading.value = true
  try {
    const all = await get<any[]>('/agents')
    const entityName = entity.value.name
    linkedAgents.value = all
      .filter(a => {
        const ids: string[] = a.entity_ids || []
        const nodes: any[] = a.nodes_json || []
        return ids.includes(entityId.value) || nodes.some((n: any) => n.data?.ontology_type === entityName)
      })
      .map(a => {
        const nodes = (a.nodes_json || []).map((n: any) => ({
          id: n.id,
          label: n.data?.label || n.type,
          color: nodeColorMap[n.type] || '#94a3b8',
        }))
        const lastNode = nodes[nodes.length - 1]
        const conclusionLabel = lastNode?.label || '输出结论'
        return { id: a.id, name: a.name, description: a.description || '', status: a.status, nodes, conclusionLabel }
      })
  } catch {
    linkedAgents.value = []
  } finally {
    agentLoading.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === '数据实例') loadInstances()
  if (tab === '智能体') loadAgents()
})
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
  font-size: var(--text-h2-size);
  font-weight: 700;
  color: var(--neutral-0);
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
  font-size: var(--text-body-size);
  color: var(--neutral-600);
}
.tier-tag {
  font-size: var(--text-caption-size);
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}
.tier-tag--tier1 { background: var(--tier1-bg); color: var(--tier1-text); }
.tier-tag--tier2 { background: var(--tier2-bg); color: var(--tier2-text); }
.tier-tag--tier3 { background: var(--tier3-bg); color: var(--tier3-text); }

.status-badge {
  font-size: var(--text-caption-size);
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
  font-size: var(--text-body-size);
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
  font-size: var(--text-body-size);
}
.data-table th {
  text-align: left;
  padding: 8px 12px;
  font-size: var(--text-caption-size);
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
  font-size: var(--text-caption-size);
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
.relation-item__from, .relation-item__to { font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-800); }
.relation-item__arrow { font-size: var(--text-caption-size); color: var(--neutral-400); display: flex; flex-direction: column; align-items: center; }
.relation-item__type { font-size: var(--text-caption-upper-size); font-weight: 600; text-transform: uppercase; color: var(--neutral-500); }
.relation-item__card { font-size: var(--text-caption-upper-size); font-weight: 500; color: var(--neutral-500); background: var(--neutral-50); padding: 1px 6px; border-radius: 3px; margin-left: auto; }

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
.action-item__name { font-size: var(--text-body-size); }
.action-item__type { font-size: var(--text-caption-size); color: var(--neutral-500); }
.action-status {
  font-size: var(--text-caption-size); font-weight: 500; padding: 2px 8px; border-radius: var(--radius-full);
}
.action-status--active { background: var(--status-success-bg); color: var(--status-success); }
.action-status--warning { background: var(--status-warning-bg); color: var(--status-warning); }
.action-exec-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 5px 12px; border-radius: var(--radius-md); border: none;
  background: var(--kinetic-500); color: var(--neutral-0); font-size: var(--text-code-size);
  font-weight: 500; cursor: pointer; transition: background var(--transition-fast);
}
.action-exec-btn:hover { background: var(--kinetic-600); }

.ds-link-tag {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 10px; border-radius: var(--radius-full);
  background: var(--status-info-bg); color: var(--status-info); font-size: var(--text-caption-size); font-weight: 500;
}

.placeholder-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  gap: 12px;
  color: var(--neutral-400);
}

/* 数据实例 */
.instance-loading {
  display: flex; align-items: center; gap: 8px; padding: 40px 0; justify-content: center; color: var(--neutral-500);
}
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.instance-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 14px; background: var(--status-info-bg);
  border: 1px solid var(--neutral-200); border-radius: var(--radius-md);
  margin-bottom: 14px; flex-wrap: wrap; gap: 10px;
}
.instance-source-info { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.instance-source-label { font-size: var(--text-caption-size); color: var(--neutral-500); }
.instance-source-name { font-size: var(--text-caption-size); font-family: var(--font-mono); color: var(--status-info); background: var(--neutral-0); padding: 1px 6px; border-radius: 3px; }
.instance-source-sep { color: var(--neutral-300); }
.instance-total { font-size: var(--text-caption-size); color: var(--neutral-500); margin-left: 8px; }

.instance-coverage { display: flex; align-items: center; gap: 8px; }
.instance-coverage-label { font-size: var(--text-caption-size); color: var(--neutral-500); white-space: nowrap; }
.instance-coverage-bar { width: 80px; height: 6px; background: var(--neutral-200); border-radius: 3px; overflow: hidden; }
.instance-coverage-fill { height: 100%; background: var(--status-success); border-radius: 3px; transition: width 0.3s; }
.instance-coverage-pct { font-size: var(--text-caption-size); font-weight: 600; color: var(--status-success); min-width: 32px; }

.instance-table-wrap { overflow-x: auto; }
.instance-table { min-width: 600px; }
.instance-col-head { display: flex; flex-direction: column; gap: 2px; }
.instance-col-field { font-family: var(--font-mono); font-size: var(--text-caption-size); color: var(--neutral-700); }
.instance-col-attr { font-size: 10px; color: var(--semantic-500); font-weight: 500; }
.instance-cell { font-size: var(--text-caption-size); font-family: var(--font-mono); color: var(--neutral-700); }

.instance-pagination {
  display: flex; align-items: center; justify-content: center; gap: 16px;
  margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--neutral-100);
}
.page-btn {
  padding: 4px 12px; border-radius: var(--radius-md); border: 1px solid var(--neutral-200);
  background: var(--neutral-0); color: var(--neutral-700); font-size: var(--text-caption-size);
  cursor: pointer; transition: all var(--transition-fast);
}
.page-btn:hover:not(:disabled) { border-color: var(--semantic-400); color: var(--semantic-600); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: var(--text-caption-size); color: var(--neutral-500); }

.agent-chain-list { display: flex; flex-direction: column; gap: 16px; }
.agent-chain-card {
  border: 1px solid var(--neutral-200); border-radius: var(--radius-lg);
  padding: 16px; display: flex; flex-direction: column; gap: 12px;
  background: var(--neutral-0);
}
.agent-chain-header { display: flex; align-items: center; gap: 12px; }
.agent-chain-icon {
  width: 36px; height: 36px; border-radius: var(--radius-md);
  background: var(--semantic-100); color: var(--semantic-700);
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; flex-shrink: 0;
}
.agent-chain-meta { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.agent-chain-name { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.agent-chain-desc { font-size: var(--text-caption-size); color: var(--neutral-500); }
.agent-chain-status { font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: var(--radius-full); }
.agent-chain-status--pub { background: var(--status-success-bg); color: var(--status-success); }
.agent-chain-status--draft { background: var(--neutral-100); color: var(--neutral-500); }

.agent-chain-flow {
  display: flex; align-items: center; gap: 4px;
  padding: 10px 14px; background: var(--neutral-50); border-radius: var(--radius-md);
  flex-wrap: wrap;
}
.agent-chain-step {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 10px; border-radius: var(--radius-md);
  font-size: var(--text-caption-size); font-weight: 500;
}
.agent-chain-step--ont { background: #eff6ff; color: #3b82f6; }
.agent-chain-step--agent { background: #f5f3ff; color: #6366f1; }
.agent-chain-step--result { background: #f0fdf4; color: #22c55e; }
.agent-chain-step-icon { display: flex; align-items: center; }
.agent-chain-arrow { flex-shrink: 0; }

.agent-chain-nodes { display: flex; flex-wrap: wrap; gap: 6px; }
.agent-chain-node-tag {
  font-size: 11px; font-weight: 500; padding: 2px 8px;
  border-radius: var(--radius-full); border: 1px solid;
}
</style>
