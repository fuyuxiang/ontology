<template>
  <div class="browser">
    <div class="browser__tabs">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.path"
        :to="tab.path"
        class="browser__tab"
        :class="{ 'browser__tab--active': isTabActive(tab.path) }"
      >
        <span class="browser__tab-icon" v-html="tab.icon"></span>
        <span>{{ tab.label }}</span>
      </RouterLink>
    </div>
    <div class="browser__content">
      <RouterView />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  {
    path: '/browser',
    label: '本体管理',
    icon: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="3" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M8 6v2M8 8L3 10M8 8l5 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  },
  {
    path: '/browser/graph',
    label: '关系画布',
    icon: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 8h3l2-4 2 8 2-4h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  },
  {
    path: '/browser/rules',
    label: '业务规则',
    icon: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M11.5 9v-1.5a1 1 0 00-1-1h-1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M11.5 14v-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  },
  {
    path: '/browser/build/auto',
    label: '自动化构建',
    icon: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M9 2L4 9h4l-1 5 5-7H8l1-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
  },
  {
    path: '/browser/build/manual',
    label: '手工构建',
    icon: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11 2l3 3-8 8H3v-3l8-8z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
  },
]

function isTabActive(path: string) {
  if (path === '/browser') return route.path === '/browser'
  return route.path.startsWith(path)
}
</script>

<style scoped>
.browser {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.browser__tabs {
  display: flex;
  gap: 0;
  padding: 0 20px;
  background: var(--neutral-0);
  border-bottom: 1px solid var(--neutral-200);
  flex-shrink: 0;
}

.browser__tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  font-size: var(--text-body-size);
  font-weight: 500;
  color: var(--neutral-500);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
  cursor: pointer;
}

.browser__tab:hover {
  color: var(--neutral-700);
}

.browser__tab--active {
  color: var(--semantic-600);
  border-bottom-color: var(--semantic-600);
}

.browser__tab-icon {
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.browser__content {
  flex: 1;
  overflow: hidden;
}
</style>
