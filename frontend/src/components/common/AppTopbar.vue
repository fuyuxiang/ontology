<template>
  <header class="topbar">
    <div class="topbar__left">
      <OntologyBreadcrumb :items="breadcrumbs" />
    </div>
    <div class="topbar__right">
      <button class="topbar__icon-btn topbar__search-btn" title="搜索 (⌘K)" @click="emit('search')">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <circle cx="7" cy="7" r="4.5" stroke="currentColor" stroke-width="1.5"/>
          <path d="M10.5 10.5l2.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <kbd class="topbar__kbd">⌘K</kbd>
      </button>
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

const emit = defineEmits<{ search: [] }>()

const route = useRoute()

const breadcrumbs = computed(() => {
  const map: Record<string, { label: string; path?: string }[]> = {
    '/ontology': [{ label: '本体管理' }],
    '/dataflow': [{ label: '数据流' }],
    '/logic': [{ label: '业务逻辑' }],
    '/dashboard': [{ label: '数据看板' }],
    '/copilot': [{ label: '智能对话' }],
  }
  const path = '/' + route.path.split('/')[1]
  return map[path] ?? [{ label: '首页' }]
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

.topbar__left {
  display: flex;
  align-items: center;
}

.topbar__right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.topbar__scene-select {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--neutral-200);
  background: var(--neutral-50);
  font-size: 12px;
  font-weight: 500;
  color: var(--neutral-700);
  cursor: pointer;
  transition: border-color var(--transition-fast);
}
.topbar__scene-select:hover {
  border-color: var(--semantic-400);
}

.topbar__divider {
  width: 1px;
  height: 20px;
  background: var(--neutral-200);
  margin: 0 6px;
}

.topbar__icon-btn {
  position: relative;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  color: var(--neutral-600);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.topbar__icon-btn:hover {
  background: var(--neutral-100);
  color: var(--neutral-800);
}

.topbar__search-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  width: auto;
  padding: 0 10px;
  min-width: 32px;
}

.topbar__kbd {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid var(--neutral-200);
  background: var(--neutral-100);
  color: var(--neutral-500);
  line-height: 1.4;
}

.topbar__badge {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--status-error);
  border: 1.5px solid var(--neutral-0);
}
</style>
