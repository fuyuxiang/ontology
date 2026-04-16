<template>
  <div class="iso-wrap">
    <svg class="iso-svg" viewBox="0 0 900 620" preserveAspectRatio="xMidYMid meet">
      <defs>
        <marker id="arr" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
          <path d="M0,0 L5,2.5 L0,5 z" fill="#10b981" opacity=".8"/>
        </marker>
        <filter id="card-shadow">
          <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="rgba(15,17,23,.1)"/>
        </filter>
        <linearGradient id="hg" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#10b981"/>
          <stop offset="100%" stop-color="#f59e0b"/>
        </linearGradient>
      </defs>

      <!-- ── 底层平台 ── -->
      <g :opacity="activeStage === 'wield' ? 0.3 : 1" style="transition:opacity .5s">
        <IsoPlatform :x="botX" :y="botY" :w="PW" :d="PD" :h="PH"
          top-color="rgba(219,234,254,.7)" front-color="rgba(147,197,253,.5)" side-color="rgba(96,165,250,.4)"
          label="FOUNDATION LAYER"/>
        <g v-for="(mod, i) in bottomModules" :key="mod.key"
          @click="$emit('selectTarget', mod.key)" style="cursor:pointer">
          <IsoCard
            :x="botX + 20 + (i % 2) * (PW/2 - 8)"
            :y="botY + 20 + Math.floor(i/2) * 70"
            :w="PW/2 - 24" :h="55"
            :selected="selectedKey === mod.key"
            color="rgba(239,246,255,.9)"
          />
          <text
            :x="ix(botX + 20 + (i%2)*(PW/2-8) + (PW/2-24)/2, botY + 20 + Math.floor(i/2)*70 + 20)"
            :y="iy(botX + 20 + (i%2)*(PW/2-8) + (PW/2-24)/2, botY + 20 + Math.floor(i/2)*70 + 20)"
            text-anchor="middle" font-size="9" fill="#1e40af" font-weight="700">{{ mod.label }}</text>
          <text
            :x="ix(botX + 20 + (i%2)*(PW/2-8) + (PW/2-24)/2, botY + 20 + Math.floor(i/2)*70 + 34)"
            :y="iy(botX + 20 + (i%2)*(PW/2-8) + (PW/2-24)/2, botY + 20 + Math.floor(i/2)*70 + 34)"
            text-anchor="middle" font-size="7.5" fill="#64748b">{{ mod.metric }} {{ mod.metricLabel }}</text>
        </g>
      </g>

      <!-- ── 底→中 连线束 ── -->
      <g :opacity="activeStage === 'hydrate' ? 0.75 : 0.1" style="transition:opacity .5s">
        <path v-for="(p,i) in lowerBundles" :key="'lb'+i" :d="p"
          fill="none" stroke="#3b82f6" stroke-width="0.7" stroke-dasharray="4 3"
          :class="{ 'flow-anim': activeStage === 'hydrate' }"
          :style="{ animationDelay: (i*0.06)+'s' }"/>
      </g>

      <!-- ── 中层平台 ── -->
      <g>
        <IsoPlatform :x="midX" :y="midY" :w="PW" :d="PD" :h="PH"
          top-color="rgba(220,252,231,.75)" front-color="rgba(134,239,172,.5)" side-color="rgba(74,222,128,.4)"
          label="ONTOLOGY"/>

        <!-- 关系连线（先画，在节点下面） -->
        <g v-for="rel in ontologyEdges" :key="rel.id">
          <path :d="rel.path" fill="none"
            :stroke="rel.highlighted ? '#10b981' : '#cbd5e1'"
            :stroke-width="rel.highlighted ? 1.8 : 0.9"
            :stroke-dasharray="rel.highlighted ? 'none' : '3 3'"
            :opacity="rel.dimmed ? 0.12 : 1"
            :marker-end="rel.highlighted ? 'url(#arr)' : ''"/>
          <circle v-if="rel.highlighted" r="2.5" fill="#10b981" opacity=".9">
            <animateMotion :dur="(2.2 + rel.idx*0.18)+'s'" repeatCount="indefinite">
              <mpath :href="'#ep-'+rel.id"/>
            </animateMotion>
          </circle>
          <path :id="'ep-'+rel.id" :d="rel.path" fill="none" stroke="none"/>
          <g v-if="rel.highlighted">
            <rect :x="rel.lx - rel.lw/2 - 5" :y="rel.ly - 7" :width="rel.lw + 10" height="13" rx="6.5"
              fill="rgba(16,185,129,.13)" stroke="rgba(16,185,129,.35)" stroke-width=".8"/>
            <text :x="rel.lx" :y="rel.ly + 2.5" text-anchor="middle" font-size="7" fill="#065f46" font-weight="700">{{ rel.label }}</text>
          </g>
        </g>

        <!-- 实体节点 -->
        <g v-for="node in ontologyNodes" :key="node.key"
          @click="$emit('selectTarget', node.key)"
          @mouseenter="hoveredKey = node.key"
          @mouseleave="hoveredKey = ''"
          style="cursor:pointer">
          <ellipse v-if="node.highlighted"
            :cx="node.sx" :cy="node.sy"
            rx="32" ry="12" fill="#10b981" opacity=".1"/>
          <IsoCard
            :x="node.wx - 34" :y="node.wy - 20"
            :w="68" :h="40"
            :selected="selectedKey === node.key || hoveredKey === node.key"
            :color="node.color"
            :dimmed="node.dimmed"
          />
          <text :x="node.sx" :y="node.sy - 4"
            text-anchor="middle" font-size="13">{{ node.emoji }}</text>
          <text :x="node.sx" :y="node.sy + 8"
            text-anchor="middle" font-size="8.5" fill="#1e293b" font-weight="700">{{ node.label }}</text>
          <text :x="node.sx" :y="node.sy + 17"
            text-anchor="middle" font-size="7" fill="#94a3b8">{{ node.meta }}</text>
        </g>
      </g>

      <!-- ── 中→顶 连线束 ── -->
      <g :opacity="activeStage === 'wield' ? 0.75 : 0.1" style="transition:opacity .5s">
        <path v-for="(p,i) in upperBundles" :key="'ub'+i" :d="p"
          fill="none" stroke="#10b981" stroke-width="0.7" stroke-dasharray="4 3"
          :class="{ 'flow-anim': activeStage === 'wield' }"
          :style="{ animationDelay: (i*0.06)+'s' }"/>
      </g>

      <!-- ── 顶层平台 ── -->
      <g :opacity="activeStage === 'hydrate' ? 0.3 : 1" style="transition:opacity .5s">
        <IsoPlatform :x="topX" :y="topY" :w="PW" :d="PD" :h="PH"
          top-color="rgba(255,247,237,.8)" front-color="rgba(253,186,116,.5)" side-color="rgba(251,146,60,.4)"
          label="APPLICATION LAYER"/>
        <g v-for="(mod, i) in topModules" :key="mod.key"
          @click="$emit('selectTarget', mod.key)" style="cursor:pointer">
          <IsoCard
            :x="topX + 14 + i*(PW/3 - 2)"
            :y="topY + 16"
            :w="PW/3 - 14" :h="PD - 32"
            :selected="selectedKey === mod.key"
            color="rgba(255,247,237,.9)"
          />
          <!-- 迷你屏幕 -->
          <rect
            :x="ix(topX + 14 + i*(PW/3-2) + (PW/3-14)/2, topY + 40) - 30"
            :y="iy(topX + 14 + i*(PW/3-2) + (PW/3-14)/2, topY + 40) - 20"
            width="60" height="30" rx="3"
            fill="#0f172a" opacity=".88"/>
          <text
            :x="ix(topX + 14 + i*(PW/3-2) + (PW/3-14)/2, topY + 40)"
            :y="iy(topX + 14 + i*(PW/3-2) + (PW/3-14)/2, topY + 40) - 5"
            text-anchor="middle" font-size="6.5" fill="#60a5fa" font-family="monospace">{{ ['ANALYTICS','WORKFLOWS','INTEGRATIONS'][i] }}</text>
          <text
            :x="ix(topX + 14 + i*(PW/3-2) + (PW/3-14)/2, topY + 40)"
            :y="iy(topX + 14 + i*(PW/3-2) + (PW/3-14)/2, topY + 40) + 8"
            text-anchor="middle" font-size="6" fill="#94a3b8">{{ mod.metric }} {{ mod.metricLabel }}</text>
          <text
            :x="ix(topX + 14 + i*(PW/3-2) + (PW/3-14)/2, topY + 130)"
            :y="iy(topX + 14 + i*(PW/3-2) + (PW/3-14)/2, topY + 130)"
            text-anchor="middle" font-size="9" fill="#1e293b" font-weight="700">{{ mod.label }}</text>
        </g>
      </g>

      <!-- ── Asset 探针卡 ── -->
      <g v-if="probeNode" style="pointer-events:none">
        <rect :x="probeNode.sx + 16" :y="probeNode.sy - 70"
          width="138" height="100" rx="10"
          fill="rgba(255,255,255,.96)" stroke="rgba(15,17,23,.09)" stroke-width="1"
          filter="url(#card-shadow)"/>
        <text :x="probeNode.sx + 26" :y="probeNode.sy - 52"
          font-size="8" fill="#94a3b8" font-weight="800" letter-spacing="1.2">ASSET DETAIL</text>
        <text :x="probeNode.sx + 26" :y="probeNode.sy - 38"
          font-size="12" fill="#1e293b" font-weight="700">{{ probeNode.label }}</text>
        <text :x="probeNode.sx + 26" :y="probeNode.sy - 24"
          font-size="8" fill="#64748b">Tier {{ probeNode.entity.tier }}</text>
        <text :x="probeNode.sx + 80" :y="probeNode.sy - 24"
          font-size="8" fill="#64748b">{{ probeNode.entity.relation_count }} 关系</text>
        <text :x="probeNode.sx + 26" :y="probeNode.sy - 12"
          font-size="8" fill="#64748b">{{ probeNode.entity.rule_count }} 规则</text>
        <text :x="probeNode.sx + 80" :y="probeNode.sy - 12"
          font-size="8" fill="#64748b">{{ probeNode.entity.status }}</text>
        <text :x="probeNode.sx + 26" :y="probeNode.sy + 4"
          font-size="8" fill="#94a3b8" font-weight="700" letter-spacing="1">HEALTH SCORE</text>
        <text :x="probeNode.sx + 26" :y="probeNode.sy + 20"
          font-size="20" fill="#f59e0b" font-weight="800">{{ probeNode.health }}</text>
        <rect :x="probeNode.sx + 26" :y="probeNode.sy + 24" width="100" height="5" rx="2.5" fill="#f1f5f9"/>
        <rect :x="probeNode.sx + 26" :y="probeNode.sy + 24" :width="probeNode.health" height="5" rx="2.5" fill="url(#hg)"/>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import IsoPlatform from './IsoPlatform.vue'
