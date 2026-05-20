<template>
  <svg :width="100" :height="14" style="vertical-align:middle">
    <rect :x="0" :y="6" :width="100" :height="2" fill="#f0f0f0" rx="1" />
    <line :x1="50" :y1="2" :x2="50" :y2="12" stroke="#d9d9d9" stroke-width="1" />
    <rect :x="rectX" :y="2" :width="rectW" :height="10" :fill="color" rx="2" opacity="0.85" />
    <text
      :x="textX"
      :y="10.5"
      font-size="9"
      :fill="color"
      :text-anchor="deviation < 0 ? 'end' : 'start'">
      {{ deviation > 0 ? '+' : '' }}{{ deviation }}%
    </text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ deviation: number }>()

const color = computed(() => {
  const abs = Math.abs(props.deviation)
  return abs > 25 ? '#ff4d4f' : abs > 15 ? '#faad14' : '#52c41a'
})
const rectW = computed(() => Math.min(Math.abs(props.deviation) / 40 * 50, 50))
const rectX = computed(() => props.deviation < 0 ? 50 - rectW.value : 50)
const textX = computed(() => 50 + (props.deviation < 0 ? -rectW.value - 3 : rectW.value + 3))
</script>
