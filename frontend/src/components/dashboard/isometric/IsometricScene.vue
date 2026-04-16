<template>
  <div class="iso-scene">
    <!-- 顶层：应用能力 -->
    <div class="iso-layer" :class="{ 'iso-layer--dim': activeStage === 'hydrate' }">
      <div class="iso-slab iso-slab--top">
        <div class="iso-slab__face">
          <div class="iso-slab__label">APPLICATION LAYER</div>
          <div class="iso-top-grid">
            <button v-for="mod in topModules" :key="mod.key"
              class="iso-app-card"
              :class="[`iso-app-card--${mod.tone}`, { 'iso-app-card--sel': selectedKey === mod.key }]"
              @click="$emit('selectTarget', mod.key)">
              <div class="iso-app-card__screen" v-html="screenSvg(mod.key)"></div>
              <div class="iso-app-card__foot">
                <span class="iso-app-card__name">{{ mod.label }}</span>
                <span class="iso-app-card__metric">{{ mod.metric }} {{ mod.metricLabel }}</span>
              </div>
            </button>
          </div>
        </div>
        <div class="iso-slab__edge iso-slab__edge--top"></div>
      </div>
    </div>

    <!-- 流线：中→顶 -->
    <div class="iso-flow" :class="{ 'iso-flow--active': activeStage === 'wield' }">
      <svg class="iso-flow__svg" viewBox="0 0 800 72" preserveAspectRatio="none">
        <path v-for="(p,i) in upperPaths" :key="'u'+i"
          :d="p" class="fline" :class="{ 'fline--on': activeStage === 'wield' }"
          :style="{ animationDelay: (i * 0.06) + 's' }"/>
      </svg>
    </div>

    <!-- 中层：本体网络 -->
    <div class="iso-layer" :class="{ 'iso-layer--glow': activeStage === 'activate' }">
      <div class="iso-slab iso-slab--mid">
        <div class="iso-slab__face iso-slab__face--mid">
          <div class="iso-slab__label">ONTOLOGY</div>
          <div class="iso-onto-wrap">
            <OntologyNetwork
              :entities="entities"
              :relations="relations"
              :activeStage="activeStage"
              :selectedKey="selectedKey"
              @select="$emit('selectTarget', $event)"
            />
            <AssetDetailCard
              :entity="selectedEntity"
              :visible="activeStage === 'activate' && !!selectedEntity"
            />
          </div>
        </div>
        <div class="iso-slab__edge iso-slab__edge--mid"></div>
      </div>
    </div>

    <!-- 流线：底→中 -->
    <div class="iso-flow" :class="{ 'iso-flow--active': activeStage === 'hydrate' }">
      <svg class="iso-flow__svg" viewBox="0 0 800 72" preserveAspectRatio="none">
        <path v-for="(p,i) in lowerPaths" :key="'l'+i"
          :d="p" class="fline" :class="{ 'fline--on': activeStage === 'hydrate' }"
          :style="{ animationDelay: (i * 0.06) + 's' }"/>
      </svg>
    </div>

    <!-- 底层：数据基座 -->
    <div class="iso-layer" :class="{ 'iso-layer--dim': activeStage === 'wield' }">
      <div class="iso-slab iso-slab--bot">
        <div class="iso-slab__face">
          <div class="iso-slab__label">FOUNDATION LAYER</div>
          <div class="iso-bot-grid">
            <button v-for="mod in bottomModules" :key="mod.key"
              class="iso-data-card"
              :class="[`iso-data-card--${mod.tone}`, { 'iso-data-card--sel': selectedKey === mod.key }]"
              @click="$emit('selectTarget', mod.key)">
              <div class="iso-data-card__icon" v-html="dsIcon(mod.key)"></div>
              <div class="iso-data-card__name">{{ mod.label }}</div>
              <div class="iso-data-card__dots">
                <span v-for="j in 8" :key="j" class="iso-dot" :class="{ 'iso-dot--on': j <= 5 }"></span>
              </div>
              <div class="iso-data-card__bar">
                <div class="iso-data-card__fill" :style="{ width: (55 + mod.key.length * 3) % 80 + 20 + '%' }"></div>
              </div>
            </button>
          </div>
        </div>
        <div class="iso-slab__edge iso-slab__edge--bot"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import OntologyNetwork from './OntologyNetwork.vue'
