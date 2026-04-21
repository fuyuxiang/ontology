<template>
  <BaseEdge :path="path" :marker-end="markerEnd" :style="edgeStyle" />
  <EdgeLabelRenderer>
    <div :style="labelStyle" class="edge-label">
      <span class="edge-label__name">{{ data.label }}</span>
      <span class="edge-label__card" v-if="data.cardinality">{{ data.cardinality }}</span>
    </div>
  </EdgeLabelRenderer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BaseEdge, EdgeLabelRenderer, getBezierPath } from '@vue-flow/core'

const props = defineProps<{
  id: string
  sourceX: number; sourceY: number
  targetX: number; targetY: number
  sourcePosition: any; targetPosition: any
  data: { label: string; cardinality: string }
  markerEnd?: string
}>()

const path = computed(() => {
  const [p] = getBezierPath({
    sourceX: props.sourceX, sourceY: props.sourceY,
    targetX: props.targetX, targetY: props.targetY,
    sourcePosition: props.sourcePosition, targetPosition: props.targetPosition,
  })
  return p
})

const edgeStyle = { stroke: '#a5b4fc', strokeWidth: 1.8, opacity: 0.7 }

const labelStyle = computed(() => ({
  position: 'absolute',
  transform: 'translate(-50%, -50%)',
  left: `${(props.sourceX + props.targetX) / 2}px`,
  top: `${(props.sourceY + props.targetY) / 2}px`,
  pointerEvents: 'all',
}))
</script>

<style scoped>
.edge-label {
  display: flex; align-items: center; gap: 4px;
  background: rgba(255,255,255,0.92); padding: 2px 8px; border-radius: 6px;
  border: 1px solid #e2e8f0; font-size: 10px; white-space: nowrap;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  backdrop-filter: blur(4px);
}
.edge-label__name { color: #475569; font-weight: 500; }
.edge-label__card { color: #94a3b8; font-size: 10px; }
</style>
