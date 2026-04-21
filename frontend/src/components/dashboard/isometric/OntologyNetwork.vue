<template>
  <div class="onto-net" ref="containerRef">
    <!-- SVG 连线层 -->
    <svg class="onto-net__svg" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none">
      <defs>
        <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="#10b981" opacity=".7"/>
        </marker>
      </defs>
      <!-- 连线 -->
      <g v-for="rel in renderedRelations" :key="rel.id">
        <path
          :d="rel.path"
          class="onto-edge"
          :class="{ 'onto-edge--hl': rel.highlighted, 'onto-edge--dim': rel.dimmed }"
          :marker-end="rel.highlighted ? 'url(#arrow)' : ''"
        />
        <!-- 流动粒子 -->
        <circle v-if="rel.highlighted" r="3" fill="#10b981" opacity=".8">
          <animateMotion :dur="(1.8 + rel.idx * 0.15) + 's'" repeatCount="indefinite">
            <mpath :href="'#path-' + rel.id"/>
          </animateMotion>
        </circle>
        <path :id="'path-' + rel.id" :d="rel.path" fill="none" stroke="none"/>
      </g>
    </svg>

    <!-- 节点 -->
    <div
      v-for="node in positionedNodes"
      :key="node.key"
      class="onto-node"
      :class="[
        `onto-node--${node.tone}`,
        { 'onto-node--sel': selectedKey === node.key, 'onto-node--dim': node.dimmed, 'onto-node--center': node.isCenter }
      ]"
      :style="{ left: node.px + 'px', top: node.py + 'px' }"
      @click="$emit('select', node.key)"
      @mouseenter="hoveredKey = node.key"
      @mouseleave="hoveredKey = ''"
    >
      <div class="onto-node__icon" v-html="nodeIcon(node.iconType)"></div>
      <div class="onto-node__name">{{ node.displayName }}</div>
      <div class="onto-node__meta">{{ node.entity.relation_count }}关系 · {{ node.entity.rule_count }}规则</div>
    </div>

    <!-- 关系标签胶囊 -->
    <div
      v-for="badge in visibleBadges"
      :key="'b-' + badge.id"
      class="onto-badge"
      :style="{ left: badge.px + 'px', top: badge.py + 'px' }"
    >{{ badge.label }}</div>

    <!-- Asset 探针卡 -->
    <transition name="probe">
      <div v-if="probeNode" class="onto-probe" :style="probeStyle">
        <div class="onto-probe__eyebrow">ASSET N°{{ probeNode.entity.id.slice(-3).toUpperCase() }}</div>
        <div class="onto-probe__name">{{ probeNode.displayName }}</div>
        <div class="onto-probe__rows">
          <div class="onto-probe__row"><span>Tier</span><strong>{{ probeNode.entity.tier }}</strong></div>
          <div class="onto-probe__row"><span>关系</span><strong>{{ probeNode.entity.relation_count }}</strong></div>
          <div class="onto-probe__row"><span>规则</span><strong>{{ probeNode.entity.rule_count }}</strong></div>
          <div class="onto-probe__row"><span>状态</span><strong>{{ probeNode.entity.status }}</strong></div>
        </div>
        <div class="onto-probe__score-lbl">HEALTH SCORE</div>
        <div class="onto-probe__score-val">{{ healthScore(probeNode.entity) }}</div>
        <div class="onto-probe__bar-wrap">
          <div class="onto-probe__bar" :style="{ width: healthScore(probeNode.entity) + '%' }"></div>
        </div>
      </div>
    </transition>

    <div v-if="positionedNodes.length === 0" class="onto-net__empty">
      导入本体对象后，这里会自动生成可点击节点
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { EntityListItem } from '../../../types'
import type { RelationData } from '../../../api/relations'

type StageId = 'hydrate' | 'activate' | 'wield'
type Tone = 'semantic' | 'dynamic' | 'kinetic'

const props = defineProps<{
  entities: EntityListItem[]
  relations: RelationData[]
  activeStage: StageId
  selectedKey: string
}>()
defineEmits<{ select: [key: string] }>()

