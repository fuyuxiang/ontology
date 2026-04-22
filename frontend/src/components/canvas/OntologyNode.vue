<template>
  <div
    class="ontology-node"
    :class="[
      `ontology-node--tier${data.tier}`,
      { 'ontology-node--selected': selected, 'ontology-node--dimmed': data.dimmed },
    ]"
    :style="{ '--tier-color': tierColor, '--tier-soft': tierSoft, '--tier-glow': tierGlow }"
  >
    <Handle type="target" :position="targetPosition" class="ontology-node__handle ontology-node__handle--target" />

    <div class="ontology-node__head">
      <span class="ontology-node__icon">{{ tierIcon }}</span>
      <span class="ontology-node__tier">T{{ data.tier }}</span>
      <span class="ontology-node__status" :class="`ontology-node__status--${data.status}`"></span>
    </div>

    <div class="ontology-node__title-wrap">
      <div class="ontology-node__title">{{ data.nameCn }}</div>
      <div class="ontology-node__title-line"></div>
    </div>
    <div class="ontology-node__subtitle">{{ data.name }}</div>

    <div class="ontology-node__metrics">
      <span class="ontology-node__metric"><i>🔗</i>{{ data.relCount }}</span>
      <span class="ontology-node__metric"><i>📋</i>{{ data.attrCount }}</span>
      <span class="ontology-node__metric"><i>⚡</i>{{ data.ruleCount }}</span>
    </div>

    <div v-if="data.datasource" class="ontology-node__datasource">
      <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
        <ellipse cx="8" cy="4" rx="6" ry="2.5" stroke="currentColor" stroke-width="1.4"/>
        <path d="M2 4v8c0 1.38 2.69 2.5 6 2.5s6-1.12 6-2.5V4" stroke="currentColor" stroke-width="1.4"/>
        <path d="M2 8c0 1.38 2.69 2.5 6 2.5s6-1.12 6-2.5" stroke="currentColor" stroke-width="1.4"/>
      </svg>
      {{ data.datasource }}
    </div>

    <Handle type="source" :position="sourcePosition" class="ontology-node__handle ontology-node__handle--source" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  data: {
    name: string
    nameCn: string
    tier: 1 | 2 | 3
    status: string
    relCount: number
    attrCount: number
    ruleCount: number
    datasource?: string | null
    dimmed?: boolean
  }
  selected?: boolean
  sourcePosition?: Position
  targetPosition?: Position
}>()

const tierColors: Record<number, string> = { 1: '#4c6ef5', 2: '#7950f2', 3: '#20c997' }
const tierSofts: Record<number, string> = { 1: '#eef2ff', 2: '#f3f0ff', 3: '#e6fcf5' }
const tierGlows: Record<number, string> = { 1: 'rgba(76, 110, 245, 0.18)', 2: 'rgba(121, 80, 242, 0.18)', 3: 'rgba(32, 201, 151, 0.18)' }
const tierIcons: Record<number, string> = { 1: '🏛️', 2: '🔗', 3: '📊' }

const tierColor = computed(() => tierColors[props.data.tier] || '#4c6ef5')
const tierSoft = computed(() => tierSofts[props.data.tier] || '#eef2ff')
const tierGlow = computed(() => tierGlows[props.data.tier] || 'rgba(76, 110, 245, 0.18)')
const tierIcon = computed(() => tierIcons[props.data.tier] || '🏛️')
</script>

<style scoped>
.ontology-node {
  position: relative;
  width: 172px;
  padding: 12px 14px 10px;
  border-radius: 32px;
  border: 1.5px solid rgba(222, 229, 238, 0.85);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, color-mix(in srgb, var(--tier-soft) 92%, #ffffff) 100%);
  box-shadow:
    0 18px 28px -24px rgba(23, 32, 51, 0.32),
    0 0 0 5px color-mix(in srgb, var(--tier-glow) 50%, transparent);
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.25s ease,
              border-color 0.25s ease,
              opacity 0.3s ease;
  animation: node-enter 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

@keyframes node-enter {
  from { opacity: 0; transform: scale(0.82); }
  to   { opacity: 1; transform: scale(1); }
}

.ontology-node:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--tier-color) 36%, #cfd7e3);
  box-shadow:
    0 22px 36px -20px rgba(23, 32, 51, 0.28),
    0 0 0 8px color-mix(in srgb, var(--tier-glow) 75%, transparent);
}

.ontology-node--selected {
  border-color: var(--tier-color);
  animation: node-pulse 2s ease-in-out infinite;
}

@keyframes node-pulse {
  0%, 100% { box-shadow: 0 0 0 5px color-mix(in srgb, var(--tier-glow) 60%, transparent); }
  50%      { box-shadow: 0 0 0 12px color-mix(in srgb, var(--tier-glow) 30%, transparent); }
}

.ontology-node--dimmed {
  opacity: 0.25;
  filter: grayscale(0.6);
  pointer-events: none;
}

.ontology-node__head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ontology-node__icon {
  font-size: 16px;
  line-height: 1;
}

.ontology-node__tier {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tier-color) 12%, #ffffff);
  color: var(--tier-color);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.45px;
  text-transform: uppercase;
}

.ontology-node__status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cbd5e1;
  margin-left: auto;
}

.ontology-node__status--active { background: var(--status-success); }
.ontology-node__status--warning { background: var(--status-warning); }
.ontology-node__status--error { background: var(--status-error); }

.ontology-node__title-wrap {
  margin-top: 8px;
}

.ontology-node__title {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.35;
  color: #172033;
  word-break: break-word;
}

.ontology-node__title-line {
  margin-top: 5px;
  height: 2px;
  border-radius: 1px;
  background: linear-gradient(90deg, var(--tier-color), transparent);
  opacity: 0.35;
}

.ontology-node__subtitle {
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--neutral-500);
  word-break: break-word;
}

.ontology-node__metrics {
  display: flex;
  gap: 5px;
  margin-top: 8px;
}

.ontology-node__metric {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(247, 249, 252, 0.94);
  border: 1px solid rgba(231, 236, 242, 0.96);
  color: var(--neutral-600);
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.ontology-node__metric i {
  font-style: normal;
  font-size: 10px;
}

.ontology-node__datasource {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.8);
  color: var(--neutral-500);
  font-size: 9px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ontology-node__datasource svg {
  flex-shrink: 0;
  color: var(--tier-color);
}

.ontology-node__handle {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--tier-color);
  border: 2px solid #fff;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tier-glow) 88%, transparent);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.ontology-node:hover .ontology-node__handle,
.ontology-node--selected .ontology-node__handle {
  opacity: 1;
}
</style>
