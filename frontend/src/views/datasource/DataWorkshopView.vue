<template>
  <div class="dw-page">
    <div class="dw-page__header">
      <div>
        <h1 class="dw-page__title">数据工坊</h1>
        <p class="dw-page__subtitle">数据接入 · 数据管道 · 数据目录 · 数据血缘 · 数据质量 · 水合演练</p>
      </div>
    </div>

    <a-tabs v-model:activeKey="activeTab" class="dw-tabs" type="line">
      <a-tab-pane key="ingest" tab="数据接入">
        <DataSourceTab />
      </a-tab-pane>
      <a-tab-pane key="pipeline" tab="数据管道">
        <DataPipelineTab />
      </a-tab-pane>
      <a-tab-pane key="catalog" tab="数据目录">
        <DataCatalogTab />
      </a-tab-pane>
      <a-tab-pane key="lineage" tab="数据血缘">
        <DataLineageTab />
      </a-tab-pane>
      <a-tab-pane key="quality" tab="数据质量">
        <DataQualityTab />
      </a-tab-pane>
      <a-tab-pane key="hydration" tab="水合演练">
        <HydrationDrillTab />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DataSourceTab from './tabs/DataSourceTab.vue'
import DataPipelineTab from './tabs/DataPipelineTab.vue'
import DataCatalogTab from './tabs/DataCatalogTab.vue'
import DataLineageTab from './tabs/DataLineageTab.vue'
import DataQualityTab from './tabs/DataQualityTab.vue'
import HydrationDrillTab from './tabs/HydrationDrillTab.vue'

const route = useRoute()
const router = useRouter()

const validTabs = ['ingest', 'pipeline', 'catalog', 'lineage', 'quality', 'hydration'] as const
type TabKey = typeof validTabs[number]

function readTab(): TabKey {
  const t = (route.query.tab as string) || 'ingest'
  return (validTabs as readonly string[]).includes(t) ? (t as TabKey) : 'ingest'
}

const activeTab = ref<TabKey>(readTab())

watch(activeTab, (v) => {
  if (route.query.tab !== v) router.replace({ query: { ...route.query, tab: v } })
})
watch(() => route.query.tab, () => { activeTab.value = readTab() })
</script>

<style scoped>
.dw-page { padding: var(--space-8) var(--space-8); }
.dw-page__header { margin-bottom: var(--space-5); }
.dw-page__title {
  font-size: var(--text-display-size); font-weight: var(--text-display-weight);
  line-height: var(--text-display-leading); letter-spacing: var(--text-display-tracking);
  color: var(--neutral-900); margin: 0;
}
.dw-page__subtitle {
  font-size: var(--text-caption-size); color: var(--neutral-500); margin-top: 4px;
}

:deep(.dw-tabs .ant-tabs-nav) {
  margin-bottom: var(--space-5);
}
:deep(.dw-tabs .ant-tabs-tab) {
  font-size: 14px; padding: 10px 4px;
}
:deep(.dw-tabs .ant-tabs-tab + .ant-tabs-tab) {
  margin-left: 28px;
}
:deep(.dw-tabs .ant-tabs-tab-active .ant-tabs-tab-btn) {
  font-weight: 600;
}
</style>
