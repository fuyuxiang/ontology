<template>
  <header class="topbar">
    <div class="topbar__left">
      <OntologyBreadcrumb :items="breadcrumbs" />
    </div>
    <div class="topbar__right">
      <button class="topbar__icon-btn" title="通知">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 2a4 4 0 00-4 4v3l-1 1.5h10L12 9V6a4 4 0 00-4-4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          <path d="M6.5 13a1.5 1.5 0 003 0" stroke="currentColor" stroke-width="1.5"/>
        </svg>
        <span class="topbar__badge"></span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import OntologyBreadcrumb from './OntologyBreadcrumb.vue'

const route = useRoute()

const breadcrumbs = computed(() => {
  const title = route.meta.title as string | undefined
  if (title) return [{ label: title }]
  return [{ label: '首页' }]
})
</script>

<style scoped>
.topbar {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--neutral-0);
  border-bottom: 1px solid var(--neutral-200);
  flex-shrink: 0;
}
.topbar__left { display: flex; align-items: center; }
.topbar__right { display: flex; align-items: center; gap: 4px; }
.topbar__icon-btn {
  position: relative;
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--radius-md);
  border: none; background: transparent;
  color: var(--neutral-600); cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.topbar__icon-btn:hover { background: var(--neutral-100); color: var(--neutral-800); }
.topbar__badge {
  position: absolute; top: 6px; right: 6px;
  width: 6px; height: 6px; border-radius: var(--radius-full);
  background: var(--status-error); border: 1.5px solid var(--neutral-0);
}
</style>
