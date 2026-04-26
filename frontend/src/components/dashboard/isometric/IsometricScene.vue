<template>
  <div class="iso-scene" ref="sceneRef"
    @mousedown="onDragStart"
    @mousemove="onDragMove"
    @mouseup="onDragEnd"
    @mouseleave="onDragEnd"
    @wheel.prevent="onWheel">

    <div class="iso-world" :style="worldStyle">
      <!-- 顶层平台 -->
      <div class="iso-platform iso-platform--top" :style="platformStyle('top')">
        <div class="iso-platform__surface">
          <div class="iso-platform__label">APPLICATION LAYER</div>
          <div class="iso-top-grid">
            <button v-for="mod in topModules" :key="mod.key"
              class="iso-card iso-card--app"
              :class="{ 'iso-card--sel': selectedKey === mod.key }"
              @click.stop="$emit('selectTarget', mod.key)">
              <div class="iso-card__screen" v-html="screenSvg(mod.key)"></div>
              <div class="iso-card__label">{{ mod.label }}</div>
            </button>
          </div>
        </div>
        <div class="iso-platform__front"></div>
        <div class="iso-platform__side"></div>
      </div>

      <!-- 中层平台 -->
      <div class="iso-platform iso-platform--mid" :style="platformStyle('mid')">
        <div class="iso-platform__surface iso-platform__surface--mid">
          <div class="iso-platform__label">ONTOLOGY</div>
          <div class="iso-onto-wrap">
            <OntologyNetwork
              :entities="entities"
              :relations="relations"
              :activeStage="activeStage"
              :selectedKey="selectedKey"
              @select="$emit('selectTarget', $event)"
            />
          </div>
        </div>
        <div class="iso-platform__front iso-platform__front--mid"></div>
        <div class="iso-platform__side iso-platform__side--mid"></div>
      </div>

      <!-- 底层平台 -->
      <div class="iso-platform iso-platform--bot" :style="platformStyle('bot')">
        <div class="iso-platform__surface">
          <div class="iso-platform__label">FOUNDATION LAYER</div>
          <div class="iso-bot-grid">
            <button v-for="mod in bottomModules" :key="mod.key"
              class="iso-card iso-card--data"
              :class="{ 'iso-card--sel': selectedKey === mod.key }"
              @click.stop="$emit('selectTarget', mod.key)">
              <div class="iso-card__ds-icon" v-html="dsIcon(mod.key)"></div>
              <div class="iso-card__label">{{ mod.label }}</div>
              <div class="iso-card__bars">
                <div v-for="j in 4" :key="j" class="iso-card__bar-seg"
                  :style="{ height: (30 + j * 15) + '%', opacity: j <= 3 ? 1 : .3 }"></div>
              </div>
            </button>
          </div>
        </div>
        <div class="iso-platform__front iso-platform__front--bot"></div>
        <div class="iso-platform__side iso-platform__side--bot"></div>
      </div>

      <!-- 层间连线 SVG（绝对定位，覆盖整个world） -->
      <svg class="iso-connectors" viewBox="0 0 100 100" preserveAspectRatio="none">
        <defs>
          <linearGradient id="lg-up" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stop-color="#10b981" stop-opacity=".6"/>
            <stop offset="100%" stop-color="#3b82f6" stop-opacity=".3"/>
          </linearGradient>
          <linearGradient id="lg-dn" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#3b82f6" stop-opacity=".6"/>
            <stop offset="100%" stop-color="#10b981" stop-opacity=".3"/>
          </linearGradient>
          <linearGradient id="lg-up-analytics" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stop-color="#10b981" stop-opacity=".5"/>
            <stop offset="100%" stop-color="#3b82f6" stop-opacity=".4"/>
          </linearGradient>
          <linearGradient id="lg-up-workflows" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stop-color="#10b981" stop-opacity=".5"/>
            <stop offset="100%" stop-color="#818cf8" stop-opacity=".4"/>
          </linearGradient>
          <linearGradient id="lg-up-integrations" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stop-color="#10b981" stop-opacity=".5"/>
            <stop offset="100%" stop-color="#f59e0b" stop-opacity=".4"/>
          </linearGradient>
          <linearGradient id="lg-dn-data" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#3b82f6" stop-opacity=".5"/>
            <stop offset="100%" stop-color="#10b981" stop-opacity=".4"/>
          </linearGradient>
          <linearGradient id="lg-dn-models" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#f59e0b" stop-opacity=".5"/>
            <stop offset="100%" stop-color="#10b981" stop-opacity=".4"/>
          </linearGradient>
        </defs>

        <!-- 底→中：DataSource(数据基座) → 本体层 -->
        <g :opacity="activeStage === 'hydrate' ? 0.7 : 0.15">
          <path v-for="(p,i) in dataToOntologyPaths" :key="'dto'+i"
            :d="p" fill="none" stroke="url(#lg-dn-data)" stroke-width=".35"
            :stroke-dasharray="activeStage === 'hydrate' ? '2.5 1.5' : '1 3'"
            :class="{ 'conn-anim': activeStage === 'hydrate' }"
            :style="{ animationDelay: (i * 0.12) + 's' }"/>
        </g>

        <!-- 底→中：LogicSource(规则模型) → 本体层 -->
        <g :opacity="activeStage === 'hydrate' ? 0.7 : 0.15">
          <path v-for="(p,i) in modelsToOntologyPaths" :key="'mto'+i"
            :d="p" fill="none" stroke="url(#lg-dn-models)" stroke-width=".35"
            :stroke-dasharray="activeStage === 'hydrate' ? '2.5 1.5' : '1 3'"
            :class="{ 'conn-anim': activeStage === 'hydrate' }"
            :style="{ animationDelay: (i * 0.12 + 0.06) + 's' }"/>
        </g>

        <!-- 中→顶：本体层 → Analytics(分析视角) -->
        <g :opacity="activeStage === 'wield' ? 0.7 : 0.15">
          <path v-for="(p,i) in ontologyToAnalyticsPaths" :key="'ota'+i"
            :d="p" fill="none" stroke="url(#lg-up-analytics)" stroke-width=".35"
            :stroke-dasharray="activeStage === 'wield' ? '2.5 1.5' : '1 3'"
            :class="{ 'conn-anim': activeStage === 'wield' }"
            :style="{ animationDelay: (i * 0.12) + 's' }"/>
        </g>

        <!-- 中→顶：本体层 → Automations(流程编排) -->
        <g :opacity="activeStage === 'wield' ? 0.7 : 0.15">
          <path v-for="(p,i) in ontologyToWorkflowsPaths" :key="'otw'+i"
            :d="p" fill="none" stroke="url(#lg-up-workflows)" stroke-width=".35"
            :stroke-dasharray="activeStage === 'wield' ? '2.5 1.5' : '1 3'"
            :class="{ 'conn-anim': activeStage === 'wield' }"
            :style="{ animationDelay: (i * 0.12 + 0.06) + 's' }"/>
        </g>

        <!-- 中→顶：本体层 → Products(集成出口) -->
        <g :opacity="activeStage === 'wield' ? 0.7 : 0.15">
          <path v-for="(p,i) in ontologyToIntegrationsPaths" :key="'oti'+i"
            :d="p" fill="none" stroke="url(#lg-up-integrations)" stroke-width=".35"
            :stroke-dasharray="activeStage === 'wield' ? '2.5 1.5' : '1 3'"
            :class="{ 'conn-anim': activeStage === 'wield' }"
            :style="{ animationDelay: (i * 0.12 + 0.12) + 's' }"/>
        </g>
      </svg>
    </div>

    <!-- 旋转提示 -->
    <div class="iso-hint" v-if="!hasDragged">拖拽旋转 · 滚轮缩放</div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive } from 'vue'
