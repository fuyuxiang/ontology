<template>
  <div class="screen-wrapper" ref="wrapperRef">
    <!-- 背景 -->
    <img class="screen-bg" src="/images/ontology/bg.png" alt="" />
    <img class="border-left" src="/images/ontology/left.png" alt="" />
    <img class="border-right" src="/images/ontology/right.png" alt="" />
    <img class="screen-title" src="/images/ontology/dh.png" alt="" />
    <img class="screen-bottom" src="/images/ontology/bottom.png" alt="" />

    <!-- 主内容（可拖拽缩放） -->
    <div class="content" :style="contentTransform">
      <!-- ═══ 顶部能力层 ═══ -->
      <div class="row row-top">
        <CapabilityCard v-for="card in topCards" :key="card.title" v-bind="card" />
      </div>

      <!-- ═══ 中间本体层 ═══ -->
      <div class="onto-layer">
        <img class="onto-layer__bg" src="/images/ontology/bg-本体层.png" alt="" />

        <!-- SVG 连线层 -->
        <svg class="onto-layer__svg" :viewBox="`0 0 ${svgW} ${svgH}`" preserveAspectRatio="none">
          <defs>
            <filter id="particle-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2.5" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
          <g v-for="link in svgLinks" :key="link.id">
            <path :id="'lp-'+link.id" :d="link.path" fill="none" stroke="none" />
            <path :d="link.path" fill="none" :stroke="link.color" stroke-width="0.5" stroke-dasharray="5 3" opacity="0.55" />
            <circle v-for="p in 3" :key="p" :r="1.5" :fill="link.particleColor" filter="url(#particle-glow)">
              <animateMotion :dur="link.dur+'s'" :begin="(-p * link.dur / 3)+'s'" repeatCount="indefinite">
                <mpath :href="'#lp-'+link.id" />
              </animateMotion>
              <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.9;1" :dur="link.dur+'s'" :begin="(-p * link.dur / 3)+'s'" repeatCount="indefinite" />
            </circle>
          </g>
        </svg>

        <!-- 本体节点区域 -->
        <div class="onto-zones">
          <!-- 域本体区域 -->
          <div v-for="(zone, zi) in domainZones" :key="'dz-'+zi" class="onto-zone" :style="zone.style">
            <div class="platform-rows-wrapper" :style="zone.gridStyle">
              <div v-for="(row, ri) in zone.rows" :key="ri" class="platform-row" :class="{ 'platform-row--offset': ri % 2 === 1 }">
                <div v-for="node in row" :key="node.id" class="platform-item"
                  @click="onNodeClick(node)" @mouseenter="hoveredNode = node" @mouseleave="hoveredNode = null">
                  <img class="platform-icon" :src="node.icon" :alt="node.label" />
                </div>
              </div>
            </div>
          </div>

          <!-- 核心本体区域（中央） -->
          <div class="onto-zone onto-zone--core" :style="coreZone.style">
            <div class="platform-rows-wrapper" :style="coreZone.gridStyle">
              <div class="platform-row">
                <div v-for="node in coreNodes" :key="node.id" class="platform-item platform-item--core"
                  @click="onNodeClick(node)" @mouseenter="hoveredNode = node" @mouseleave="hoveredNode = null">
                  <img class="platform-icon platform-icon--core" :src="node.icon" :alt="node.label" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ 底部数据层 ═══ -->
      <div class="row row-bottom">
        <CapabilityCard v-for="card in bottomCards" :key="card.title" v-bind="card" />
      </div>
    </div>

    <!-- 底部控制 -->
    <div class="bottom-controls">
      <button class="bottom-btn" @click="resetView"><img src="/images/ontology/btn-重置视角.png" alt="重置" /></button>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import CapabilityCard from '../../components/dashboard/panels/CapabilityCard.vue'
import NodeDetailPanel from '../../components/dashboard/panels/NodeDetailPanel.vue'
import { dashboardApi } from '../../api/dashboard'
import type { DashboardStatsEx } from '../../api/dashboard'
import { entityApi } from '../../api/ontology'
import { relationApi } from '../../api/relations'
import type { EntityListItem } from '../../types'
import type { RelationData } from '../../api/relations'

const router = useRouter()

/* ── Data ── */
const stats = ref<DashboardStatsEx | null>(null)
const entities = ref<EntityListItem[]>([])
const relations = ref<RelationData[]>([])
const hoveredNode = ref<OntologyNode | null>(null)
const selectedNode = ref<OntologyNode | null>(null)

interface OntologyNode {
  id: string; label: string; desc: string; icon: string
  tier: number; status: string
  relationCount: number; ruleCount: number; attrCount: number; actionCount: number
  isCore: boolean
}

