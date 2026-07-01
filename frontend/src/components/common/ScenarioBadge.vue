<template>
  <span
    class="scenario-badge"
    :style="{ background: bg, color: fg, borderColor: border }"
    :title="label"
  >
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useScenarioStore } from '../../store/scenarios'

const props = defineProps<{ code: string }>()
const store = useScenarioStore()

const scenario = computed(() => store.byCode(props.code))
const label = computed(() => scenario.value?.name || props.code)
const color = computed(() => scenario.value?.color || '#64748b')

// 用场景色做描边和浅色底，保证在浅色背景下可读
const bg = computed(() => hexToRgba(color.value, 0.12))
const fg = computed(() => color.value)
const border = computed(() => hexToRgba(color.value, 0.35))

function hexToRgba(hex: string, alpha: number): string {
  const m = hex.replace('#', '')
  const full = m.length === 3 ? m.split('').map(c => c + c).join('') : m
  const r = parseInt(full.slice(0, 2), 16)
  const g = parseInt(full.slice(2, 4), 16)
  const b = parseInt(full.slice(4, 6), 16)
  if ([r, g, b].some(Number.isNaN)) return hex
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
</script>

<style scoped>
.scenario-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid transparent;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.5;
  white-space: nowrap;
}
</style>
