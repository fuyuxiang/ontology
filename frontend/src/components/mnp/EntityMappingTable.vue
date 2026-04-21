<template>
  <div class="mapping-table">
    <div class="mapping-table__header">
      <div class="mapping-table__title">{{ title }}</div>
      <div class="mapping-table__badge" v-if="badge" :class="`badge--${badgeType}`">{{ badge }}</div>
    </div>
    <table class="mtable">
      <thead>
        <tr>
          <th>规则条件</th>
          <th>来源实体</th>
          <th>来源属性</th>
          <th>运算符</th>
          <th>阈值</th>
          <th v-if="hasActual">实际值</th>
          <th v-if="hasActual">命中</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, i) in conditions" :key="i">
          <td>{{ item.condition }}</td>
          <td class="entity-cell">{{ item.sourceEntity }}</td>
          <td class="attr-cell">{{ item.sourceAttribute }}</td>
          <td>{{ item.operator }}</td>
          <td>{{ item.threshold }}</td>
          <td v-if="hasActual" class="actual-cell">{{ item.actualValue ?? '-' }}</td>
          <td v-if="hasActual" class="match-cell">
            <span v-if="item.matched === true" class="match-icon match--yes">&#10003;</span>
            <span v-else-if="item.matched === false" class="match-icon match--no">&#10007;</span>
            <span v-else>-</span>
          </td>
        </tr>
      </tbody>
    </table>
    <div class="mapping-table__footer" v-if="conditions.length">
      <span class="footer-icon">&#9679;</span>
      {{ conditions.length }} 项规则条件，覆盖 {{ uniqueEntities }} 个本体实体
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface MappingCondition {
  condition: string
  sourceEntity: string
  sourceAttribute: string
  operator: string
  threshold: string
  actualValue?: string
  matched?: boolean
}

const props = defineProps<{
  title: string
  badge?: string
  badgeType?: 'high' | 'medium' | 'low'
  conditions: MappingCondition[]
}>()

const uniqueEntities = computed(() => new Set(props.conditions.map(c => c.sourceEntity)).size)
const hasActual = computed(() => props.conditions.some(c => c.actualValue !== undefined))
</script>

<style scoped>
.mapping-table { background: var(--neutral-0); border-radius: 10px; border: 1px solid var(--neutral-200); padding: 16px; }
.mapping-table__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.mapping-table__title { font-size: var(--text-body-size); font-weight: 600; color: var(--neutral-800); }
.mapping-table__badge { font-size: var(--text-caption-size); font-weight: 600; padding: 3px 10px; border-radius: 4px; }
.badge--high { background: var(--status-error-bg); color: var(--status-error); }
.badge--medium { background: var(--status-warning-bg); color: var(--kinetic-500); }
.badge--low { background: var(--status-info-bg); color: var(--status-info); }
.mtable { width: 100%; border-collapse: collapse; font-size: var(--text-code-size); }
.mtable th { text-align: left; padding: 8px 10px; background: var(--neutral-50); color: var(--neutral-700); font-weight: 600; border-bottom: 2px solid var(--neutral-200); }
.mtable td { padding: 8px 10px; border-bottom: 1px solid var(--neutral-100); color: var(--neutral-700); }
.entity-cell { color: var(--semantic-600); font-weight: 500; }
.attr-cell { font-family: var(--font-mono); font-size: var(--text-caption-size); color: var(--tier2-primary); }
.actual-cell { font-weight: 600; color: var(--neutral-900); }
.match-cell { text-align: center; }
.match-icon { font-size: var(--text-body-size); font-weight: 700; }
.match--yes { color: var(--status-success); }
.match--no { color: var(--status-error); }
.mapping-table__footer { margin-top: 12px; padding: 10px 12px; background: var(--neutral-50); border-radius: 8px; font-size: var(--text-body-size); font-weight: 500; color: var(--neutral-800); }
.footer-icon { color: var(--semantic-600); margin-right: 6px; }
</style>
