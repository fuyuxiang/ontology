<template>
  <div class="ontology-node" :class="[`ontology-node--tier${data.tier}`, { 'ontology-node--selected': selected }]">
    <Handle type="target" :position="targetPosition" />
    <div class="ontology-node__badge" :style="{ background: tierColor }">T{{ data.tier }}</div>
    <div class="ontology-node__body">
      <div class="ontology-node__name">{{ data.nameCn }}</div>
    </div>
    <div class="ontology-node__count">{{ data.relCount }}</div>
    <Handle type="source" :position="sourcePosition" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  data: { name: string; nameCn: string; tier: 1 | 2 | 3; status: string; relCount: number }
  selected?: boolean
  sourcePosition?: Position
  targetPosition?: Position
}>()

const tierColors: Record<number, string> = { 1: '#4c6ef5', 2: '#7950f2', 3: '#20c997' }
const tierColor = computed(() => tierColors[props.data.tier] || '#4c6ef5')
</script>

<style scoped>
.ontology-node {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; min-width: 160px;
  background: #fff; border: 1.5px solid var(--neutral-200, #e9ecef);
  border-radius: 10px; cursor: grab; transition: all 0.15s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.ontology-node:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.ontology-node--selected { border-color: #4c6ef5; box-shadow: 0 0 0 2px rgba(76,110,245,0.2); }
.ontology-node--tier2.ontology-node--selected { border-color: #7950f2; box-shadow: 0 0 0 2px rgba(121,80,242,0.2); }
.ontology-node--tier3.ontology-node--selected { border-color: #20c997; box-shadow: 0 0 0 2px rgba(32,201,151,0.2); }
.ontology-node__badge {
  width: 28px; height: 28px; border-radius: 6px; display: flex;
  align-items: center; justify-content: center; color: #fff;
  font-size: 10px; font-weight: 700; flex-shrink: 0;
}
.ontology-node__body { flex: 1; min-width: 0; }
.ontology-node__name { font-size: 13px; font-weight: 600; color: #343a40; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ontology-node__cn { font-size: 11px; color: #868e96; margin-top: 1px; }
.ontology-node__count {
  font-size: 10px; color: #adb5bd; background: #f8f9fa;
  padding: 2px 6px; border-radius: 4px; flex-shrink: 0;
}
</style>
