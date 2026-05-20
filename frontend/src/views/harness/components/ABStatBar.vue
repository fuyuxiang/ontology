<template>
  <svg :width="240" :height="56" style="display:block">
    <!-- 对照组 -->
    <rect :x="0" :y="4" :width="ctrlW" :height="18" rx="4" fill="#8c8c8c" opacity="0.25" />
    <rect :x="0" :y="4" :width="ctrlW" :height="18" rx="4" fill="none" stroke="#8c8c8c" stroke-width="1" />
    <line :x1="Math.max(0, ctrlW - ctrlCI)" :y1="13" :x2="ctrlW + ctrlCI" :y2="13" stroke="#8c8c8c" stroke-width="1.5" />
    <line :x1="Math.max(0, ctrlW - ctrlCI)" :y1="9" :x2="Math.max(0, ctrlW - ctrlCI)" :y2="17" stroke="#8c8c8c" stroke-width="1" />
    <line :x1="ctrlW + ctrlCI" :y1="9" :x2="ctrlW + ctrlCI" :y2="17" stroke="#8c8c8c" stroke-width="1" />
    <text :x="ctrlW + ctrlCI + 6" :y="17" font-size="11" fill="#8c8c8c" font-weight="600">{{ control }}%</text>

    <!-- 实验组 -->
    <rect :x="0" :y="30" :width="trtW" :height="18" rx="4" :fill="trtColor" opacity="0.35" />
    <rect :x="0" :y="30" :width="trtW" :height="18" rx="4" fill="none" :stroke="trtColor" stroke-width="1" />
    <line :x1="Math.max(0, trtW - trtCI)" :y1="39" :x2="trtW + trtCI" :y2="39" :stroke="trtColor" stroke-width="1.5" />
    <line :x1="Math.max(0, trtW - trtCI)" :y1="35" :x2="Math.max(0, trtW - trtCI)" :y2="43" :stroke="trtColor" stroke-width="1" />
    <line :x1="trtW + trtCI" :y1="35" :x2="trtW + trtCI" :y2="43" :stroke="trtColor" stroke-width="1" />
    <text :x="trtW + trtCI + 6" :y="43" font-size="11" :fill="trtColor" font-weight="600">{{ treatment }}%</text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ control: number; treatment: number; pValue: number }>()

const scale = computed(() => 200 / (Math.max(props.control, props.treatment, 1) * 1.4))
const ctrlW = computed(() => props.control * scale.value)
const trtW = computed(() => props.treatment * scale.value)
const trtColor = computed(() => props.pValue < 0.05 ? '#52c41a' : '#1677ff')

function ci(rate: number) { return Math.max(0.5, 1.96 * Math.sqrt(rate * (100 - rate) / 1000) * scale.value) }
const ctrlCI = computed(() => ci(props.control))
const trtCI = computed(() => ci(props.treatment))
</script>
