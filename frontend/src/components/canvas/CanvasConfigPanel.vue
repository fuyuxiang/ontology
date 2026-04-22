<template>
  <aside class="config-panel">
    <template v-if="node">
      <div class="config-panel__hero">
        <div class="config-panel__badge" :style="{ background: tierColors[node.tier] }">T{{ node.tier }}</div>
        <div class="config-panel__title-block">
          <p class="config-panel__eyebrow">当前选中对象</p>
          <h2 class="config-panel__title">{{ node.nameCn }}</h2>
          <p class="config-panel__subtitle">{{ node.name }}</p>
        </div>
      </div>

      <div class="config-panel__chips">
        <span class="config-chip" :class="`config-chip--tier${node.tier}`">Tier {{ node.tier }} {{ tierLabels[node.tier] }}</span>
        <span class="config-chip" :class="`config-chip--${node.status}`">{{ statusLabels[node.status] || node.status }}</span>
        <span v-if="node.datasource" class="config-chip config-chip--neutral">{{ node.datasource }}</span>
      </div>

      <div class="config-metrics">
        <div class="config-metric">
          <span class="config-metric__value">{{ node.relCount }}</span>
          <span class="config-metric__label">关系总数</span>
        </div>
        <div class="config-metric">
          <span class="config-metric__value">{{ node.attrCount }}</span>
          <span class="config-metric__label">属性数</span>
        </div>
        <div class="config-metric">
          <span class="config-metric__value">{{ node.ruleCount }}</span>
          <span class="config-metric__label">规则数</span>
        </div>
        <div class="config-metric">
          <span class="config-metric__value">{{ inEdges.length + outEdges.length }}</span>
          <span class="config-metric__label">可视链路</span>
        </div>
      </div>

      <div class="config-section">
        <div class="config-section__head">
          <span class="config-section__title">图谱摘要</span>
        </div>
        <div class="config-kv">
          <span class="config-kv__label">对象名称</span>
          <span class="config-kv__value">{{ node.nameCn }}</span>
        </div>
        <div class="config-kv">
          <span class="config-kv__label">英文标识</span>
          <span class="config-kv__value config-kv__value--mono">{{ node.name }}</span>
        </div>
        <div class="config-kv">
          <span class="config-kv__label">对象层级</span>
          <span class="config-kv__value">Tier {{ node.tier }} {{ tierLabels[node.tier] }}</span>
        </div>
      </div>

      <div class="config-section" v-if="inEdges.length">
        <div class="config-section__head">
          <span class="config-section__title">上游输入</span>
          <span class="config-section__count">{{ inEdges.length }}</span>
        </div>
        <div class="config-link-list">
          <div class="config-link" v-for="edge in inEdges" :key="edge.id">
            <span class="config-link__tier" :class="`config-link__tier--tier${edge.sourceTier}`">T{{ edge.sourceTier }}</span>
            <div class="config-link__body">
              <span class="config-link__entity">{{ edge.sourceName }}</span>
              <span class="config-link__meta">{{ edge.label }} · {{ edge.cardinality }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="config-section" v-if="outEdges.length">
        <div class="config-section__head">
          <span class="config-section__title">下游输出</span>
          <span class="config-section__count">{{ outEdges.length }}</span>
        </div>
        <div class="config-link-list">
          <div class="config-link" v-for="edge in outEdges" :key="edge.id">
            <span class="config-link__tier" :class="`config-link__tier--tier${edge.targetTier}`">T{{ edge.targetTier }}</span>
            <div class="config-link__body">
              <span class="config-link__entity">{{ edge.targetName }}</span>
              <span class="config-link__meta">{{ edge.label }} · {{ edge.cardinality }}</span>
            </div>
          </div>
        </div>
      </div>

      <button class="config-detail-btn" @click="$emit('detail', node.id)">查看完整对象详情</button>
    </template>

    <template v-else>
      <div class="config-empty">
        <div class="config-empty__icon">
          <svg width="42" height="42" viewBox="0 0 42 42" fill="none">
            <circle cx="21" cy="12" r="5" stroke="currentColor" stroke-width="1.6"/>
            <circle cx="11" cy="30" r="5" stroke="currentColor" stroke-width="1.6"/>
            <circle cx="31" cy="30" r="5" stroke="currentColor" stroke-width="1.6"/>
            <path d="M21 17v4M21 21l-10 3M21 21l10 3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
        </div>
        <p class="config-empty__title">选择节点查看详情</p>
        <p class="config-empty__desc">
          当前图谱共有 {{ visibleNodeCount }} 个可视对象、{{ totalEdgeCount }} 条关系。点击左侧清单或中间画布中的任意对象查看连接结构。
        </p>
        <div class="config-empty__legend">
          <span class="config-chip config-chip--tier1">T1 核心对象</span>
          <span class="config-chip config-chip--tier2">T2 领域对象</span>
          <span class="config-chip config-chip--tier3">T3 场景对象</span>
        </div>
        <div class="config-empty__stats">
          <div class="config-empty__stat">
            <strong>{{ visibleNodeCount }}</strong>
            <span>当前对象</span>
          </div>
          <div class="config-empty__stat">
            <strong>{{ totalNodeCount }}</strong>
            <span>全量对象</span>
          </div>
        </div>
      </div>
    </template>
  </aside>
</template>

<script setup lang="ts">
interface NodeData {
  id: string
  name: string
  nameCn: string
  tier: 1 | 2 | 3
  status: string
  relCount: number
  attrCount: number
  ruleCount: number
  datasource?: string | null
}

interface EdgeInfo {
  id: string
  sourceName: string
  sourceTier: 1 | 2 | 3
  targetName: string
  targetTier: 1 | 2 | 3
  label: string
  cardinality: string
}

defineProps<{
  node: NodeData | null
  inEdges: EdgeInfo[]
  outEdges: EdgeInfo[]
  visibleNodeCount: number
  totalNodeCount: number
  totalEdgeCount: number
}>()

defineEmits<{ detail: [id: string] }>()

const tierColors: Record<number, string> = { 1: '#4c6ef5', 2: '#7950f2', 3: '#20c997' }
const tierLabels: Record<number, string> = { 1: '核心对象', 2: '领域对象', 3: '场景对象' }
const statusLabels: Record<string, string> = { active: '健康', warning: '预警', error: '异常' }
</script>

<style scoped>
.config-panel {
  min-width: 0;
  padding: 18px 18px 20px;
  border-left: 1px solid rgba(208, 217, 229, 0.74);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.82) 100%);
  backdrop-filter: blur(12px);
  overflow-y: auto;
}

