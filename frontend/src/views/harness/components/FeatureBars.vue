<template>
  <svg :width="200" :height="height" style="display:block;margin-top:6px">
    <g v-for="(f, i) in features" :key="i" :transform="`translate(0, ${i * 22})`">
      <rect :x="56" :y="2" :width="barWidth(i)" :height="14" rx="3" :fill="colorOf(i)" opacity="0.75" />
      <text :x="52" :y="13" font-size="10" fill="#666" text-anchor="end">
        {{ f.length > 6 ? f.slice(0, 6) + '..' : f }}
      </text>
      <text :x="56 + barWidth(i) + 4" :y="13" font-size="9" fill="#999">{{ valueOf(i) }}%</text>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ features: string[] }>()
const COLORS = ['#1677ff', '#36cfc9', '#9254de', '#faad14', '#ff7a45']
const height = computed(() => props.features.length * 22 + 4)

function valueOf(i: number) { return 100 - i * 15 }
function barWidth(i: number) {
  const v = valueOf(i)
  const max = valueOf(0) || 1
  return v / max * 140
}
function colorOf(i: number) { return COLORS[i % COLORS.length] }
</script>