import IsoCard from './IsoCard.vue'
import type { EntityListItem } from '../../../types'
import type { RelationData } from '../../../api/relations'

type StageId = 'hydrate' | 'activate' | 'wield'
interface ModuleCard { key: string; title: string; label: string; metric: string; metricLabel: string; tone: string; placement: 'top' | 'bottom'; [k: string]: unknown }

const props = defineProps<{
  entities: EntityListItem[]; relations: RelationData[]
  activeStage: StageId; selectedKey: string
  topModules: ModuleCard[]; bottomModules: ModuleCard[]
}>()
defineEmits<{ selectTarget: [key: string] }>()

const ANG = Math.PI / 6
const CX = 450; const CY = 310
function ix(wx: number, wy: number) { return CX + (wx - wy) * Math.cos(ANG) }
function iy(wx: number, wy: number) { return CY + (wx + wy) * Math.sin(ANG) * 0.5 }

const PW = 340; const PD = 220; const PH = 16
const topX = -PW/2; const topY = -PD/2 - 170
const midX = -PW/2; const midY = -PD/2
const botX = -PW/2; const botY = -PD/2 + 170

const nodeSlots = [
  { wx: 0, wy: 0 }, { wx: -85, wy: -65 }, { wx: 85, wy: -65 },
  { wx: -115, wy: 10 }, { wx: 115, wy: 10 }, { wx: -85, wy: 75 },
  { wx: 85, wy: 75 }, { wx: 0, wy: -95 }, { wx: 0, wy: 95 },
]
const nodeColors = ['rgba(220,252,231,.95)','rgba(219,234,254,.95)','rgba(254,249,195,.95)','rgba(252,231,243,.95)','rgba(237,233,254,.95)','rgba(220,252,231,.95)','rgba(219,234,254,.95)','rgba(254,249,195,.95)','rgba(252,231,243,.95)']
const nodeEmojis = ['👤','🏭','🚛','🏢','⚙️','📄','📱','🛡️','📊']

