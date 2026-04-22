<template>
  <div class="data-node" :class="{ 'data-node--selected': selected }">
    <Handle type="target" :position="targetPosition ?? Position.Top" class="data-node__handle" />
    <div class="data-node__header">
      <svg width="11" height="11" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4M3 8v4c0 1.1 2.24 2 5 2s5-.9 5-2V8" stroke="currentColor" stroke-width="1.5"/></svg>
      <span class="data-node__table">{{ data.table_name }}</span>
    </div>
    <div class="data-node__stats">
      <span class="data-node__count">{{ formatCount(data.record_count) }} 条</span>
      <span class="data-node__sep">·</span>
      <span class="data-node__fields">{{ data.field_count }} 字段</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'

defineProps<{
  data: { entity_id: string; entity_name_cn: string; table_name: string; field_count: number; record_count: number; datasource_name: string }
  selected?: boolean
  targetPosition?: Position
}>()

function formatCount(n: number) {
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return n.toString()
}
</script>

<style scoped>
.data-node {
  min-width: 110px;
  padding: 6px 10px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1.5px dashed #cbd5e1;
  display: flex; flex-direction: column; gap: 3px;
  cursor: pointer; transition: all 0.15s;
}
.data-node:hover {
  border-color: #94a3b8;
  background: #f1f5f9;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.data-node--selected {
  border-color: #64748b;
  background: #f1f5f9;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.data-node__header {
  display: flex; align-items: center; gap: 5px;
  color: #475569;
}
.data-node__table {
  font-size: 11px; font-weight: 600; color: #334155;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 90px;
}
.data-node__stats {
  display: flex; align-items: center; gap: 4px;
  font-size: 10px; color: #94a3b8;
}
.data-node__count { color: #64748b; font-weight: 500; }
.data-node__sep { color: #cbd5e1; }
.data-node__handle {
  width: 6px; height: 6px;
  background: #94a3b8; border: 2px solid #fff;
  border-radius: 50%;
}
</style>
