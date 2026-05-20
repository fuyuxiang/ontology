<template>
  <div class="harness-shell">
    <!-- 闭环说明条 -->
    <div class="harness-banner">
      <ThunderboltOutlined class="harness-banner__icon" />
      <span class="harness-banner__label">本体进化闭环:</span>
      <span class="harness-banner__text">执行结果 → 漂移检测 → 演化提案 → 规则/模型更新 → 本体自进化</span>
    </div>

    <!-- 标题区 -->
    <div class="harness-title">
      <h4 class="harness-title__main">Ontology Harness (本体试车场)</h4>
      <span class="harness-title__sub">自学习 / 自迭代 / 漂移检测 / A/B 测试 / 演化管理</span>
    </div>

    <!-- Tabs -->
    <a-tabs v-model:activeKey="activeKey" type="card" class="harness-tabs">
      <a-tab-pane key="health">
        <template #tab><DashboardOutlined /> 健康大盘</template>
        <HealthDashboardTab />
      </a-tab-pane>
      <a-tab-pane key="drift">
        <template #tab><AimOutlined /> 漂移诊断</template>
        <DriftDiagnoseTab />
      </a-tab-pane>
      <a-tab-pane key="experiment">
        <template #tab><ThunderboltOutlined /> A/B 实验室</template>
        <ExperimentLabTab />
      </a-tab-pane>
      <a-tab-pane key="evolution">
        <template #tab><BranchesOutlined /> 演化管理</template>
        <EvolutionMgrTab />
      </a-tab-pane>
      <a-tab-pane key="report">
        <template #tab><FileTextOutlined /> 进化报告</template>
        <EvolutionReportTab />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  DashboardOutlined,
  AimOutlined,
  ThunderboltOutlined,
  BranchesOutlined,
  FileTextOutlined,
} from '@ant-design/icons-vue'
import HealthDashboardTab from './tabs/HealthDashboardTab.vue'
import DriftDiagnoseTab from './tabs/DriftDiagnoseTab.vue'
import ExperimentLabTab from './tabs/ExperimentLabTab.vue'
import EvolutionMgrTab from './tabs/EvolutionMgrTab.vue'
import EvolutionReportTab from './tabs/EvolutionReportTab.vue'

const activeKey = ref('health')
</script>

<style scoped>
.harness-shell {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 4px 0 0;
}
.harness-banner {
  margin-bottom: 12px;
  padding: 8px 14px;
  border-radius: 8px;
  background: #ECFEFF;
  border: 1px solid #a5f3fc;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.harness-banner__icon { color: #0891B2; }
.harness-banner__label { color: #164E63; font-weight: 600; }
.harness-banner__text { color: #0E7490; }
.harness-title { margin-bottom: 20px; }
.harness-title__main { font-size: 18px; font-weight: 600; margin: 0; color: rgba(0,0,0,0.88); }
.harness-title__sub { color: rgba(0,0,0,0.45); font-size: 13px; }
.harness-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.harness-tabs :deep(.ant-tabs-content-holder) { flex: 1; min-height: 0; display: flex; }
.harness-tabs :deep(.ant-tabs-content) { flex: 1; min-height: 0; }
.harness-tabs :deep(.ant-tabs-tabpane) { height: 100%; }
.harness-tabs :deep(.ant-tabs-tabpane-active) {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 8px;
  padding-bottom: 24px;
}
</style>