onMounted(async () => {
  const [s, e, r] = await Promise.all([
    dashboardApi.stats().catch(() => null),
    entityApi.list().catch(() => []),
    relationApi.list().catch(() => []),
  ])
  stats.value = s as any
  entities.value = e as EntityListItem[]
  relations.value = r as RelationData[]
})

/* ── Icon mapping ── */
const coreNames = new Set(['Customer', 'Order', 'Product', 'Channel', 'Organization', 'Staff', 'Address'])
const iconMap: Record<string, string> = {
  Customer: '/images/ontology/icon-客户.png',
  Order: '/images/ontology/icon-订单.png',
  Product: '/images/ontology/icon-产品.png',
  Address: '/images/ontology/icon-地址.png',
  Channel: '/images/ontology/icon-渠道.png',
  Staff: '/images/ontology/icon-员工.png',
  Organization: '/images/ontology/icon-组织.png',
  InstallOrder: '/images/ontology/icon-订单.png',
  InstallChurn: '/images/ontology/icon-域本体.png',
  Engineer: '/images/ontology/icon-员工.png',
}

function toNode(e: EntityListItem): OntologyNode {
  const isCore = coreNames.has(e.name) || e.tier === 1 || e.tier === 2
  return {
    id: e.id,
    label: e.name_cn || e.name,
    desc: `${e.name} · Tier ${e.tier}`,
    icon: iconMap[e.name] || (isCore ? '/images/ontology/icon-核心本体.png' : '/images/ontology/icon-域本体.png'),
    tier: e.tier,
    status: e.status,
    relationCount: e.relation_count,
    ruleCount: e.rule_count,
    attrCount: e.attr_count ?? 0,
    actionCount: e.action_count ?? 0,
    isCore,
  }
}

/* ── Node layout ── */
const coreNodes = computed(() => entities.value.filter(e => coreNames.has(e.name) || e.tier === 1).map(toNode))
const domainNodes = computed(() => entities.value.filter(e => !coreNames.has(e.name) && e.tier !== 1).map(toNode))

// Split domain nodes into zones (up to 5 zones with trapezoid layout)
const domainZones = computed(() => {
  const nodes = domainNodes.value
  if (!nodes.length) return []
  const perZone = Math.ceil(nodes.length / Math.min(5, Math.max(1, Math.ceil(nodes.length / 4))))
  const zones: { style: Record<string, string>; gridStyle: Record<string, string>; rows: OntologyNode[][] }[] = []

  // Zone positions (percentage-based trapezoid layout)
  const zonePositions = [
    { left: '5%', top: '16%', width: '22%', height: '42%' },
    { left: '28%', top: '15%', width: '21%', height: '17%' },
    { left: '51%', top: '15%', width: '21%', height: '17%' },
    { left: '70%', top: '16%', width: '25%', height: '42%' },
    { left: '19%', top: '35%', width: '62%', height: '25%' },
  ]

  for (let i = 0; i < Math.min(5, Math.ceil(nodes.length / perZone)); i++) {
    const chunk = nodes.slice(i * perZone, (i + 1) * perZone)
    if (!chunk.length) break
    const cols = Math.min(chunk.length, i === 4 ? 5 : 3)
    const row1 = chunk.slice(0, cols)
    const row2 = chunk.slice(cols)
    zones.push({
      style: zonePositions[i] || zonePositions[0],
      gridStyle: { '--cols': String(cols), '--item-width': `${100 / cols}%` },
      rows: row2.length ? [row1, row2] : [row1],
    })
  }
  return zones
})

const coreZone = computed(() => {
  const n = coreNodes.value.length || 1
  return {
    style: { left: '26%', bottom: '5%', width: '48%', height: '30%' },
    gridStyle: { '--cols': String(n), '--item-width': `${100 / n}%` },
  }
})

/* ── SVG connections ── */
const svgW = 1920
const svgH = 600

