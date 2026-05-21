<template>
  <div class="assets-panel">
    <div class="assets-panel-hint">
      <span>订阅资产后拖入画布</span>
      <span class="drag-hint-icon">⠿</span>
      <span v-if="selectedCount > 0" style="margin-left:8px;color:#10b981;font-size:12px">已订阅 {{ selectedCount }} 个</span>
    </div>

    <div v-if="structuredAssets.length" class="asset-channel">
      <div class="asset-channel-header structured">
        <span style="margin-right:6px">🗃️</span>
        结构化资产
        <span class="asset-channel-count">{{ structuredAssets.length }} 个</span>
      </div>
      <div class="asset-channel-desc">来自数据中台 · 模型表/标签/指标/规则</div>
      <AssetCard
        v-for="a in structuredAssets"
        :key="`structured-${a.id}`"
        :asset="a"
        @toggle="$emit('toggle-subscribe', $event)"
      />
    </div>

    <div v-if="unstructuredAssets.length" class="asset-channel">
      <div class="asset-channel-header unstructured">
        <span style="margin-right:6px">📄</span>
        非结构化文档
        <span class="asset-channel-count">{{ unstructuredAssets.length }} 个</span>
      </div>
      <div class="asset-channel-desc">来自 SOP / FAQ / 知识图谱 / 外呼录音</div>
      <AssetCard
        v-for="a in unstructuredAssets"
        :key="`unstructured-${a.id}`"
        :asset="a"
        @toggle="$emit('toggle-subscribe', $event)"
      />
    </div>

    <button
      v-if="selectedCount > 0 && !graphReady"
      class="build-ontology-btn"
      @click="$emit('start-graph')"
    >
      ⚡ 基于 {{ selectedCount }} 个资产生成本体画布
    </button>
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
