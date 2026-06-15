<template>
  <div class="twin-view">
    <!-- 上方：本体活体网络 SVG panorama -->
    <section class="twin-view__panorama">
      <header class="twin-view__panorama-head">
        <span class="twin-view__panorama-title">本体活体网络</span>
        <span class="twin-view__panorama-sub">节点大小 = 实例数对数刻度 · 流光 = 实时事件</span>
      </header>

      <div class="twin-view__svg-wrap">
        <svg
          ref="svgRef"
          :viewBox="`-100 -100 ${svgW} ${svgH}`"
          preserveAspectRatio="xMidYMid meet"
          width="100%"
          height="100%"
        >
          <defs>
            <pattern id="twinGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" stroke-width="0.5" />
            </pattern>
            <radialGradient id="twinPulse">
              <stop offset="0%" stop-color="#ffffff" stop-opacity="0" />
              <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
            </radialGradient>
          </defs>
          <rect :x="-100" :y="-100" :width="svgW" :height="svgH" fill="url(#twinGrid)" />

          <!-- 连线 -->
          <g>
            <g v-for="(link, idx) in renderedLinks" :key="link.id">
              <path
                :id="`twin-path-${idx}`"
                :d="link.path"
                fill="none"
                :stroke="link.stroke"
                stroke-width="1.5"
              />
              <text
                v-if="link.label"
                :x="link.midX"
                :y="link.midY - 3"
                class="twin-view__link-label"
                text-anchor="middle"
              >
                {{ link.label }}
              </text>
              <circle
                v-if="link.hasFlow"
                r="2.6"
                :fill="link.particleColor"
              >
                <animateMotion :dur="`${2.8 + idx % 5 * 0.4}s`" repeatCount="indefinite">
                  <mpath :href="`#twin-path-${idx}`" />
                </animateMotion>
                <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.9;1" :dur="`${2.8 + idx % 5 * 0.4}s`" repeatCount="indefinite" />
              </circle>
            </g>
          </g>

          <!-- 节点 -->
          <g>
            <g
              v-for="node in renderedNodes"
              :key="node.id"
              :style="{ cursor: 'pointer', opacity: filterTier === null || node.tier === filterTier ? 1 : 0.15 }"
              @click="onNodeClick(node.id)"
            >
              <circle
                :cx="node.x"
                :cy="node.y"
                :r="node.r + 4"
                :fill="node.color"
                opacity="0.3"
              >
                <animate attributeName="r" :values="`${node.r + 4};${(node.r + 4) * 1.4};${node.r + 4}`" :dur="`${2 + node.tier * 0.5}s`" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.3;0.1;0.3" :dur="`${2 + node.tier * 0.5}s`" repeatCount="indefinite" />
              </circle>
              <circle
                :cx="node.x"
                :cy="node.y"
                :r="node.r"
                :fill="`${node.color}33`"
                :stroke="node.color"
                stroke-width="1.5"
              />
              <text :x="node.x" :y="node.y + node.r + 14" class="twin-view__node-label" text-anchor="middle">
                {{ node.label }}
              </text>
              <text :x="node.x" :y="node.y + node.r + 26" class="twin-view__node-count" text-anchor="middle">
                {{ formatCount(node.count) }}
              </text>
            </g>
          </g>
        </svg>

        <!-- Tier 图例 -->
        <div class="twin-view__legend">
          <span
            v-for="t in legendTiers"
            :key="t.tier"
            class="twin-view__legend-item"
            :class="{ 'twin-view__legend-item--active': filterTier === t.tier }"
            @click="filterTier = filterTier === t.tier ? null : t.tier"
            :style="{ color: filterTier === t.tier ? t.color : '#64748b' }"
          >
            <span class="twin-view__legend-dot" :style="{ background: t.color }"></span>
            {{ t.label }}
          </span>
        </div>
      </div>
    </section>

    <!-- 下方：4 卡片 dashboard -->
    <section class="twin-view__grid">
      <!-- 实时事件流 -->
      <div class="twin-card">
        <header class="twin-card__head">
          <span class="twin-card__title">实时事件流</span>
          <span class="twin-card__tag" :style="{ color: useRealEvents ? '#10b981' : '#94a3b8' }">
            {{ useRealEvents ? 'EVENT BUS · LIVE' : 'EVENT BUS · DEMO' }}
          </span>
        </header>
        <div class="twin-card__events">
          <div
            v-for="(ev, i) in events"
            :key="ev.id"
            class="twin-event"
            :class="{ 'twin-event--new': i === 0 }"
            :style="{ opacity: i > 18 ? 0.45 : 1 }"
          >
            <span class="twin-event__ts">{{ ev.ts }}</span>
            <span class="twin-event__icon" :style="{ color: eventColor(ev.type) }">{{ ev.icon }}</span>
            <span class="twin-event__desc">{{ ev.desc }}</span>
            <span v-if="i === 0" class="twin-event__new">NEW</span>
          </div>
        </div>
      </div>

      <!-- 三盒指标 -->
      <div class="twin-card">
        <header class="twin-card__head">
          <span class="twin-card__title">三盒指标</span>
          <span class="twin-card__tag">T-BOX · A-BOX · R-BOX</span>
        </header>
        <div class="twin-card__metrics">
          <div v-for="m in metrics" :key="m.label" class="twin-metric">
            <div class="twin-metric__label">{{ m.label }}</div>
            <div class="twin-metric__value">{{ m.value }}</div>
            <div class="twin-metric__foot">
              <span>{{ m.sub }}</span>
              <span :style="{ color: m.tagTone }" class="twin-metric__tag">{{ m.tag }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 系统呼吸 -->
      <div class="twin-card">
        <header class="twin-card__head">
          <span class="twin-card__title">系统呼吸</span>
          <span class="twin-card__tag">HEARTBEAT</span>
        </header>
        <div class="twin-card__heartbeat">
          <div class="twin-heart">
            <div>
              <div class="twin-heart__label">决策 / 分钟</div>
              <div class="twin-heart__value" :style="{ color: heartTone(decisionPerMin, 80, 180) }">{{ decisionPerMin }}</div>
            </div>
            <div class="twin-heart__bars">
              <span
                v-for="(h, i) in decisionBars"
                :key="i"
                class="twin-heart__bar"
                :style="{ height: `${Math.max(6, h * 100)}%`, background: heartTone(decisionPerMin, 80, 180) }"
              />
            </div>
          </div>
          <div class="twin-heart">
            <div>
              <div class="twin-heart__label">推理 / 分钟</div>
              <div class="twin-heart__value" :style="{ color: heartTone(inferencePerMin, 600, 1200) }">{{ inferencePerMin }}</div>
            </div>
            <div class="twin-heart__bars">
              <span
                v-for="(h, i) in inferenceBars"
                :key="i"
                class="twin-heart__bar"
                :style="{ height: `${Math.max(6, h * 100)}%`, background: heartTone(inferencePerMin, 600, 1200) }"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 异常告警 -->
      <div class="twin-card">
        <header class="twin-card__head">
          <span class="twin-card__title">异常告警</span>
          <span class="twin-card__tag">{{ alerts.length }} 条 · 实时</span>
        </header>
        <div class="twin-card__alerts">
          <div
            v-for="a in alerts"
            :key="a.id"
            class="twin-alert"
            :class="`twin-alert--${a.tone}`"
          >
            <span class="twin-alert__icon">{{ alertIcon(a.tone) }}</span>
            <div class="twin-alert__body">
              <div class="twin-alert__title">
                <span class="twin-alert__priority" :style="{ color: alertColor(a.tone), background: alertColor(a.tone) + '14', borderColor: alertColor(a.tone) + '55' }">
                  {{ a.priority }}
                </span>
                <span>{{ a.title }}</span>
              </div>
              <div class="twin-alert__detail">{{ a.detail }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import type { StudioObjectType, StudioLinkType } from '../../api/studio'
import { studioApi } from '../../api/studio'

const props = defineProps<{
  objects: StudioObjectType[]
  relations: StudioLinkType[]
  selected?: StudioObjectType | null
}>()

const emit = defineEmits<{ (e: 'select', obj: StudioObjectType): void }>()

const svgRef = ref<SVGSVGElement | null>(null)
const svgW = 1300
const svgH = 700

const tierColor: Record<1 | 2 | 3, string> = { 1: '#2E5BFF', 2: '#00C7B1', 3: '#FF6B35' }
const filterTier = ref<1 | 2 | 3 | null>(null)

const legendTiers = [
  { tier: 1 as const, color: tierColor[1], label: 'Tier1 核心' },
  { tier: 2 as const, color: tierColor[2], label: 'Tier2 领域' },
  { tier: 3 as const, color: tierColor[3], label: 'Tier3 场景' },
]

// ── 节点布局：分三个区域（T1 居中 / T2 上方 / T3 周边）──
const renderedNodes = computed(() => {
  const cx = 540
  const cy = 250
  const t1 = props.objects.filter(o => o.tier === 1)
  const t2 = props.objects.filter(o => o.tier === 2)
  const t3 = props.objects.filter(o => o.tier === 3)

  const out: Array<{
    id: string; label: string; tier: 1 | 2 | 3; x: number; y: number; r: number; color: string; count: number
  }> = []

  // T1 圆内
  t1.forEach((o, i) => {
    const theta = (i / Math.max(t1.length, 3)) * 2 * Math.PI - Math.PI / 2
    out.push({
      id: o.apiName, label: o.displayName, tier: 1,
      x: cx + Math.cos(theta) * 110, y: cy + Math.sin(theta) * 110,
      r: nodeRadius(o.aboxScale), color: tierColor[1], count: o.aboxScale,
    })
  })

  // T2 顶部环
  t2.forEach((o, i) => {
    const theta = (i / Math.max(t2.length, 3)) * Math.PI - Math.PI / 2 - 0.3
    out.push({
      id: o.apiName, label: o.displayName, tier: 2,
      x: cx + Math.cos(theta) * 260, y: cy - 80 + Math.sin(theta) * 100,
      r: nodeRadius(o.aboxScale), color: tierColor[2], count: o.aboxScale,
    })
  })

  // T3 外层
  t3.forEach((o, i) => {
    const theta = (i / Math.max(t3.length, 6)) * 2 * Math.PI
    const isUpper = Math.sin(theta) < 0
    out.push({
      id: o.apiName, label: o.displayName, tier: 3,
      x: cx + Math.cos(theta) * 420,
      y: cy + Math.sin(theta) * (isUpper ? 240 : 280),
      r: nodeRadius(o.aboxScale), color: tierColor[3], count: o.aboxScale,
    })
  })

  return out
})

const nodeMap = computed(() => {
  const m = new Map<string, typeof renderedNodes.value[0]>()
  for (const n of renderedNodes.value) m.set(n.id, n)
  return m
})

const renderedLinks = computed(() => {
  return props.relations
    .map((r, i) => {
      const s = nodeMap.value.get(r.source)
      const t = nodeMap.value.get(r.target)
      if (!s || !t) return null
      const visible = (filterTier.value === null) || s.tier === filterTier.value || t.tier === filterTier.value
      return {
        id: `${r.source}-${r.target}-${i}`,
        path: `M ${s.x} ${s.y} L ${t.x} ${t.y}`,
        stroke: visible ? 'rgba(148,163,184,0.5)' : 'rgba(148,163,184,0.08)',
        label: visible ? r.displayName : '',
        midX: (s.x + t.x) / 2,
        midY: (s.y + t.y) / 2,
        hasFlow: visible && (i % 4 === 0),  // 1/4 关系显示粒子流
        particleColor: tierColor[s.tier as 1 | 2 | 3],
      }
    })
    .filter((x): x is NonNullable<typeof x> => x !== null)
})

function nodeRadius(count: number): number {
  const base = 8 + Math.log10(Math.max(2, count + 1)) * 6
  return Math.min(28, Math.max(10, base))
}

function formatCount(n: number): string {
  if (n === 0) return '—'
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(n)
}

function onNodeClick(id: string) {
  const obj = props.objects.find(o => o.apiName === id)
  if (obj) emit('select', obj)
}

// ── 实时事件流 ──
interface EventItem { id: string; ts: string; type: string; icon: string; desc: string }
const events = ref<EventItem[]>([])
const useRealEvents = ref(false)
function nowTime(): string {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}
function formatTs(iso: string): string {
  if (!iso) return nowTime()
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}
async function fetchRealEvents() {
  try {
    const res = await studioApi.events(30)
    if (res.events && res.events.length > 0) {
      useRealEvents.value = true
      events.value = res.events.map(e => ({ ...e, ts: formatTs(e.ts) }))
      return true
    }
  } catch (e) {
    console.warn('events api failed', e)
  }
  return false
}
function eventColor(type: string): string {
  return ({ state_change: '#5E6AD2', touchpoint: '#06B6D4', order: '#10B981', skill: '#A78BFA', rule: '#F59E0B', alert: '#EF4444', ml: '#EC4899', segment: '#3B82F6' } as Record<string, string>)[type] || '#94a3b8'
}

// ── 三盒指标 ──
const aboxLive = ref(34242)
const metrics = computed(() => [
  { label: 'T-box 类型', value: String(props.objects.length), sub: `基线 ${props.objects.length}`, tag: '基线达标', tagTone: '#10B981' },
  { label: 'A-box 实例', value: aboxLive.value.toLocaleString(), sub: '过去 5 分钟 +127', tag: '↑', tagTone: '#10B981' },
  { label: 'R-box 关系', value: String(props.relations.length), sub: `基线 ${props.relations.length}`, tag: '基线达标', tagTone: '#10B981' },
  { label: 'Skill · 演化', value: '5', sub: '点击审议 →', tag: '7 待审', tagTone: '#F59E0B' },
])

// ── 系统呼吸 ──
const decisionPerMin = ref(127)
const inferencePerMin = ref(892)
const decisionBars = ref([0.5, 0.7, 0.6, 0.8, 0.65])
const inferenceBars = ref([0.6, 0.55, 0.8, 0.7, 0.75])

function heartTone(v: number, lo: number, hi: number): string {
  return v < lo ? '#EF4444' : v > hi ? '#F59E0B' : '#10B981'
}

// ── 异常告警 ──
const alerts = [
  { id: 'A-001', priority: 'P1', tone: 'critical', title: 'SEG_001 转化漂移', detail: '近 24h 续约转化 0.32%,低于阈值 0.55% 达 38%' },
  { id: 'A-002', priority: 'P1', tone: 'critical', title: '装机退单激增', detail: '某地市 InstallChurn 24h 暴涨 47%,工程师未达约占比 62%' },
  { id: 'A-003', priority: 'P2', tone: 'warn', title: 'KPI 营收YTD 异常', detail: '某地市同比 -12.3%,血缘溯源指向异网竞争' },
  { id: 'A-004', priority: 'P2', tone: 'warn', title: 'BR-SCORE-005 命中率下降', detail: '过去 6h 命中率 0.18,基线 0.42' },
  { id: 'A-005', priority: 'P2', tone: 'warn', title: 'PendingPool 积压告警', detail: '待装地址积压 200,超阈值 150' },
  { id: 'A-006', priority: 'P3', tone: 'info', title: 'TouchEvent 异议高发', detail: 'Objection.价格异议 触发率 0.34,建议刷新话术' },
] as const

function alertColor(tone: string): string {
  return tone === 'critical' ? '#EF4444' : tone === 'warn' ? '#F59E0B' : '#3B82F6'
}
function alertIcon(tone: string): string {
  return tone === 'critical' ? '🔴' : tone === 'warn' ? '🟡' : '🟢'
}

// ── 定时器 ──
let eventTimer: number | undefined
let heartbeatTimer: number | undefined

onMounted(async () => {
  await fetchRealEvents()

  eventTimer = window.setInterval(async () => {
    if (useRealEvents.value) {
      await fetchRealEvents()
    }
  }, 5000)

  heartbeatTimer = window.setInterval(() => {
    decisionPerMin.value = Math.max(60, Math.min(220, decisionPerMin.value + Math.floor((Math.random() - 0.45) * 24)))
    inferencePerMin.value = Math.max(500, Math.min(1400, inferencePerMin.value + Math.floor((Math.random() - 0.45) * 120)))
    decisionBars.value = [...decisionBars.value.slice(1), 0.4 + Math.random() * 0.55]
    inferenceBars.value = [...inferenceBars.value.slice(1), 0.4 + Math.random() * 0.55]
  }, 2000)
})

onBeforeUnmount(() => {
  if (eventTimer) window.clearInterval(eventTimer)
  if (heartbeatTimer) window.clearInterval(heartbeatTimer)
})
</script>

<style scoped>
.twin-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px 18px;
  background: #fafafa;
  overflow: auto;
}

.twin-view__panorama {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
}
.twin-view__panorama-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid #f1f5f9;
}
.twin-view__panorama-title { font-size: 13px; font-weight: 600; color: #1a1a2e; letter-spacing: 0.3px; }
.twin-view__panorama-sub { font-size: 10px; color: #94a3b8; font-family: monospace; }

.twin-view__svg-wrap {
  position: relative;
  width: 100%;
  height: 460px;
  margin-top: 10px;
}

.twin-view__link-label {
  font-size: 8px;
  fill: #94a3b8;
  font-family: monospace;
  pointer-events: none;
}
.twin-view__node-label {
  font-size: 10px;
  fill: #334155;
  font-weight: 600;
  pointer-events: none;
}
.twin-view__node-count {
  font-size: 9px;
  fill: #94a3b8;
  font-family: monospace;
  pointer-events: none;
}

.twin-view__legend {
  position: absolute;
  bottom: 8px;
  left: 8px;
  display: flex;
  gap: 12px;
  background: rgba(255,255,255,0.9);
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  font-size: 11px;
}
.twin-view__legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}
.twin-view__legend-item--active { font-weight: 700; }
.twin-view__legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

/* 卡片网格 */
.twin-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.twin-card {
  background: #fff;
  border: 1px solid #e4e4e7;
  border-radius: 8px;
  padding: 14px;
  height: 300px;
  display: flex;
  flex-direction: column;
}
.twin-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f1f3;
  margin-bottom: 10px;
}
.twin-card__title { font-size: 12px; font-weight: 600; color: #18181b; letter-spacing: 0.4px; }
.twin-card__tag { font-size: 10px; color: #6b7280; font-family: monospace; }

/* 事件流 */
.twin-card__events {
  flex: 1;
  overflow-y: auto;
  font-family: 'SF Mono', 'JetBrains Mono', Menlo, monospace;
  font-size: 11px;
  line-height: 1.7;
}
.twin-event {
  display: flex;
  gap: 8px;
  padding: 3px 0;
  color: #374151;
  transition: opacity 0.6s;
}
.twin-event__ts { color: #6b7280; flex-shrink: 0; }
.twin-event__icon { flex-shrink: 0; width: 14px; }
.twin-event__desc { flex: 1; }
.twin-event__new {
  font-size: 9px;
  font-weight: 700;
  color: #10b981;
  background: #10b98122;
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid #10b98155;
  flex-shrink: 0;
}

/* 三盒指标 */
.twin-card__metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  flex: 1;
}
.twin-metric {
  background: #fafafa;
  border: 1px solid #f1f1f3;
  border-radius: 6px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.twin-metric__label { font-size: 11px; color: #6b7280; }
.twin-metric__value {
  font-size: 22px;
  font-weight: 700;
  color: #18181b;
  letter-spacing: -0.5px;
  font-family: 'SF Mono', Menlo, monospace;
}
.twin-metric__foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
}
.twin-metric__foot > span:first-child { color: #6b7280; }
.twin-metric__tag { font-weight: 600; }

/* 系统呼吸 */
.twin-card__heartbeat {
  display: grid;
  grid-template-rows: 1fr 1fr;
  gap: 12px;
  flex: 1;
}
.twin-heart {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.twin-heart__label { font-size: 11px; color: #6b7280; margin-bottom: 4px; }
.twin-heart__value {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.5px;
  font-family: 'SF Mono', Menlo, monospace;
}
.twin-heart__bars {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 36px;
}
.twin-heart__bar {
  width: 6px;
  border-radius: 1px;
  transition: height 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 告警 */
.twin-card__alerts {
  flex: 1;
  overflow-y: auto;
}
.twin-alert {
  display: flex;
  gap: 8px;
  padding: 8px 6px;
  border-bottom: 1px solid #f8f8fa;
  align-items: flex-start;
}
.twin-alert--critical { background: #fef2f2; }
.twin-alert__icon { font-size: 11px; line-height: 14px; }
.twin-alert__body { flex: 1; min-width: 0; }
.twin-alert__title {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 2px;
  font-size: 12px;
  font-weight: 600;
  color: #18181b;
}
.twin-alert__priority {
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid;
}
.twin-alert__detail {
  font-size: 11px;
  color: #6b7280;
  line-height: 1.5;
}
</style>
