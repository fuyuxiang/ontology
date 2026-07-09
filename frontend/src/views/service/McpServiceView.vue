<template>
  <div class="mcp-service">
    <div class="mcp-service__tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === tab.key }"
        @click="activeTab = tab.key"
      >{{ tab.label }}</button>
    </div>
    <div class="mcp-service__content">
      <OverviewTab v-if="activeTab === 'overview'" />
      <DocsTab v-else />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import OverviewTab from './mcp/OverviewTab.vue'
import DocsTab from './mcp/DocsTab.vue'

const tabs = [
  { key: 'overview', label: '服务概览' },
  { key: 'docs', label: '接入文档' },
]
const activeTab = ref('overview')
</script>

<style scoped>
.mcp-service { display: flex; flex-direction: column; height: 100%; overflow: hidden; max-width: 1400px; margin: 0 auto; }
.mcp-service__tabs { display: flex; gap: 0; padding: 0 32px; border-bottom: 1px solid var(--neutral-200, #e5e5e5); flex-shrink: 0; background: #fff; }
.tab-btn { padding: 12px 20px; font-size: 13px; font-weight: 500; color: var(--neutral-500, #888); background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; transition: all 0.15s; }
.tab-btn:hover { color: var(--neutral-700, #333); }
.tab-btn--active { color: var(--primary, #2563eb); border-bottom-color: var(--primary, #2563eb); }
.mcp-service__content { flex: 1; overflow-y: auto; padding: 24px 0; }
</style>
