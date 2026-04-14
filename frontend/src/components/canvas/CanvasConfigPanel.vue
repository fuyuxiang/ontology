<template>
  <div class="config-panel">
    <template v-if="node">
      <div class="config-panel__header">
        <div class="config-badge" :style="{ background: tierColors[node.tier] }">T{{ node.tier }}</div>
        <div>
          <div class="config-panel__name">{{ node.name }}</div>
          <div class="config-panel__cn">{{ node.nameCn }}</div>
        </div>
      </div>

      <div class="config-section">
        <div class="config-section__title">基本信息</div>
        <div class="config-row">
          <span class="config-label">类型</span>
          <span class="config-value">Tier {{ node.tier }} {{ tierLabels[node.tier] }}</span>
        </div>
        <div class="config-row">
          <span class="config-label">状态</span>
          <span class="config-status" :class="`config-status--${node.status}`">{{ node.status }}</span>
        </div>
        <div class="config-row">
          <span class="config-label">关系数</span>
          <span class="config-value">{{ node.relCount }}</span>
        </div>
      </div>

      <div class="config-section" v-if="inEdges.length">
        <div class="config-section__title">入边 ({{ inEdges.length }})</div>
        <div class="config-edge" v-for="e in inEdges" :key="e.id">
          <span class="config-edge__from">{{ e.sourceName }}</span>
          <span class="config-edge__label">{{ e.label }}</span>
          <span class="config-edge__card">{{ e.cardinality }}</span>
        </div>
      </div>

      <div class="config-section" v-if="outEdges.length">
        <div class="config-section__title">出边 ({{ outEdges.length }})</div>
        <div class="config-edge" v-for="e in outEdges" :key="e.id">
          <span class="config-edge__label">{{ e.label }}</span>
          <span class="config-edge__to">{{ e.targetName }}</span>
          <span class="config-edge__card">{{ e.cardinality }}</span>
        </div>
      </div>

      <button class="config-detail-btn" @click="$emit('detail', node.id)">查看完整详情 →</button>
    </template>
    <template v-else>
      <div class="config-empty">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none"><circle cx="20" cy="20" r="18" stroke="#dee2e6" stroke-width="1.5" stroke-dasharray="4 3"/><path d="M14 20h12M20 14v12" stroke="#ced4da" stroke-width="1.5" stroke-linecap="round"/></svg>
        <p>点击节点查看详情</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface NodeData { id: string; name: string; nameCn: string; tier: 1|2|3; status: string; relCount: number }
interface EdgeInfo { id: string; sourceName: string; targetName: string; label: string; cardinality: string }

const props = defineProps<{
  node: NodeData | null
  inEdges: EdgeInfo[]
  outEdges: EdgeInfo[]
}>()

defineEmits<{ detail: [id: string] }>()

const tierColors: Record<number, string> = { 1: '#4c6ef5', 2: '#7950f2', 3: '#20c997' }
const tierLabels: Record<number, string> = { 1: '核心对象', 2: '领域对象', 3: '场景对象' }
</script>

<style scoped>
.config-panel {
  width: 280px; flex-shrink: 0; background: #fff;
  border-left: 1px solid #e9ecef; padding: 16px;
  overflow-y: auto; display: flex; flex-direction: column;
}
.config-panel__header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.config-badge {
  width: 32px; height: 32px; border-radius: 8px; display: flex;
  align-items: center; justify-content: center; color: #fff;
  font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.config-panel__name { font-size: 15px; font-weight: 600; color: #343a40; }
.config-panel__cn { font-size: 12px; color: #868e96; }
.config-section { margin-bottom: 16px; }
.config-section__title { font-size: 11px; font-weight: 600; color: #868e96; letter-spacing: 0.3px; margin-bottom: 8px; text-transform: uppercase; }
.config-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 12px; border-bottom: 1px solid #f1f3f5; }
.config-label { color: #868e96; }
.config-value { color: #343a40; font-weight: 500; }
.config-status { padding: 1px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
.config-status--active { background: #e6fcf5; color: #087f5b; }
.config-status--warning { background: #fff8e1; color: #e67700; }
.config-status--error { background: #fff5f5; color: #c92a2a; }
.config-edge { display: flex; align-items: center; gap: 6px; padding: 4px 0; font-size: 11px; border-bottom: 1px solid #f8f9fa; }
.config-edge__from, .config-edge__to { color: #343a40; font-weight: 500; }
.config-edge__label { color: #4c6ef5; flex: 1; }
.config-edge__card { color: #adb5bd; font-size: 10px; }
.config-detail-btn {
  margin-top: auto; padding: 10px; border-radius: 8px; border: none;
  background: #4c6ef5; color: #fff; font-size: 13px; font-weight: 500;
  cursor: pointer; transition: background 0.15s;
}
.config-detail-btn:hover { background: #4263eb; }
.config-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: #adb5bd; font-size: 13px; }
</style>
