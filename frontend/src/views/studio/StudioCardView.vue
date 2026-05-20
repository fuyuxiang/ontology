<template>
  <div class="card-view">
    <!-- 顶部使用提示 -->
    <div class="card-view__hint">
      <span class="card-view__hint-title">如何消费本体</span>
      <span>点击对象 → 查看属性/规则/动作</span>
      <span class="card-view__hint-sep">|</span>
      <span>切换"语义网络" → 查看业务全景</span>
      <span class="card-view__hint-sep">|</span>
      <span>在 AI 助手中输入 "@Customer 分析" → 获取 AI 解读</span>
    </div>

    <!-- 卡片网格 -->
    <div class="card-view__grid">
      <article
        v-for="obj in objects"
        :key="obj.apiName"
        class="card"
        :class="`card--t${obj.tier}`"
        @click="$emit('select', obj)"
      >
        <header class="card__header">
          <div class="card__icon" :style="{ background: tierColor[obj.tier] + '18', color: tierColor[obj.tier] }">
            {{ obj.displayName.charAt(0) }}
          </div>
          <div class="card__title">
            <div class="card__name">{{ obj.displayName }}</div>
            <div class="card__en">{{ obj.apiName }}</div>
          </div>
          <span class="card__tier" :style="{ background: tierColor[obj.tier] + '15', color: tierColor[obj.tier] }">
            T{{ obj.tier }}
          </span>
        </header>

        <div class="card__meta">
          <span class="card__meta-item">{{ obj.properties.length }} 属性</span>
          <span v-if="obj.scenarioCode !== 'core'" class="card__meta-scenario">{{ obj.scenarioCode }}</span>
        </div>

        <div class="card__badges">
          <span class="card__badge card__badge--instance">
            {{ formatNumber(obj.aboxScale) }} 实例
          </span>
          <span v-if="obj.ruleCount > 0" class="card__badge card__badge--rule">
            {{ obj.ruleCount }} 规则
          </span>
          <span v-if="hydrationOf(obj.apiName)" class="card__badge" :class="`card__badge--hydration-${hydrationOf(obj.apiName)!.level}`">
            {{ hydrationLabel[hydrationOf(obj.apiName)!.level] }}
          </span>
        </div>

        <div class="card__rel-row" v-if="relCount[obj.apiName]">
          <span class="card__rel">
            <span class="card__rel-icon">⇄</span>
            {{ relCount[obj.apiName]?.inbound ?? 0 }} 入 · {{ relCount[obj.apiName]?.outbound ?? 0 }} 出
          </span>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StudioObjectType, StudioLinkType, StudioHydration } from '../../api/studio'

const props = defineProps<{
  objects: StudioObjectType[]
  relations: StudioLinkType[]
  hydration: Record<string, StudioHydration>
}>()

defineEmits<{
  (e: 'select', obj: StudioObjectType): void
}>()

const tierColor: Record<1 | 2 | 3, string> = { 1: '#2E5BFF', 2: '#00C7B1', 3: '#FF6B35' }
const hydrationLabel: Record<StudioHydration['level'], string> = {
  full: '完全水合', partial: '部分水合', mapping: '映射中', none: '未水合',
}

const relCount = computed(() => {
  const m: Record<string, { inbound: number; outbound: number }> = {}
  for (const o of props.objects) m[o.apiName] = { inbound: 0, outbound: 0 }
  for (const r of props.relations) {
    if (m[r.source]) m[r.source].outbound++
    if (m[r.target]) m[r.target].inbound++
  }
  return m
})

function hydrationOf(apiName: string): StudioHydration | undefined {
  return props.hydration[apiName]
}

function formatNumber(n: number) {
  if (n === 0) return '—'
  return n.toLocaleString('en-US')
}
</script>

<style scoped>
.card-view {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card-view__hint {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  font-size: 11px;
  color: #64748b;
}
.card-view__hint-title { font-weight: 600; color: #334155; }
.card-view__hint-sep { color: #cbd5e1; }

.card-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 14px;
  cursor: pointer;
  transition: all 0.18s;
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
  overflow: hidden;
}
.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--tc);
}
.card--t1 { --tc: #2E5BFF; }
.card--t2 { --tc: #00C7B1; }
.card--t3 { --tc: #FF6B35; }

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0,0,0,0.08), 0 0 0 1px var(--tc);
}

.card__header {
  display: flex;
  align-items: center;
  gap: 10px;
}
.card__icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}
.card__title { flex: 1; min-width: 0; }
.card__name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card__en {
  font-size: 10px;
  color: #94a3b8;
  font-family: monospace;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card__tier {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.card__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #64748b;
}
.card__meta-scenario {
  background: #ede9fe;
  color: #6d28d9;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-family: monospace;
  font-weight: 600;
}

.card__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.card__badge {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 4px;
  font-weight: 500;
  border: 1px solid transparent;
}
.card__badge--instance { background: #ecfeff; color: #0e7490; border-color: #cffafe; }
.card__badge--rule { background: #fff7ed; color: #c2410c; border-color: #fed7aa; }
.card__badge--hydration-full { background: #f0fdf4; color: #16a34a; border-color: #bbf7d0; }
.card__badge--hydration-partial { background: #eff6ff; color: #2563eb; border-color: #bfdbfe; }
.card__badge--hydration-mapping { background: #fef3c7; color: #b45309; border-color: #fde68a; }
.card__badge--hydration-none {
  background: transparent;
  color: #94a3b8;
  border-color: #cbd5e1;
  border-style: dashed;
}

.card__rel-row {
  display: flex;
  gap: 8px;
  padding-top: 4px;
  border-top: 1px solid #f1f5f9;
}
.card__rel {
  font-size: 10px;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.card__rel-icon { color: #00C7B1; font-weight: 700; }
</style>