import AssetDetailCard from './AssetDetailCard.vue'
import type { EntityListItem } from '../../../types'
import type { RelationData } from '../../../api/relations'

type StageId = 'hydrate' | 'activate' | 'wield'
interface ModuleCard {
  key: string; title: string; label: string
  metric: string; metricLabel: string; tone: string
  placement: 'top' | 'bottom'; [k: string]: unknown
}

const props = defineProps<{
  entities: EntityListItem[]
  relations: RelationData[]
  activeStage: StageId
  selectedKey: string
  topModules: ModuleCard[]
  bottomModules: ModuleCard[]
}>()
defineEmits<{ selectTarget: [key: string] }>()

const selectedEntity = computed(() => {
  if (!props.selectedKey.startsWith('entity:')) return null
  const id = props.selectedKey.slice(7)
  return props.entities.find(e => e.id === id) ?? null
})

// 扇形流线：底部均匀 → 顶部三个汇聚点
function fanPaths(anchors: number[], n: number, fromY: number, toY: number) {
  return Array.from({ length: n }, (_, i) => {
    const bx = 30 + i * (740 / (n - 1))
    const ax = anchors[i % anchors.length]
    const my = (fromY + toY) / 2
    return `M${bx},${fromY} C${bx},${my} ${ax},${my} ${ax},${toY}`
  })
}
const upperPaths = computed(() => fanPaths([160, 400, 640], 20, 70, 2))
const lowerPaths = computed(() => fanPaths([200, 400, 600], 20, 70, 2))