.config-panel__hero {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.config-panel__badge {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: var(--text-body-size);
  font-weight: 700;
  box-shadow: 0 10px 24px -18px rgba(23, 32, 51, 0.45);
}

.config-panel__eyebrow {
  margin: 0 0 4px;
  font-size: var(--text-caption-upper-size);
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--neutral-500);
}

.config-panel__title {
  margin: 0;
  font-size: 24px;
  line-height: 1.1;
  color: #172033;
}

.config-panel__subtitle {
  margin: 5px 0 0;
  font-size: var(--text-code-size);
  color: var(--neutral-600);
}

.config-panel__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.config-chip {
  display: inline-flex;
  align-items: center;
  padding: 7px 10px;
  border-radius: 999px;
  font-size: var(--text-caption-size);
  font-weight: 700;
}

.config-chip--tier1 {
  background: var(--tier1-bg);
  color: var(--tier1-text);
}

.config-chip--tier2 {
  background: var(--tier2-bg);
  color: var(--tier2-text);
}

.config-chip--tier3 {
  background: var(--tier3-bg);
  color: var(--tier3-text);
}

.config-chip--active {
  background: var(--status-success-bg);
  color: var(--dynamic-900);
}

.config-chip--warning {
  background: var(--status-warning-bg);
  color: var(--kinetic-700);
}

.config-chip--error {
  background: var(--status-error-bg);
  color: var(--kinetic-900);
}

.config-chip--neutral {
  background: rgba(241, 245, 249, 0.94);
  color: var(--neutral-700);
}

.config-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 18px;
}

.config-metric {
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(225, 231, 239, 0.92);
}

.config-metric__value {
  display: block;
  font-size: 24px;
  line-height: 1;
  font-weight: 700;
  color: #172033;
}

.config-metric__label {
  display: block;
  margin-top: 6px;
  font-size: var(--text-caption-size);
  color: var(--neutral-500);
}

.config-section {
  margin-bottom: 16px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(227, 232, 241, 0.92);
}

.config-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.config-section__title {
  font-size: var(--text-caption-upper-size);
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--neutral-600);
}

.config-section__count {
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.9);
  color: var(--neutral-600);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-caption-size);
  font-weight: 700;
}

.config-kv {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 9px 0;
  border-bottom: 1px solid rgba(236, 240, 245, 0.96);
}

.config-kv:last-child {
  border-bottom: none;
}

.config-kv__label {
  color: var(--neutral-500);
  font-size: var(--text-code-size);
}

.config-kv__value {
  text-align: right;
  color: #172033;
  font-size: var(--text-code-size);
  font-weight: 600;
}

.config-kv__value--mono {
  font-family: var(--font-mono);
}

.config-link-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.92);
  border: 1px solid rgba(233, 237, 243, 0.94);
}

.config-link__tier {
  min-width: 34px;
  height: 28px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-caption-size);
  font-weight: 700;
}

.config-link__tier--tier1 {
  background: var(--tier1-bg);
  color: var(--tier1-text);
}

.config-link__tier--tier2 {
  background: var(--tier2-bg);
  color: var(--tier2-text);
}

.config-link__tier--tier3 {
  background: var(--tier3-bg);
  color: var(--tier3-text);
}

.config-link__body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.config-link__entity {
  font-size: var(--text-body-size);
  font-weight: 600;
  color: #172033;
}

.config-link__meta {
  font-size: var(--text-caption-size);
  color: var(--neutral-500);
}

.config-detail-btn {
  width: 100%;
  margin-top: 4px;
  padding: 12px 14px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #4c6ef5 0%, #4263eb 100%);
  color: #fff;
  font-size: var(--text-body-size);
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 14px 28px -18px rgba(66, 99, 235, 0.6);
}

.config-empty {
  height: 100%;
  min-height: 460px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 14px;
  color: var(--neutral-500);
}

.config-empty__icon {
  width: 84px;
  height: 84px;
  border-radius: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(220, 227, 237, 0.96);
  background: rgba(255, 255, 255, 0.94);
  color: rgba(134, 142, 150, 0.86);
  box-shadow: var(--shadow-sm);
}

.config-empty__title {
  font-size: var(--text-h2-size);
  font-weight: 700;
  color: #172033;
}

.config-empty__desc {
  max-width: 270px;
  line-height: 1.75;
}

.config-empty__legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.config-empty__stats {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

.config-empty__stat {
  min-width: 92px;
  padding: 12px 10px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(227, 232, 241, 0.92);
}

.config-empty__stat strong {
  display: block;
  font-size: 22px;
  line-height: 1;
  color: #172033;
}

.config-empty__stat span {
  display: block;
  margin-top: 6px;
  font-size: var(--text-caption-size);
}
</style>
