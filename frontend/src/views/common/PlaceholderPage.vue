<template>
  <div class="placeholder">
    <div class="placeholder__icon">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <rect x="6" y="10" width="36" height="28" rx="4" stroke="currentColor" stroke-width="2"/>
        <path d="M6 18h36" stroke="currentColor" stroke-width="2"/>
        <circle cx="12" cy="14" r="1.5" fill="currentColor"/>
        <circle cx="17" cy="14" r="1.5" fill="currentColor"/>
        <circle cx="22" cy="14" r="1.5" fill="currentColor"/>
        <path d="M18 28l4-4 4 4M30 26l3-3 3 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    <h2 class="placeholder__title">{{ title }}</h2>
    <p class="placeholder__desc">该功能正在开发中，敬请期待</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => (route.meta.title as string) || '功能开发中')
</script>

<style scoped>
.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  color: var(--neutral-400);
}
.placeholder__icon {
  margin-bottom: 16px;
  opacity: 0.5;
}
.placeholder__title {
  font-size: var(--text-h2-size);
  font-weight: 600;
  color: var(--neutral-600);
  margin-bottom: 8px;
}
.placeholder__desc {
  font-size: var(--text-body-size);
  color: var(--neutral-400);
}
</style>
