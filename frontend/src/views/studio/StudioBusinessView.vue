<template>
  <div class="biz-view">
    <!-- 顶部：场景切换 + R/A-box toggle -->
    <header class="biz-view__head">
      <div class="biz-view__tabs">
        <button
          v-for="t in scenarioTabs"
          :key="t.value"
          class="biz-view__tab"
          :class="{ 'biz-view__tab--active': activeTab === t.value }"
          @click="activeTab = t.value"
        >
          {{ t.label }}
        </button>
      </div>

      <div class="biz-view__meta">
        <span class="biz-view__badge biz-view__badge--blue">{{ filteredNodes.length }} 个对象</span>
        <span class="biz-view__badge biz-view__badge--cyan">{{ filteredEdges.length }} 条关系</span>
      </div>

      <div v-if="activeTab !== 'tier1'" class="biz-view__overlays">
        <button class="biz-view__overlay" :class="{ 'biz-view__overlay--active biz-view__overlay--rbox': showRbox }" @click="showRbox = !showRbox">
          R-box {{ showRbox ? '✓' : '' }}
        </button>
        <button class="biz-view__overlay" :class="{ 'biz-view__overlay--active biz-view__overlay--abox': showAbox }" @click="showAbox = !showAbox">
          A-box {{ showAbox ? '✓' : '' }}
        </button>
      </div>
    </header>

    <!-- 图谱 -->
    <div class="biz-view__canvas">
      <VueFlow
        v-model:nodes="flowNodes"
        v-model:edges="flowEdges"
        :node-types="nodeTypes"
        :default-edge-options="defaultEdgeOptions"
        :fit-view-on-init="true"
        :nodes-draggable="true"
        @node-click="onNodeClick"
      >
        <Background pattern-color="#e8ecf1" :gap="24" :size="0.8" />
        <Controls position="bottom-left" />
      </VueFlow>

      <!-- 层级图例 -->
      <div class="biz-view__legend">
        <div class="biz-view__legend-item biz-view__legend-item--t1">
          <span class="biz-view__legend-dot"></span>T1 核心
        </div>
        <div class="biz-view__legend-item biz-view__legend-item--t2">
          <span class="biz-view__legend-dot"></span>T2 领域
        </div>
        <div class="biz-view__legend-item biz-view__legend-item--t3">
          <span class="biz-view__legend-dot"></span>T3 场景
        </div>
        <div v-if="showRbox" class="biz-view__legend-item biz-view__legend-item--rbox">
          <span class="biz-view__legend-dot"></span>R-box 规则节点
        </div>
        <div v-if="showAbox" class="biz-view__legend-item biz-view__legend-item--abox">
          <span class="biz-view__legend-dot"></span>A-box 实例计数
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, markRaw } from 'vue'
import { VueFlow, MarkerType, Position, type Node, type Edge } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import StudioNode from './StudioNode.vue'
import type { StudioObjectType, StudioLinkType } from '../../api/studio'

const props = defineProps<{
  objects: StudioObjectType[]
  relations: StudioLinkType[]
  selected?: StudioObjectType | null
}>()

const emit = defineEmits<{ (e: 'select', obj: StudioObjectType | null): void }>()

const nodeTypes = { studioNode: markRaw(StudioNode) }
const defaultEdgeOptions = { markerEnd: MarkerType.ArrowClosed, animated: false }

type ScenarioTab = 'tier1' | 'fttr' | 'churn' | 'ge'
const activeTab = ref<ScenarioTab>('tier1')
const showRbox = ref(false)
const showAbox = ref(false)

const scenarioTabs: { value: ScenarioTab; label: string; scenarios: string[] }[] = [
  { value: 'tier1',  label: 'Tier 1 核心',     scenarios: ['core'] },
  { value: 'fttr',   label: 'FTTR 续约策划',   scenarios: ['core', 's2', 'fttr'] },
  { value: 'churn',  label: '退单智能归因',     scenarios: ['core', 's1', 'churn', 'broadband'] },
  { value: 'ge',     label: '政企智能问数',     scenarios: ['core', 's4', 'ge', 'enterprise'] },
]

// 当前 tab 对应的对象集合
const filteredObjects = computed(() => {
  const tab = scenarioTabs.find(t => t.value === activeTab.value)!
  if (activeTab.value === 'tier1') {
    return props.objects.filter(o => o.tier === 1)
  }
  const scSet = new Set(tab.scenarios)
  return props.objects.filter(o => o.tier === 1 || scSet.has(o.scenarioCode))
})

const filteredNodes = computed(() => filteredObjects.value)
const filteredEdges = computed(() => {
  const nameSet = new Set(filteredObjects.value.map(o => o.apiName))
  return props.relations.filter(r => nameSet.has(r.source) && nameSet.has(r.target))
})

const tierColor: Record<1 | 2 | 3, string> = { 1: '#2E5BFF', 2: '#00C7B1', 3: '#FF6B35' }

