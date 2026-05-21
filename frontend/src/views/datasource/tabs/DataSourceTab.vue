<template>
  <div class="ds-tab-wrap">
    <DataSourceView />
  </div>
</template>

<script setup lang="ts">
import DataSourceView from '../DataSourceView.vue'
</script>

<style scoped>
.ds-tab-wrap :deep(.ds-page) {
  padding: 0 !important;
}
.ds-tab-wrap :deep(.ds-page__header) {
  margin-bottom: var(--space-4);
}
.ds-tab-wrap :deep(.ds-page__title) {
  font-size: 18px !important;
  font-weight: 600 !important;
  letter-spacing: -0.2px;
}
.ds-tab-wrap :deep(.ds-page__subtitle) {
  font-size: 12px !important;
}
.ds-tab-wrap :deep(.ds-stats-row) {
  gap: 40px;
}
</style>
