<template>
  <div v-if="loading" class="page-loading">
    <div class="page-loading__spinner"></div>
    <p v-if="text" class="page-loading__text">{{ text }}</p>
  </div>
  <div v-else-if="empty" class="page-empty">
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
      <rect x="8" y="8" width="32" height="32" rx="8" stroke="var(--neutral-300)" stroke-width="2"/>
      <path d="M16 24h16M16 18h10M16 30h8" stroke="var(--neutral-300)" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <p class="page-empty__text">{{ emptyText || '暂无数据' }}</p>
    <slot name="empty-action" />
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
defineProps<{
  loading?: boolean
  empty?: boolean
  text?: string
  emptyText?: string
}>()
</script>

<style scoped>
.page-loading {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 0; gap: 12px;
}
.page-loading__spinner {
  width: 32px; height: 32px; border: 3px solid var(--neutral-200);
  border-top-color: var(--semantic-500); border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.page-loading__text { font-size: var(--text-body-size); color: var(--neutral-500); }

.page-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 0; gap: 12px; color: var(--neutral-400);
}
.page-empty__text { font-size: var(--text-body-size); color: var(--neutral-500); }
</style>
