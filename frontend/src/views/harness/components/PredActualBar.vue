<template>
  <svg width="160" height="32" style="display:block">
    <rect :x="0" :y="2" :width="predW" :height="12" rx="3" fill="#1677ff" opacity="0.3" />
    <rect :x="0" :y="2" :width="predW" :height="12" rx="3" fill="none" stroke="#1677ff" stroke-width="1" stroke-dasharray="3,2" />
    <text :x="predW + 4" :y="11" font-size="9" fill="#1677ff">{{ predicted }}%</text>
    <rect :x="0" :y="18" :width="actualW" :height="12" rx="3" :fill="actualColor" opacity="0.7" />
    <text :x="actualW + 4" :y="27" font-size="9" :fill="actualColor">{{ actual }}%</text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  predicted: number
  actual: number
  maxVal: number
}>()

const scale = computed(() => 120 / (props.maxVal || 1))
const predW = computed(() => props.predicted * scale.value)
const actualW = computed(() => props.actual * scale.value)
const actualColor = computed(() => props.actual >= props.predicted ? '#52c41a' : '#ff4d4f')
</script>
