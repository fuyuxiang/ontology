<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
defineProps<{ data: any; id: string; selected?: boolean }>()
</script>
<template>
  <div class="lc-node lc-node--ui" :class="{ 'lc-node--selected': selected }">
    <div class="lc-node__header lc-node__header--blue">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="1" stroke="#fff" stroke-width="1.5"/><path d="M2 6h12M6 6v7M10 6v7" stroke="#fff" stroke-width="1" opacity="0.6"/></svg>
      <span>{{ data.label || 'Table' }}</span>
    </div>
    <div class="lc-node__body">
      <div class="lc-node__table-preview">
        <div class="lc-node__table-row lc-node__table-row--head">
          <span>列1</span><span>列2</span><span>列3</span>
        </div>
        <div class="lc-node__table-row"><span>...</span><span>...</span><span>...</span></div>
      </div>
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
.lc-node__body { padding: 8px 10px; }
.lc-node__table-preview { border: 1px solid var(--neutral-200); border-radius: 4px; overflow: hidden; }
.lc-node__table-row { display: grid; grid-template-columns: 1fr 1fr 1fr; font-size: 10px; color: var(--text-muted); }
.lc-node__table-row span { padding: 2px 6px; border-right: 1px solid var(--neutral-100); }
.lc-node__table-row--head { background: var(--neutral-100); font-weight: 600; color: var(--text-secondary); }
</style>
