<template>
  <div class="semantic-canvas">
    <div class="sc-header">
      <div class="sc-title">🗺️ 语义网络画布</div>
      <div class="sc-meta">{{ headerMessage }}</div>
    </div>

    <div v-if="!objects.length" class="sc-empty">
      <div class="sc-empty__icon">🗺️</div>
      <div class="sc-empty__title">{{ placeholderMessage || '将左侧资产拖入此处' }}</div>
      <div class="sc-empty__desc">AI 将根据场景×资产组合动态构建本体</div>
    </div>

    <div v-else class="sc-grid" ref="containerRef">
      <svg class="sc-edges" :width="svgSize.w" :height="svgSize.h">
        <defs>
          <marker id="sc-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0 0L10 5L0 10z" fill="#94a3b8"/>
          </marker>
        </defs>
        <g v-for="r in resolvedRelations" :key="r.id">
          <line
            :x1="r.x1" :y1="r.y1" :x2="r.x2" :y2="r.y2"
            stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="4 4"
            marker-end="url(#sc-arrow)"
          />
          <text :x="(r.x1 + r.x2) / 2" :y="(r.y1 + r.y2) / 2 - 6" text-anchor="middle" class="sc-edge-label">{{ r.displayName }}</text>
        </g>
      </svg>

      <div
        v-for="(o, idx) in objects"
        :key="o.id"
        class="sc-node"
        :class="`sc-node--t${o.tier}`"
        :style="positionStyle(idx)"
      >
        <div class="sc-node__icon">{{ o.icon || o.displayName.charAt(0) }}</div>
        <div class="sc-node__body">
          <div class="sc-node__name">{{ o.displayName }}</div>
          <div class="sc-node__en">{{ o.name }} · T{{ o.tier }}</div>
          <div class="sc-node__count">{{ o.properties.length }} 属性 · {{ o.instanceCount.toLocaleString() }} 实例</div>
        </div>
        <button class="sc-node__del" @click="$emit('delete', o.id)" title="删除对象">×</button>
      </div>
    </div>

    <div class="sc-toolbar">
      <button class="sc-toolbar__btn" :disabled="!editable" @click="$emit('add')">+ 新增对象</button>
      <span class="sc-toolbar__hint">点击对象可在右侧编辑；新增关系请进入"专家走测审批"</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import type { OntologyClassDraft, OntologyRelationDraft, Step1Phase } from '../../../../types/builder'

const props = defineProps<{
  objects: OntologyClassDraft[]
  relations: OntologyRelationDraft[]
  phase: Step1Phase
  graphPhaseLabel?: string
  placeholderMessage?: string
  editable?: boolean
}>()
defineEmits<{ (e: 'add'): void; (e: 'delete', id: string): void }>()

const containerRef = ref<HTMLElement | null>(null)
const svgSize = ref({ w: 800, h: 600 })

function updateSize() {
  if (containerRef.value) {
    svgSize.value = {
      w: containerRef.value.clientWidth,
      h: containerRef.value.clientHeight,
    }
  }
}
onMounted(() => {
  updateSize()
  window.addEventListener('resize', updateSize)
})
onBeforeUnmount(() => window.removeEventListener('resize', updateSize))

const headerMessage = computed(() => {
  if (props.phase === 'graph_done' || props.objects.length > 0) {
    return `已构建 ${props.objects.length} 个对象 · ${props.relations.length} 条关系`
  }
  return 'Tier 1 核心层等待场景构建'
})

function positionStyle(idx: number) {
  const cols = Math.ceil(Math.sqrt(props.objects.length))
  const colW = 260
  const rowH = 130
  const col = idx % cols
  const row = Math.floor(idx / cols)
  return {
    left: `${col * colW + 24}px`,
    top: `${row * rowH + 24}px`,
  }
}

function nodeCenter(idx: number) {
  const cols = Math.ceil(Math.sqrt(props.objects.length))
  const colW = 260
  const rowH = 130
  const col = idx % cols
  const row = Math.floor(idx / cols)
  return {
    x: col * colW + 24 + 110, // 节点宽 ≈ 220
    y: row * rowH + 24 + 36,
  }
}

