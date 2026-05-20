<template>
  <div class="sem-view">
    <header class="sem-view__head">
      <div class="sem-view__info">
        <strong>本体语义网络 · 业务全景图</strong>
        <span class="sem-view__badge sem-view__badge--blue">{{ objects.length }} 对象</span>
        <span class="sem-view__badge sem-view__badge--cyan">{{ relations.length }} 关系</span>
      </div>
      <div class="sem-view__hint">
        点击节点查看属性 · 鼠标拖拽平移 · 滚轮缩放
      </div>
    </header>

    <div class="sem-view__canvas">
      <svg
        ref="svgRef"
        :viewBox="viewBox"
        preserveAspectRatio="xMidYMid meet"
        width="100%"
        height="100%"
        @wheel.prevent="onWheel"
        @mousedown="onMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @mouseleave="onMouseUp"
      >
        <defs>
          <pattern id="semGrid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#e2e8f0" stroke-width="0.4" />
          </pattern>
          <marker id="semArrow" viewBox="-10 -5 10 10" refX="0" refY="0" orient="auto" markerWidth="10" markerHeight="10">
            <path d="M -10 -5 L 0 0 L -10 5 Z" fill="#94a3b8" />
          </marker>
        </defs>

        <rect :x="vx" :y="vy" :width="vw" :height="vh" fill="url(#semGrid)" />

        <!-- 三层分带背景 -->
        <g>
          <rect :x="vx" :y="bands.t1.top" :width="vw" :height="bands.t1.height" fill="rgba(46,91,255,0.04)" />
          <text :x="vx + 20" :y="bands.t1.top + 22" class="sem-view__band-label" fill="#2E5BFF">基础层 · Tier 1</text>
          <rect :x="vx" :y="bands.t2.top" :width="vw" :height="bands.t2.height" fill="rgba(0,199,177,0.04)" />
          <text :x="vx + 20" :y="bands.t2.top + 22" class="sem-view__band-label" fill="#00C7B1">领域层 · Tier 2</text>
          <rect :x="vx" :y="bands.t3.top" :width="vw" :height="bands.t3.height" fill="rgba(255,107,53,0.04)" />
          <text :x="vx + 20" :y="bands.t3.top + 22" class="sem-view__band-label" fill="#FF6B35">场景层 · Tier 3</text>
        </g>

        <!-- 关系连线 -->
        <g>
          <g v-for="(link, idx) in renderedLinks" :key="link.id" :class="{ 'sem-view__link--highlight': highlightId === link.source || highlightId === link.target }">
            <path
              :id="`sem-path-${idx}`"
              :d="link.path"
              fill="none"
              :stroke="link.cross ? '#94a3b8' : '#cbd5e1'"
              :stroke-width="link.cross ? 1.3 : 0.9"
              stroke-opacity="0.6"
              marker-end="url(#semArrow)"
            />
            <text
              :x="link.midX"
              :y="link.midY - 4"
              class="sem-view__link-label"
              text-anchor="middle"
            >
              {{ link.label }}
            </text>
            <!-- 跨层关系流动粒子 -->
            <circle v-if="link.cross" r="2.4" fill="#3b82f6" opacity="0.85">
              <animateMotion :dur="`${3 + idx % 4 * 0.5}s`" repeatCount="indefinite">
                <mpath :href="`#sem-path-${idx}`" />
              </animateMotion>
              <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.9;1" :dur="`${3 + idx % 4 * 0.5}s`" repeatCount="indefinite" />
            </circle>
          </g>
        </g>

        <!-- 节点 -->
        <g>
          <g
            v-for="node in renderedNodes"
            :key="node.id"
            :style="{ cursor: 'pointer' }"
            @click="onNodeClick(node.id)"
            @mouseenter="highlightId = node.id"
            @mouseleave="highlightId = null"
          >
            <rect
              :x="node.x - node.w / 2"
              :y="node.y - 22"
              :width="node.w"
              :height="44"
              :rx="22"
              :ry="22"
              :fill="`${node.color}10`"
              :stroke="node.color"
              :stroke-width="highlightId === node.id ? 2.5 : 1.5"
            />
            <text :x="node.x" :y="node.y - 2" class="sem-view__node-label" text-anchor="middle" :fill="node.color">
              {{ node.label }}
            </text>
            <text :x="node.x" :y="node.y + 12" class="sem-view__node-en" text-anchor="middle">
              {{ node.apiName }}
            </text>
          </g>
        </g>
      </svg>

      <!-- 视图控制 -->
      <div class="sem-view__controls">
        <button class="sem-view__ctrl" @click="zoomBy(1.2)">+</button>
        <button class="sem-view__ctrl" @click="zoomBy(0.8)">−</button>
        <button class="sem-view__ctrl sem-view__ctrl--reset" @click="resetView">⟲</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { StudioObjectType, StudioLinkType } from '../../api/studio'

const props = defineProps<{
  objects: StudioObjectType[]
  relations: StudioLinkType[]
  selected?: StudioObjectType | null
}>()
const emit = defineEmits<{ (e: 'select', obj: StudioObjectType): void }>()

const tierColor: Record<1 | 2 | 3, string> = { 1: '#2E5BFF', 2: '#00C7B1', 3: '#FF6B35' }

const svgRef = ref<SVGSVGElement | null>(null)
const highlightId = ref<string | null>(null)

// 视图变换（缩放 + 平移）
const vx = ref(-100)
const vy = ref(-20)
const vw = ref(1600)
const vh = ref(900)
const viewBox = computed(() => `${vx.value} ${vy.value} ${vw.value} ${vh.value}`)

