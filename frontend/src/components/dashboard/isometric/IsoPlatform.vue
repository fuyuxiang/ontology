<template>
  <!-- 等距平台：顶面 + 前面 + 右侧面 -->
  <g>
    <!-- 顶面 -->
    <polygon :points="topFace" :fill="topColor" stroke="rgba(15,17,23,.08)" stroke-width=".8" opacity=".85"/>
    <!-- 前面 -->
    <polygon :points="frontFace" :fill="frontColor" stroke="rgba(15,17,23,.06)" stroke-width=".8" opacity=".7"/>
    <!-- 右侧面 -->
    <polygon :points="sideFace" :fill="sideColor" stroke="rgba(15,17,23,.06)" stroke-width=".8" opacity=".6"/>
    <!-- 标签 -->
    <text :x="labelX" :y="labelY" font-size="8" font-weight="800" letter-spacing="1.5"
      fill="#94a3b8" text-anchor="middle" style="text-transform:uppercase">{{ label }}</text>
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  x: number; y: number; w: number; d: number; h: number
  topColor: string; frontColor: string; sideColor: string
  label: string
}>()

const ANG = Math.PI / 6
function ix(wx: number, wy: number) { return 450 + (wx - wy) * Math.cos(ANG) }
function iy(wx: number, wy: number) { return 310 + (wx + wy) * Math.sin(ANG) * 0.5 }

// 四个顶角 (world coords)
// A=左前, B=右前, C=右后, D=左后
const A = computed(() => [props.x,          props.y + props.d])
const B = computed(() => [props.x + props.w, props.y + props.d])
const C = computed(() => [props.x + props.w, props.y          ])
const D = computed(() => [props.x,           props.y          ])

function pt(wx: number, wy: number, dy = 0) { return `${ix(wx,wy)},${iy(wx,wy) + dy}` }

const topFace = computed(() => [
  pt(A.value[0], A.value[1]),
  pt(B.value[0], B.value[1]),
  pt(C.value[0], C.value[1]),
  pt(D.value[0], D.value[1]),
].join(' '))

const frontFace = computed(() => [
  pt(A.value[0], A.value[1]),
  pt(B.value[0], B.value[1]),
  pt(B.value[0], B.value[1], props.h),
  pt(A.value[0], A.value[1], props.h),
].join(' '))

const sideFace = computed(() => [
  pt(B.value[0], B.value[1]),
  pt(C.value[0], C.value[1]),
  pt(C.value[0], C.value[1], props.h),
  pt(B.value[0], B.value[1], props.h),
].join(' '))

const labelX = computed(() => ix(props.x + props.w/2, props.y + props.d/2))
const labelY = computed(() => iy(props.x + props.w/2, props.y + props.d/2) - 6)
</script>
