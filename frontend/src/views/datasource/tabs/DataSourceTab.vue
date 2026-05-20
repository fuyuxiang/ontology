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
.ds-tab-wrap :deep(.ds-page__title) {
  font-size: 16px !important;
}
.ds-tab-wrap :deep(.ds-page__subtitle) {
  font-size: 12px !important;
}
</style>
