<template>
  <div
    class="entity-card"
    :class="[`entity-card--tier${entity.tier}`, { 'entity-card--selected': selected }]"
    @click="$emit('click', entity)"
  >
    <TierBadge :tier="entity.tier" />
    <div class="entity-card__body">
      <div class="entity-card__header">
        <span class="entity-card__name">{{ entity.nameCn }}</span>
      </div>
      <div class="entity-card__meta">
        <span>属性: {{ entity.attrs }}</span>
        <span>关系: {{ entity.relations }}</span>
        <span>规则: {{ entity.rules }}</span>
        <span v-if="entity.datasource" class="entity-card__ds" title="已关联数据源">
          <svg width="10" height="10" viewBox="0 0 12 12" fill="none"><path d="M2 3.5A1.5 1.5 0 013.5 2h5A1.5 1.5 0 0110 3.5v0A1.5 1.5 0 018.5 5h-5A1.5 1.5 0 012 3.5zm0 5A1.5 1.5 0 013.5 7h5A1.5 1.5 0 0110 8.5v0A1.5 1.5 0 018.5 10h-5A1.5 1.5 0 012 8.5z" stroke="currentColor" stroke-width="1"/></svg>
          {{ entity.datasource }}
        </span>
      </div>
    </div>
    <div class="entity-card__status" :class="`status--${entity.status}`"></div>
  </div>
</template>

<script setup lang="ts">
import TierBadge from './TierBadge.vue'

export interface Entity {
  id: string
  name: string
  nameCn: string
  tier: 1 | 2 | 3
  attrs: number
  relations: number
  rules: number
  status: 'active' | 'warning' | 'error'
  datasource?: string | null
}

defineProps<{ entity: Entity; selected?: boolean }>()
defineEmits<{ click: [entity: Entity] }>()
</script>

<style scoped>
.entity-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--neutral-200);
  background: var(--neutral-0);
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
}
.entity-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.entity-card--tier1:hover { background: var(--tier1-bg); border-color: var(--tier1-primary); }
.entity-card--tier2:hover { background: var(--tier2-bg); border-color: var(--tier2-primary); }
.entity-card--tier3:hover { background: var(--tier3-bg); border-color: var(--tier3-primary); }

.entity-card--selected.entity-card--tier1 { background: var(--tier1-bg); border-left: 2px solid var(--tier1-primary); }
.entity-card--selected.entity-card--tier2 { background: var(--tier2-bg); border-left: 2px solid var(--tier2-primary); }
.entity-card--selected.entity-card--tier3 { background: var(--tier3-bg); border-left: 2px solid var(--tier3-primary); }

.entity-card__body {
  flex: 1;
  min-width: 0;
}

.entity-card__header {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 3px;
}

.entity-card__name {
  font-size: var(--text-body-size);
  font-weight: 500;
  color: var(--neutral-800);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entity-card__name-cn {
  font-size: var(--text-caption-size);
  color: var(--neutral-500);
  white-space: nowrap;
}

.entity-card__meta {
  display: flex;
  gap: 8px;
  font-size: var(--text-caption-size);
  color: var(--neutral-600);
}

.entity-card__status {
  width: 7px;
  height: 7px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}
.status--active { background: var(--status-success); }
.status--warning { background: var(--status-warning); }
.status--error { background: var(--status-error); }

.entity-card__ds {
  display: inline-flex; align-items: center; gap: 2px;
  color: var(--status-info); font-size: var(--text-caption-upper-size); font-weight: 500;
  max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
</style>
