<template>
  <div class="ont-node" :class="[`ont-node--t${data.tier}`, { 'ont-node--selected': selected }]">
    <Handle type="target" :position="targetPosition ?? Position.Left" class="ont-node__handle" />
    <div class="ont-node__tier">T{{ data.tier }}</div>
    <div class="ont-node__name">{{ data.nameCn }}</div>
    <div class="ont-node__rel" v-if="data.relCount > 0">{{ data.relCount }} 关系</div>
    <Handle type="source" :position="sourcePosition ?? Position.Right" class="ont-node__handle ont-node__handle--src" />
  </div>
</template>

<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'

defineProps<{
  data: { name: string; nameCn: string; tier: 1 | 2 | 3; status: string; relCount: number }
  selected?: boolean
  sourcePosition?: Position
  targetPosition?: Position
}>()
</script>

<style scoped>
.ont-node {
  min-width: 96px; max-width: 120px;
  padding: 8px 12px 7px;
  border-radius: 10px;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06), 0 0 0 0 transparent;
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  cursor: pointer; transition: all 0.18s;
  position: relative;
}
.ont-node:hover {
  border-color: var(--tc);
  box-shadow: 0 4px 14px rgba(0,0,0,0.08), 0 0 0 3px color-mix(in srgb, var(--tc) 12%, transparent);
  transform: translateY(-1px);
}
.ont-node--selected {
  border-color: var(--tc);
  box-shadow: 0 4px 14px rgba(0,0,0,0.1), 0 0 0 3px color-mix(in srgb, var(--tc) 18%, transparent);
}
.ont-node--t1 { --tc: #4f6ef7; }
.ont-node--t2 { --tc: #8b5cf6; }
.ont-node--t3 { --tc: #10b981; }

.ont-node__tier {
  font-size: 9px; font-weight: 700; color: var(--tc);
  background: color-mix(in srgb, var(--tc) 10%, transparent);
  padding: 1px 6px; border-radius: 4px; letter-spacing: 0.3px;
  align-self: flex-start;
}
.ont-node__name {
  font-size: 12px; font-weight: 600; color: #1e293b;
  text-align: center; line-height: 1.3;
  word-break: break-all;
}
.ont-node__rel {
  font-size: 10px; color: #94a3b8;
}
.ont-node__handle {
  width: 8px; height: 8px;
  background: var(--tc); border: 2px solid #fff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}
</style>
