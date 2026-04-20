<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
defineProps<{ data: any; id: string; selected?: boolean }>()
</script>
<template>
  <div class="lc-node lc-node--ui" :class="{ 'lc-node--selected': selected }">
    <div class="lc-node__header lc-node__header--blue">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="2" stroke="#fff" stroke-width="1.5"/><path d="M5 7h6M5 10h4" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span>{{ data.label || 'HITL Inbox' }}</span>
    </div>
    <div class="lc-node__body">
      <div class="lc-node__inbox-row"><span class="lc-node__dot lc-node__dot--pending"></span> 待审批任务列表</div>
      <div class="lc-node__inbox-row"><span class="lc-node__dot lc-node__dot--done"></span> 批准 / 拒绝</div>
    </div>
    <Handle type="target" :position="Position.Left" />
    <Handle type="source" :position="Position.Right" />
  </div>
</template>
<style scoped>
.lc-node { border-radius: 10px; border: 2px solid var(--neutral-200); background: var(--bg-primary); min-width: 180px; font-size: 12px; }
.lc-node--selected { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }
.lc-node--ui { border-color: #93c5fd; }
.lc-node__header { display: flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 8px 8px 0 0; color: #fff; font-weight: 600; font-size: 12px; }
.lc-node__header--blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.lc-node__body { padding: 8px 10px; display: flex; flex-direction: column; gap: 4px; }
.lc-node__inbox-row { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-secondary); }
.lc-node__dot { width: 6px; height: 6px; border-radius: 50%; }
.lc-node__dot--pending { background: #f59e0b; }
.lc-node__dot--done { background: #10b981; }
</style>
