<template>
  <BaseEdge :path="path" :marker-end="markerEnd" :style="edgeStyle" />
  <EdgeLabelRenderer>
    <div :style="labelStyle" class="edge-label">
      <span class="edge-label__name">{{ data.label }}</span>
      <span class="edge-label__card">{{ data.cardinality }}</span>
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

const edgeStyle = { stroke: '#91a7ff', strokeWidth: 1.5 }

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
  background: #fff; padding: 2px 8px; border-radius: 4px;
  border: 1px solid #e9ecef; font-size: 10px; white-space: nowrap;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.edge-label__name { color: #495057; font-weight: 500; }
.edge-label__card { color: #adb5bd; font-size: 9px; }
</style>
