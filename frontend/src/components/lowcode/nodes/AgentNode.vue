<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
defineProps<{ data: any; id: string; selected?: boolean }>()
</script>
<template>
  <div class="lc-node lc-node--logic" :class="{ 'lc-node--selected': selected }">
    <div class="lc-node__header lc-node__header--purple">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="#fff" stroke-width="1.5"/><path d="M6 8h4M8 6v4" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span>{{ data.label || 'Agent' }}</span>
    </div>
    <div class="lc-node__body">
      <div class="lc-node__meta" v-if="data.config?.persona">
        <span class="lc-node__tag">Persona</span>
        <span class="lc-node__val">{{ data.config.persona.slice(0, 30) }}{{ data.config.persona.length > 30 ? '...' : '' }}</span>
      </div>
      <div class="lc-node__meta">
        <span class="lc-node__tag">Tools</span>
        <span class="lc-node__val">{{ (data.config?.boundTools || []).length }} 个</span>
      </div>
      <div class="lc-node__meta">
        <span class="lc-node__tag">MaxSteps</span>
        <span class="lc-node__val">{{ data.config?.maxSteps || 8 }}</span>
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
.lc-node__body { padding: 8px 10px; display: flex; flex-direction: column; gap: 3px; }
.lc-node__meta { display: flex; align-items: center; gap: 6px; font-size: 11px; }
.lc-node__tag { background: var(--neutral-100); padding: 1px 6px; border-radius: 4px; font-weight: 600; color: var(--text-secondary); white-space: nowrap; }
.lc-node__val { color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