const svgLinks = computed(() => {
  const nodeMap = new Map<string, OntologyNode>()
  for (const n of [...coreNodes.value, ...domainNodes.value]) nodeMap.set(n.id, n)

  // Simple layout: assign approximate positions based on index
  const allNodes = [...coreNodes.value, ...domainNodes.value]
  const posMap = new Map<string, { x: number; y: number }>()
  allNodes.forEach((n, i) => {
    if (n.isCore) {
      const ci = coreNodes.value.indexOf(n)
      const cx = svgW * 0.3 + (ci / Math.max(1, coreNodes.value.length - 1)) * svgW * 0.4
      posMap.set(n.id, { x: cx, y: svgH * 0.8 })
    } else {
      const di = domainNodes.value.indexOf(n)
      const total = domainNodes.value.length
      const angle = (di / total) * Math.PI + Math.PI * 0.1
      posMap.set(n.id, {
        x: svgW * 0.5 + Math.cos(angle) * svgW * 0.35,
        y: svgH * 0.15 + Math.sin(angle) * svgH * 0.45,
      })
    }
  })

  const linkColors: Record<string, { color: string; particleColor: string }> = {
    'core-core': { color: '#0050EA', particleColor: '#4a9ff5' },
    'core-domain': { color: '#6592EA', particleColor: '#7ab0ff' },
    'domain-domain': { color: '#C2D0EA', particleColor: '#a0b8e0' },
  }

  return relations.value
    .filter(r => posMap.has(r.from_entity_id) && posMap.has(r.to_entity_id))
    .map((r, idx) => {
      const f = posMap.get(r.from_entity_id)!
      const t = posMap.get(r.to_entity_id)!
      const fromCore = nodeMap.get(r.from_entity_id)?.isCore
      const toCore = nodeMap.get(r.to_entity_id)?.isCore
      const type = fromCore && toCore ? 'core-core' : (fromCore || toCore) ? 'core-domain' : 'domain-domain'
      const lc = linkColors[type]
      const dx = t.x - f.x, dy = t.y - f.y
      const path = `M${f.x},${f.y} C${f.x + dx * 0.05},${f.y + dy * 0.3} ${t.x - dx * 0.05},${t.y - dy * 0.3} ${t.x},${t.y}`
      return { id: r.id, path, color: lc.color, particleColor: lc.particleColor, dur: 1.8 + (idx % 5) * 0.15 }
    })
})

const nodeRelations = computed(() => {
  if (!selectedNode.value) return []
  const id = selectedNode.value.id
  return relations.value.filter(r => r.from_entity_id === id || r.to_entity_id === id)
})

/* ── Drag & zoom ── */
const wrapperRef = ref<HTMLElement | null>(null)
const scale = ref(1)
const ox = ref(0)
const oy = ref(0)

const contentTransform = computed(() => ({
  transform: `translate(${ox.value}px, ${oy.value}px) scale(${scale.value})`,
  transformOrigin: 'center center',
}))

function resetView() { scale.value = 1; ox.value = 0; oy.value = 0 }

function onWheel(e: WheelEvent) {
  e.preventDefault()
  const delta = e.deltaY > 0 ? 0.95 : 1.05
  scale.value = Math.max(0.4, Math.min(2.5, scale.value * delta))
}

let dragging = false
let dragStart = { x: 0, y: 0 }

function onMouseDown(e: MouseEvent) {
  if (e.button !== 0) return
  dragging = true
  dragStart = { x: e.clientX - ox.value, y: e.clientY - oy.value }
}
function onMouseMove(e: MouseEvent) {
  if (!dragging) return
  ox.value = e.clientX - dragStart.x
  oy.value = e.clientY - dragStart.y
}
function onMouseUp() { dragging = false }

onMounted(() => {
  const el = wrapperRef.value
  if (el) {
    el.addEventListener('wheel', onWheel, { passive: false })
    el.addEventListener('mousedown', onMouseDown)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  }
})
onBeforeUnmount(() => {
  const el = wrapperRef.value
  if (el) {
    el.removeEventListener('wheel', onWheel)
    el.removeEventListener('mousedown', onMouseDown)
  }
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
})

function onNodeClick(node: OntologyNode) {
  selectedNode.value = node
}

/* ── Top & Bottom cards ── */
const topCards = computed(() => [
  {
    title: '',
    bg: '/images/ontology/bg-ANALYTICS &WORKFLOWS.png',
    flex: 479,
    items: [],
  },
  {
    title: '',
    bg: '/images/ontology/bg-AUTOMATIONS.png',
    flex: 537,
    items: [],
  },
  {
    title: '',
    bg: '/images/ontology/bg-PRODUCTS & SDKs.png',
    flex: 470,
    items: [],
  },
])

const bottomCards = computed(() => {
  return [
    {
      title: '',
      bg: '/images/ontology/bg-DATA SOURCES.png',
      icon: '/images/ontology/icon-DATA SOURCES.png',
      flex: 514,
      items: [],
    },
    {
      title: '',
      bg: '/images/ontology/bg-LOGIC SOURCES.png',
      icon: '/images/ontology/icon-LOGIC SOURCES.png',
      flex: 514,
      items: [],
    },
    {
      title: '',
      bg: '/images/ontology/bg-SYSTEMS OF ACTION.png',
      icon: '/images/ontology/icon-SYSTEMS OF ACTION.png',
      flex: 441,
      items: [],
    },
  ]
})
</script>

<style scoped>
@font-face {
  font-family: AlimamaFangYuanTiVF-Regular;
  src: url(/fonts/AlimamaFangYuanTiVF-Thin.ttf) format('truetype');
  font-weight: 400;
}

