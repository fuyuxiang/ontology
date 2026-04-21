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
              <div class="platform-row">
                <div v-for="node in coreNodes" :key="node.id" class="platform-item platform-item--core"
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
        <CapabilityCard v-for="card in bottomCards" :key="card.title" v-bind="card" />
      </div>
    </div>

    <!-- 底部控制 -->
    <div class="bottom-controls">
      <button class="bottom-btn" @click="resetView"><img src="/images/ontology/btn-重置视角.png" alt="重置" /></button>
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
      @close="showConfig = false" @saved="onConfigSaved" />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
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

  const interval = (cfg as any)?.refresh_interval ?? 30
  refreshTimer = setInterval(async () => {
    stats.value = await dashboardApi.stats().catch(() => stats.value) as any
  }, interval * 1000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
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
    return [
      { key: 'analytics', title: 'ANALYTICS & WORKFLOWS', flex: 479, bg: BG_MAP.analytics, items: stats.value ? [`${stats.value.entity_count} 个实体`, `${stats.value.relation_count} 条关系`, `${stats.value.rule_count} 条规则`, `${stats.value.active_rule_count} 条活跃规则`] : ['加载中...'] },
      { key: 'automations', title: 'AUTOMATIONS', flex: 537, bg: BG_MAP.automations, items: stats.value ? [...(stats.value.top_rules.slice(0, 4).map((r: any) => r.name)), ...(stats.value.top_rules.length === 0 ? ['暂无规则'] : [])] : ['加载中...'] },
      { key: 'products', title: 'PRODUCTS & SDKs', flex: 470, bg: BG_MAP.products, items: ['Ontology Center', 'AI Copilot', 'AIP Workflow', 'API Gateway'] },
      { key: 'datasources', title: 'DATA SOURCES', flex: 514, bg: BG_MAP.datasources, icon: ICON_MAP.datasources, items: dsItems.slice(0, 8) },
      { key: 'logic', title: 'LOGIC SOURCES', flex: 514, bg: BG_MAP.logic, icon: ICON_MAP.logic, items: (stats.value as any)?.rule_priority?.length ? (stats.value as any).rule_priority.map((r: any) => `${r.priority} 优先级: ${r.count}`) : ['暂无规则'] },
      { key: 'actions', title: 'SYSTEMS OF ACTION', flex: 441, bg: BG_MAP.actions, icon: ICON_MAP.actions, items: (stats.value as any)?.recent_activities?.length ? (stats.value as any).recent_activities.slice(0, 5).map((a: any) => a.description || a.name) : ['暂无动态'] },
    ]
  }
  return cards.filter(c => c.enabled).map(c => ({
    key: c.key, title: c.title,
    flex: FLEX_MAP[c.key] ?? 470,
    bg: BG_MAP[c.key] ?? BG_MAP.analytics,
    icon: ICON_MAP[c.key],
    items: resolveCardItems(c),
  }))
})

const topCards = computed(() => allCards.value.slice(0, 3))
const bottomCards = computed(() => allCards.value.slice(3))
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
.config-btn { color: rgba(0,50,145,0.7); padding: 4px; border-radius: 6px; }
.config-btn:hover { color: #003291; filter: none; background: rgba(0,50,145,0.1); }
</style>
