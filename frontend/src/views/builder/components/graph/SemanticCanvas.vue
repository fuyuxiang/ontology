<template>
  <div class="canvas-wrap">
    <div class="graph-canvas-wrap">
      <svg
        ref="svgRef"
        class="graph-canvas-svg"
        :viewBox="viewBox"
        preserveAspectRatio="xMidYMid meet"
        @wheel.prevent="onWheel"
        @mousedown="onBgMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @mouseleave="onMouseUp"
      >
        <defs>
          <marker id="graphArrow" viewBox="-10 -5 10 10" refX="0" refY="0" orient="auto" markerWidth="8" markerHeight="8">
            <path d="M -10 -5 L 0 0 L -10 5 Z" fill="#64748b" />
          </marker>
          <filter id="graph-shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.10" />
          </filter>
        </defs>

        <rect :x="vx" :y="vy" :width="vw" :height="vh" fill="#fafbfd" />

        <!-- edges -->
        <g>
          <g v-for="link in renderedLinks" :key="link.id">
            <path
              :d="link.path"
              fill="none"
              stroke="#94a3b8"
              stroke-width="1.4"
              stroke-opacity="0.7"
              marker-end="url(#graphArrow)"
            />
            <text :x="link.midX" :y="link.midY - 5" class="graph-link-label" text-anchor="middle">{{ link.label }}</text>
          </g>
        </g>

        <!-- nodes -->
        <g>
          <g
            v-for="n in layoutNodes"
            :key="n.id"
            :transform="`translate(${n.x},${n.y})`"
            class="graph-node"
            :class="{ 'graph-node--selected': selected === n.id }"
            @mousedown.stop="onNodeMouseDown($event, n.id)"
            @click.stop="onNodeClick(n.id)"
          >
            <circle
              :r="n.r"
              :fill="n.color + '18'"
              :stroke="n.color"
              stroke-width="2"
              filter="url(#graph-shadow)"
            />
            <text x="0" :y="1" text-anchor="middle" class="graph-node-label" :fill="n.color">{{ n.icon }} {{ n.label }}</text>
            <text x="0" :y="n.r + 14" text-anchor="middle" class="graph-node-sub">{{ n.count }} 实例</text>
          </g>
        </g>
      </svg>

      <div class="graph-controls">
        <button class="graph-ctrl" @click="zoomBy(1.2)">＋</button>
        <button class="graph-ctrl" @click="zoomBy(1 / 1.2)">－</button>
        <button class="graph-ctrl" @click="resetView">⤾</button>
        <button class="graph-ctrl" :disabled="!editable" @click="$emit('add')" title="新增对象">＋⊕</button>
      </div>
    </div>

    <div v-if="selected && editable" class="canvas-divider"><span>选中：{{ selectedNode?.label }}（点击空白取消选中）</span></div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import type { OntologyObjectDraft, OntologyRelationDraft, Step1Phase } from '../../../../types/builder'

const props = defineProps<{
  objects: OntologyObjectDraft[]
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

const nodeColors = ['#2E5BFF', '#00C7B1', '#FF6B35', '#7C3AED', '#EC4899', '#F59E0B']

const svgRef = ref<SVGSVGElement | null>(null)
const selected = ref<string | null>(null)

const vx = ref(-400)
const vy = ref(-300)
const vw = ref(800)
const vh = ref(600)
const viewBox = computed(() => `${vx.value} ${vy.value} ${vw.value} ${vh.value}`)

interface LayoutNode { id: string; label: string; icon: string; count: number; x: number; y: number; r: number; color: string; vx: number; vy: number }

const layoutNodes = ref<LayoutNode[]>([])
let simRunning = false
let animFrame = 0
let draggingNodeId: string | null = null
let dragOffset = { x: 0, y: 0 }

function initLayout() {
  const nodes: LayoutNode[] = props.objects.map((o, i) => {
    const angle = (2 * Math.PI * i) / Math.max(props.objects.length, 1)
    const radius = Math.min(200, props.objects.length * 30)
    return {
      id: o.id,
      label: o.displayName,
      icon: o.icon || '',
      count: o.instanceCount || 0,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      r: Math.max(32, Math.min(50, 28 + (o.properties?.length || 0) * 2)),
      color: nodeColors[i % nodeColors.length],
      vx: 0, vy: 0,
    }
  })
  layoutNodes.value = nodes
  simRunning = true
  runSimulation()
}

function runSimulation() {
  const alpha = 0.3
  const repulsion = 8000
  const linkDist = 180
  const linkStrength = 0.05
  const centerStrength = 0.01
  let iterations = 0
  const maxIter = 300

  function tick() {
    if (!simRunning || iterations > maxIter) { simRunning = false; return }
    iterations++
    const nodes = layoutNodes.value

    for (const n of nodes) {
      n.vx += -n.x * centerStrength
      n.vy += -n.y * centerStrength
    }

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[j].x - nodes[i].x
        const dy = nodes[j].y - nodes[i].y
        const dist = Math.max(Math.hypot(dx, dy), 1)
        const force = repulsion / (dist * dist)
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        nodes[i].vx -= fx; nodes[i].vy -= fy
        nodes[j].vx += fx; nodes[j].vy += fy
      }
    }

    const nodeIndex = new Map(nodes.map((n, i) => [n.id, i]))
    for (const rel of props.relations) {
      const si = nodeIndex.get(rel.source) ?? nodeIndex.get(findNodeIdByName(rel.source))
      const ti = nodeIndex.get(rel.target) ?? nodeIndex.get(findNodeIdByName(rel.target))
      if (si === undefined || ti === undefined) continue
      const s = nodes[si]; const t = nodes[ti]
      const dx = t.x - s.x; const dy = t.y - s.y
      const dist = Math.max(Math.hypot(dx, dy), 1)
      const force = (dist - linkDist) * linkStrength
      const fx = (dx / dist) * force; const fy = (dy / dist) * force
      s.vx += fx; s.vy += fy
      t.vx -= fx; t.vy -= fy
    }

    for (const n of nodes) {
      if (n.id === draggingNodeId) { n.vx = 0; n.vy = 0; continue }
      n.vx *= alpha; n.vy *= alpha
      n.x += n.vx; n.y += n.vy
    }

    layoutNodes.value = [...nodes]
    animFrame = requestAnimationFrame(tick)
  }

  animFrame = requestAnimationFrame(tick)
}

