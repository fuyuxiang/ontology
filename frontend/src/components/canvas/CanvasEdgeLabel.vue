<template>
  <svg style="position:absolute;width:0;height:0;overflow:hidden">
    <defs>
      <linearGradient :id="`edge-grad-${id}`" gradientUnits="userSpaceOnUse"
        :x1="sourceX" :y1="sourceY" :x2="targetX" :y2="targetY">
        <stop offset="0%" :stop-color="sourceColor" />
        <stop offset="100%" :stop-color="targetColor" />
      </linearGradient>
      <marker :id="`arrow-${id}`" viewBox="0 0 10 8" refX="9" refY="4"
        markerWidth="8" markerHeight="6" orient="auto-start-reverse">
        <path d="M0 0 L10 4 L0 8 Z" :fill="targetColor" opacity="0.7" />
      </marker>
    </defs>
  </svg>

  <path
    :d="path"
    :stroke="`url(#edge-grad-${id})`"
    :stroke-width="highlighted ? 2.5 : 1.8"
    stroke-linecap="round"
    fill="none"
    :opacity="dimmed ? 0.12 : 0.88"
    :stroke-dasharray="highlighted ? 'none' : '6 4'"
    :style="dimmed ? {} : animStyle"
    :marker-end="`url(#arrow-${id})`"
    class="edge-path"
  />

  <EdgeLabelRenderer>
    <div v-if="data.label" :style="labelStyle" class="edge-label" :class="{ 'edge-label--dimmed': dimmed }">
      <span class="edge-label__bar" :style="{ background: sourceColor }"></span>
      <span class="edge-label__name">{{ data.label }}</span>
      <span class="edge-label__card" v-if="data.cardinality">{{ data.cardinality }}</span>
    </div>
  </EdgeLabelRenderer>
</template>

<script setup lang="ts">
import { computed, type CSSProperties } from 'vue'
import { EdgeLabelRenderer, getBezierPath } from '@vue-flow/core'

const props = defineProps<{
  id: string
  sourceX: number
  sourceY: number
  targetX: number
  targetY: number
  sourcePosition: unknown
  targetPosition: unknown
  data: {
    label: string
    cardinality: string
    sourceTier?: number
    targetTier?: number
    highlighted?: boolean
    dimmed?: boolean
  }
  markerEnd?: string
}>()

const tierColors: Record<number, string> = { 1: '#4c6ef5', 2: '#7950f2', 3: '#20c997' }

const sourceColor = computed(() => tierColors[props.data.sourceTier ?? 1] || '#8d9db5')
const targetColor = computed(() => tierColors[props.data.targetTier ?? 1] || '#8d9db5')
const highlighted = computed(() => props.data.highlighted ?? false)
const dimmed = computed(() => props.data.dimmed ?? false)

const edgePathData = computed(() =>
  getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    targetX: props.targetX,
    targetY: props.targetY,
    sourcePosition: props.sourcePosition as never,
    targetPosition: props.targetPosition as never,
  })
)

const path = computed(() => edgePathData.value[0])
const labelX = computed(() => edgePathData.value[1])
const labelY = computed(() => edgePathData.value[2])

const animStyle = computed<CSSProperties>(() => ({
  animation: highlighted.value ? 'none' : 'edge-flow 1.2s linear infinite',
}))

const labelStyle = computed<CSSProperties>(() => ({
  position: 'absolute',
  transform: 'translate(-50%, -50%)',
  left: `${labelX.value}px`,
  top: `${labelY.value}px`,
  pointerEvents: 'none',
}))
</script>

<style scoped>
@keyframes edge-flow {
  to { stroke-dashoffset: -20; }
}

.edge-path {
  transition: stroke-width 0.25s ease, opacity 0.3s ease;
}

.edge-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 4px 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(228, 233, 241, 0.94);
  box-shadow: 0 4px 14px -8px rgba(30, 41, 59, 0.3);
  backdrop-filter: blur(10px);
  white-space: nowrap;
  transition: opacity 0.3s ease;
}

.edge-label--dimmed {
  opacity: 0.15;
}

.edge-label__bar {
  width: 3px;
  height: 14px;
  border-radius: 2px;
  flex-shrink: 0;
}

.edge-label__name {
  color: #475569;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12px;
}

.edge-label__card {
  color: #94a3b8;
  font-size: 9px;
  font-weight: 700;
}
</style>