// 拖动
let dragStart: { x: number; y: number; vx: number; vy: number } | null = null
function onMouseDown(e: MouseEvent) {
  dragStart = { x: e.clientX, y: e.clientY, vx: vx.value, vy: vy.value }
}
function onMouseMove(e: MouseEvent) {
  if (!dragStart || !svgRef.value) return
  const rect = svgRef.value.getBoundingClientRect()
  const scale = vw.value / rect.width
  vx.value = dragStart.vx - (e.clientX - dragStart.x) * scale
  vy.value = dragStart.vy - (e.clientY - dragStart.y) * scale
}
function onMouseUp() { dragStart = null }
function onWheel(e: WheelEvent) {
  const factor = e.deltaY < 0 ? 0.9 : 1.1
  zoomBy(1 / factor)
}
function zoomBy(factor: number) {
  const newW = vw.value / factor
  const newH = vh.value / factor
  vx.value += (vw.value - newW) / 2
  vy.value += (vh.value - newH) / 2
  vw.value = newW
  vh.value = newH
}
function resetView() {
  vx.value = -100
  vy.value = -20
  vw.value = 1600
  vh.value = 900
}

// 三层分带 y 坐标
const bands = {
  t1: { top: 0, height: 200, centerY: 100 },
  t2: { top: 220, height: 200, centerY: 320 },
  t3: { top: 440, height: 360, centerY: 600 },
}

// 节点布局：每层水平排列
const renderedNodes = computed(() => {
  const t1 = props.objects.filter(o => o.tier === 1)
  const t2 = props.objects.filter(o => o.tier === 2)
  const t3 = props.objects.filter(o => o.tier === 3)

  const colSpacing = 200
  const out: Array<{ id: string; apiName: string; label: string; tier: 1 | 2 | 3; x: number; y: number; w: number; color: string }> = []

  const place = (objs: StudioObjectType[], y: number, tier: 1 | 2 | 3, maxPerRow = 6) => {
    const rows = Math.ceil(objs.length / maxPerRow)
    objs.forEach((o, i) => {
      const row = Math.floor(i / maxPerRow)
      const col = i % maxPerRow
      const itemsInRow = row === rows - 1 ? (objs.length - row * maxPerRow) : maxPerRow
      const startX = -(itemsInRow - 1) * colSpacing / 2 + 700
      out.push({
        id: o.apiName,
        apiName: o.apiName,
        label: o.displayName,
        tier,
        x: startX + col * colSpacing,
        y: y + (row - (rows - 1) / 2) * 60,
        w: Math.max(120, o.displayName.length * 14 + 28),
        color: tierColor[tier],
      })
    })
  }

  place(t1, bands.t1.centerY, 1, 6)
  place(t2, bands.t2.centerY, 2, 6)
  place(t3, bands.t3.centerY, 3, 6)

  return out
})

const nodeMap = computed(() => {
  const m = new Map<string, typeof renderedNodes.value[0]>()
  for (const n of renderedNodes.value) m.set(n.id, n)
  return m
})

const renderedLinks = computed(() => {
  return props.relations
    .map((r, i) => {
      const s = nodeMap.value.get(r.source)
      const t = nodeMap.value.get(r.target)
      if (!s || !t) return null
      // 节点边缘衔接
      const dx = t.x - s.x
      const dy = t.y - s.y
      const len = Math.hypot(dx, dy) || 1
      const ux = dx / len
      const uy = dy / len
      const sx = s.x + ux * (s.w / 2)
      const sy = s.y + uy * 22
      const tx = t.x - ux * (t.w / 2 + 8)
      const ty = t.y - uy * 22
      return {
        id: `${r.source}-${r.target}-${i}`,
        source: r.source,
        target: r.target,
        path: `M ${sx} ${sy} L ${tx} ${ty}`,
        midX: (sx + tx) / 2,
        midY: (sy + ty) / 2,
        label: r.displayName,
        cross: s.tier !== t.tier,
      }
    })
    .filter((x): x is NonNullable<typeof x> => x !== null)
})

function onNodeClick(id: string) {
  const obj = props.objects.find(o => o.apiName === id)
  if (obj) emit('select', obj)
}
</script>

<style scoped>
.sem-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fafbfd;
}

.sem-view__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}
.sem-view__info {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #1e293b;
}
.sem-view__badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.sem-view__badge--blue { background: #dbeafe; color: #1d4ed8; }
.sem-view__badge--cyan { background: #cffafe; color: #0e7490; }
.sem-view__hint {
  font-size: 11px;
  color: #94a3b8;
}

.sem-view__canvas {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #fafbfd;
}

.sem-view__band-label {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 2px;
  opacity: 0.6;
  pointer-events: none;
}

.sem-view__link-label {
  font-size: 8px;
  fill: #94a3b8;
  font-family: monospace;
  pointer-events: none;
  opacity: 0.8;
}

.sem-view__link--highlight path { stroke: #3b82f6 !important; stroke-width: 2 !important; }

.sem-view__node-label {
  font-size: 12px;
  font-weight: 700;
  pointer-events: none;
}
.sem-view__node-en {
  font-size: 9px;
  fill: #94a3b8;
  font-family: monospace;
  pointer-events: none;
}

.sem-view__controls {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.sem-view__ctrl {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  color: #475569;
  border-radius: 4px;
  font-weight: 700;
}
.sem-view__ctrl:hover { background: #f1f5f9; }
.sem-view__ctrl--reset { font-size: 14px; }
</style>
