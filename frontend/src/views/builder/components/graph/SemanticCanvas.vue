<template>
  <div class="canvas-wrap">
    <div class="bubble-canvas-wrap">
      <svg
        ref="svgRef"
        class="bubble-canvas-svg"
        :viewBox="viewBox"
        preserveAspectRatio="xMidYMid meet"
        @wheel.prevent="onWheel"
        @mousedown="onMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @mouseleave="onMouseUp"
      >
        <defs>
          <pattern id="bubGrid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#e2e8f0" stroke-width="0.4" />
          </pattern>
          <marker id="bubArrow" viewBox="-10 -5 10 10" refX="0" refY="0" orient="auto" markerWidth="10" markerHeight="10">
            <path d="M -10 -5 L 0 0 L -10 5 Z" fill="#94a3b8" />
          </marker>
        </defs>

        <rect :x="vx" :y="vy" :width="vw" :height="vh" fill="url(#bubGrid)" />

        <!-- 三层分带 -->
        <g>
          <rect :x="vx" :y="bands.t1.top" :width="vw" :height="bands.t1.height" fill="rgba(46,91,255,0.04)" />
          <text :x="vx + 20" :y="bands.t1.top + 22" class="bub-band-label" fill="#2E5BFF">基础层 · Tier 1</text>
          <rect :x="vx" :y="bands.t2.top" :width="vw" :height="bands.t2.height" fill="rgba(0,199,177,0.04)" />
          <text :x="vx + 20" :y="bands.t2.top + 22" class="bub-band-label" fill="#00C7B1">领域层 · Tier 2</text>
          <rect :x="vx" :y="bands.t3.top" :width="vw" :height="bands.t3.height" fill="rgba(255,107,53,0.04)" />
          <text :x="vx + 20" :y="bands.t3.top + 22" class="bub-band-label" fill="#FF6B35">场景层 · Tier 3</text>
        </g>

        <!-- 关系连线 -->
        <g>
          <g v-for="(link, idx) in renderedLinks" :key="link.id">
            <path
              :id="`bub-path-${idx}`"
              :d="link.path"
              fill="none"
              :stroke="link.cross ? '#94a3b8' : '#cbd5e1'"
              :stroke-width="link.cross ? 1.4 : 1"
              stroke-opacity="0.65"
              marker-end="url(#bubArrow)"
            />
            <text :x="link.midX" :y="link.midY - 4" class="bub-link-label" text-anchor="middle">{{ link.label }}</text>
            <circle v-if="link.cross" r="2.4" fill="#3b82f6" opacity="0.85">
              <animateMotion :dur="`${3 + (idx % 4) * 0.5}s`" repeatCount="indefinite">
                <mpath :href="`#bub-path-${idx}`" />
              </animateMotion>
            </circle>
          </g>
        </g>

        <!-- 节点 -->
        <g>
          <g
            v-for="n in renderedNodes"
            :key="n.id"
            :transform="`translate(${n.x},${n.y})`"
            class="bub-node"
            :class="{ 'bub-node--selected': selected === n.id }"
            @click="onNodeClick(n.id)"
          >
            <rect
              :x="-n.w / 2" y="-22"
              :width="n.w" height="44" rx="22"
              :fill="n.tier === 1 ? '#fff' : n.tier === 2 ? '#fff' : '#fff'"
              :stroke="n.color" stroke-width="1.6"
              filter="url(#bub-shadow)"
            />
            <text x="0" y="2" text-anchor="middle" class="bub-node-label" :fill="n.color">{{ n.icon }} {{ n.label }}</text>
            <text x="0" y="14" text-anchor="middle" class="bub-node-en">T{{ n.tier }} · {{ n.count }} 实例</text>
          </g>
        </g>

        <filter id="bub-shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#0f172a" flood-opacity="0.08" />
        </filter>
      </svg>

      <div class="bub-controls">
        <button class="bub-ctrl" @click="zoomBy(1.2)">＋</button>
        <button class="bub-ctrl" @click="zoomBy(1 / 1.2)">－</button>
        <button class="bub-ctrl bub-ctrl--reset" @click="resetView">⤾</button>
        <button class="bub-ctrl" :disabled="!editable" @click="$emit('add')" title="新增对象">＋⊕</button>
      </div>
    </div>

    <div v-if="selected && editable" class="canvas-divider"><span>选中：{{ selectedNode?.label }}（点击空白取消选中）</span></div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { OntologyClassDraft, OntologyRelationDraft, Step1Phase } from '../../../../types/builder'

const props = defineProps<{
  objects: OntologyClassDraft[]
  relations: OntologyRelationDraft[]
  phase: Step1Phase
  graphPhaseLabel?: string
  editable?: boolean
}>()
const emit = defineEmits<{
  (e: 'add'): void
  (e: 'delete', id: string): void
  (e: 'drop', ev: DragEvent): void
}>()

const tierColor: Record<1 | 2 | 3, string> = { 1: '#2E5BFF', 2: '#00C7B1', 3: '#FF6B35' }

const svgRef = ref<SVGSVGElement | null>(null)
const selected = ref<string | null>(null)

const vx = ref(-100)
const vy = ref(-20)
const vw = ref(1600)
const vh = ref(900)
const viewBox = computed(() => `${vx.value} ${vy.value} ${vw.value} ${vh.value}`)