const hoveredKey = ref('')

const entityDegree = computed(() => {
  const m = new Map<string, number>()
  for (const r of props.relations) {
    m.set(r.from_entity_id, (m.get(r.from_entity_id) ?? 0) + 1)
    m.set(r.to_entity_id, (m.get(r.to_entity_id) ?? 0) + 1)
  }
  return m
})

const ontologyNodes = computed(() => {
  const sorted = [...props.entities]
    .sort((a, b) => (entityDegree.value.get(b.id) ?? 0) - (entityDegree.value.get(a.id) ?? 0))
    .slice(0, 9)
  const selId = props.selectedKey.startsWith('entity:') ? props.selectedKey.slice(7) : null
  const hovId = hoveredKey.value.startsWith('entity:') ? hoveredKey.value.slice(7) : null
  const activeId = selId || hovId
  return sorted.map((entity, i) => {
    const s = nodeSlots[i] ?? nodeSlots[0]
    const wx = midX + PW/2 + s.wx; const wy = midY + PD/2 + s.wy
    const dimmed = activeId ? entity.id !== activeId && !props.relations.some(r =>
      (r.from_entity_id === activeId && r.to_entity_id === entity.id) ||
      (r.to_entity_id === activeId && r.from_entity_id === entity.id)) : false
    return {
      key: `entity:${entity.id}`, entity, wx, wy,
      sx: ix(wx, wy), sy: iy(wx, wy),
      color: nodeColors[i], emoji: nodeEmojis[i],
      label: entity.name_cn || entity.name,
      meta: `${entity.relation_count}关系·${entity.rule_count}规则`,
      highlighted: activeId ? entity.id === activeId : false, dimmed,
    }
  })
})

