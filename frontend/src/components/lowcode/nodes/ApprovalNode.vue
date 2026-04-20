<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
defineProps<{ data: any; id: string; selected?: boolean }>()
</script>
<template>
  <div class="lc-node lc-node--logic" :class="{ 'lc-node--selected': selected }">
    <div class="lc-node__header lc-node__header--purple">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2l6 4v4l-6 4-6-4V6l6-4z" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 6v4" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="12" r="0.8" fill="#fff"/></svg>
      <span>{{ data.label || '审批节点' }}</span>
    </div>
    <div class="lc-node__body">
      <div class="lc-node__meta">
        <span class="lc-node__tag">敏感工具</span>
        <span class="lc-node__val">{{ (data.config?.sensitiveTools || []).length }} 个</span>
      </div>
    </div>
    <Handle type="target" :position="Position.Left" />
    <Handle type="source" :position="Position.Right" />
  </div>
</template>
<style scoped>
.lc-node { border-radius: 10px; border: 2px solid var(--neutral-200); background: var(--bg-primary); min-width: 180px; font-size: 12px; }
.lc-node--selected { border-color: #8b5cf6; box-shadow: 0 0 0 2px rgba(139,92,246,0.2); }
.lc-node--logic { border-color: #c4b5fd; }
.lc-node__header { display: flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 8px 8px 0 0; color: #fff; font-weight: 600; font-size: 12px; }
.lc-node__header--purple { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }
.lc-node__body { padding: 8px 10px; }
.lc-node__meta { display: flex; align-items: center; gap: 6px; font-size: 11px; }
.lc-node__tag { background: var(--neutral-100); padding: 1px 6px; border-radius: 4px; font-weight: 600; color: var(--text-secondary); }
.lc-node__val { color: var(--text-muted); }
</style>
