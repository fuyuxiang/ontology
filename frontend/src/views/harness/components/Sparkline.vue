<template>
  <svg :width="width" :height="height" style="display:block;margin-top:4px" v-if="data.length">
    <defs>
      <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity="0.2" />
        <stop offset="100%" :stop-color="color" stop-opacity="0.02" />
      </linearGradient>
    </defs>
    <path :d="areaPath" :fill="`url(#${gradId})`" />
    <polyline :points="points" fill="none" :stroke="color" stroke-width="1.5" stroke-linejoin="round" />
    <circle v-if="data.length > 1" :cx="width" :cy="lastY" r="2.5" :fill="color" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  data: number[]
  color: string
  width?: number
  height?: number
}>(), {
  width: 80,
  height: 28,
})

const min = computed(() => Math.min(...props.data))
const range = computed(() => Math.max(...props.data) - min.value || 1)

const points = computed(() => props.data.map((v, i) =>
  `${i / (props.data.length - 1) * props.width},${props.height - (v - min.value) / range.value * (props.height - 4) - 2}`
).join(' '))

const areaPath = computed(() => {
  if (!props.data.length) return ''
  const pts = points.value.split(' ')
  return `M 0,${props.height} L ${pts.join(' L ')} L ${props.width},${props.height} Z`
})

const lastY = computed(() => {
  if (!props.data.length) return 0
  const last = props.data[props.data.length - 1]
  return props.height - (last - min.value) / range.value * (props.height - 4) - 2
})

const gradId = computed(() => `spark-${props.color.replace('#', '')}-${Math.floor(Math.random() * 10000)}`)
</script>