function screenSvg(key: string): string {
  const m: Record<string, string> = {
    'module:analytics': `<svg width="100%" height="100%" viewBox="0 0 120 70" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="120" height="70" rx="4" fill="#0f172a"/>
      <rect x="8" y="42" width="10" height="20" rx="1.5" fill="#3b82f6" opacity=".7"/>
      <rect x="22" y="32" width="10" height="30" rx="1.5" fill="#3b82f6"/>
      <rect x="36" y="22" width="10" height="40" rx="1.5" fill="#60a5fa"/>
      <rect x="50" y="36" width="10" height="26" rx="1.5" fill="#3b82f6" opacity=".8"/>
      <rect x="64" y="14" width="10" height="48" rx="1.5" fill="#3b82f6"/>
      <rect x="78" y="28" width="10" height="34" rx="1.5" fill="#60a5fa" opacity=".9"/>
      <polyline points="13,40 27,30 41,20 55,34 69,12 83,26 97,18" stroke="#10b981" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="13" cy="40" r="3" fill="#10b981"/>
      <circle cx="69" cy="12" r="3" fill="#10b981"/>
    </svg>`,
    'module:workflows': `<svg width="100%" height="100%" viewBox="0 0 120 70" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="120" height="70" rx="4" fill="#0f172a"/>
      <rect x="40" y="6" width="40" height="14" rx="3" fill="#1e3a5f" stroke="#3b82f6" stroke-width="1"/>
      <text x="60" y="16" text-anchor="middle" font-size="7" fill="#60a5fa" font-family="monospace">TRIGGER</text>
      <line x1="60" y1="20" x2="60" y2="28" stroke="#3b82f6" stroke-width="1.2" stroke-dasharray="3 2"/>
      <rect x="14" y="28" width="36" height="14" rx="3" fill="#052e16" stroke="#10b981" stroke-width="1"/>
      <text x="32" y="38" text-anchor="middle" font-size="7" fill="#10b981" font-family="monospace">RULE CHECK</text>
      <rect x="70" y="28" width="36" height="14" rx="3" fill="#1e1b4b" stroke="#818cf8" stroke-width="1"/>
      <text x="88" y="38" text-anchor="middle" font-size="7" fill="#818cf8" font-family="monospace">ACTION</text>
      <line x1="32" y1="42" x2="60" y2="50" stroke="#10b981" stroke-width="1.2" stroke-dasharray="3 2"/>
      <line x1="88" y1="42" x2="60" y2="50" stroke="#818cf8" stroke-width="1.2" stroke-dasharray="3 2"/>
      <rect x="36" y="50" width="48" height="14" rx="3" fill="#2d1f00" stroke="#f59e0b" stroke-width="1"/>
      <text x="60" y="60" text-anchor="middle" font-size="7" fill="#f59e0b" font-family="monospace">DISPATCH</text>
    </svg>`,
    'module:integrations': `<svg width="100%" height="100%" viewBox="0 0 120 70" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="120" height="70" rx="4" fill="#0f172a"/>
      <rect x="6" y="10" width="24" height="18" rx="3" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="18" y="22" text-anchor="middle" font-size="7" fill="#94a3b8" font-family="monospace">API</text>
      <rect x="6" y="42" width="24" height="18" rx="3" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="18" y="54" text-anchor="middle" font-size="7" fill="#94a3b8" font-family="monospace">API</text>
      <rect x="90" y="10" width="24" height="18" rx="3" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="102" y="22" text-anchor="middle" font-size="7" fill="#94a3b8" font-family="monospace">API</text>
      <rect x="90" y="42" width="24" height="18" rx="3" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="102" y="54" text-anchor="middle" font-size="7" fill="#94a3b8" font-family="monospace">API</text>
      <circle cx="60" cy="35" r="14" fill="#0f1f3d" stroke="#3b82f6" stroke-width="1.5"/>
      <text x="60" y="38" text-anchor="middle" font-size="8" fill="#60a5fa" font-family="monospace">HUB</text>
      <line x1="30" y1="19" x2="46" y2="30" stroke="#3b82f6" stroke-width="1" stroke-dasharray="3 2"/>
      <line x1="30" y1="51" x2="46" y2="40" stroke="#3b82f6" stroke-width="1" stroke-dasharray="3 2"/>
      <line x1="90" y1="19" x2="74" y2="30" stroke="#3b82f6" stroke-width="1" stroke-dasharray="3 2"/>
      <line x1="90" y1="51" x2="74" y2="40" stroke="#3b82f6" stroke-width="1" stroke-dasharray="3 2"/>
    </svg>`,
  }
  return m[key] ?? m['module:analytics']
}

function dsIcon(key: string): string {
  if (key.includes('data')) return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><ellipse cx="12" cy="6" rx="9" ry="3.5" stroke="#64748b" stroke-width="1.5"/><path d="M3 6v6c0 1.93 4 3.5 9 3.5s9-1.57 9-3.5V6" stroke="#64748b" stroke-width="1.5"/><path d="M3 12v6c0 1.93 4 3.5 9 3.5s9-1.57 9-3.5v-6" stroke="#64748b" stroke-width="1.5"/></svg>`
  return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="4" stroke="#64748b" stroke-width="1.5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5.64 5.64l2.12 2.12M16.24 16.24l2.12 2.12M5.64 18.36l2.12-2.12M16.24 7.76l2.12-2.12" stroke="#64748b" stroke-width="1.5" stroke-linecap="round"/></svg>`
}
</script>

<style scoped>
.iso-scene {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 20px;
  background:
    radial-gradient(ellipse at 50% 0%, rgba(59,130,246,.05) 0%, transparent 55%),
    radial-gradient(ellipse at 15% 100%, rgba(16,185,129,.04) 0%, transparent 45%),
    #f8fafc;
  border-radius: 20px;
  border: 1px solid rgba(15,17,23,.06);
  overflow: hidden;
}

