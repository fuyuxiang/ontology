<template>
  <div class="mcp-service">
    <div class="mcp-service__header">
      <div>
        <h1 class="text-display">本体服务</h1>
        <p class="text-caption" style="margin-top: 4px;">基于 MCP 协议对外暴露本体查询、数据探索与 Python 运行时能力</p>
      </div>
      <div class="mcp-service__endpoint">
        <span class="mcp-service__status">
          <span class="status-dot"></span>
          服务运行中
        </span>
        <code>{{ endpoint }}</code>
        <button class="btn-copy" @click="copyEndpoint">{{ copied ? '已复制' : '复制' }}</button>
      </div>
    </div>

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

const endpoint = `${window.location.origin}/api/v1/mcp`
const copied = ref(false)

async function copyEndpoint() {
  try {
    await navigator.clipboard.writeText(endpoint)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch { /* ignore */ }
}
</script>

<style scoped>
.mcp-service {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  padding: 24px 32px 0;
  max-width: 1200px;
  margin: 0 auto;
  box-sizing: border-box;
  width: 100%;
}

.mcp-service__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  flex-shrink: 0;
}

.mcp-service__endpoint {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--neutral-0, #fff);
  border: 1px solid var(--neutral-200, #e9ecef);
  border-radius: var(--radius-md, 8px);
}
.mcp-service__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  color: var(--status-success, #12b886);
  white-space: nowrap;
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--status-success, #12b886);
  animation: pulse 2s infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.mcp-service__endpoint code {
  font-size: 12px;
  font-family: var(--font-mono, monospace);
  color: var(--neutral-700, #495057);
  padding-left: 10px;
  border-left: 1px solid var(--neutral-200, #e9ecef);
}
.btn-copy {
  font-size: 11px;
  background: var(--semantic-50, #eef2ff);
  border: 1px solid var(--semantic-200, #bac8ff);
  color: var(--semantic-600, #4c6ef5);
  padding: 4px 10px;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.btn-copy:hover { background: var(--semantic-100, #dbe4ff); }

.mcp-service__tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--neutral-200, #e9ecef);
  flex-shrink: 0;
}
.tab-btn {
  padding: 10px 4px;
  margin-right: 20px;
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-500, #adb5bd);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.tab-btn:hover { color: var(--neutral-800, #343a40); }
.tab-btn--active {
  color: var(--semantic-600, #4c6ef5);
  border-bottom-color: var(--semantic-600, #4c6ef5);
}

.mcp-service__content { flex: 1; overflow-y: auto; padding: 24px 0; }
</style>
