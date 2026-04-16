<template>
  <div class="glass-panel activity-panel">
    <div class="activity-panel__title">RECENT ACTIVITY</div>
    <div class="activity-list">
      <div v-for="a in activities" :key="a.id" class="activity-row">
        <span class="activity-dot" :class="`dot--${a.type}`"></span>
        <div class="activity-body">
          <span class="activity-target">{{ a.target_name }}</span>
          <span class="activity-meta">{{ a.user }} · {{ a.time }}</span>
        </div>
      </div>
      <div v-if="!activities.length" class="activity-empty">暂无活动</div>
    </div>

    <div v-if="healthList.length" class="health-section">
      <div class="activity-panel__title" style="margin-top:12px">HEALTH STATUS</div>
      <div v-for="h in healthList" :key="h.id" class="health-row">
        <span class="health-dot" :class="`dot--${h.status}`"></span>
        <span class="health-name">{{ h.name_cn || h.name }}</span>
        <span class="health-tier">T{{ h.tier }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DashboardStatsEx } from '../../../api/dashboard'

const props = defineProps<{ stats: DashboardStatsEx | null }>()

const activities = computed(() => (props.stats?.recent_activities ?? []).slice(0, 8))
const healthList = computed(() => (props.stats?.health_status ?? []).slice(0, 6))
</script>

<style scoped>
.glass-panel {
  position: absolute;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  color: #E2E8F0;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  padding: 14px;
  pointer-events: auto;
  z-index: 10;
}
.activity-panel {
  bottom: 16px;
  right: 16px;
  width: 240px;
  max-height: 380px;
  overflow-y: auto;
}
.activity-panel__title {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .12em;
  color: #64748B;
  margin-bottom: 8px;
}
.activity-list { display: flex; flex-direction: column; gap: 6px; }
.activity-row { display: flex; align-items: flex-start; gap: 8px; }
.activity-dot {
  width: 6px; height: 6px; border-radius: 50%; margin-top: 5px; flex-shrink: 0;
  background: #64748B;
}
.dot--create { background: #20C997; }
.dot--update { background: #5C7CFA; }
.dot--execute { background: #F59F00; }
.dot--warning { background: #FA5252; }
.dot--delete { background: #FA5252; }
.dot--active { background: #20C997; }
.dot--error { background: #FA5252; }
.activity-body { flex: 1; min-width: 0; }
.activity-target { display: block; font-size: 11px; color: #CBD5E1; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.activity-meta { font-size: 9px; color: #64748B; }
.activity-empty { font-size: 11px; color: #475569; text-align: center; padding: 12px 0; }

.health-section { margin-top: 4px; }
.health-row { display: flex; align-items: center; gap: 6px; font-size: 11px; padding: 2px 0; }
.health-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.health-name { color: #CBD5E1; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.health-tier { color: #64748B; font-size: 9px; font-weight: 700; }
</style>
