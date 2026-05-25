<template>
  <div class="pr-page">
    <div class="pr-page__header">
      <h1 class="pr-page__title">治理 · 发布前关卡</h1>
      <p class="pr-page__subtitle">本体发布前的水合演练 · 实例验证 · 评分关卡</p>
    </div>

    <HydrationDrillTab />
  </div>
</template>

<script setup lang="ts">
import HydrationDrillTab from '../datasource/tabs/HydrationDrillTab.vue'
</script>

<style scoped>
.pr-page { padding: 24px; }
.pr-page__header { margin-bottom: 16px; }
.pr-page__title { font-size: 24px; font-weight: 600; color: #111827; margin: 0; }
.pr-page__subtitle { font-size: 13px; color: #6b7280; margin-top: 4px; }
</style>
