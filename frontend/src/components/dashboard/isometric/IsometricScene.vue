<template>
  <div class="iso-scene">
    <!-- 顶层：应用能力 -->
    <div class="iso-layer iso-layer--top" :class="{ 'iso-layer--dim': activeStage === 'hydrate' }">
      <div class="iso-platform iso-platform--top">
        <div class="iso-platform__edge iso-platform__edge--top"></div>
        <div class="iso-platform__face">
          <div class="iso-platform__label">APPLICATION LAYER</div>
          <div class="iso-top-modules">
            <button v-for="mod in topModules" :key="mod.key"
              class="iso-app-card" :class="[`iso-app-card--${mod.tone}`, { 'iso-app-card--sel': selectedKey === mod.key }]"
              @click="$emit('selectTarget', mod.key)">
              <div class="iso-app-card__screen">
                <div class="iso-app-card__screen-inner" v-html="screenSvg(mod.key)"></div>
              </div>
              <div class="iso-app-card__label">{{ mod.label }}</div>
              <div class="iso-app-card__metric">{{ mod.metric }} {{ mod.metricLabel }}</div>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 流线：中→顶 -->
    <div class="iso-flow iso-flow--up" :class="{ 'iso-flow--active': activeStage === 'wield' }">
      <svg class="iso-flow__svg" viewBox="0 0 800 80" preserveAspectRatio="none">
        <!-- 扇形收束线：从底部宽散到顶部三个点 -->
        <path v-for="(p, i) in upperFlowPaths" :key="'uf'+i" :d="p.d" class="flow-path" :class="{ 'flow-path--active': activeStage === 'wield' }" :style="{ animationDelay: (i * 0.08) + 's' }"/>
      </svg>
      <div v-for="i in 6" :key="'pu'+i" class="flow-dot flow-dot--up" :style="{ left: (8 + i * 14) + '%', animationDelay: (i * 0.28) + 's' }"></div>
    </div>

    <!-- 中层：本体网络 -->
    <div class="iso-layer iso-layer--mid" :class="{ 'iso-layer--glow': activeStage === 'activate' }">
      <div class="iso-platform iso-platform--mid">
        <div class="iso-platform__edge iso-platform__edge--mid"></div>
        <div class="iso-platform__face iso-platform__face--mid">
          <div class="iso-platform__label">ONTOLOGY</div>
          <div class="iso-ontology-wrap">
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
      </div>
    </div>

    <!-- 流线：底→中 -->
    <div class="iso-flow iso-flow--down" :class="{ 'iso-flow--active': activeStage === 'hydrate' }">
      <svg class="iso-flow__svg" viewBox="0 0 800 80" preserveAspectRatio="none">
        <path v-for="(p, i) in lowerFlowPaths" :key="'lf'+i" :d="p.d" class="flow-path" :class="{ 'flow-path--active': activeStage === 'hydrate' }" :style="{ animationDelay: (i * 0.08) + 's' }"/>
      </svg>
      <div v-for="i in 6" :key="'pd'+i" class="flow-dot flow-dot--up" :style="{ left: (8 + i * 14) + '%', animationDelay: (i * 0.28) + 's' }"></div>
    </div>

    <!-- 底层：数据基座 -->
    <div class="iso-layer iso-layer--bot" :class="{ 'iso-layer--dim': activeStage === 'wield' }">
      <div class="iso-platform iso-platform--bot">
        <div class="iso-platform__edge iso-platform__edge--bot"></div>
        <div class="iso-platform__face">
          <div class="iso-platform__label">FOUNDATION LAYER</div>
          <div class="iso-bot-modules">
            <button v-for="mod in bottomModules" :key="mod.key"
              class="iso-data-card" :class="[`iso-data-card--${mod.tone}`, { 'iso-data-card--sel': selectedKey === mod.key }]"
              @click="$emit('selectTarget', mod.key)">
              <div class="iso-data-card__icon" v-html="moduleIcon(mod.key)"></div>
              <div class="iso-data-card__label">{{ mod.label }}</div>
              <div class="iso-data-card__grid">
                <span v-for="j in 6" :key="j" class="iso-data-card__cell" :class="{ 'cell--lit': j <= 4 }"></span>
              </div>
            </button>
          </div>
        </div>
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

// 扇形流线：底部均匀分布 → 顶部三个汇聚点
function buildFanPaths(topAnchors: number[], count: number) {
  return Array.from({ length: count }, (_, i) => {
    const bx = 40 + i * (720 / (count - 1))
    const anchor = topAnchors[i % topAnchors.length]
    const mx = (bx + anchor) / 2
    return { d: `M${bx},78 C${mx},40 ${anchor},40 ${anchor},2` }
  })
}

const upperFlowPaths = computed(() => buildFanPaths([160, 400, 640], 18))
const lowerFlowPaths = computed(() => buildFanPaths([200, 400, 600], 18))