import OntologyNetwork from './OntologyNetwork.vue'
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

// ── 3D 旋转状态 ──
const rotX = ref(28)   // 初始俯仰角
const rotY = ref(-20)  // 初始偏转角
const scale = ref(1)
const drag = reactive({ active: false, startX: 0, startY: 0, baseX: 28, baseY: -20 })
const hasDragged = ref(false)
const sceneRef = ref<HTMLElement | null>(null)

function onDragStart(e: MouseEvent) {
  drag.active = true
  drag.startX = e.clientX
  drag.startY = e.clientY
  drag.baseX = rotX.value
  drag.baseY = rotY.value
}
function onDragMove(e: MouseEvent) {
  if (!drag.active) return
  hasDragged.value = true
  const dx = e.clientX - drag.startX
  const dy = e.clientY - drag.startY
  rotY.value = drag.baseY + dx * 0.4
  rotX.value = Math.max(5, Math.min(60, drag.baseX + dy * 0.3))
}
function onDragEnd() { drag.active = false }
function onWheel(e: WheelEvent) {
  scale.value = Math.max(0.5, Math.min(1.8, scale.value - e.deltaY * 0.001))
}

const worldStyle = computed(() => ({
  transform: `rotateX(${rotX.value}deg) rotateY(${rotY.value}deg) scale(${scale.value})`,
  cursor: drag.active ? 'grabbing' : 'grab',
}))

