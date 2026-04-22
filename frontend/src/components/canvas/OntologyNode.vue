<template>
  <div class="ontology-node" :class="[`ontology-node--tier${data.tier}`, { 'ontology-node--selected': selected }]"
       :style="{ '--tier-color': tierColor, '--tier-light': tierLight, '--tier-glow': tierGlow }">
    <Handle type="target" :position="targetPosition" class="ontology-node__handle" />
    <div class="ontology-node__name">{{ data.nameCn }}</div>
    <span class="ontology-node__tier">T{{ data.tier }}</span>
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

const tierColors: Record<number, string> = { 1: '#4f6ef7', 2: '#8b5cf6', 3: '#10b981' }
const tierLights: Record<number, string> = { 1: '#eef2ff', 2: '#f3f0ff', 3: '#ecfdf5' }
const tierGlows: Record<number, string> = { 1: 'rgba(79,110,247,0.12)', 2: 'rgba(139,92,246,0.12)', 3: 'rgba(16,185,129,0.12)' }
const tierColor = computed(() => tierColors[props.data.tier] || '#4f6ef7')
const tierLight = computed(() => tierLights[props.data.tier] || '#eef2ff')
const tierGlow = computed(() => tierGlows[props.data.tier] || 'rgba(79,110,247,0.12)')
</script>

<style scoped>
.ontology-node {
  width: 90px; height: 90px; border-radius: 50%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 3px; cursor: grab; position: relative;
  background:
    radial-gradient(circle at 36% 32%, rgba(255,255,255,0.95) 0%, transparent 55%),
    linear-gradient(145deg, #ffffff 0%, var(--tier-light) 55%, color-mix(in srgb, var(--tier-light) 70%, var(--tier-color)) 100%);
  border: 2px solid color-mix(in srgb, var(--tier-color) 30%, #e2e8f0);
  box-shadow:
    0 0 0 3px var(--tier-glow),
    0 4px 14px -2px rgba(0,0,0,0.07),
    0 1px 4px rgba(0,0,0,0.04),
    inset 0 1px 4px rgba(255,255,255,0.9);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.ontology-node:hover {
  transform: translateY(-2px) scale(1.06);
  border-color: color-mix(in srgb, var(--tier-color) 55%, #e2e8f0);
  box-shadow:
    0 0 0 5px var(--tier-glow),
    0 12px 28px -4px color-mix(in srgb, var(--tier-color) 16%, transparent),
    0 6px 14px -4px rgba(0,0,0,0.06),
    inset 0 1px 4px rgba(255,255,255,0.9);
}
.ontology-node--selected {
  border-color: var(--tier-color);
  box-shadow:
    0 0 0 5px color-mix(in srgb, var(--tier-color) 22%, transparent),
    0 12px 28px -4px color-mix(in srgb, var(--tier-color) 22%, transparent),
    0 6px 14px -4px rgba(0,0,0,0.08),
    inset 0 1px 4px rgba(255,255,255,0.9);
}
.ontology-node__name {
  font-size: 11px; font-weight: 650; color: #1e293b;
  max-width: 68px; text-align: center; line-height: 1.25;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ontology-node__tier {
  font-size: 9px; font-weight: 700; color: var(--tier-color);
  letter-spacing: 0.4px;
  background: color-mix(in srgb, var(--tier-color) 10%, transparent);
  padding: 1px 7px; border-radius: 6px;
  line-height: 1.4;
}
.ontology-node__handle {
  width: 7px; height: 7px; background: var(--tier-color);
  border: 2px solid #fff; border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
</style>