const W = 800
const H = 320
const containerRef = ref<HTMLElement | null>(null)
const hoveredKey = ref('')

// 布局槽位（百分比 → 像素）
const slots = [
  { xp: 50, yp: 50 },
  { xp: 28, yp: 28 }, { xp: 72, yp: 28 },
  { xp: 16, yp: 52 }, { xp: 84, yp: 52 },
  { xp: 28, yp: 76 }, { xp: 72, yp: 76 },
  { xp: 50, yp: 14 }, { xp: 50, yp: 86 },
]

const tones: Tone[] = ['dynamic', 'semantic', 'kinetic', 'semantic', 'dynamic', 'kinetic', 'semantic', 'dynamic', 'kinetic']
const iconTypes = ['person', 'factory', 'truck', 'building', 'gear', 'document', 'phone', 'shield', 'chart']

const entityDegree = computed(() => {
  const m = new Map<string, number>()
  for (const r of props.relations) {
    m.set(r.from_entity_id, (m.get(r.from_entity_id) ?? 0) + 1)
    m.set(r.to_entity_id, (m.get(r.to_entity_id) ?? 0) + 1)
  }
  return m
})

const positionedNodes = computed(() => {
  const sorted = [...props.entities]
    .sort((a, b) => (entityDegree.value.get(b.id) ?? 0) - (entityDegree.value.get(a.id) ?? 0))
    .slice(0, 9)
  const selId = props.selectedKey.startsWith('entity:') ? props.selectedKey.slice(7) : null
  const hId = hoveredKey.value.startsWith('entity:') ? hoveredKey.value.slice(7) : null
  const activeId = selId || hId

  return sorted.map((entity, i) => {
    const s = slots[i] ?? slots[0]
    const px = s.xp / 100 * W
    const py = s.yp / 100 * H
    const dimmed = activeId ? entity.id !== activeId && !props.relations.some(r =>
      (r.from_entity_id === activeId && r.to_entity_id === entity.id) ||
      (r.to_entity_id === activeId && r.from_entity_id === entity.id)
    ) : false
    return {
      key: `entity:${entity.id}`,
      entity, px, py,
      tone: tones[i],
      iconType: iconTypes[i % iconTypes.length],
      displayName: entity.name_cn || entity.name,
      isCenter: i === 0,
      dimmed,
    }
  })
})

const renderedRelations = computed(() => {
  const posMap = new Map(positionedNodes.value.map(n => [n.entity.id, { px: n.px, py: n.py }]))
  const selId = props.selectedKey.startsWith('entity:') ? props.selectedKey.slice(7) : null
  const hId = hoveredKey.value.startsWith('entity:') ? hoveredKey.value.slice(7) : null
  const activeId = selId || hId

  return props.relations
    .filter(r => posMap.has(r.from_entity_id) && posMap.has(r.to_entity_id))
    .map((r, idx) => {
      const f = posMap.get(r.from_entity_id)!
      const t = posMap.get(r.to_entity_id)!
      const dx = t.px - f.px
      const dy = t.py - f.py
      const cx1 = f.px + dx * 0.4 + dy * 0.15
      const cy1 = f.py + dy * 0.4 - dx * 0.15
      const cx2 = f.px + dx * 0.6 + dy * 0.15
      const cy2 = f.py + dy * 0.6 - dx * 0.15
      const path = `M${f.px},${f.py} C${cx1},${cy1} ${cx2},${cy2} ${t.px},${t.py}`
      const highlighted = activeId
        ? r.from_entity_id === activeId || r.to_entity_id === activeId
        : props.activeStage === 'activate'
      const dimmed = activeId
        ? r.from_entity_id !== activeId && r.to_entity_id !== activeId
        : false
      return {
        id: r.id, idx, path,
        label: r.name.replaceAll('_', ' '),
        midPx: (f.px + t.px) / 2,
        midPy: (f.py + t.py) / 2 + (idx % 2 === 0 ? -8 : 8),
        highlighted, dimmed,
      }
    })
})