// 平台垂直偏移
function platformStyle(layer: 'top' | 'mid' | 'bot') {
  const offsets = { top: -160, mid: 0, bot: 160 }
  return { transform: `translateY(${offsets[layer]}px)` }
}

// 层间连线：模仿本体层实体间的曲线风格
// 底层 grid 2列: 数据基座(左25%) 规则模型(右75%)
// 中层本体锚点散布在 y=50 附近
// 顶层 grid 3列: 分析视角(左17%) 流程编排(中50%) 集成出口(右83%)

function buildCurvedPaths(
  sources: { x: number; y: number }[],
  targets: { x: number; y: number }[],
  count: number,
  curvature = 0.15,
) {
  const paths: string[] = []
  for (let i = 0; i < count; i++) {
    const s = sources[i % sources.length]
    const t = targets[i % targets.length]
    const jx = (i - count / 2) * 1.8
    const jy = (i % 3 - 1) * 2.5
    const sx = s.x + jx
    const sy = s.y + jy * 0.3
    const tx = t.x + jx * 0.6
    const ty = t.y - jy * 0.3
    const dx = tx - sx
    const dy = ty - sy
    const cx1 = sx + dx * 0.35 + dy * curvature
    const cy1 = sy + dy * 0.35 - dx * curvature * 0.5
    const cx2 = sx + dx * 0.65 - dy * curvature
    const cy2 = sy + dy * 0.65 + dx * curvature * 0.5
    paths.push(`M${sx.toFixed(1)},${sy.toFixed(1)} C${cx1.toFixed(1)},${cy1.toFixed(1)} ${cx2.toFixed(1)},${cy2.toFixed(1)} ${tx.toFixed(1)},${ty.toFixed(1)}`)
  }
  return paths
}

const ontoAnchors = [
  { x: 30, y: 50 }, { x: 42, y: 48 }, { x: 50, y: 51 },
  { x: 58, y: 49 }, { x: 70, y: 50 }, { x: 36, y: 52 },
]

// 底→中: DataSource(数据基座, 左列) → 本体层
const dataToOntologyPaths = computed(() => buildCurvedPaths(
  [{ x: 20, y: 88 }, { x: 25, y: 87 }, { x: 30, y: 89 }, { x: 18, y: 88 }, { x: 28, y: 87 }, { x: 22, y: 89 }],
  [ontoAnchors[0], ontoAnchors[1], ontoAnchors[2], ontoAnchors[5], ontoAnchors[3], ontoAnchors[4]],
  6, 0.12,
))

// 底→中: LogicSource(规则模型, 右列) → 本体层
const modelsToOntologyPaths = computed(() => buildCurvedPaths(
  [{ x: 70, y: 88 }, { x: 75, y: 87 }, { x: 80, y: 89 }, { x: 72, y: 88 }, { x: 78, y: 87 }, { x: 68, y: 89 }],
  [ontoAnchors[4], ontoAnchors[3], ontoAnchors[2], ontoAnchors[1], ontoAnchors[0], ontoAnchors[5]],
  6, 0.12,
))