const ontologyEdges = computed(() => {
  const posMap = new Map(ontologyNodes.value.map(n => [n.entity.id, n]))
  const selId = props.selectedKey.startsWith('entity:') ? props.selectedKey.slice(7) : null
  const hovId = hoveredKey.value.startsWith('entity:') ? hoveredKey.value.slice(7) : null
  const activeId = selId || hovId
  return props.relations
    .filter(r => posMap.has(r.from_entity_id) && posMap.has(r.to_entity_id))
    .map((r, idx) => {
      const f = posMap.get(r.from_entity_id)!; const t = posMap.get(r.to_entity_id)!
      const fx = f.sx; const fy = f.sy; const tx = t.sx; const ty = t.sy
      const mx = (fx+tx)/2; const my = (fy+ty)/2
      const off = (idx % 2 === 0 ? -1 : 1) * 18
      const path = `M${fx},${fy} Q${mx+off},${my+off} ${tx},${ty}`
      const hl = activeId ? r.from_entity_id === activeId || r.to_entity_id === activeId : props.activeStage === 'activate'
      const dim = activeId ? r.from_entity_id !== activeId && r.to_entity_id !== activeId : false
      const lbl = r.name.replaceAll('_', ' ')
      return { id: r.id, idx, path, label: lbl, lx: mx+off, ly: my+off, lw: lbl.length * 4.5, highlighted: hl, dimmed: dim }
    })
})

function bundlePaths(fromWPts: [number,number][], toWPts: [number,number][]) {
  const paths: string[] = []
  fromWPts.forEach(f => {
    toWPts.forEach(t => {
      const fx = ix(f[0],f[1]); const fy = iy(f[0],f[1])
      const tx = ix(t[0],t[1]); const ty = iy(t[0],t[1])
      paths.push(`M${fx},${fy} C${fx},${(fy+ty)/2} ${tx},${(fy+ty)/2} ${tx},${ty}`)
    })
  })
  return paths
}

const midTopPts: [number,number][] = [[midX+60,midY],[midX+170,midY],[midX+280,midY],[midX+60,midY+PD],[midX+170,midY+PD],[midX+280,midY+PD]]
const topBotPts: [number,number][] = [[topX+80,topY+PD],[topX+170,topY+PD],[topX+260,topY+PD]]
const botTopPts: [number,number][] = [[botX+80,botY],[botX+170,botY],[botX+260,botY]]

const upperBundles = computed(() => bundlePaths(midTopPts, topBotPts))
const lowerBundles = computed(() => bundlePaths(botTopPts, midTopPts))

const probeNode = computed(() => {
  const k = hoveredKey.value || props.selectedKey
  if (!k.startsWith('entity:')) return null
  const n = ontologyNodes.value.find(n => n.key === k)
  if (!n) return null
  const base = n.entity.status === 'active' ? 68 : 38
  const health = Math.min(100, base + (n.entity.relation_count ?? 0) * 3 + (n.entity.rule_count ?? 0) * 2)
  return { ...n, health }
})
</script>

<style scoped>
.iso-wrap {
  width: 100%;
  background:
    radial-gradient(ellipse at 50% 20%, rgba(59,130,246,.05) 0%, transparent 55%),
    radial-gradient(ellipse at 80% 80%, rgba(16,185,129,.04) 0%, transparent 45%),
    #f8fafc;
  border-radius: 20px;
  border: 1px solid rgba(15,17,23,.05);
  overflow: hidden;
}
.iso-svg { display: block; width: 100%; height: auto; }
.flow-anim { animation: dash-flow 1.6s linear infinite; }
@keyframes dash-flow { to { stroke-dashoffset: -14; } }
</style>