function screenSvg(key: string): string {
  const screens: Record<string, string> = {
    'module:analytics': `<svg width="100%" height="100%" viewBox="0 0 80 50" fill="none">
      <rect x="2" y="2" width="76" height="46" rx="3" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
      <rect x="8" y="30" width="8" height="14" rx="1" fill="#3b82f6" opacity=".8"/>
      <rect x="20" y="22" width="8" height="22" rx="1" fill="#3b82f6"/>
      <rect x="32" y="16" width="8" height="28" rx="1" fill="#60a5fa"/>
      <rect x="44" y="26" width="8" height="18" rx="1" fill="#3b82f6" opacity=".7"/>
      <rect x="56" y="10" width="8" height="34" rx="1" fill="#3b82f6"/>
      <polyline points="8,28 20,20 32,14 44,24 56,8 68,18" stroke="#10b981" stroke-width="1.5" fill="none"/>
      <circle cx="8" cy="28" r="2" fill="#10b981"/>
      <circle cx="56" cy="8" r="2" fill="#10b981"/>
    </svg>`,
    'module:workflows': `<svg width="100%" height="100%" viewBox="0 0 80 50" fill="none">
      <rect x="2" y="2" width="76" height="46" rx="3" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
      <rect x="28" y="6" width="24" height="10" rx="2" fill="#1e3a5f" stroke="#3b82f6" stroke-width="1"/>
      <text x="40" y="14" text-anchor="middle" font-size="5" fill="#60a5fa">TRIGGER</text>
      <line x1="40" y1="16" x2="40" y2="22" stroke="#3b82f6" stroke-width="1" stroke-dasharray="2 1"/>
      <rect x="14" y="22" width="20" height="9" rx="2" fill="#052e16" stroke="#10b981" stroke-width="1"/>
      <text x="24" y="29" text-anchor="middle" font-size="4.5" fill="#10b981">RULE CHECK</text>
      <rect x="46" y="22" width="20" height="9" rx="2" fill="#1e1b4b" stroke="#818cf8" stroke-width="1"/>
      <text x="56" y="29" text-anchor="middle" font-size="4.5" fill="#818cf8">ACTION</text>
      <line x1="34" y1="31" x2="34" y2="37" stroke="#10b981" stroke-width="1" stroke-dasharray="2 1"/>
      <rect x="22" y="37" width="36" height="9" rx="2" fill="#2d1f00" stroke="#f59e0b" stroke-width="1"/>
      <text x="40" y="44" text-anchor="middle" font-size="4.5" fill="#f59e0b">DISPATCH</text>
    </svg>`,
    'module:integrations': `<svg width="100%" height="100%" viewBox="0 0 80 50" fill="none">
      <rect x="2" y="2" width="76" height="46" rx="3" fill="#0a1628" stroke="#1e3a5f" stroke-width="1"/>
      <rect x="6" y="8" width="18" height="14" rx="2" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="15" y="17" text-anchor="middle" font-size="5" fill="#94a3b8">API</text>
      <rect x="6" y="28" width="18" height="14" rx="2" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="15" y="37" text-anchor="middle" font-size="5" fill="#94a3b8">API</text>
      <rect x="56" y="8" width="18" height="14" rx="2" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="65" y="17" text-anchor="middle" font-size="5" fill="#94a3b8">API</text>
      <rect x="56" y="28" width="18" height="14" rx="2" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="65" y="37" text-anchor="middle" font-size="5" fill="#94a3b8">API</text>
      <circle cx="40" cy="25" r="8" fill="#0f1f3d" stroke="#3b82f6" stroke-width="1.5"/>
      <text x="40" y="28" text-anchor="middle" font-size="5" fill="#60a5fa">HUB</text>
      <line x1="24" y1="15" x2="32" y2="22" stroke="#3b82f6" stroke-width="1" stroke-dasharray="2 1"/>
      <line x1="24" y1="35" x2="32" y2="28" stroke="#3b82f6" stroke-width="1" stroke-dasharray="2 1"/>
      <line x1="56" y1="15" x2="48" y2="22" stroke="#3b82f6" stroke-width="1" stroke-dasharray="2 1"/>
      <line x1="56" y1="35" x2="48" y2="28" stroke="#3b82f6" stroke-width="1" stroke-dasharray="2 1"/>
    </svg>`,
  }
  return screens[key] ?? screens['module:analytics']
}