// 中→顶: 本体层 → Analytics(分析视角, 左列)
const ontologyToAnalyticsPaths = computed(() => buildCurvedPaths(
  [ontoAnchors[0], ontoAnchors[1], ontoAnchors[5], ontoAnchors[2], ontoAnchors[0], ontoAnchors[1]],
  [{ x: 14, y: 38 }, { x: 18, y: 37 }, { x: 16, y: 39 }, { x: 20, y: 38 }, { x: 12, y: 37 }, { x: 22, y: 39 }],
  6, 0.12,
))

// 中→顶: 本体层 → Workflows(流程编排, 中列)
const ontologyToWorkflowsPaths = computed(() => buildCurvedPaths(
  [ontoAnchors[2], ontoAnchors[1], ontoAnchors[3], ontoAnchors[5], ontoAnchors[2], ontoAnchors[3]],
  [{ x: 47, y: 38 }, { x: 50, y: 37 }, { x: 53, y: 39 }, { x: 48, y: 38 }, { x: 52, y: 37 }, { x: 50, y: 39 }],
  6, 0.10,
))

// 中→顶: 本体层 → Integrations(集成出口, 右列)
const ontologyToIntegrationsPaths = computed(() => buildCurvedPaths(
  [ontoAnchors[4], ontoAnchors[3], ontoAnchors[2], ontoAnchors[4], ontoAnchors[3], ontoAnchors[2]],
  [{ x: 80, y: 38 }, { x: 84, y: 37 }, { x: 82, y: 39 }, { x: 86, y: 38 }, { x: 78, y: 37 }, { x: 88, y: 39 }],
  6, 0.12,
))

