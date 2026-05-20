<template>
  <svg viewBox="0 0 500 180" style="display:block;width:100%;max-height:200px">
    <defs>
      <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#52c41a" stop-opacity="0.15" />
        <stop offset="100%" stop-color="#52c41a" stop-opacity="0.01" />
      </linearGradient>
    </defs>

    <!-- 网格线 -->
    <g v-for="(t, i) in gridTicks" :key="i">
      <line :x1="margin.l" :y1="t.y" :x2="margin.l + width" :y2="t.y" stroke="#f5f5f5" stroke-width="1" />
      <text :x="margin.l - 6" :y="t.y + 3" font-size="9" fill="#bbb" text-anchor="end">{{ t.label }}</text>
    </g>

    <!-- X 轴标签 -->
    <text v-for="(label, i) in xLabels" :key="'x' + i"
      :x="margin.l + i / (xLabels.length - 1) * width"
      :y="172"
      font-size="9" fill="#999" text-anchor="middle">{{ label }}</text>

    <!-- 演化生效辅助线 -->
    <line :x1="markerX" :y1="margin.t" :x2="markerX" :y2="margin.t + height" stroke="#faad14" stroke-width="1" stroke-dasharray="4,3" />
    <text :x="markerX" :y="margin.t - 6" font-size="8" fill="#faad14" text-anchor="middle">演化生效</text>

    <!-- 面积 + 折线 -->
    <path :d="areaPath" fill="url(#trendFill)" />
    <path :d="linePath" fill="none" stroke="#52c41a" stroke-width="2" stroke-linejoin="round" />
    <circle v-for="(p, i) in points" :key="i"
      :cx="p.x" :cy="p.y"
      :r="i === points.length - 1 ? 4 : 2.5"
      :fill="i >= 5 ? '#52c41a' : '#1677ff'"
      stroke="white" stroke-width="1.5" />

    <!-- 末端标签 -->
    <rect :x="lastPoint.x - 30" :y="lastPoint.y - 22" width="60" height="16" rx="4" fill="#52c41a" />
    <text :x="lastPoint.x" :y="lastPoint.y - 11" font-size="9" fill="white" text-anchor="middle" font-weight="600">+{{ lift }}%</text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ before: number; after: number; lift: number }>()

const margin = { t: 20, r: 20, b: 30, l: 40 }
const width = 500 - margin.l - margin.r
const height = 180 - margin.t - margin.b

const series = computed(() => [
  props.before * 0.95,
  props.before * 0.98,
  props.before,
  props.before * 1.01,
  props.before * 0.99,
  props.before + (props.after - props.before) * 0.3,
  props.before + (props.after - props.before) * 0.7,
  props.after,
])
const xLabels = ['W-7', 'W-6', 'W-5', 'W-4', 'W-3', 'W-2', 'W-1', '本周']

const yMin = computed(() => Math.min(...series.value) * 0.9)
const yRange = computed(() => Math.max(...series.value) * 1.1 - yMin.value || 1)

const points = computed(() => series.value.map((v, i) => ({
  x: margin.l + i / (series.value.length - 1) * width,
  y: margin.t + height - (v - yMin.value) / yRange.value * height,
})))

const linePath = computed(() => points.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' '))
const areaPath = computed(() => `${linePath.value} L ${points.value[points.value.length - 1].x} ${margin.t + height} L ${points.value[0].x} ${margin.t + height} Z`)
const lastPoint = computed(() => points.value[points.value.length - 1])
const markerX = computed(() => margin.l + 4.5 / (series.value.length - 1) * width)

const gridTicks = computed(() =>
  [0, 0.25, 0.5, 0.75, 1].map(p => ({
    y: margin.t + height * (1 - p),
    label: (yMin.value + yRange.value * p).toFixed(1),
  }))
)
</script>
