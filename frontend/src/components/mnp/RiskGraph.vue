<template>
  <div class="risk-graph">
    <div class="risk-graph__header">
      <span class="risk-graph__title">关系图谱</span>
      <span class="risk-graph__sub">家庭 + 常联系人风险传导</span>
    </div>
    <div class="risk-graph__canvas">
      <EntityLineageGraph :entity-id="entityId" />
    </div>
  </div>
</template>

<script setup lang="ts">
import EntityLineageGraph from '../canvas/EntityLineageGraph.vue'
defineProps<{ entityId: string }>()
</script>

<style scoped>
.risk-graph { background: #fff; border-radius: 10px; border: 1px solid #e9ecef; overflow: hidden; }
.risk-graph__header { display: flex; align-items: baseline; gap: 8px; padding: 12px 16px; border-bottom: 1px solid #f1f3f5; }
.risk-graph__title { font-size: 14px; font-weight: 600; color: #343a40; }
.risk-graph__sub { font-size: 11px; color: #adb5bd; }
.risk-graph__canvas { height: 280px; }
.risk-graph__canvas :deep(.lineage-graph) { height: 100%; }
.risk-graph__canvas :deep(.lineage-graph__toolbar) { display: none; }
.risk-graph__canvas :deep(.lineage-graph__canvas) { border: none; border-radius: 0; }
</style>