function screenSvg(key: string): string {
  const m: Record<string, string> = {
    'module:analytics': `<svg width="100%" height="100%" viewBox="0 0 120 68" fill="none">
      <rect width="120" height="68" rx="3" fill="#0f172a"/>
      <rect x="8" y="40" width="10" height="20" rx="1" fill="#3b82f6" opacity=".7"/>
      <rect x="22" y="30" width="10" height="30" rx="1" fill="#3b82f6"/>
      <rect x="36" y="20" width="10" height="40" rx="1" fill="#60a5fa"/>
      <rect x="50" y="34" width="10" height="26" rx="1" fill="#3b82f6" opacity=".8"/>
      <rect x="64" y="12" width="10" height="48" rx="1" fill="#3b82f6"/>
      <polyline points="13,38 27,28 41,18 55,32 69,10 83,24" stroke="#10b981" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="13" cy="38" r="3" fill="#10b981"/>
      <circle cx="69" cy="10" r="3" fill="#10b981"/>
    </svg>`,
    'module:workflows': `<svg width="100%" height="100%" viewBox="0 0 120 68" fill="none">
      <rect width="120" height="68" rx="3" fill="#0f172a"/>
      <rect x="40" y="5" width="40" height="13" rx="2.5" fill="#1e3a5f" stroke="#3b82f6" stroke-width="1"/>
      <text x="60" y="14.5" text-anchor="middle" font-size="6.5" fill="#60a5fa" font-family="monospace">TRIGGER</text>
      <line x1="60" y1="18" x2="60" y2="25" stroke="#3b82f6" stroke-width="1.2" stroke-dasharray="2 2"/>
      <rect x="12" y="25" width="36" height="13" rx="2.5" fill="#052e16" stroke="#10b981" stroke-width="1"/>
      <text x="30" y="34" text-anchor="middle" font-size="6" fill="#10b981" font-family="monospace">RULE CHECK</text>
      <rect x="72" y="25" width="36" height="13" rx="2.5" fill="#1e1b4b" stroke="#818cf8" stroke-width="1"/>
      <text x="90" y="34" text-anchor="middle" font-size="6.5" fill="#818cf8" font-family="monospace">ACTION</text>
      <line x1="30" y1="38" x2="60" y2="48" stroke="#10b981" stroke-width="1" stroke-dasharray="2 2"/>
      <line x1="90" y1="38" x2="60" y2="48" stroke="#818cf8" stroke-width="1" stroke-dasharray="2 2"/>
      <rect x="36" y="48" width="48" height="13" rx="2.5" fill="#2d1f00" stroke="#f59e0b" stroke-width="1"/>
      <text x="60" y="57" text-anchor="middle" font-size="6.5" fill="#f59e0b" font-family="monospace">DISPATCH</text>
    </svg>`,
    'module:integrations': `<svg width="100%" height="100%" viewBox="0 0 120 68" fill="none">
      <rect width="120" height="68" rx="3" fill="#0f172a"/>
      <rect x="5" y="10" width="24" height="16" rx="2.5" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="17" y="21" text-anchor="middle" font-size="6.5" fill="#94a3b8" font-family="monospace">API</text>
      <rect x="5" y="42" width="24" height="16" rx="2.5" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="17" y="53" text-anchor="middle" font-size="6.5" fill="#94a3b8" font-family="monospace">API</text>
      <rect x="91" y="10" width="24" height="16" rx="2.5" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="103" y="21" text-anchor="middle" font-size="6.5" fill="#94a3b8" font-family="monospace">API</text>
      <rect x="91" y="42" width="24" height="16" rx="2.5" fill="#1e2535" stroke="#475569" stroke-width="1"/>
      <text x="103" y="53" text-anchor="middle" font-size="6.5" fill="#94a3b8" font-family="monospace">API</text>
      <circle cx="60" cy="34" r="14" fill="#0f1f3d" stroke="#3b82f6" stroke-width="1.5"/>
      <text x="60" y="37" text-anchor="middle" font-size="7.5" fill="#60a5fa" font-family="monospace">HUB</text>
      <line x1="29" y1="18" x2="46" y2="28" stroke="#3b82f6" stroke-width="1" stroke-dasharray="2 2"/>
      <line x1="29" y1="50" x2="46" y2="40" stroke="#3b82f6" stroke-width="1" stroke-dasharray="2 2"/>
      <line x1="91" y1="18" x2="74" y2="28" stroke="#3b82f6" stroke-width="1" stroke-dasharray="2 2"/>
      <line x1="91" y1="50" x2="74" y2="40" stroke="#3b82f6" stroke-width="1" stroke-dasharray="2 2"/>
    </svg>`,
  }
  return m[key] ?? m['module:analytics']
}

function dsIcon(key: string): string {
  if (key.includes('data')) return `<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><ellipse cx="11" cy="5.5" rx="8" ry="3" stroke="#64748b" stroke-width="1.4"/><path d="M3 5.5v5c0 1.66 3.58 3 8 3s8-1.34 8-3v-5" stroke="#64748b" stroke-width="1.4"/><path d="M3 10.5v5c0 1.66 3.58 3 8 3s8-1.34 8-3v-5" stroke="#64748b" stroke-width="1.4"/></svg>`
  return `<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><circle cx="11" cy="11" r="3.5" stroke="#64748b" stroke-width="1.4"/><path d="M11 2v3M11 17v3M2 11h3M17 11h3M4.64 4.64l2.12 2.12M15.24 15.24l2.12 2.12M4.64 17.36l2.12-2.12M15.24 6.76l2.12-2.12" stroke="#64748b" stroke-width="1.4" stroke-linecap="round"/></svg>`
}
</script>

<style scoped>
/* ── Scene container ── */
.iso-scene {
  position: relative;
  width: 100%;
  height: 680px;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 50% 30%, rgba(59,130,246,.06) 0%, transparent 60%),
    radial-gradient(ellipse at 20% 80%, rgba(16,185,129,.04) 0%, transparent 50%),
    #f0f4f8;
  border-radius: 20px;
  border: 1px solid rgba(15,17,23,.05);
  user-select: none;
}

/* ── 3D world ── */
.iso-world {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transform-style: preserve-3d;
  transition: transform .05s linear;
  will-change: transform;
}

/* ── Platform ── */
.iso-platform {
  position: absolute;
  width: 680px;
  transform-style: preserve-3d;
}