let dragStart: { x: number; y: number; vx: number; vy: number } | null = null
function onMouseDown(e: MouseEvent) {
  if ((e.target as Element).closest('.bub-node')) return
  dragStart = { x: e.clientX, y: e.clientY, vx: vx.value, vy: vy.value }
  selected.value = null
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
  zoomBy(e.deltaY < 0 ? 1.1 : 1 / 1.1)
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
  vx.value = -100; vy.value = -20; vw.value = 1600; vh.value = 900
}

const bands = {
  t1: { top: 0,   height: 200, centerY: 100 },
  t2: { top: 220, height: 200, centerY: 320 },
  t3: { top: 440, height: 360, centerY: 600 },
}

interface RNode { id: string; label: string; icon: string; count: number; tier: 1 | 2 | 3; x: number; y: number; w: number; color: string }

const renderedNodes = computed<RNode[]>(() => {
  const t1 = props.objects.filter(o => o.tier === 1)
  const t2 = props.objects.filter(o => o.tier === 2)
  const t3 = props.objects.filter(o => o.tier === 3)
  const out: RNode[] = []
  const colSpacing = 200
  const place = (objs: OntologyClassDraft[], y: number, tier: 1 | 2 | 3, maxPerRow = 6) => {
    const rows = Math.max(1, Math.ceil(objs.length / maxPerRow))
    objs.forEach((o, i) => {
      const row = Math.floor(i / maxPerRow)
      const col = i % maxPerRow
      const itemsInRow = row === rows - 1 ? (objs.length - row * maxPerRow) : maxPerRow
      const startX = -(itemsInRow - 1) * colSpacing / 2 + 700
      out.push({
        id: o.id,
        label: o.displayName,
        icon: o.icon || '',
        count: o.instanceCount || 0,
        tier,
        x: startX + col * colSpacing,
        y: y + (row - (rows - 1) / 2) * 60,
        w: Math.max(140, o.displayName.length * 16 + 36),
        color: tierColor[tier],
      })
    })
  }
  place(t1, bands.t1.centerY, 1)
  place(t2, bands.t2.centerY, 2)
  place(t3, bands.t3.centerY, 3)
  return out
})

const nodeMap = computed(() => {
  const m = new Map<string, RNode>()
  for (const n of renderedNodes.value) m.set(n.id, n)
  return m
})

const renderedLinks = computed(() => {
  return props.relations.map((r, i) => {
    const s = nodeMap.value.get(r.source) || nodeMap.value.get(findNodeIdByName(r.source))
    const t = nodeMap.value.get(r.target) || nodeMap.value.get(findNodeIdByName(r.target))
    if (!s || !t) return null
    const dx = t.x - s.x; const dy = t.y - s.y
    const len = Math.hypot(dx, dy) || 1
    const ux = dx / len; const uy = dy / len
    const sx = s.x + ux * (s.w / 2); const sy = s.y + uy * 22
    const tx = t.x - ux * (t.w / 2 + 8); const ty = t.y - uy * 22
    return {
      id: `${r.source}-${r.target}-${i}`,
      source: r.source, target: r.target,
      path: `M ${sx} ${sy} L ${tx} ${ty}`,
      midX: (sx + tx) / 2, midY: (sy + ty) / 2,
      label: r.displayName,
      cross: s.tier !== t.tier,
    }
  }).filter((x): x is NonNullable<typeof x> => x !== null)
})

function findNodeIdByName(nameOrId: string) {
  const o = props.objects.find(o => o.name === nameOrId || o.id === nameOrId)
  return o?.id || nameOrId
}

function onNodeClick(id: string) {
  selected.value = selected.value === id ? null : id
}
const selectedNode = computed(() => selected.value ? renderedNodes.value.find(n => n.id === selected.value) : null)
</script>

<style scoped>
.canvas-wrap { display: flex; flex-direction: column; flex: 1; min-height: 0; background: #fafbfd; overflow: hidden; }
.bubble-canvas-wrap { flex: 1; min-height: 0; padding: 4px 8px; position: relative; }
.bubble-canvas-svg { width: 100%; height: 100%; display: block; cursor: grab; }
.bubble-canvas-svg:active { cursor: grabbing; }
.bub-band-label { font-size: 16px; font-weight: 700; letter-spacing: 2px; opacity: 0.6; pointer-events: none; }
.bub-link-label { font-size: 9px; fill: #64748b; font-family: monospace; pointer-events: none; opacity: 0.85; }
.bub-node { cursor: pointer; }
.bub-node:hover rect { stroke-width: 2.4; }
.bub-node--selected rect { stroke-width: 3; filter: drop-shadow(0 0 4px rgba(99,102,241,0.5)); }
.bub-node-label { font-size: 13px; font-weight: 700; pointer-events: none; }
.bub-node-en { font-size: 9px; fill: #94a3b8; pointer-events: none; }
.bub-controls {
  position: absolute; bottom: 16px; right: 16px;
  display: flex; flex-direction: column; gap: 4px;
  background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.bub-ctrl {
  width: 32px; height: 32px; border: 0; background: transparent;
  cursor: pointer; font-size: 14px; color: #475569; border-radius: 4px; font-weight: 700;
}
.bub-ctrl:hover { background: #f1f5f9; }
.bub-ctrl:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
