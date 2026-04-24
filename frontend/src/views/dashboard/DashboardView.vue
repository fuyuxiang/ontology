<template>
  <div class="screen-wrapper" ref="wrapperRef">
    <!-- 背景 -->
    <img class="screen-bg" src="/images/ontology/bg.png" alt="" />
    <img class="screen-bottom" src="/images/ontology/bottom.png" alt="" />

    <!-- 主内容（可拖拽缩放） -->
    <div class="content" ref="contentRef" :style="contentTransform">
      <!-- ═══ 跨层数据流线 ═══ -->
      <svg class="cross-layer-svg" :viewBox="`0 0 ${crossSvgW} ${crossSvgH}`" preserveAspectRatio="none">
        <defs>
          <filter id="cl-particle-glow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="4" result="blur1" />
            <feGaussianBlur stdDeviation="1.5" in="SourceGraphic" result="blur2" />
            <feMerge><feMergeNode in="blur1" /><feMergeNode in="blur1" /><feMergeNode in="blur2" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="cl-line-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <g v-for="link in crossLayerLinks" :key="link.id" class="onto-link cl-link">
          <path :id="'cl-'+link.id" :d="link.path" fill="none" stroke="none" />
          <path class="onto-link__line cl-line" :d="link.path" fill="none" :stroke="link.color" stroke-width="1.2" stroke-opacity="0.2" filter="url(#cl-line-glow)" />
          <path class="onto-link__line-dash" :d="link.path" fill="none" :stroke="link.color" stroke-width="0.7" stroke-dasharray="8 6" stroke-opacity="0.45">
            <animate attributeName="stroke-dashoffset" from="0" to="28" :dur="(link.dur * 0.8)+'s'" repeatCount="indefinite" />
          </path>
          <circle v-for="p in link.particles" :key="p" class="onto-link__particle cl-particle" :r="link.rArr[p-1]" :fill="link.particleColor" filter="url(#cl-particle-glow)">
            <animateMotion :dur="link.dur+'s'" :begin="(-p * link.dur / link.particles)+'s'" repeatCount="indefinite" calcMode="spline" keyPoints="0;1" keyTimes="0;1" keySplines="0.4 0 0.6 1">
              <mpath :href="'#cl-'+link.id" />
            </animateMotion>
            <animate attributeName="opacity" values="0;0.6;1;1;0.6;0" keyTimes="0;0.08;0.25;0.75;0.92;1" :dur="link.dur+'s'" :begin="(-p * link.dur / link.particles)+'s'" repeatCount="indefinite" />
            <animate attributeName="r" :values="`${link.rArr[p-1]*0.6};${link.rArr[p-1]};${link.rArr[p-1]*1.2};${link.rArr[p-1]};${link.rArr[p-1]*0.6}`" keyTimes="0;0.2;0.5;0.8;1" :dur="link.dur+'s'" :begin="(-p * link.dur / link.particles)+'s'" repeatCount="indefinite" />
          </circle>
        </g>
      </svg>

      <!-- ═══ 顶部能力层 ═══ -->
      <div class="row row-top">
        <CapabilityCard v-for="card in topCards" :key="card.title" v-bind="card" :card-key="card.key" />
      </div>

      <!-- ═══ 中间本体层 ═══ -->
      <div class="onto-layer" ref="ontoLayerRef">
        <img class="onto-layer__bg" src="/images/ontology/bg-本体层.png" alt="" />

        <!-- SVG 连线层 -->
        <svg class="onto-layer__svg" :viewBox="`0 0 ${svgW} ${svgH}`" preserveAspectRatio="none">
          <defs>
            <filter id="particle-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <filter id="line-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="1.5" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
          <g v-for="link in svgLinks" :key="link.id" class="onto-link" :class="linkHighlightClass(link)">
            <path :id="'lp-'+link.id" :d="link.path" fill="none" stroke="none" />
            <path class="onto-link__line" :d="link.path" fill="none" :stroke="link.color" stroke-width="1" stroke-opacity="0.35" filter="url(#line-glow)" />
            <path class="onto-link__line-dash" :d="link.path" fill="none" :stroke="link.color" stroke-width="0.6" stroke-dasharray="6 4" stroke-opacity="0.6" />
            <circle v-for="p in 4" :key="p" class="onto-link__particle" :r="2" :fill="link.particleColor" filter="url(#particle-glow)">
              <animateMotion :dur="link.dur+'s'" :begin="(-p * link.dur / 4)+'s'" repeatCount="indefinite">
                <mpath :href="'#lp-'+link.id" />
              </animateMotion>
              <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.9;1" :dur="link.dur+'s'" :begin="(-p * link.dur / 4)+'s'" repeatCount="indefinite" />
            </circle>
          </g>
        </svg>

        <!-- 本体节点区域 -->
        <div class="onto-zones">
          <!-- 域本体区域 -->
          <div v-for="(zone, zi) in domainZones" :key="'dz-'+zi" class="onto-zone" :style="zone.style">
            <div class="platform-rows-wrapper" :style="zone.gridStyle">
              <div v-for="(row, ri) in zone.rows" :key="ri" class="platform-row" :class="{ 'platform-row--offset': ri % 2 === 1 }">
                <div v-for="node in row" :key="node.id" class="platform-item" :class="nodeHighlightClass(node)"
                  :data-node-id="node.id"
                  @click="onNodeClick(node)" @mouseenter="hoveredNode = node" @mouseleave="hoveredNode = null">
                  <img class="platform-icon" :src="node.icon" :alt="node.label" />
                  <span class="platform-label">{{ node.label }}</span>
                  <div class="platform-tooltip">
                    <div class="platform-tooltip-name">{{ node.label }}</div>
                    <div class="platform-tooltip-desc">{{ node.desc }}</div>
                    <div class="platform-tooltip-row">关系 {{ node.relationCount }} · 规则 {{ node.ruleCount }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 核心本体区域（中央） -->
          <div class="onto-zone onto-zone--core" :style="coreZone.style">
            <div class="platform-rows-wrapper" :style="coreZone.gridStyle">
              <div v-for="(row, ri) in coreRows" :key="'cr-'+ri" class="platform-row" :class="{ 'platform-row--offset': ri % 2 === 1 }">
                <div v-for="node in row" :key="node.id" class="platform-item platform-item--core" :class="nodeHighlightClass(node)"
                  :data-node-id="node.id"
                  @click="onNodeClick(node)" @mouseenter="hoveredNode = node" @mouseleave="hoveredNode = null">
                  <img class="platform-icon platform-icon--core" :src="node.icon" :alt="node.label" />
                  <span class="platform-label">{{ node.label }}</span>
                  <div class="platform-tooltip">
                    <div class="platform-tooltip-name">{{ node.label }}</div>
                    <div class="platform-tooltip-desc">{{ node.desc }}</div>
                    <div class="platform-tooltip-row">关系 {{ node.relationCount }} · 规则 {{ node.ruleCount }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ 底部数据层 ═══ -->
      <div class="row row-bottom">
        <CapabilityCard v-for="card in bottomCards" :key="card.title" v-bind="card" :card-key="card.key" />
      </div>
    </div>

    <!-- 底部控制 -->
    <div class="bottom-controls">
      <button class="bottom-btn config-btn" @click="showConfig = true" title="配置仪表盘">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="2.5" stroke="currentColor" stroke-width="1.5"/>
          <path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.22 4.22l1.42 1.42M14.36 14.36l1.42 1.42M4.22 15.78l1.42-1.42M14.36 5.64l1.42-1.42" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
    </div>

    <!-- 节点详情面板 -->
    <NodeDetailPanel v-if="selectedNode" :node="selectedNode" :relations="nodeRelations"
      @close="selectedNode = null"
      @updated="onNodeMutated"
      @created="onNodeMutated"
      @deleted="onNodeMutated" />

    <!-- 仪表盘配置抽屉 -->
    <DashboardConfigDrawer v-if="dashConfig" :visible="showConfig" :config="dashConfig"
      @close="showConfig = false" @saved="onConfigSaved" @reset-view="resetView" />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import CapabilityCard from '../../components/dashboard/panels/CapabilityCard.vue'
import NodeDetailPanel from '../../components/dashboard/panels/NodeDetailPanel.vue'
import DashboardConfigDrawer from '../../components/dashboard/panels/DashboardConfigDrawer.vue'
import { dashboardApi } from '../../api/dashboard'
import type { DashboardStatsEx, DashboardConfig } from '../../api/dashboard'
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
const dashConfig = ref<DashboardConfig | null>(null)
const showConfig = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | null = null

interface OntologyNode {
  id: string; label: string; desc: string; icon: string
  tier: number; status: string
  relationCount: number; ruleCount: number; attrCount: number; actionCount: number
  isCore: boolean
}

onMounted(async () => {
  const [s, e, r, cfg] = await Promise.all([
    dashboardApi.stats().catch(() => null),
    entityApi.list().catch(() => []),
    relationApi.list().catch(() => []),
    dashboardApi.getConfig().catch(() => null),
  ])
  stats.value = s as any
  entities.value = e as EntityListItem[]
  relations.value = r as RelationData[]
  dashConfig.value = cfg as any

  nextTick(recalcPositions)
  window.addEventListener('resize', recalcPositions)

  const interval = (cfg as any)?.refresh_interval ?? 30
  refreshTimer = setInterval(async () => {
    stats.value = await dashboardApi.stats().catch(() => stats.value) as any
  }, interval * 1000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  window.removeEventListener('resize', recalcPositions)
})

function onConfigSaved(cfg: DashboardConfig) {
  dashConfig.value = cfg
  if (refreshTimer) clearInterval(refreshTimer)
  refreshTimer = setInterval(async () => {
    stats.value = await dashboardApi.stats().catch(() => stats.value) as any
  }, cfg.refresh_interval * 1000)
}

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

function toBalancedRows<T>(items: T[], maxCols: number): T[][] {
  if (!items.length) return []
  const rowCount = Math.ceil(items.length / maxCols)
  const cols = Math.ceil(items.length / rowCount)
  const rows: T[][] = []
  for (let i = 0; i < items.length; i += cols) rows.push(items.slice(i, i + cols))
  return rows
}

const coreRows = computed(() => toBalancedRows(coreNodes.value, 4))

// Split domain nodes into zones (up to 5 zones with balanced multi-row layout)
const domainZones = computed(() => {
  const nodes = domainNodes.value
  if (!nodes.length) return []
  const zones: { style: Record<string, string>; gridStyle: Record<string, string>; rows: OntologyNode[][] }[] = []
  const zoneCount = Math.min(5, Math.max(1, Math.ceil(nodes.length / 4)))
  const perZone = Math.ceil(nodes.length / zoneCount)

  // Zone positions (percentage-based trapezoid layout)
  const zonePositions = [
    { style: { left: '6%', top: '29%', width: '23%', height: '39%' }, maxCols: 3, rowOffset: '0.35vw' },
    { style: { left: '27.5%', top: '28%', width: '21%', height: '22%' }, maxCols: 3, rowOffset: '0.45vw' },
    { style: { left: '50.5%', top: '28%', width: '21%', height: '22%' }, maxCols: 3, rowOffset: '0.45vw' },
    { style: { left: '70%', top: '29%', width: '22.5%', height: '39%' }, maxCols: 3, rowOffset: '-0.35vw' },
    { style: { left: '17.5%', top: '50%', width: '62.5%', height: '22%' }, maxCols: 6, rowOffset: '0.45vw' },
  ]

  for (let i = 0; i < zoneCount; i++) {
    const chunk = nodes.slice(i * perZone, (i + 1) * perZone)
    if (!chunk.length) break
    const zone = zonePositions[i] || zonePositions[0]
    const rows = toBalancedRows(chunk, zone.maxCols)
    const cols = Math.max(1, ...rows.map(row => row.length))
    zones.push({
      style: zone.style,
      gridStyle: {
        '--cols': String(cols),
        '--item-width': `${100 / cols}%`,
        '--row-gap': 'clamp(7px, 0.6vw, 13px)',
        '--col-gap': 'clamp(8px, 0.75vw, 15px)',
        '--row-offset': zone.rowOffset,
      },
      rows,
    })
  }
  return zones
})

const coreZone = computed(() => {
  const cols = Math.max(1, ...coreRows.value.map(row => row.length))
  return {
    style: { left: '23.5%', bottom: '10%', width: '52%', height: '29%' },
    gridStyle: {
      '--cols': String(cols),
      '--item-width': `${100 / cols}%`,
      '--row-gap': 'clamp(8px, 0.7vw, 15px)',
      '--col-gap': 'clamp(10px, 0.9vw, 18px)',
      '--row-offset': '0.45vw',
    },
  }
})

const visibleNodeIds = computed(() => new Set([...coreNodes.value, ...domainNodes.value].map(n => n.id)))

const highlightedNodeIds = computed(() => {
  const rootId = hoveredNode.value?.id
  if (!rootId) return new Set<string>()

  const validIds = visibleNodeIds.value
  const adjacency = new Map<string, Set<string>>()
  for (const id of validIds) adjacency.set(id, new Set())

  for (const r of relations.value) {
    if (!validIds.has(r.from_entity_id) || !validIds.has(r.to_entity_id)) continue
    adjacency.get(r.from_entity_id)?.add(r.to_entity_id)
    adjacency.get(r.to_entity_id)?.add(r.from_entity_id)
  }

  const related = new Set<string>([rootId])
  const queue = [rootId]
  while (queue.length) {
    const id = queue.shift()!
    for (const next of adjacency.get(id) ?? []) {
      if (related.has(next)) continue
      related.add(next)
      queue.push(next)
    }
  }
  return related
})

const isHoverFiltering = computed(() => !!hoveredNode.value)

function nodeHighlightClass(node: OntologyNode) {
  if (!isHoverFiltering.value) return {}
  const isRelated = highlightedNodeIds.value.has(node.id)
  return {
    'platform-item--focus': hoveredNode.value?.id === node.id,
    'platform-item--related': isRelated && hoveredNode.value?.id !== node.id,
    'platform-item--hidden': !isRelated,
  }
}

function linkHighlightClass(link: { highlighted: boolean }) {
  if (!isHoverFiltering.value) return {}
  return {
    'onto-link--highlighted': link.highlighted,
    'onto-link--hidden': !link.highlighted,
  }
}

/* ── SVG connections (DOM-based positions) ── */
const ontoLayerRef = ref<HTMLElement | null>(null)
const svgW = 1920
const svgH = 600
const crossSvgW = 1920
const crossSvgH = 1080
const contentRef = ref<HTMLElement | null>(null)
const domPositionTick = ref(0)

function recalcPositions() {
  domPositionTick.value++
}

watch([entities, relations], () => {
  nextTick(recalcPositions)
})

const svgLinks = computed(() => {
  domPositionTick.value // reactive dependency

  const layer = ontoLayerRef.value
  if (!layer) return []

  const layerRect = layer.getBoundingClientRect()
  if (!layerRect.width || !layerRect.height) return []

  const nodeMap = new Map<string, OntologyNode>()
  for (const n of [...coreNodes.value, ...domainNodes.value]) nodeMap.set(n.id, n)

  const posMap = new Map<string, { x: number; y: number }>()
  const nodeEls = layer.querySelectorAll('[data-node-id]')
  for (const el of nodeEls) {
    const id = (el as HTMLElement).dataset.nodeId!
    const r = el.getBoundingClientRect()
    const cx = r.left + r.width / 2 - layerRect.left
    const cy = r.top + r.height / 2 - layerRect.top
    posMap.set(id, {
      x: (cx / layerRect.width) * svgW,
      y: (cy / layerRect.height) * svgH,
    })
  }

  const linkColors: Record<string, { color: string; particleColor: string }> = {
    'core-core': { color: '#4c6ef5', particleColor: '#748ffc' },
    'core-domain': { color: '#91a7ff', particleColor: '#bac8ff' },
    'domain-domain': { color: '#bac8ff', particleColor: '#dbe4ff' },
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
      const mx = (f.x + t.x) / 2, my = (f.y + t.y) / 2
      const dist = Math.sqrt(dx * dx + dy * dy)
      const bulge = dist * 0.15
      const nx = -dy / (dist || 1), ny = dx / (dist || 1)
      const cx1 = mx + nx * bulge, cy1 = my + ny * bulge
      const path = `M${f.x},${f.y} Q${cx1},${cy1} ${t.x},${t.y}`
      const activeIds = highlightedNodeIds.value
      const highlighted = !isHoverFiltering.value || (activeIds.has(r.from_entity_id) && activeIds.has(r.to_entity_id))
      return {
        id: r.id, path, color: lc.color, particleColor: lc.particleColor,
        dur: 1.5 + (idx % 5) * 0.12,
        highlighted,
      }
    })
})

/* ── Cross-layer flow lines (cards ↔ onto-layer) ── */
const CROSS_LAYER_CONNECTIONS: { cardKey: string; direction: 'up' | 'down'; count: number; hue: number }[] = [
  { cardKey: 'datasources', direction: 'up', count: 6, hue: 210 },
  { cardKey: 'logic', direction: 'up', count: 5, hue: 260 },
  { cardKey: 'actions', direction: 'down', count: 5, hue: 170 },
  { cardKey: 'analytics', direction: 'down', count: 5, hue: 230 },
  { cardKey: 'automations', direction: 'down', count: 6, hue: 280 },
  { cardKey: 'products', direction: 'down', count: 5, hue: 200 },
]

function seededRand(seed: number) {
  const x = Math.sin(seed * 9301 + 49297) * 49297
  return x - Math.floor(x)
}

const crossLayerLinks = computed(() => {
  domPositionTick.value
  const content = contentRef.value
  if (!content) return []
  const cRect = content.getBoundingClientRect()
  if (!cRect.width || !cRect.height) return []

  const layer = ontoLayerRef.value
  if (!layer) return []
  const lRect = layer.getBoundingClientRect()

  const links: { id: string; path: string; color: string; particleColor: string; dur: number; particles: number; rArr: number[] }[] = []

  for (const conn of CROSS_LAYER_CONNECTIONS) {
    const cardEl = content.querySelector(`[data-card-key="${conn.cardKey}"]`) as HTMLElement | null
    if (!cardEl) continue
    const cardRect = cardEl.getBoundingClientRect()

    const isBottom = ['datasources', 'logic', 'actions'].includes(conn.cardKey)

    const cardCenterX = cardRect.left + cardRect.width / 2 - cRect.left
    const cardCenterRatio = cardCenterX / cRect.width
    const layerPad = 0.06
    const slotW = cardRect.width * 0.7 / cRect.width

    for (let i = 0; i < conn.count; i++) {
      const t = (i + 1) / (conn.count + 1)
      const cardX = cardRect.left + cardRect.width * t - cRect.left

      const layerRatio = cardCenterRatio - slotW / 2 + slotW * t
      const layerXClamped = Math.max(layerPad, Math.min(1 - layerPad, layerRatio))
      const layerX = lRect.left + lRect.width * layerXClamped - cRect.left

      let cardY: number, layerY: number
      if (isBottom) {
        cardY = cardRect.top - cRect.top
        layerY = lRect.bottom - cRect.top
      } else {
        cardY = cardRect.bottom - cRect.top
        layerY = lRect.top - cRect.top
      }

      const sx = (cardX / cRect.width) * crossSvgW
      const sy = (cardY / cRect.height) * crossSvgH
      const ex = (layerX / cRect.width) * crossSvgW
      const ey = (layerY / cRect.height) * crossSvgH

      const seed = conn.hue * 100 + i
      const sway = (seededRand(seed) - 0.5) * 40
      const bulge = (seededRand(seed + 1) - 0.5) * 20

      const dy = ey - sy
      const c1x = sx + sway
      const c1y = sy + dy * 0.3 + bulge
      const c2x = ex - sway * 0.6
      const c2y = sy + dy * 0.7 - bulge

      const path = conn.direction === 'up'
        ? `M${sx},${sy} C${c1x},${c1y} ${c2x},${c2y} ${ex},${ey}`
        : `M${ex},${ey} C${c2x},${c2y} ${c1x},${c1y} ${sx},${sy}`

      const sat = 70 + seededRand(seed + 2) * 20
      const light = 68 + seededRand(seed + 3) * 10
      const color = `hsl(${conn.hue}, ${sat}%, ${light}%)`
      const particleColor = `hsl(${conn.hue}, ${sat + 10}%, ${light + 12}%)`

      const pCount = 3 + Math.round(seededRand(seed + 4) * 2)
      const rArr: number[] = []
      for (let p = 0; p < pCount; p++) rArr.push(1.5 + seededRand(seed + 10 + p) * 2)

      links.push({
        id: `cl-${conn.cardKey}-${i}`,
        path, color, particleColor,
        dur: 2.2 + seededRand(seed + 5) * 1.6,
        particles: pCount,
        rArr,
      })
    }
  }
  return links
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

function resetView() {
  scale.value = 1
  ox.value = 0
  oy.value = 0
}

function onWheel(e: WheelEvent) {
  if (showConfig.value || selectedNode.value) return
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
  if (refreshTimer) clearInterval(refreshTimer)
})

function onNodeClick(node: OntologyNode) {
  selectedNode.value = node
}

async function onNodeMutated() {
  selectedNode.value = null
  const [e, r] = await Promise.all([
    entityApi.list().catch(() => entities.value),
    relationApi.list().catch(() => relations.value),
  ])
  entities.value = e as EntityListItem[]
  relations.value = r as any
  stats.value = await dashboardApi.stats().catch(() => stats.value) as any
}

/* ── Top & Bottom cards ── */
const BG_MAP: Record<string, string> = {
  analytics: '/images/ontology/bg-ANALYTICS &WORKFLOWS.png',
  automations: '/images/ontology/bg-AUTOMATIONS.png',
  products: '/images/ontology/bg-PRODUCTS & SDKs.png',
  datasources: '/images/ontology/bg-DATA SOURCES.png',
  logic: '/images/ontology/bg-LOGIC SOURCES.png',
  actions: '/images/ontology/bg-SYSTEMS OF ACTION.png',
}
const ICON_MAP: Record<string, string> = {
  datasources: '/images/ontology/icon-DATA SOURCES.png',
  logic: '/images/ontology/icon-LOGIC SOURCES.png',
  actions: '/images/ontology/icon-SYSTEMS OF ACTION.png',
}
const WORKFLOW_ICON = '/images/ontology/icon-核心本体.png'
const WORKFLOW_CARD_ITEMS = [
  { icon: WORKFLOW_ICON, label: '风险工作流' },
  { icon: WORKFLOW_ICON, label: '证据检测流' },
  { icon: WORKFLOW_ICON, label: '客户分析' },
  { icon: WORKFLOW_ICON, label: '异网分析' },
  { icon: WORKFLOW_ICON, label: '仪表盘' },
]
const AUTOMATION_ICON_ITEMS = [
  { icon: WORKFLOW_ICON, label: '合约到期提醒' },
  { icon: WORKFLOW_ICON, label: '异常预警' },
  { icon: WORKFLOW_ICON, label: '本体优化建议' },
]
const PRODUCT_ICON_ITEMS = [
  { icon: WORKFLOW_ICON, label: '智能问答' },
  { icon: WORKFLOW_ICON, label: '场景验证' },
]
const DATASOURCE_ICON_ITEMS = [
  { icon: WORKFLOW_ICON, label: 'CBSS' },
  { icon: WORKFLOW_ICON, label: '外呼录音' },
  { icon: WORKFLOW_ICON, label: '地址库' },
  { icon: WORKFLOW_ICON, label: '待装库' },
  { icon: WORKFLOW_ICON, label: '通话记录' },
  { icon: WORKFLOW_ICON, label: '客户信息' },
]
const LOGIC_ICON_ITEMS = [
  { icon: WORKFLOW_ICON, label: 'Deepseekv3' },
  { icon: WORKFLOW_ICON, label: 'ASR' },
  { icon: WORKFLOW_ICON, label: 'Qwen2.5-VL' },
]
const ACTIONS_ICON_ITEMS = [
  { icon: WORKFLOW_ICON, label: '二次营销外呼' },
  { icon: WORKFLOW_ICON, label: '维挽' },
  { icon: WORKFLOW_ICON, label: '员工培训' },
]
const ICON_ITEMS_MAP: Record<string, { icon: string; label: string }[]> = {
  analytics: WORKFLOW_CARD_ITEMS,
  automations: AUTOMATION_ICON_ITEMS,
  products: PRODUCT_ICON_ITEMS,
  datasources: DATASOURCE_ICON_ITEMS,
  logic: LOGIC_ICON_ITEMS,
  actions: ACTIONS_ICON_ITEMS,
}
const FLEX_MAP: Record<string, number> = {
  analytics: 479, automations: 537, products: 470,
  datasources: 514, logic: 514, actions: 441,
}

function resolveCardItems(card: any): string[] {
  if (!stats.value) return ['加载中...']
  const s = stats.value as any
  const items: string[] = []
  for (const item of card.items) {
    if (item.type === 'static') {
      items.push(item.text || '')
    } else if (item.type === 'dynamic') {
      const val = s[item.field] ?? ''
      items.push(`${val} ${item.label || ''}`.trim())
    } else if (item.type === 'top_rules') {
      const rules = s.top_rules?.slice(0, item.count ?? 4) ?? []
      items.push(...(rules.length ? rules.map((r: any) => r.name) : ['暂无规则']))
    } else if (item.type === 'datasources') {
      const dsList = s.datasources ?? []
      const bb = dsList.filter((d: any) => d.name.startsWith('bb_'))
      const other = dsList.filter((d: any) => !d.name.startsWith('bb_'))
      if (bb.length) items.push(`宽带退单(${bb.length}表)`, ...bb.slice(0, 4).map((d: any) => d.name.replace('bb_', '')))
      if (other.length) items.push(`携号转网(${other.length}表)`, ...other.slice(0, 3).map((d: any) => d.name))
      if (!dsList.length) items.push('暂无数据源')
    } else if (item.type === 'rule_priority') {
      const rp = s.rule_priority ?? []
      items.push(...(rp.length ? rp.map((r: any) => `${r.priority} 优先级: ${r.count}`) : ['暂无规则']))
    } else if (item.type === 'recent_activities') {
      const acts = s.recent_activities?.slice(0, item.count ?? 5) ?? []
      items.push(...(acts.length ? acts.map((a: any) => a.description || a.name || a.target_name) : ['暂无动态']))
    }
  }
  return items.slice(0, 8)
}

const allCards = computed(() => {
  const cards = dashConfig.value?.cards_config
  if (!cards) {
    // fallback to hardcoded defaults
    const dsList = (stats.value as any)?.datasources ?? []
    const bb = dsList.filter((d: any) => d.name.startsWith('bb_'))
    const other = dsList.filter((d: any) => !d.name.startsWith('bb_'))
    const dsItems = [
      ...(bb.length ? [`宽带退单(${bb.length}表)`, ...bb.slice(0, 4).map((d: any) => d.name.replace('bb_', ''))] : []),
      ...(other.length ? [`携号转网(${other.length}表)`, ...other.slice(0, 3).map((d: any) => d.name)] : []),
      ...(!dsList.length ? ['暂无数据源'] : []),
    ]
    const activeRules = stats.value ? stats.value.top_rules.slice(0, 4).map((r: any) => r.name) : []
    return [
      { key: 'analytics', title: 'ANALYTICS & WORKFLOWS', flex: 479, bg: BG_MAP.analytics, items: [], iconItems: WORKFLOW_CARD_ITEMS },
      { key: 'automations', title: 'AUTOMATIONS', flex: 537, bg: BG_MAP.automations, items: [], iconItems: AUTOMATION_ICON_ITEMS },
      { key: 'products', title: 'PRODUCTS & SDKs', flex: 470, bg: BG_MAP.products, items: [], iconItems: PRODUCT_ICON_ITEMS },
      { key: 'datasources', title: 'DATA SOURCES', flex: 514, bg: BG_MAP.datasources, items: [], iconItems: DATASOURCE_ICON_ITEMS },
      { key: 'logic', title: 'LOGIC SOURCES', flex: 514, bg: BG_MAP.logic, items: [], iconItems: LOGIC_ICON_ITEMS },
      { key: 'actions', title: 'SYSTEMS OF ACTION', flex: 441, bg: BG_MAP.actions, items: [], iconItems: ACTIONS_ICON_ITEMS },
    ]
  }
  return cards.filter(c => c.enabled).map(c => ({
    key: c.key, title: c.title,
    flex: FLEX_MAP[c.key] ?? 470,
    bg: BG_MAP[c.key] ?? BG_MAP.analytics,
    icon: ICON_MAP[c.key],
    items: ICON_ITEMS_MAP[c.key] ? [] : resolveCardItems(c),
    iconItems: ICON_ITEMS_MAP[c.key],
  }))
})

const topCards = computed(() => allCards.value.slice(0, 3))
const bottomCards = computed(() => allCards.value.slice(3))
</script>

<style scoped>
@font-face {
  font-family: var(--font-sans);
  src: url(/fonts/AlimamaFangYuanTiVF-Thin.ttf) format('truetype');
  font-weight: 400;
}

.screen-wrapper {
  width: 100%; height: 100%; min-height: 720px;
  position: relative; overflow: hidden; background: var(--neutral-0);
  cursor: grab;
}
.screen-wrapper:active { cursor: grabbing; }

.screen-bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; }
.screen-title { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 46.15%; height: auto; z-index: 20; pointer-events: none; }
.screen-bottom { position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); width: 31.25%; height: auto; z-index: 20; pointer-events: none; }

.content {
  position: relative; z-index: 5;
  display: flex; flex-direction: column;
  width: 100%; height: 100%;
  padding: 3.5vw 60px 40px;
  box-sizing: border-box;
  transition: transform 0.05s linear;
}

.cross-layer-svg {
  position: absolute; inset: 0; width: 100%; height: 100%;
  pointer-events: none; z-index: 3;
  overflow: visible;
}
.cl-line {
  animation: cl-breathe 3s ease-in-out infinite alternate;
}
.cl-particle {
  mix-blend-mode: screen;
}
@keyframes cl-breathe {
  0%   { stroke-opacity: 0.15; stroke-width: 0.8; }
  100% { stroke-opacity: 0.35; stroke-width: 1.4; }
}

.row { display: flex; justify-content: space-between; align-items: center; gap: 16px; width: 100%; }
.row-top { align-items: flex-end; }
.row-bottom { margin-top: 2vw; }

/* ── 本体层 ── */
.onto-layer {
  position: relative; width: 96.15%; max-width: 100%; margin: 1.5vw auto 0;
  flex: 1; min-height: 300px; overflow: visible;
}
.onto-layer__bg { width: 100%; height: auto; display: block; }
.onto-layer__svg {
  position: absolute; inset: 0; width: 100%; height: 100%;
  pointer-events: none; z-index: 1;
}
.onto-link {
  transition: opacity .18s ease, filter .18s ease;
}
.onto-link--hidden {
  opacity: 0;
}
.onto-link--highlighted .onto-link__line {
  stroke-width: 1.8;
  stroke-opacity: 0.7;
}
.onto-link--highlighted .onto-link__line-dash {
  stroke-width: 1;
  stroke-opacity: 0.9;
}
.onto-link--highlighted .onto-link__particle {
  r: 3;
}
.onto-zones { position: absolute; inset: 0; z-index: 2; overflow: visible; }

.onto-zone { position: absolute; z-index: 6; overflow: visible; }
.onto-zone--core { z-index: 7; }

.platform-rows-wrapper {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  width: 100%; height: 100%;
  gap: var(--row-gap, clamp(7px, 0.6vw, 13px));
}
.platform-row {
  display: flex; justify-content: center; align-items: flex-end;
  gap: var(--col-gap, clamp(8px, 0.75vw, 15px));
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  padding: 0 0.5vw;
  overflow: visible;
}
.platform-row--offset { transform: translateX(var(--row-offset, 0.75vw)); }

.platform-item {
  display: flex; flex-direction: column; align-items: center;
  padding: 0; cursor: pointer; position: relative;
  transition: opacity .15s, filter .15s, transform .15s;
  user-select: none; z-index: 1;
  flex: 0 0 auto;
  width: clamp(64px, 4.25vw, 82px);
  height: clamp(54px, 3.8vw, 70px);
}
.platform-item:hover {
  z-index: 200;
  filter: brightness(1.05) drop-shadow(0 2px 8px rgba(76, 110, 245, 0.2));
  transform: scale(1.06);
}
.platform-item--focus {
  z-index: 230;
  filter: brightness(1.12) drop-shadow(0 0 14px rgba(76, 110, 245, 0.35));
  transform: scale(1.1);
}
.platform-item--related {
  z-index: 210;
  filter: brightness(1.08) drop-shadow(0 0 10px rgba(76, 110, 245, 0.22));
  transform: scale(1.04);
}
.platform-item--hidden {
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: scale(0.96);
}
.platform-item--core {
  width: clamp(74px, 5vw, 96px);
  height: clamp(64px, 4.45vw, 82px);
}

.platform-icon {
  width: clamp(42px, 2.35vw, 50px); height: auto; flex-shrink: 0;
}
.platform-icon--core { width: clamp(52px, 3vw, 62px); }

.platform-label {
  color: var(--semantic-900);
  text-align: center; white-space: nowrap;
  font-family: var(--font-sans);
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
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(76, 110, 245, 0.25);
  border-radius: 0.21vw;
  min-width: 8.33vw; max-width: 16.67vw;
  padding: 0.42vw 0.63vw;
  transition: opacity .15s, transform .15s, visibility .15s;
}
.platform-item:hover .platform-tooltip {
  opacity: 1; visibility: visible;
  transform: translateX(-50%) translateY(0);
}
.platform-tooltip-name { color: var(--neutral-900); font-size: 0.68vw; font-weight: 600; margin-bottom: 0.21vw; }
.platform-tooltip-desc { color: var(--neutral-600); font-size: 0.57vw; line-height: 1.5; white-space: normal; margin-bottom: 0.21vw; }
.platform-tooltip-row { color: var(--neutral-700); font-size: 0.57vw; line-height: 1.6; white-space: nowrap; }

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
.config-btn { color: rgba(76, 110, 245, 0.7); padding: 4px; border-radius: 6px; }
.config-btn:hover { color: var(--semantic-700); filter: none; background: rgba(76, 110, 245, 0.08); }
</style>
