<template>
  <div class="ont-node" :class="[`ont-node--t${data.tier}`, { 'ont-node--selected': selected }]">
    <Handle type="target" :position="targetPosition ?? Position.Top" class="ont-node__handle" />
    <div class="ont-node__header">
      <span class="ont-node__tier">T{{ data.tier }} · {{ tierLabel }}</span>
      <span class="ont-node__status" :class="`ont-node__status--${data.status}`"></span>
    </div>
    <div class="ont-node__name">{{ data.nameCn }}</div>
    <div class="ont-node__en">{{ data.name }}</div>
    <div class="ont-node__stats">
      <span v-if="data.attrCount">{{ data.attrCount }} 属性</span>
      <span v-if="data.relCount">{{ data.relCount }} 关系</span>
    </div>
    <Handle type="source" :position="sourcePosition ?? Position.Bottom" class="ont-node__handle ont-node__handle--src" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  data: { name: string; nameCn: string; tier: 1 | 2 | 3; status: string; relCount: number; attrCount?: number }
  selected?: boolean
  sourcePosition?: Position
  targetPosition?: Position
}>()

const tierLabel = computed(() => ({ 1: '核心', 2: '领域', 3: '场景' }[props.data.tier]))
</script>

<style scoped>
.ont-node {
  min-width: 140px; max-width: 180px;
  padding: 10px 14px 8px;
  border-radius: 12px;
  background: #fff;
  border: 2px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  display: flex; flex-direction: column; gap: 3px;
  cursor: pointer; transition: all 0.18s;
  position: relative;
}
.ont-node:hover {
  border-color: var(--tc);
  box-shadow: 0 4px 16px rgba(0,0,0,0.1), 0 0 0 3px color-mix(in srgb, var(--tc) 12%, transparent);
  transform: translateY(-2px);
}
.ont-node--selected {
  border-color: var(--tc);
  box-shadow: 0 4px 16px rgba(0,0,0,0.12), 0 0 0 4px color-mix(in srgb, var(--tc) 18%, transparent);
}
.ont-node--t1 { --tc: #4f6ef7; border-top: 3px solid #4f6ef7; }
.ont-node--t2 { --tc: #8b5cf6; border-top: 3px solid #8b5cf6; }
.ont-node--t3 { --tc: #10b981; border-top: 3px solid #10b981; }

.ont-node__header { display: flex; align-items: center; justify-content: space-between; }
.ont-node__tier {
  font-size: 10px; font-weight: 700; color: var(--tc);
  background: color-mix(in srgb, var(--tc) 10%, transparent);
  padding: 1px 7px; border-radius: 4px; letter-spacing: 0.3px;
}
.ont-node__status { width: 7px; height: 7px; border-radius: 50%; }
.ont-node__status--active { background: #10b981; }
.ont-node__status--warning { background: #f59e0b; }
.ont-node__status--error { background: #ef4444; }

.ont-node__name {
  font-size: 13px; font-weight: 700; color: #1e293b;
  line-height: 1.3; margin-top: 2px;
}
.ont-node__en {
  font-size: 10px; color: #94a3b8; font-family: monospace;
}
.ont-node__stats {
  display: flex; gap: 8px; margin-top: 4px;
  padding-top: 4px; border-top: 1px solid #f1f5f9;
}
.ont-node__stats span {
  font-size: 10px; color: #64748b; font-weight: 500;
}
.ont-node__handle {
  width: 8px; height: 8px;
  background: var(--tc); border: 2px solid #fff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}
</style>
