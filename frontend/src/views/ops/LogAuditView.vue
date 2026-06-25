<template>
  <div class="dashboard-container">
    <!-- Header -->
    <div class="dashboard-header">
      <h2>日志与审计</h2>
      <div class="header-right">
        <a-segmented v-model:value="activeTab" :options="tabOptions" />
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

    <!-- 内容区 -->
    <a-card :bordered="false" style="margin-top: 16px;">
      <LogQueryTab v-if="activeTab === 'logs'" />
      <AuditTab v-if="activeTab === 'audit'" @count-change="auditCount = $event" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Dropdown as ADropdown, Button as AButton, Menu as AMenu, MenuItem as AMenuItem, Card as ACard, Segmented as ASegmented } from 'ant-design-vue'
import { DownloadOutlined, DownOutlined, FileTextOutlined, FileExcelOutlined } from '@ant-design/icons-vue'
import LogQueryTab from './LogQueryTab.vue'
import AuditTab from './AuditTab.vue'
import { useToast } from '../../composables/useToast'

const { success, error } = useToast()

const activeTab = ref<'logs' | 'audit'>('logs')
const exporting = ref(false)
const auditCount = ref(0)

const tabOptions = computed(() => [
  { label: `📋 日志查询`, value: 'logs' },
  { label: `🔍 审计记录${auditCount.value > 0 ? ` (${auditCount.value})` : ''}`, value: 'audit' },
])

async function handleExport({ key }: { key: string | number }) {
  exporting.value = true
  try {
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
.dashboard-container {
  padding: 24px 32px;
}
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.dashboard-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
