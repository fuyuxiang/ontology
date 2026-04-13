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
import { ref, computed, onMounted, watch } from 'vue'
import EntityCard, { type Entity } from '../../components/common/EntityCard.vue'
import TierBadge from '../../components/common/TierBadge.vue'
import { useOntologyStore } from '../../store/ontology'

const store = useOntologyStore()

const searchQuery = ref('')
const selectedId = ref<string | null>(null)
const activeTab = ref('属性')
const tabs = ['属性', '关系', '规则', '动作', '血缘']

onMounted(() => {
  store.fetchEntities()
})

// 将 store 数据映射为 EntityCard 需要的格式
const allEntities = computed<Entity[]>(() =>
  store.entities.map(e => ({
    id: e.id,
    name: e.name,
    nameCn: e.name_cn,
    tier: e.tier as 1 | 2 | 3,
    attrs: e.attr_count,
    relations: e.relation_count,
    rules: e.rule_count,
    status: e.status as 'active' | 'warning' | 'error',
  }))
)

const groups = computed(() => [
  { tier: 1 as const, label: 'Tier 1 核心对象', entities: allEntities.value.filter(e => e.tier === 1) },
  { tier: 2 as const, label: 'Tier 2 领域对象', entities: allEntities.value.filter(e => e.tier === 2) },
  { tier: 3 as const, label: 'Tier 3 场景对象', entities: allEntities.value.filter(e => e.tier === 3) },
])

const filteredGroups = computed(() => {
  if (!searchQuery.value) return groups.value
  const q = searchQuery.value.toLowerCase()
  return groups.value.map(g => ({
    ...g,
    entities: g.entities.filter(e =>
      e.name.toLowerCase().includes(q) || e.nameCn.includes(q)
    )
  })).filter(g => g.entities.length > 0)
})

const totalEntities = computed(() => allEntities.value.length)
const selected = computed(() => allEntities.value.find(e => e.id === selectedId.value) ?? null)

// 选中实体时从 API 加载详情
watch(selectedId, async (id) => {
  if (id) {
    await store.fetchEntity(id)
  }
})

const detail = computed(() => store.currentEntity)

const metrics = computed(() => {
  if (!detail.value) {
    return selected.value ? [
      { label: '属性', value: selected.value.attrs },
      { label: '关系', value: selected.value.relations },
      { label: '规则', value: selected.value.rules },
      { label: '动作', value: 0 },
    ] : []
  }
  return [
    { label: '属性', value: detail.value.attributes.length },
    { label: '关系', value: detail.value.relations.length },
    { label: '规则', value: detail.value.rules.length },
    { label: '动作', value: detail.value.actions.length },
  ]
})

const tierLabel = (t: number) => ({ 1: '核心对象', 2: '领域对象', 3: '场景对象' }[t] ?? '')

function selectEntity(entity: Entity) {
  selectedId.value = entity.id
  activeTab.value = '属性'
}

// 属性、关系、规则、动作全部从详情 API 获取
const selectedAttrs = computed(() =>
  detail.value?.attributes.map(a => ({
    name: a.name, type: a.type, desc: a.description, required: a.required,
  })) ?? []
)

const selectedRelations = computed(() =>
  detail.value?.relations.map(r => ({
    name: r.name,
    type: r.rel_type,
    target: r.to_entity_name || r.from_entity_name,
    targetTier: (r.to_entity_tier || 1) as 1 | 2 | 3,
  })) ?? []
)

const selectedRules = computed(() =>
  detail.value?.rules.map(r => ({
    id: r.id, name: r.name,
    condition: r.condition_expr, action: r.action_desc,
    status: r.status,
  })) ?? []
)

const selectedActions = computed(() =>
  detail.value?.actions.map(a => ({
    id: a.id, name: a.name, type: a.type, status: a.status,
  })) ?? []
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