const visibleBadges = computed(() => {
  const hl = renderedRelations.value.filter(r => r.highlighted)
  return hl.slice(0, 4).map(r => ({
    id: r.id, label: r.label,
    px: r.midPx, py: r.midPy,
  }))
})

const probeNode = computed(() => {
  const k = hoveredKey.value || props.selectedKey
  if (!k.startsWith('entity:')) return null
  return positionedNodes.value.find(n => n.key === k) ?? null
})

const probeStyle = computed(() => {
  if (!probeNode.value) return {}
  const px = probeNode.value.px
  const py = probeNode.value.py
  const left = px > W * 0.6 ? 'auto' : (px / W * 100 + 2) + '%'
  const right = px > W * 0.6 ? ((1 - px / W) * 100 + 2) + '%' : 'auto'
  const top = (py / H * 100) + '%'
  return { left, right, top }
})

function healthScore(e: EntityListItem) {
  const base = e.status === 'active' ? 70 : e.status === 'warning' ? 45 : 20
  return Math.min(100, base + (e.relation_count ?? 0) * 3 + (e.rule_count ?? 0) * 2)
}

function nodeIcon(type: string): string {
  const icons: Record<string, string> = {
    person: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="5" r="3.5" stroke="currentColor" stroke-width="1.4"/><path d="M2 16c0-3.9 3.1-7 7-7s7 3.1 7 7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
    factory: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M1 16V7l5 3.5V7l5 3.5V4h6v12H1z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>`,
    truck: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="1" y="5" width="10" height="9" rx="1" stroke="currentColor" stroke-width="1.4"/><path d="M11 8h4l2 4v2h-6V8z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><circle cx="4.5" cy="15" r="1.8" stroke="currentColor" stroke-width="1.2"/><circle cx="14" cy="15" r="1.8" stroke="currentColor" stroke-width="1.2"/></svg>`,
    building: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="3" y="1" width="12" height="16" rx="1" stroke="currentColor" stroke-width="1.4"/><rect x="6" y="4" width="2.5" height="2.5" rx=".5" fill="currentColor"/><rect x="9.5" y="4" width="2.5" height="2.5" rx=".5" fill="currentColor"/><rect x="6" y="8.5" width="2.5" height="2.5" rx=".5" fill="currentColor"/><rect x="9.5" y="8.5" width="2.5" height="2.5" rx=".5" fill="currentColor"/><rect x="7.5" y="13" width="3" height="4" fill="currentColor" rx=".5"/></svg>`,
    gear: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="3" stroke="currentColor" stroke-width="1.4"/><path d="M9 1v2.5M9 14.5V17M1 9h2.5M14.5 9H17M3.4 3.4l1.77 1.77M12.83 12.83l1.77 1.77M3.4 14.6l1.77-1.77M12.83 5.17l1.77-1.77" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
    document: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4 1h7l5 5v11H4V1z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M11 1v5h5M6 9h6M6 12h4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
    phone: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="4" y="1" width="10" height="16" rx="2.5" stroke="currentColor" stroke-width="1.4"/><circle cx="9" cy="14" r="1.2" fill="currentColor"/></svg>`,
    shield: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M9 1L2 4.5v5C2 13.5 5 16.5 9 17.5c4-1 7-4 7-8v-5L9 1z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>`,
    chart: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="1" y="10" width="4" height="7" rx=".8" stroke="currentColor" stroke-width="1.4"/><rect x="7" y="6" width="4" height="11" rx=".8" stroke="currentColor" stroke-width="1.4"/><rect x="13" y="1" width="4" height="16" rx=".8" stroke="currentColor" stroke-width="1.4"/></svg>`,
  }
  return icons[type] ?? icons.gear
}
</script>

<style scoped>
.onto-net {
  position: relative;
  width: 100%;
  height: 320px;
}

.onto-net__svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

