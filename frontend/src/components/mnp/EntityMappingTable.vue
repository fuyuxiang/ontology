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
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, i) in conditions" :key="i">
          <td>{{ item.condition }}</td>
          <td class="entity-cell">{{ item.sourceEntity }}</td>
          <td class="attr-cell">{{ item.sourceAttribute }}</td>
          <td>{{ item.operator }}</td>
          <td>{{ item.threshold }}</td>
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
}

const props = defineProps<{
  title: string
  badge?: string
  badgeType?: 'high' | 'medium' | 'low'
  conditions: MappingCondition[]
}>()

const uniqueEntities = computed(() => new Set(props.conditions.map(c => c.sourceEntity)).size)
</script>

<style scoped>
.mapping-table { background: #fff; border-radius: 10px; border: 1px solid #e9ecef; padding: 16px; }
.mapping-table__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.mapping-table__title { font-size: 14px; font-weight: 600; color: #343a40; }
.mapping-table__badge { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 4px; }
.badge--high { background: #fff5f5; color: #fa5252; }
.badge--medium { background: #fff8e1; color: #f59f00; }
.badge--low { background: #e7f5ff; color: #339af0; }
.mtable { width: 100%; border-collapse: collapse; font-size: 12px; }
.mtable th { text-align: left; padding: 8px 10px; background: #f8f9fa; color: #495057; font-weight: 600; border-bottom: 2px solid #e9ecef; }
.mtable td { padding: 8px 10px; border-bottom: 1px solid #f1f3f5; color: #495057; }
.entity-cell { color: #4c6ef5; font-weight: 500; }
.attr-cell { font-family: monospace; font-size: 11px; color: #7048e8; }
.mapping-table__footer { margin-top: 12px; padding: 10px 12px; background: #f8f9fa; border-radius: 8px; font-size: 13px; font-weight: 500; color: #343a40; }
.footer-icon { color: #4c6ef5; margin-right: 6px; }
</style>