.screen-wrapper {
  width: 100%; height: 100%; min-height: 720px;
  position: relative; overflow: hidden; background: #0a0e1a;
  cursor: grab;
}
.screen-wrapper:active { cursor: grabbing; }

.screen-bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; }
.border-left { position: absolute; top: 0; left: 0; width: 48%; height: 100%; object-fit: fill; z-index: 10; pointer-events: none; padding-bottom: 10px; }
.border-right { position: absolute; top: 0; right: 0; width: 48%; height: 100%; object-fit: fill; z-index: 10; pointer-events: none; padding-bottom: 10px; }
.screen-title { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 46.15%; height: auto; z-index: 20; pointer-events: none; }
.screen-bottom { position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); width: 31.25%; height: auto; z-index: 20; pointer-events: none; }

.content {
  position: relative; z-index: 5;
  display: flex; flex-direction: column;
  width: 100%; height: 100%;
  padding: 10.1vw 60px 40px;
  box-sizing: border-box;
  transition: transform 0.05s linear;
}

.row { display: flex; justify-content: space-between; align-items: center; gap: 16px; width: 100%; }
.row-top { align-items: flex-end; }
.row-bottom { margin-top: -8.33vw; }

/* ── 本体层 ── */
.onto-layer {
  position: relative; width: 96.15vw; margin: 0 auto;
  flex: 1; min-height: 300px;
}
.onto-layer__bg { width: 100%; height: auto; display: block; }
.onto-layer__svg {
  position: absolute; inset: 0; width: 100%; height: 100%;
  pointer-events: none; z-index: 1;
}
.onto-zones { position: absolute; inset: 0; z-index: 2; }

.onto-zone { position: absolute; z-index: 6; }
.onto-zone--core { z-index: 7; }

.platform-rows-wrapper {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  display: flex; flex-direction: column; align-items: center;
  width: 100%;
}
.platform-row { display: flex; justify-content: center; }
.platform-row--offset { margin-left: 0; }

.platform-item {
  display: flex; flex-direction: column; align-items: center;
  padding: 0 4px; cursor: pointer; position: relative;
  transition: opacity .15s, filter .15s, transform .15s;
  user-select: none; z-index: 1;
  width: 80px;
}
.platform-item:hover {
  z-index: 200;
  filter: brightness(1.05) drop-shadow(0 2px 8px rgba(0, 50, 145, 0.25));
  transform: scale(1.06);
}
.platform-item--core { width: 90px; }

.platform-icon {
  width: 50px; height: auto; flex-shrink: 0;
}
.platform-icon--core { width: 65px; }

.platform-label {
  color: #003291;
  text-align: center; white-space: nowrap;
  font-family: AlimamaFangYuanTiVF-Regular, sans-serif;
  font-size: 0.625vw; font-weight: 400;
  letter-spacing: 0;
  background: url(/images/ontology/label-bg.png) center / 100% 100% no-repeat;
  padding: 0.1vw 0.42vw;
  border-radius: 0;
  position: absolute; bottom: 0; left: 50%;
  transform: translateX(-50%);
}

/* ── Tooltip ── */
.platform-tooltip {
  position: absolute; bottom: calc(100% + 6px); left: 50%;
  transform: translateX(-50%) translateY(4px);
  pointer-events: none; white-space: nowrap; z-index: 9999;
  opacity: 0; visibility: hidden;
  background: rgba(0, 18, 68, 0.92);
  border: 1px solid rgba(0, 80, 234, 0.5);
  border-radius: 0.21vw;
  min-width: 8.33vw; max-width: 16.67vw;
  padding: 0.42vw 0.63vw;
  transition: opacity .15s, transform .15s, visibility .15s;
}
.platform-item:hover .platform-tooltip {
  opacity: 1; visibility: visible;
  transform: translateX(-50%) translateY(0);
}
.platform-tooltip-name { color: #e8f0ff; font-size: 0.68vw; font-weight: 600; margin-bottom: 0.21vw; }
.platform-tooltip-desc { color: rgba(200, 220, 255, 0.75); font-size: 0.57vw; line-height: 1.5; white-space: normal; margin-bottom: 0.21vw; }
.platform-tooltip-row { color: rgba(200, 220, 255, 0.85); font-size: 0.57vw; line-height: 1.6; white-space: nowrap; }

/* ── 底部控制 ── */
.bottom-controls {
  position: absolute; bottom: 5px; left: 50%; transform: translateX(-50%);
  z-index: 999; display: flex; align-items: center; gap: 0.63vw;
}
.bottom-btn {
  cursor: pointer; background: transparent; border: none;
  display: flex; align-items: center; padding: 0;
}
.bottom-btn img { width: auto; height: 2.78vh; display: block; }
.bottom-btn:hover { filter: brightness(1.2); }
</style>
