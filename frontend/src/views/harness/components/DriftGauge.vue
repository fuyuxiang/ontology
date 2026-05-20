<template>
  <a-progress
    type="dashboard"
    :percent="clamped"
    :stroke-color="strokeColor"
    :stroke-width="8"
    :size="90"
    :format="format"
  />
</template>

<script setup lang="ts">
import { computed, h } from 'vue'

const props = defineProps<{ value: number }>()

const clamped = computed(() => Math.max(0, Math.min(100, props.value)))
const color = computed(() => clamped.value < 15 ? '#52c41a' : clamped.value < 30 ? '#faad14' : '#ff4d4f')

const strokeColor = {
  '0%': '#52c41a',
  '50%': '#faad14',
  '100%': '#ff4d4f',
}

const format = () => h('div', null, [
  h('div', { style: { fontSize: '18px', fontWeight: 700, color: color.value, lineHeight: 1.2 } }, clamped.value.toFixed(1)),
  h('div', { style: { fontSize: '9px', color: '#999' } }, '/ 100'),
])
</script>
