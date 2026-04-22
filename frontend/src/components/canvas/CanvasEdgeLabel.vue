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
import { BaseEdge, EdgeLabelRenderer, getStraightPath } from '@vue-flow/core'

const props = defineProps<{
  id: string
  sourceX: number; sourceY: number
  targetX: number; targetY: number
  sourcePosition: any; targetPosition: any
  data: { label: string; cardinality: string }
  markerEnd?: string
}>()

const path = computed(() => {
  const [p] = getStraightPath({
    sourceX: props.sourceX, sourceY: props.sourceY,
    targetX: props.targetX, targetY: props.targetY,
  })
  return p
})

const edgeStyle = { stroke: '#b4bfcc', strokeWidth: 1.2, opacity: 0.9 }

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
  display: flex; align-items: center; gap: 5px;
  background: rgba(255,255,255,0.97); padding: 3px 10px; border-radius: 12px;
  border: 1px solid #edf0f4; font-size: 10px; white-space: nowrap;
  box-shadow: 0 2px 6px rgba(0,0,0,0.04);
  backdrop-filter: blur(8px);
}
.edge-label__name { color: #475569; font-weight: 600; letter-spacing: 0.15px; }
.edge-label__card { color: #a1aab6; font-size: 9px; font-weight: 500; }
</style>
