<template>
  <div class="glass-panel stats-panel">
    <div class="stats-panel__title">SYSTEM OVERVIEW</div>
    <div class="stats-grid">
      <div v-for="item in metrics" :key="item.label" class="stat-card">
        <div class="stat-card__val">{{ item.value }}</div>
        <div class="stat-card__lbl">{{ item.label }}</div>
        <svg class="stat-card__spark" viewBox="0 0 60 20" preserveAspectRatio="none">
          <polyline :points="item.spark" fill="none" :stroke="item.color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity=".6"/>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DashboardStatsEx } from '../../../api/dashboard'

const props = defineProps<{ stats: DashboardStatsEx | null }>()

function fakeSpark(val: number, color: string) {
  const pts: string[] = []
  let y = 14
  for (let i = 0; i < 8; i++) {
    y = Math.max(2, Math.min(18, y + (Math.random() - 0.45) * 6))
    pts.push(`${i * 8.5},${y}`)
  }
  return { spark: pts.join(' '), color }
}

const metrics = computed(() => {
  const s = props.stats
  return [
    { label: '实体', value: s?.entity_count ?? 0, ...fakeSpark(s?.entity_count ?? 0, '#5C7CFA') },
    { label: '关系', value: s?.relation_count ?? 0, ...fakeSpark(s?.relation_count ?? 0, '#20C997') },
    { label: '规则', value: s?.rule_count ?? 0, ...fakeSpark(s?.rule_count ?? 0, '#F59F00') },
    { label: '数据源', value: s?.datasource_count ?? 0, ...fakeSpark(s?.datasource_count ?? 0, '#FA5252') },
  ]
})
</script>

<style scoped>
.glass-panel {
  position: absolute;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  color: var(--neutral-300);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  padding: 14px;
  pointer-events: auto;
  z-index: 10;
}
.stats-panel {
  top: 16px;
  left: 16px;
  width: 220px;
}
.stats-panel__title {
  font-size: var(--text-caption-upper-size);
  font-weight: 800;
  letter-spacing: .12em;
  color: var(--neutral-700);
  margin-bottom: 10px;
}
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.stat-card {
  position: relative;
  padding: 10px;
  background: rgba(30,41,59,.5);
  border-radius: 8px;
  border: 1px solid rgba(148,163,184,.06);
  overflow: hidden;
}
.stat-card__val {
  font-size: var(--text-h2-size);
  font-weight: 800;
  color: var(--neutral-300);
  line-height: 1;
}
.stat-card__lbl {
  font-size: var(--text-caption-upper-size);
  color: var(--neutral-500);
  margin-top: 2px;
}
.stat-card__spark {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 60px;
  height: 20px;
  opacity: .5;
}
</style>
