<template>
  <div class="assets-panel">
    <div class="assets-panel__head">
      <div>
        <div class="assets-panel__title">📦 资产清单</div>
        <div class="assets-panel__sub">已订阅 {{ selectedCount }} / {{ assets.length }} 个 · 拖入或点击订阅</div>
      </div>
      <button
        class="assets-panel__action"
        :disabled="selectedCount === 0 || graphReady"
        @click="$emit('start-graph')"
      >
        ⚡ 一键生成画布
      </button>
    </div>

    <div class="assets-panel__body">
      <div v-if="structuredAssets.length" class="asset-channel">
        <div class="asset-channel-header structured">
          <span class="ach-icon">🗃️</span>
          <span class="ach-label">结构化资产</span>
          <span class="ach-count">{{ structuredAssets.length }}</span>
        </div>
        <div class="asset-list">
          <AssetCard v-for="a in structuredAssets" :key="a.id" :asset="a" @toggle="$emit('toggle-subscribe', $event)" />
        </div>
      </div>

      <div v-if="unstructuredAssets.length" class="asset-channel">
        <div class="asset-channel-header unstructured">
          <span class="ach-icon">📄</span>
          <span class="ach-label">非结构化文档</span>
          <span class="ach-count">{{ unstructuredAssets.length }}</span>
        </div>
        <div class="asset-list">
          <AssetCard v-for="a in unstructuredAssets" :key="a.id" :asset="a" @toggle="$emit('toggle-subscribe', $event)" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DataAsset } from '../../../../types/builder'
import AssetCard from './AssetCard.vue'

const props = defineProps<{
  assets: DataAsset[]
  selectedCount: number
  graphReady: boolean
}>()
defineEmits<{
  (e: 'toggle-subscribe', id: string): void
  (e: 'start-graph'): void
}>()

const structuredAssets = computed(() => props.assets.filter(a => a.category === 'structured'))
const unstructuredAssets = computed(() => props.assets.filter(a => a.category !== 'structured'))
</script>

<style scoped>
.assets-panel { display: flex; flex-direction: column; height: 100%; }
.assets-panel__head {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  display: flex; justify-content: space-between; align-items: center; gap: 8px;
}
.assets-panel__title { font-size: 13px; font-weight: 600; color: #0f172a; }
.assets-panel__sub { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.assets-panel__action {
  padding: 6px 12px; border-radius: 8px;
  border: 0;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff; font-size: 12px; font-weight: 600;
  cursor: pointer; flex-shrink: 0;
  transition: all 150ms ease;
}
.assets-panel__action:disabled { opacity: 0.4; cursor: not-allowed; }
.assets-panel__action:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 14px -4px rgba(79, 70, 229, 0.4); }

.assets-panel__body { flex: 1; overflow-y: auto; padding: 12px; }
.asset-channel + .asset-channel { margin-top: 14px; }
.asset-channel-header {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px; font-weight: 600;
  margin-bottom: 8px;
}
.asset-channel-header.structured { background: rgba(99, 102, 241, 0.08); color: #4f46e5; }
.asset-channel-header.unstructured { background: rgba(245, 158, 11, 0.08); color: #b45309; }
.ach-count {
  margin-left: auto; padding: 1px 8px; border-radius: 999px;
  background: rgba(255,255,255,0.7); font-size: 11px; font-weight: 700;
}
.asset-list { display: grid; gap: 8px; }
</style>
