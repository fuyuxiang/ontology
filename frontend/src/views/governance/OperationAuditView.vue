<template>
  <div class="oa-page">
    <div class="oa-page__header">
      <h1 class="oa-page__title">操作审计</h1>
      <p class="oa-page__subtitle">数据访问 · 权限变更 · Agent 推理 — 全平台可追溯</p>
    </div>
    <a-tabs v-model:activeKey="active" class="oa-tabs">
      <a-tab-pane key="data" tab="数据访问审计">
        <ExecutionAuditPage />
      </a-tab-pane>
      <a-tab-pane key="auth" tab="权限审计">
        <AuditLogView />
      </a-tab-pane>
      <a-tab-pane key="agent" tab="Agent 推理">
        <AgentTracesView />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Tabs as ATabs, TabPane as ATabPane } from 'ant-design-vue'
import ExecutionAuditPage from '../datasource/ExecutionAuditPage.vue'
import AuditLogView from './AuditLogView.vue'
import AgentTracesView from '../ops/AgentTracesView.vue'

const active = ref<string>('data')
</script>

<style scoped>
.oa-page { padding: 0; height: 100%; display: flex; flex-direction: column; }
.oa-page__header { padding: 20px 24px 8px; }
.oa-page__title { font-size: 22px; font-weight: 600; color: #111827; margin: 0; }
.oa-page__subtitle { font-size: 13px; color: #6b7280; margin-top: 4px; }
.oa-tabs { padding: 0 24px; flex: 1; overflow: hidden; }
:deep(.ant-tabs-content) { height: 100%; }
:deep(.ant-tabs-tabpane) { height: 100%; overflow: auto; }
</style>
