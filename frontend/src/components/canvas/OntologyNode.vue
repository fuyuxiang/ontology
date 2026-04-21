<template>
  <div class="ontology-node" :class="[`ontology-node--tier${data.tier}`, { 'ontology-node--selected': selected }]"
       :style="{ '--tier-color': tierColor, '--tier-light': tierLight }">
    <Handle type="target" :position="targetPosition" class="ontology-node__handle" />
    <div class="ontology-node__name">{{ data.nameCn }}</div>
    <div class="ontology-node__tier">T{{ data.tier }}</div>
    <Handle type="source" :position="sourcePosition" class="ontology-node__handle" />
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
const tierLights: Record<number, string> = { 1: '#dbe4ff', 2: '#e5dbff', 3: '#c3fae8' }
const tierColor = computed(() => tierColors[props.data.tier] || '#4c6ef5')
const tierLight = computed(() => tierLights[props.data.tier] || '#dbe4ff')
</script>

<style scoped>
.ontology-node {
  width: 80px; height: 80px; border-radius: 50%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 2px; cursor: grab;
  background: radial-gradient(circle at 35% 35%, #ffffff 0%, var(--tier-light) 70%);
  border: 2.5px solid var(--tier-color);
  transition: all 0.2s ease;
  box-shadow: 0 3px 14px rgba(0,0,0,0.1);
}
.ontology-node:hover {
  box-shadow: 0 4px 20px rgba(0,0,0,0.15), 0 0 0 4px color-mix(in srgb, var(--tier-color) 18%, transparent);
  transform: scale(1.06);
}
.ontology-node--selected {
  box-shadow: 0 4px 24px rgba(0,0,0,0.18), 0 0 0 4px color-mix(in srgb, var(--tier-color) 35%, transparent);
}
.ontology-node__name {
  font-size: 11px; font-weight: 600; color: #1a1a2e;
  max-width: 64px; text-align: center;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ontology-node__tier {
  font-size: 9px; font-weight: 700; color: var(--tier-color);
  letter-spacing: 0.5px;
}
.ontology-node__handle {
  width: 6px; height: 6px; background: var(--tier-color);
  border: 2px solid #fff; border-radius: 50%;
}
</style>
