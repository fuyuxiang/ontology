<template>
  <div class="di-page">
    <div class="di-page__header">
      <h1 class="di-page__title">水合演练</h1>
      <p class="di-page__subtitle">T-box 水合验证执行历史与综合评分报告</p>
    </div>
    <HydrationDrillTab />
  </div>
</template>

<script setup lang="ts">
import HydrationDrillTab from '../tabs/HydrationDrillTab.vue'
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