// 按 tier 分层布局：T1 顶部 / T2 中部 / T3 底部
function layoutByTier(objs: StudioObjectType[]): Record<string, { x: number; y: number }> {
  const bands: Record<1 | 2 | 3, StudioObjectType[]> = { 1: [], 2: [], 3: [] }
  for (const o of objs) bands[o.tier as 1 | 2 | 3].push(o)
  const map: Record<string, { x: number; y: number }> = {}
  const bandY: Record<1 | 2 | 3, number> = { 1: 80, 2: 320, 3: 560 }
  const colWidth = 220
  for (const tier of [1, 2, 3] as const) {
    const arr = bands[tier]
    const startX = -(arr.length - 1) * colWidth / 2
    arr.forEach((o, i) => { map[o.apiName] = { x: startX + i * colWidth, y: bandY[tier] } })
  }
  return map
}

// tier1 视图用圆形布局
function layoutCircle(objs: StudioObjectType[]): Record<string, { x: number; y: number }> {
  const map: Record<string, { x: number; y: number }> = {}
  const n = Math.max(objs.length, 3)
  const r = 320
  objs.forEach((o, i) => {
    const theta = (i / n) * 2 * Math.PI - Math.PI / 2
    map[o.apiName] = { x: Math.cos(theta) * r, y: Math.sin(theta) * r }
  })
  return map
}

const flowNodes = ref<Node[]>([])
const flowEdges = ref<Edge[]>([])

function rebuild() {
  const objs = filteredObjects.value
  const layout = activeTab.value === 'tier1' ? layoutCircle(objs) : layoutByTier(objs)

  flowNodes.value = objs.map(o => ({
    id: o.apiName,
    type: 'studioNode',
    position: layout[o.apiName] ?? { x: 0, y: 0 },
    data: {
      apiName: o.apiName,
      displayName: o.displayName,
      tier: o.tier,
      color: tierColor[o.tier],
      instanceCount: o.aboxScale,
      ruleCount: o.ruleCount,
      propCount: o.properties.length,
      showAbox: showAbox.value,
      showRbox: showRbox.value && o.ruleCount > 0,
    },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  }))

  flowEdges.value = filteredEdges.value.map(r => ({
    id: `${r.source}-${r.target}-${r.apiName}`,
    source: r.source,
    target: r.target,
    type: 'default',
    label: r.displayName,
    labelStyle: { fontSize: '10px', fill: '#64748b' },
    labelBgStyle: { fill: '#fff', fillOpacity: 0.85 },
    style: { stroke: '#94a3b8', strokeWidth: 1.2 },
    markerEnd: MarkerType.ArrowClosed,
  }))
}

watch([activeTab, () => props.objects, () => props.relations, showRbox, showAbox], rebuild, { immediate: true })

function onNodeClick(event: { node: Node }) {
  const obj = props.objects.find(o => o.apiName === event.node.id)
  if (obj) emit('select', obj)
}
</script>

<style scoped>
.biz-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.biz-view__head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-wrap: wrap;
}

.biz-view__tabs {
  display: inline-flex;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 2px;
  gap: 2px;
}
.biz-view__tab {
  padding: 6px 14px;
  font-size: 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #475569;
  font-weight: 500;
}
.biz-view__tab:hover { background: rgba(255,255,255,0.5); }
.biz-view__tab--active { background: #fff; color: #1e293b; font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }

.biz-view__meta {
  display: flex;
  gap: 6px;
}
.biz-view__badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.biz-view__badge--blue { background: #dbeafe; color: #1d4ed8; }
.biz-view__badge--cyan { background: #cffafe; color: #0e7490; }

.biz-view__overlays {
  display: flex;
  gap: 6px;
  margin-left: auto;
}
.biz-view__overlay {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #64748b;
  cursor: pointer;
  user-select: none;
  font-weight: 500;
}
.biz-view__overlay:hover { background: #f8fafc; }
.biz-view__overlay--active.biz-view__overlay--rbox { background: #fef2f2; color: #dc2626; border-color: #fecaca; }
.biz-view__overlay--active.biz-view__overlay--abox { background: #f0fdf4; color: #16a34a; border-color: #bbf7d0; }

.biz-view__canvas {
  flex: 1;
  position: relative;
}

.biz-view__legend {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(4px);
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.biz-view__legend-item {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  font-weight: 500;
  color: #334155;
}
.biz-view__legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.biz-view__legend-item--t1 .biz-view__legend-dot { background: #2E5BFF; }
.biz-view__legend-item--t2 .biz-view__legend-dot { background: #00C7B1; }
.biz-view__legend-item--t3 .biz-view__legend-dot { background: #FF6B35; }
.biz-view__legend-item--rbox .biz-view__legend-dot { background: #dc2626; }
.biz-view__legend-item--abox .biz-view__legend-dot { background: #16a34a; }
</style>
