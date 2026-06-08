<template>
  <div class="log-audit-page">
    <!-- 标题区 -->
    <div class="log-audit-page__header">
      <div class="log-audit-page__title-group">
        <h1 class="text-display">日志与审计</h1>
        <p class="text-caption" style="margin-top: 4px;">系统日志查询 · 操作审计追溯</p>
      </div>
      <div class="log-audit-page__actions">
        <a-dropdown>
          <a-button>
            <template #icon><DownloadOutlined /></template>
            导出 CSV
            <DownOutlined style="font-size: 10px; margin-left: 4px" />
          </a-button>
          <template #overlay>
            <a-menu @click="handleExport">
              <a-menu-item key="csv">导出 CSV</a-menu-item>
              <a-menu-item key="excel">导出 Excel</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </div>

    <!-- Segmented 切换 -->
    <div class="log-audit-page__tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="log-audit-tab"
        :class="{ 'log-audit-tab--active': activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 内容区 -->
    <div class="log-audit-page__content">
      <LogQueryTab v-if="activeTab === 'logs'" />
      <AuditTab v-if="activeTab === 'audit'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Dropdown as ADropdown, Button as AButton, Menu as AMenu, MenuItem as AMenuItem } from 'ant-design-vue'
import { DownloadOutlined, DownOutlined } from '@ant-design/icons-vue'
import LogQueryTab from './LogQueryTab.vue'
import AuditTab from './AuditTab.vue'
import { useToast } from '../../composables/useToast'

const { success } = useToast()

const activeTab = ref<'logs' | 'audit'>('logs')

const tabs = [
  { key: 'logs', label: '日志查询' },
  { key: 'audit', label: '审计记录' },
]

function handleExport({ key }: { key: string }) {
  // TODO: 实际导出逻辑
  success(`正在导出 ${key === 'csv' ? 'CSV' : 'Excel'} 文件...`)
}
</script>

<style scoped>
.log-audit-page {
  padding: 24px 32px;
  max-width: 1400px;
}

.log-audit-page__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.log-audit-page__title-group {
  flex: 1;
}

.log-audit-page__actions {
  display: flex;
  gap: 8px;
}

/* Tab 切换 */
.log-audit-page__tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--neutral-100);
}
.log-audit-tab {
  padding: 10px 18px;
  border: none;
  background: transparent;
  font-size: 13px;
  color: var(--neutral-500);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
  font-family: inherit;
}
.log-audit-tab:hover {
  color: var(--neutral-800);
}
.log-audit-tab--active {
  color: var(--semantic-600);
  border-bottom-color: var(--semantic-600);
  font-weight: 500;
}

.log-audit-page__content {
  animation: fadeIn 0.2s;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 响应式 */
@media (max-width: 1280px) {
  .log-audit-page {
    padding: 20px;
  }
}
</style>
