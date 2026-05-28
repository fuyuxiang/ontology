<template>
  <div class="di-page">
    <div class="di-page__header">
      <h1 class="di-page__title">数据质量</h1>
      <p class="di-page__subtitle">资产健康度 · 规则契约 · 状态历史 · 评估结果聚合</p>
    </div>
    <DataQualityTab />
  </div>
</template>

<script setup lang="ts">
import DataQualityTab from '../tabs/DataQualityTab.vue'
</script>

<style scoped>
.di-page { padding: var(--space-8) var(--space-8); }
.di-page__header { margin-bottom: var(--space-5); }
.di-page__title {
  font-size: var(--text-display-size); font-weight: var(--text-display-weight);
  line-height: var(--text-display-leading); letter-spacing: var(--text-display-tracking);
  color: var(--neutral-900); margin: 0;
}
.di-page__subtitle {
  font-size: var(--text-caption-size); color: var(--neutral-500); margin-top: 4px;
}
</style>
