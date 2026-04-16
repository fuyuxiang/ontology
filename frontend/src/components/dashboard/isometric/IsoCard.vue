<template>
  <g :opacity="dimmed ? 0.2 : 1" style="transition:opacity .3s">
    <rect
      :x="sx - w2" :y="sy - h2"
      :width="sw" :height="sh"
      :rx="4"
      :fill="selected ? 'rgba(16,185,129,.15)' : color"
      :stroke="selected ? '#10b981' : 'rgba(15,17,23,.08)'"
      :stroke-width="selected ? 1.5 : 0.8"
      style="filter:drop-shadow(0 2px 6px rgba(15,17,23,.08))"
    />
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  x: number; y: number; w: number; h: number
  color?: string; selected?: boolean; dimmed?: boolean
}>()

const ANG = Math.PI / 6
function ix(wx: number, wy: number) { return 450 + (wx - wy) * Math.cos(ANG) }
function iy(wx: number, wy: number) { return 310 + (wx + wy) * Math.sin(ANG) * 0.5 }

// 把 world 矩形中心投影到屏幕，用屏幕坐标画矩形（近似，不做完整等距变形）
const cx = computed(() => props.x + props.w / 2)
const cy = computed(() => props.y + props.h / 2)
const sx = computed(() => ix(cx.value, cy.value))
const sy = computed(() => iy(cx.value, cy.value))
// 屏幕宽高近似
const sw = computed(() => props.w * Math.cos(ANG) * 1.1)
const sh = computed(() => props.h * 0.55)
const w2 = computed(() => sw.value / 2)
const h2 = computed(() => sh.value / 2)
</script>