const resolvedRelations = computed(() =>
  props.relations.map(r => {
    const sIdx = props.objects.findIndex(o => o.id === r.source || o.name === r.source)
    const tIdx = props.objects.findIndex(o => o.id === r.target || o.name === r.target)
    if (sIdx < 0 || tIdx < 0) return null
    const s = nodeCenter(sIdx)
    const t = nodeCenter(tIdx)
    return { id: r.id, x1: s.x, y1: s.y, x2: t.x, y2: t.y, displayName: r.displayName }
  }).filter(Boolean) as { id: string; x1: number; y1: number; x2: number; y2: number; displayName: string }[],
)
</script>

<style scoped>
.semantic-canvas {
  display: flex; flex-direction: column;
  height: 100%;
}
.sc-header {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  display: flex; justify-content: space-between; align-items: center;
}
.sc-title { font-size: 13px; font-weight: 600; color: #0f172a; }
.sc-meta { font-size: 11px; color: #94a3b8; }

.sc-empty {
  flex: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px;
  border: 2px dashed #cbd5e1;
  border-radius: 16px;
  margin: 24px;
  background: repeating-linear-gradient(45deg, transparent, transparent 12px, rgba(99, 102, 241, 0.02) 12px, rgba(99, 102, 241, 0.02) 24px);
}
.sc-empty__icon { font-size: 56px; opacity: 0.4; }
.sc-empty__title { font-size: 14px; font-weight: 600; color: #475569; }
.sc-empty__desc { font-size: 12px; color: #94a3b8; }

.sc-grid {
  flex: 1;
  position: relative;
  overflow: auto;
  background:
    radial-gradient(circle at 1px 1px, rgba(99, 102, 241, 0.08) 1px, transparent 1px) 0 0 / 24px 24px,
    #fafbff;
}
.sc-edges { position: absolute; top: 0; left: 0; pointer-events: none; }

.sc-node {
  position: absolute;
  width: 220px;
  padding: 12px;
  border-radius: 12px;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  box-shadow: 0 4px 12px -4px rgba(15, 23, 42, 0.08);
  display: flex; gap: 10px; align-items: flex-start;
  cursor: pointer;
  transition: transform 150ms ease, box-shadow 150ms ease;
}
.sc-node:hover { transform: translateY(-2px); box-shadow: 0 12px 24px -8px rgba(15, 23, 42, 0.15); }
.sc-node--t1 { border-top: 3px solid #4c6ef5; }
.sc-node--t2 { border-top: 3px solid #7950f2; }
.sc-node--t3 { border-top: 3px solid #20c997; }
.sc-node__icon {
  width: 32px; height: 32px; border-radius: 8px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff; font-size: 14px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.sc-node__body { flex: 1; min-width: 0; line-height: 1.4; }
.sc-node__name { font-size: 13px; font-weight: 600; color: #0f172a; }
.sc-node__en { font-size: 10px; color: #94a3b8; margin-top: 2px; }
.sc-node__count { font-size: 11px; color: #64748b; margin-top: 4px; }
.sc-node__del {
  width: 18px; height: 18px; border-radius: 50%;
  background: #f1f5f9; border: 0; cursor: pointer;
  color: #94a3b8; font-size: 14px; line-height: 1;
}
.sc-node__del:hover { background: #fee2e2; color: #ef4444; }

.sc-edge-label {
  font-size: 10px;
  fill: #64748b;
  font-weight: 500;
}

.sc-toolbar {
  padding: 10px 16px;
  border-top: 1px solid #f1f5f9;
  display: flex; align-items: center; gap: 12px;
  background: #fff;
}
.sc-toolbar__btn {
  padding: 6px 14px; border-radius: 8px;
  background: #fff; border: 1px solid #e2e8f0;
  color: #475569; font-size: 12px; cursor: pointer;
  transition: all 150ms ease;
}
.sc-toolbar__btn:disabled { opacity: 0.4; cursor: not-allowed; }
.sc-toolbar__btn:hover:not(:disabled) { border-color: #4f46e5; color: #4f46e5; }
.sc-toolbar__hint { font-size: 11px; color: #94a3b8; }
</style>