/* Surface (top face) */
.iso-platform__surface {
  position: relative;
  background: rgba(255,255,255,.55);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,.7);
  border-radius: 16px;
  padding: 14px 18px 18px;
  box-shadow: 0 2px 24px rgba(15,17,23,.06);
}
.iso-platform__surface--mid {
  background: rgba(255,255,255,.6);
  min-height: 300px;
}

/* Front face (bottom edge) */
.iso-platform__front {
  position: absolute;
  bottom: -14px;
  left: 8px;
  right: 8px;
  height: 14px;
  border-radius: 0 0 10px 10px;
  background: linear-gradient(180deg, rgba(200,210,230,.6) 0%, rgba(160,175,200,.4) 100%);
  border: 1px solid rgba(255,255,255,.4);
  border-top: none;
}
.iso-platform__front--mid { background: linear-gradient(180deg, rgba(16,185,129,.25) 0%, rgba(16,185,129,.1) 100%); }
.iso-platform__front--bot { background: linear-gradient(180deg, rgba(59,130,246,.25) 0%, rgba(59,130,246,.1) 100%); }

/* Side face (right edge) */
.iso-platform__side {
  position: absolute;
  top: 8px;
  right: -14px;
  bottom: -6px;
  width: 14px;
  border-radius: 0 10px 10px 0;
  background: linear-gradient(90deg, rgba(200,210,230,.5) 0%, rgba(160,175,200,.3) 100%);
  border: 1px solid rgba(255,255,255,.35);
  border-left: none;
}
.iso-platform__side--mid { background: linear-gradient(90deg, rgba(16,185,129,.2) 0%, rgba(16,185,129,.08) 100%); }
.iso-platform__side--bot { background: linear-gradient(90deg, rgba(59,130,246,.2) 0%, rgba(59,130,246,.08) 100%); }

.iso-platform__label {
  font-size: var(--text-caption-upper-size);
  font-weight: 800;
  letter-spacing: .16em;
  color: var(--neutral-500);
  text-transform: uppercase;
  margin-bottom: 10px;
}

/* ── App cards (top layer) ── */
.iso-top-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.iso-card {
  border-radius: 10px;
  cursor: pointer;
  transition: transform .2s, box-shadow .2s;
  text-align: left;
  border: 1px solid rgba(15,17,23,.07);
  background: rgba(255,255,255,.7);
  backdrop-filter: blur(8px);
  overflow: hidden;
}
.iso-card:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(15,17,23,.1); }
.iso-card--sel { border-color: rgba(59,130,246,.4); box-shadow: 0 0 0 2px rgba(59,130,246,.15); }

.iso-card--app .iso-card__screen { width: 100%; aspect-ratio: 16/9; display: block; }
.iso-card__label { font-size: var(--text-caption-size); font-weight: 700; color: var(--neutral-900); padding: 6px 10px 8px; }

/* ── Data cards (bottom layer) ── */
.iso-bot-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.iso-card--data { padding: 12px; }
.iso-card__ds-icon { color: var(--neutral-700); margin-bottom: 6px; }
.iso-card__bars { display: flex; align-items: flex-end; gap: 3px; height: 28px; margin-top: 8px; }
.iso-card__bar-seg { width: 8px; border-radius: 2px 2px 0 0; background: linear-gradient(180deg, #3b82f6, #10b981); }

/* ── Ontology wrap ── */
.iso-onto-wrap { position: relative; min-height: 260px; }

/* ── Connector SVG ── */
.iso-connectors {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.conn-anim {
  animation: dash-flow 2.2s linear infinite;
}
@keyframes dash-flow { to { stroke-dashoffset: -10; } }

/* ── Hint ── */
.iso-hint {
  position: absolute;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  font-size: var(--text-caption-size);
  color: var(--neutral-500);
  background: rgba(255,255,255,.7);
  backdrop-filter: blur(8px);
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid rgba(15,17,23,.06);
  pointer-events: none;
  animation: fadeOut 3s ease 2s forwards;
}
@keyframes fadeOut { to { opacity: 0; } }
</style>
