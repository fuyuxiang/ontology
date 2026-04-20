<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
defineProps<{ data: any; id: string; selected?: boolean }>()
</script>
<template>
  <div class="lc-node lc-node--ui" :class="{ 'lc-node--selected': selected }">
    <div class="lc-node__header lc-node__header--blue">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="3" y="5" width="10" height="6" rx="2" stroke="#fff" stroke-width="1.5"/><path d="M6 8h4" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span>{{ data.label || 'Button' }}</span>
    </div>
    <div class="lc-node__body">
      <div class="lc-node__btn-preview">{{ data.config?.text || '点击执行' }}</div>
    </div>
    <Handle type="target" :position="Position.Left" />
    <Handle type="source" :position="Position.Right" />
  </div>
</template>
<style scoped>
.lc-node { border-radius: 10px; border: 2px solid var(--neutral-200); background: var(--bg-primary); min-width: 160px; font-size: 12px; }
.lc-node--selected { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }
.lc-node--ui { border-color: #93c5fd; }
.lc-node__header { display: flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 8px 8px 0 0; color: #fff; font-weight: 600; font-size: 12px; }
.lc-node__header--blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.lc-node__body { padding: 8px 10px; }
.lc-node__btn-preview { background: #3b82f6; color: #fff; text-align: center; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; }
</style>
