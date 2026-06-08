<template>
  <div class="log-audit-page">
    <!-- 标题区 -->
    <div class="log-audit-page__header">
      <div class="log-audit-page__title-group">
        <h1 class="log-audit-page__title">日志与审计</h1>
        <p class="log-audit-page__subtitle">系统日志查询 · 操作审计追溯</p>
      </div>
      <div class="log-audit-page__actions">
        <a-dropdown :disabled="exporting">
          <a-button :loading="exporting">
            <template #icon><DownloadOutlined /></template>
            {{ exporting ? '导出中...' : '导出' }}
            <DownOutlined v-if="!exporting" style="font-size: 10px; margin-left: 4px" />
          </a-button>
          <template #overlay>
            <a-menu @click="handleExport">
              <a-menu-item key="csv">
                <FileTextOutlined style="margin-right: 8px" />导出 CSV
              </a-menu-item>
              <a-menu-item key="excel">
                <FileExcelOutlined style="margin-right: 8px" />导出 Excel
              </a-menu-item>
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
        <span class="log-audit-tab__icon">{{ tab.icon }}</span>
        {{ tab.label }}
        <span v-if="tab.key === 'audit' && auditCount > 0" class="log-audit-tab__badge">{{ auditCount }}</span>
      </button>
    </div>

    <!-- 内容区 -->
    <div class="log-audit-page__content">
      <LogQueryTab v-if="activeTab === 'logs'" />
      <AuditTab v-if="activeTab === 'audit'" @count-change="auditCount = $event" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Dropdown as ADropdown, Button as AButton, Menu as AMenu, MenuItem as AMenuItem } from 'ant-design-vue'
import { DownloadOutlined, DownOutlined, FileTextOutlined, FileExcelOutlined } from '@ant-design/icons-vue'
import LogQueryTab from './LogQueryTab.vue'
import AuditTab from './AuditTab.vue'
import { useToast } from '../../composables/useToast'

const { success, error } = useToast()

const activeTab = ref<'logs' | 'audit'>('logs')
const exporting = ref(false)
const auditCount = ref(0)

const tabs = [
  { key: 'logs', label: '日志查询', icon: '📋' },
  { key: 'audit', label: '审计记录', icon: '🔍' },
]

async function handleExport({ key }: { key: string }) {
  exporting.value = true
  try {
    // 模拟导出延迟
    await new Promise(r => setTimeout(r, 1500))
    success(`${key === 'csv' ? 'CSV' : 'Excel'} 文件已开始下载`)
  } catch {
    error('导出失败，请重试')
  } finally {
    exporting.value = false
  }
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
  margin-bottom: 20px;
}

.log-audit-page__title {
  font-size: 28px;
  font-weight: 700;
  color: var(--neutral-900);
  margin: 0;
  line-height: 1.2;
}

.log-audit-page__subtitle {
  font-size: 13px;
  color: var(--neutral-500);
  margin: 6px 0 0;
}

.log-audit-page__actions {
  display: flex;
  gap: 8px;
}

/* Tab 切换 */
.log-audit-page__tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--neutral-100);
  padding-bottom: 0;
}

.log-audit-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--neutral-500);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.2s ease;
  font-family: inherit;
  position: relative;
}

.log-audit-tab:hover {
  color: var(--neutral-700);
  background: var(--neutral-50);
  border-radius: 8px 8px 0 0;
}

.log-audit-tab--active {
  color: var(--semantic-600);
  border-bottom-color: var(--semantic-600);
  font-weight: 600;
}

.log-audit-tab__icon {
  font-size: 16px;
}

.log-audit-tab__badge {
  font-size: 11px;
  background: var(--semantic-100, #e8f0fe);
  color: var(--semantic-600);
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 600;
  min-width: 18px;
  text-align: center;
}

.log-audit-page__content {
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 响应式 */
@media (max-width: 1280px) {
  .log-audit-page {
    padding: 20px;
  }
}

@media (max-width: 768px) {
  .log-audit-page__header {
    flex-direction: column;
    gap: 12px;
  }

  .log-audit-page__actions {
    width: 100%;
  }
}
</style>