/* Edges */
.onto-edge {
  fill: none;
  stroke: #cbd5e1;
  stroke-width: 1.2;
  stroke-dasharray: 5 4;
  transition: stroke .3s, opacity .3s;
}
.onto-edge--hl {
  stroke: #10b981;
  stroke-width: 1.8;
  stroke-dasharray: none;
  filter: drop-shadow(0 0 3px rgba(16,185,129,.4));
}
.onto-edge--dim { opacity: .15; }

/* Nodes */
.onto-node {
  position: absolute;
  width: 110px;
  padding: 8px 10px;
  border-radius: 14px;
  border: 1px solid rgba(15,17,23,.08);
  background: rgba(255,255,255,.95);
  transform: translate(-50%, -50%);
  cursor: pointer;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  text-align: center;
  box-shadow: 0 4px 16px rgba(15,17,23,.07);
  transition: transform .2s, box-shadow .2s, opacity .3s, border-color .2s;
}
.onto-node:hover { transform: translate(-50%, calc(-50% - 4px)); box-shadow: 0 12px 28px rgba(15,17,23,.12); }
.onto-node--sel { border-color: rgba(16,185,129,.35); box-shadow: 0 0 0 3px rgba(16,185,129,.15), 0 12px 28px rgba(16,185,129,.12); }
.onto-node--dim { opacity: .25; }
.onto-node--center { width: 124px; }
.onto-node--semantic { background: rgba(238,242,255,.96); }
.onto-node--dynamic { background: rgba(230,252,245,.96); }
.onto-node--kinetic { background: rgba(255,248,225,.96); }

.onto-node__icon { color: var(--neutral-700); display: flex; align-items: center; justify-content: center; }
.onto-node__name { font-size: var(--text-caption-size); font-weight: 700; color: var(--neutral-900); line-height: 1.3; }
.onto-node__meta { font-size: var(--text-caption-upper-size); color: var(--neutral-500); }

/* Relation badges */
.onto-badge {
  position: absolute;
  transform: translate(-50%, -50%);
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(16,185,129,.1);
  border: 1px solid rgba(16,185,129,.22);
  color: var(--dynamic-900);
  font-size: var(--text-caption-upper-size);
  font-weight: 700;
  white-space: nowrap;
  z-index: 3;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(16,185,129,.1);
}

/* Probe card */
.onto-probe {
  position: absolute;
  z-index: 10;
  width: 160px;
  background: rgba(255,255,255,.96);
  border: 1px solid rgba(15,17,23,.1);
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 16px 40px rgba(15,17,23,.12);
  pointer-events: none;
  transform: translateY(-50%);
}
.onto-probe__eyebrow { font-size: var(--text-caption-upper-size); font-weight: 800; letter-spacing: .1em; color: var(--neutral-500); text-transform: uppercase; }
.onto-probe__name { font-size: var(--text-body-size); font-weight: 700; color: var(--neutral-900); margin: 4px 0 8px; }
.onto-probe__rows { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; }
.onto-probe__row { display: flex; justify-content: space-between; font-size: var(--text-caption-size); }
.onto-probe__row span { color: var(--neutral-500); }
.onto-probe__row strong { color: var(--neutral-800); }
.onto-probe__score-lbl { font-size: var(--text-caption-upper-size); font-weight: 700; letter-spacing: .08em; color: var(--neutral-500); text-transform: uppercase; }
.onto-probe__score-val { font-size: var(--text-h1-size); font-weight: 800; color: var(--kinetic-500); margin: 2px 0 6px; }
.onto-probe__bar-wrap { height: 5px; background: var(--neutral-50); border-radius: 3px; overflow: hidden; }
.onto-probe__bar { height: 100%; background: linear-gradient(90deg, #10b981, #f59e0b); border-radius: 3px; transition: width .5s ease; }

.probe-enter-active, .probe-leave-active { transition: opacity .2s, transform .2s; }
.probe-enter-from, .probe-leave-to { opacity: 0; transform: translateY(calc(-50% + 8px)); }

.onto-net__empty {
  position: absolute;
  inset: 20% 15%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
  color: var(--neutral-500);
  font-size: var(--text-body-size);
  background: rgba(255,255,255,.7);
}
</style>