watch(() => props.objects, initLayout, { deep: true })
onMounted(initLayout)
onUnmounted(() => { simRunning = false; cancelAnimationFrame(animFrame) })

const renderedLinks = computed(() => {
  const nodeMap = new Map(layoutNodes.value.map(n => [n.id, n]))
  return props.relations.map((r, i) => {
    const s = nodeMap.get(r.source) || nodeMap.get(findNodeIdByName(r.source))
    const t = nodeMap.get(r.target) || nodeMap.get(findNodeIdByName(r.target))
    if (!s || !t) return null
    const dx = t.x - s.x; const dy = t.y - s.y
    const dist = Math.max(Math.hypot(dx, dy), 1)
    const ux = dx / dist; const uy = dy / dist
    const sx = s.x + ux * s.r; const sy = s.y + uy * s.r
    const tx = t.x - ux * (t.r + 8); const ty = t.y - uy * (t.r + 8)
    return {
      id: `${r.source}-${r.target}-${i}`,
      path: `M ${sx} ${sy} L ${tx} ${ty}`,
      midX: (sx + tx) / 2, midY: (sy + ty) / 2,
      label: r.displayName,
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
const selectedNode = computed(() => selected.value ? layoutNodes.value.find(n => n.id === selected.value) : null)

let panStart: { x: number; y: number; vx: number; vy: number } | null = null
function onBgMouseDown(e: MouseEvent) {
  if ((e.target as Element).closest('.graph-node')) return
  panStart = { x: e.clientX, y: e.clientY, vx: vx.value, vy: vy.value }
  selected.value = null
}
function onNodeMouseDown(e: MouseEvent, id: string) {
  draggingNodeId = id
  const node = layoutNodes.value.find(n => n.id === id)
  if (!node || !svgRef.value) return
  const rect = svgRef.value.getBoundingClientRect()
  const scale = vw.value / rect.width
  dragOffset = { x: e.clientX * scale + vx.value - node.x, y: e.clientY * scale + vy.value - node.y }
}
function onMouseMove(e: MouseEvent) {
  if (!svgRef.value) return
  const rect = svgRef.value.getBoundingClientRect()
  const scale = vw.value / rect.width
  if (draggingNodeId) {
    const node = layoutNodes.value.find(n => n.id === draggingNodeId)
    if (node) {
      node.x = e.clientX * scale + vx.value - dragOffset.x
      node.y = e.clientY * scale + vy.value - dragOffset.y
      layoutNodes.value = [...layoutNodes.value]
    }
  } else if (panStart) {
    vx.value = panStart.vx - (e.clientX - panStart.x) * scale
    vy.value = panStart.vy - (e.clientY - panStart.y) * scale
  }
}
function onMouseUp() { panStart = null; draggingNodeId = null }
function onWheel(e: WheelEvent) { zoomBy(e.deltaY < 0 ? 1.1 : 1 / 1.1) }
function zoomBy(factor: number) {
  const newW = vw.value / factor; const newH = vh.value / factor
  vx.value += (vw.value - newW) / 2; vy.value += (vh.value - newH) / 2
  vw.value = newW; vh.value = newH
}
function resetView() { vx.value = -400; vy.value = -300; vw.value = 800; vh.value = 600 }
</script>

<style scoped>
.canvas-wrap { display: flex; flex-direction: column; flex: 1; min-height: 0; background: #fafbfd; overflow: hidden; }
.graph-canvas-wrap { flex: 1; min-height: 0; padding: 4px 8px; position: relative; }
.graph-canvas-svg { width: 100%; height: 100%; display: block; cursor: grab; }
.graph-canvas-svg:active { cursor: grabbing; }
.graph-link-label { font-size: 10px; fill: #64748b; font-family: monospace; pointer-events: none; }
.graph-node { cursor: pointer; }
.graph-node:hover circle { stroke-width: 3; }
.graph-node--selected circle { stroke-width: 3.5; filter: drop-shadow(0 0 6px rgba(99,102,241,0.5)); }
.graph-node-label { font-size: 12px; font-weight: 600; pointer-events: none; }
.graph-node-sub { font-size: 9px; fill: #94a3b8; pointer-events: none; }
.graph-controls {
  position: absolute; bottom: 16px; right: 16px;
  display: flex; flex-direction: column; gap: 4px;
  background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.graph-ctrl {
  width: 32px; height: 32px; border: 0; background: transparent;
  cursor: pointer; font-size: 14px; color: #475569; border-radius: 4px; font-weight: 700;
}
.graph-ctrl:hover { background: #f1f5f9; }
.graph-ctrl:disabled { opacity: 0.4; cursor: not-allowed; }
.canvas-divider { padding: 6px 12px; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; background: #fff; }
</style>