/* ── Layer ── */
.iso-layer { transition: opacity .5s ease; }
.iso-layer--dim { opacity: .3; }
.iso-layer--glow .iso-slab--mid .iso-slab__face { box-shadow: 0 0 0 1.5px rgba(16,185,129,.2), 0 20px 50px rgba(16,185,129,.1); }

/* ── Slab (platform with thick edge) ── */
.iso-slab { position: relative; margin-bottom: 2px; }

.iso-slab__face {
  background: rgba(255,255,255,.94);
  border: 1px solid rgba(15,17,23,.07);
  border-radius: 14px;
  padding: 14px 18px 18px;
  box-shadow: 0 2px 0 rgba(255,255,255,.9) inset, 0 12px 32px rgba(15,17,23,.06);
  transform: perspective(1000px) rotateX(4deg);
  transform-origin: bottom center;
  position: relative;
  z-index: 1;
}
.iso-slab__face--mid {
  transform: perspective(1000px) rotateX(2deg);
  min-height: 340px;
}

/* Thick bottom edge — the "slab" illusion */
.iso-slab__edge {
  position: absolute;
  bottom: -10px;
  left: 8px;
  right: 8px;
  height: 12px;
  border-radius: 0 0 10px 10px;
  z-index: 0;
}
.iso-slab__edge--top { background: linear-gradient(180deg, #c8a020 0%, #8a6a00 100%); }
.iso-slab__edge--mid { background: linear-gradient(180deg, #0d9488 0%, #065f46 100%); }
.iso-slab__edge--bot { background: linear-gradient(180deg, #3b5bdb 0%, #1e3a8a 100%); }

.iso-slab__label {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .16em;
  color: #94a3b8;
  text-transform: uppercase;
  margin-bottom: 12px;
}

/* ── Top: app cards ── */
.iso-top-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.iso-app-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  background: #fff;
  transition: transform .2s, box-shadow .2s, border-color .2s;
  text-align: left;
}
.iso-app-card:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(15,17,23,.1); }
.iso-app-card--sel { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,.2); }

.iso-app-card__screen { width: 100%; aspect-ratio: 16/9; display: block; }
.iso-app-card__foot { padding: 8px 10px; }
.iso-app-card__name { display: block; font-size: 11px; font-weight: 700; color: #1e293b; }
.iso-app-card__metric { display: block; font-size: 10px; color: #94a3b8; margin-top: 1px; }

/* ── Bottom: data cards ── */
.iso-bot-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.iso-data-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: transform .2s, box-shadow .2s;
}
.iso-data-card:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(15,17,23,.08); }
.iso-data-card--sel { border-color: #3b82f6; }
.iso-data-card__icon { color: #64748b; margin-bottom: 6px; }
.iso-data-card__name { font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 8px; }
.iso-data-card__dots { display: flex; gap: 3px; margin-bottom: 6px; }
.iso-dot { width: 8px; height: 8px; border-radius: 2px; background: #e2e8f0; }
.iso-dot--on { background: #3b82f6; opacity: .7; }
.iso-data-card__bar { height: 4px; background: #f1f5f9; border-radius: 2px; overflow: hidden; }
.iso-data-card__fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #10b981); border-radius: 2px; }

/* ── Ontology wrap ── */
.iso-onto-wrap { position: relative; min-height: 300px; }

/* ── Flow zone ── */
.iso-flow {
  position: relative;
  height: 60px;
  margin: -2px 0;
  z-index: 2;
  overflow: hidden;
}
.iso-flow__svg { position: absolute; inset: 0; width: 100%; height: 100%; }

.fline {
  fill: none;
  stroke: #cbd5e1;
  stroke-width: .8;
  stroke-dasharray: 4 4;
  opacity: .4;
  transition: stroke .4s, opacity .4s;
}
.fline--on {
  stroke: #10b981;
  opacity: .65;
  animation: dash-anim 1.6s linear infinite;
}
@keyframes dash-anim { to { stroke-dashoffset: -16; } }
</style>
