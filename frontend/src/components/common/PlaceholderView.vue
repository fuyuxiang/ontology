<template>
  <div class="placeholder">
    <div class="placeholder__icon">{{ icon }}</div>
    <h1 class="placeholder__title">{{ title }}</h1>
    <p class="placeholder__subtitle">{{ subtitle }}</p>
    <p v-if="description" class="placeholder__desc">{{ description }}</p>
    <div v-if="$slots.default" class="placeholder__slot">
      <slot />
    </div>
    <a-tag color="orange" class="placeholder__tag">功能开发中</a-tag>
  </div>
</template>

<script setup lang="ts">
import { Tag as ATag } from 'ant-design-vue'
defineProps<{
  icon?: string
  title: string
  subtitle?: string
  description?: string
}>()
</script>

<style scoped>
.placeholder {
  min-height: calc(100vh - 64px);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; padding: 48px 24px; gap: 12px;
  color: var(--neutral-700, #374151);
}
.placeholder__icon {
  font-size: 56px; line-height: 1; color: var(--neutral-300, #d1d5db);
  margin-bottom: 8px;
}
.placeholder__title { font-size: 22px; font-weight: 600; margin: 0; color: var(--neutral-900, #111827); }
.placeholder__subtitle { font-size: 14px; color: var(--neutral-500, #6b7280); margin: 0; max-width: 560px; }
.placeholder__desc { font-size: 12px; color: var(--neutral-400, #9ca3af); margin-top: 8px; max-width: 560px; line-height: 1.7; }
.placeholder__slot { margin-top: 16px; }
.placeholder__tag { margin-top: 16px; }
</style>