function moduleIcon(key: string): string {
  const icons: Record<string, string> = {
    'module:data': `<svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <ellipse cx="14" cy="8" rx="9" ry="4" stroke="currentColor" stroke-width="1.5"/>
      <path d="M5 8v6c0 2.2 4 4 9 4s9-1.8 9-4V8" stroke="currentColor" stroke-width="1.5"/>
      <path d="M5 14v6c0 2.2 4 4 9 4s9-1.8 9-4v-6" stroke="currentColor" stroke-width="1.5"/>
    </svg>`,
    'module:models': `<svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <circle cx="14" cy="14" r="4" stroke="currentColor" stroke-width="1.5"/>
      <path d="M14 4v4M14 20v4M4 14h4M20 14h4M6.93 6.93l2.83 2.83M18.24 18.24l2.83 2.83M6.93 21.07l2.83-2.83M18.24 9.76l2.83-2.83" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,
  }
  return icons[key] ?? icons['module:data']
}
</script>

<style scoped>
.iso-scene {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 24px 20px;
  background:
    radial-gradient(ellipse at 50% 0%, rgba(59,130,246,.07) 0%, transparent 60%),
    radial-gradient(ellipse at 20% 100%, rgba(16,185,129,.05) 0%, transparent 50%),
    #f8fafc;
  border-radius: 20px;
  border: 1px solid rgba(15,17,23,.06);
  overflow: hidden;
  min-height: 680px;
}

/* ── Layer wrapper ── */
.iso-layer { transition: opacity .5s ease, transform .5s ease; }
.iso-layer--dim { opacity: .35; }
.iso-layer--glow .iso-platform--mid { box-shadow: 0 0 0 1px rgba(16,185,129,.25), 0 24px 60px rgba(16,185,129,.12); }

/* ── Platform (the "slab") ── */
.iso-platform {
  position: relative;
  border-radius: 16px;
  overflow: visible;
}

.iso-platform__face {
  position: relative;
  background: rgba(255,255,255,.92);
  border: 1px solid rgba(15,17,23,.07);
  border-radius: 14px;
  padding: 14px 18px 18px;
  box-shadow: 0 2px 0 rgba(255,255,255,.9) inset, 0 16px 40px rgba(15,17,23,.06);
  transform: perspective(900px) rotateX(5deg);
  transform-origin: bottom center;
}

.iso-platform__face--mid {
  transform: perspective(900px) rotateX(3deg);
  min-height: 300px;
}

/* Thick bottom edge — gives the "slab" illusion */
.iso-platform__edge {
  position: absolute;
  bottom: -10px;
  left: 6px;
  right: 6px;
  height: 12px;
  border-radius: 0 0 12px 12px;
  z-index: -1;
}
.iso-platform__edge--top { background: linear-gradient(180deg, #d4a017, #a07010); }
.iso-platform__edge--mid { background: linear-gradient(180deg, #0d9488, #065f46); }
.iso-platform__edge--bot { background: linear-gradient(180deg, #3b5bdb, #1e3a8a); }

.iso-platform__label {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .16em;
  color: #94a3b8;
  text-transform: uppercase;
  margin-bottom: 12px;
}

/* ── Top layer: app cards with mini screens ── */
.iso-top-modules {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.iso-app-card {
  background: #0d1117;
  border: 1px solid #1e2535;
  border-radius: 10px;
  padding: 0 0 10px;
  cursor: pointer;
  transition: transform .2s, box-shadow .2s;
  text-align: center;
  overflow: hidden;
}
.iso-app-card:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(0,0,0,.2); }
.iso-app-card--sel { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,.3); }

.iso-app-card__screen {
  width: 100%;
  aspect-ratio: 16/10;
  overflow: hidden;
  border-radius: 8px 8px 0 0;
}
.iso-app-card__screen-inner { width: 100%; height: 100%; }
.iso-app-card__label { font-size: 11px; font-weight: 700; color: #e2e8f0; margin-top: 8px; }
.iso-app-card__metric { font-size: 10px; color: #475569; margin-top: 2px; }

/* ── Bottom layer: data cards ── */
.iso-bot-modules {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.iso-data-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: transform .2s, box-shadow .2s;
  text-align: left;
}
.iso-data-card:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(15,17,23,.08); }
.iso-data-card--sel { border-color: #3b82f6; }
.iso-data-card__icon { color: #64748b; margin-bottom: 6px; }
.iso-data-card__label { font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 8px; }
.iso-data-card__grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; }
.iso-data-card__cell { height: 6px; border-radius: 2px; background: #e2e8f0; }
.cell--lit { background: #3b82f6; opacity: .7; }

/* ── Ontology wrap ── */
.iso-ontology-wrap { position: relative; min-height: 280px; }

/* ── Flow zone ── */
.iso-flow {
  position: relative;
  height: 64px;
  margin: -4px 0;
  z-index: 2;
}

.iso-flow__svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.flow-path {
  fill: none;
  stroke: #cbd5e1;
  stroke-width: 1;
  stroke-dasharray: 5 4;
  opacity: .5;
}

.flow-path--active {
  stroke: #10b981;
  opacity: .7;
  animation: dash-flow 1.4s linear infinite;
}

@keyframes dash-flow { to { stroke-dashoffset: -18; } }

.flow-dot {
  position: absolute;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #10b981;
  opacity: 0;
  bottom: 0;
  pointer-events: none;
}

.iso-flow--active .flow-dot--up {
  animation: dot-rise 1.6s ease-in-out infinite;
}

@keyframes dot-rise {
  0%   { bottom: 0;    opacity: 0; transform: scale(.5); }
  15%  { opacity: .9;  transform: scale(1); }
  85%  { opacity: .9;  transform: scale(1); }
  100% { bottom: 100%; opacity: 0; transform: scale(.5); }
}
</style>
