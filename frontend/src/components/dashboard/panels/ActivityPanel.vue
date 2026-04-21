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
  color: var(--neutral-300);
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
  font-size: var(--text-caption-upper-size);
  font-weight: 800;
  letter-spacing: .12em;
  color: var(--neutral-700);
  margin-bottom: 8px;
}
.activity-list { display: flex; flex-direction: column; gap: 6px; }
.activity-row { display: flex; align-items: flex-start; gap: 8px; }
.activity-dot {
  width: 6px; height: 6px; border-radius: 50%; margin-top: 5px; flex-shrink: 0;
  background: var(--neutral-700);
}
.dot--create { background: var(--dynamic-500); }
.dot--update { background: var(--semantic-500); }
.dot--execute { background: var(--kinetic-500); }
.dot--warning { background: var(--status-error); }
.dot--delete { background: var(--status-error); }
.dot--active { background: var(--dynamic-500); }
.dot--error { background: var(--status-error); }
.activity-body { flex: 1; min-width: 0; }
.activity-target { display: block; font-size: var(--text-caption-size); color: var(--neutral-400); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.activity-meta { font-size: var(--text-caption-upper-size); color: var(--neutral-700); }
.activity-empty { font-size: var(--text-caption-size); color: var(--neutral-800); text-align: center; padding: 12px 0; }

.health-section { margin-top: 4px; }
.health-row { display: flex; align-items: center; gap: 6px; font-size: var(--text-caption-size); padding: 2px 0; }
.health-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.health-name { color: var(--neutral-400); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.health-tier { color: var(--neutral-700); font-size: var(--text-caption-upper-size); font-weight: 700; }
</style>
