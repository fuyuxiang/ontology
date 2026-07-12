<template>
  <div class="mcp-service">
    <!-- 顶部 Banner，与本体列表风格一致 -->
    <div class="page-banner">
      <div class="page-banner__content">
        <h1 class="page-banner__title">本体服务</h1>
        <p class="page-banner__desc">基于 MCP 协议对外暴露本体查询、数据探索与 Python 运行时能力，支持 Claude Desktop、Cursor 等 AI 客户端直接接入</p>
      </div>
      <div class="page-banner__right">
        <div class="page-banner__status">
          <span class="status-dot"></span>
          <span>服务运行中</span>
        </div>
        <div class="page-banner__endpoint">
          <code>{{ endpoint }}</code>
          <button class="copy-btn" @click="copyEndpoint">{{ copied ? '已复制' : '复制' }}</button>
        </div>
      </div>
    </div>

    <!-- 标签导航 -->
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
  max-width: 1400px;
  margin: 0 auto;
}

.page-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32px 32px;
  background: linear-gradient(135deg, #e8f4fd 0%, #dbeafe 50%, #eff6ff 100%);
  border-radius: var(--radius-lg, 12px);
  margin-bottom: 24px;
}
.page-banner__title { font-size: 24px; font-weight: 700; color: var(--neutral-900, #111); margin: 0 0 8px; }
.page-banner__desc { font-size: 13px; color: var(--neutral-600, #555); margin: 0; max-width: 600px; line-height: 1.5; }
.page-banner__right { text-align: right; flex-shrink: 0; }
.page-banner__status { display: flex; align-items: center; gap: 6px; justify-content: flex-end; font-size: 13px; color: #16a34a; font-weight: 500; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #16a34a; display: inline-block; animation: pulse 2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.page-banner__endpoint { margin-top: 10px; display: flex; align-items: center; justify-content: flex-end; }
.page-banner__endpoint code { font-size: 12px; background: rgba(37,99,235,0.08); color: var(--primary, #2563eb); padding: 5px 10px; border-radius: 6px; }
.copy-btn { margin-left: 8px; font-size: 11px; background: var(--primary, #2563eb); border: none; color: #fff; padding: 5px 12px; border-radius: 6px; cursor: pointer; transition: opacity 0.15s; }
.copy-btn:hover { opacity: 0.9; }

.mcp-service__tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--neutral-200, #e5e5e5);
  margin: 0 0 24px;
}
.tab-btn {
  padding: 10px 4px;
  margin-right: 24px;
  font-size: 14px;
  font-weight: 500;
  color: var(--neutral-500, #888);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.tab-btn:hover { color: var(--neutral-800, #333); }
.tab-btn--active {
  color: var(--primary, #2563eb);
  border-bottom-color: var(--primary, #2563eb);
}

.mcp-service__content { padding-bottom: 24px; }
</style>
