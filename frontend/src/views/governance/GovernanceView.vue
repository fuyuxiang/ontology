<template>
  <div class="governance">
    <div class="governance__sidebar">
      <h3 class="governance__title">系统设置</h3>
      <RouterLink
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="governance__menu-item"
        :class="{ 'governance__menu-item--active': route.path === item.path }"
      >
        <span class="governance__menu-icon" v-html="item.icon"></span>
        <span>{{ item.label }}</span>
      </RouterLink>
      <RouterLink to="/dashboard" class="governance__back">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M10 4L6 8l4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        返回主页
      </RouterLink>
    </div>
    <div class="governance__content">
      <RouterView />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const menuItems = [
  { path: '/governance/permissions', label: '权限控制', icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="4" y="7" width="8" height="6" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M6 7V5a2 2 0 014 0v2" stroke="currentColor" stroke-width="1.5"/></svg>' },
  { path: '/governance/audit', label: '审计日志', icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.5"/><path d="M6 5h4M6 8h4M6 11h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>' },
  { path: '/governance/glossary', label: '帮助文档', icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 2h7a3 3 0 010 6H3V2z" stroke="currentColor" stroke-width="1.5"/><path d="M3 8h8a3 3 0 010 6H3V8z" stroke="currentColor" stroke-width="1.5"/></svg>' },
]
</script>

<style scoped>
.governance { display: flex; height: 100%; }
.governance__sidebar {
  width: 220px; min-width: 220px;
  background: var(--neutral-0);
  border-right: 1px solid var(--neutral-200);
  padding: 20px 12px;
  display: flex; flex-direction: column;
}
.governance__title {
  font-size: 18px; font-weight: 600; color: var(--neutral-800);
  padding: 0 10px 16px; margin: 0;
  border-bottom: 1px solid var(--neutral-200);
  margin-bottom: 12px;
}
.governance__menu-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px;
  color: var(--neutral-600); text-decoration: none;
  font-size: 14px; font-weight: 500;
  transition: all 0.15s;
}
.governance__menu-item:hover { background: var(--neutral-100); color: var(--neutral-800); }
.governance__menu-item--active {
  background: var(--semantic-50, #eef2ff);
  color: var(--semantic-600);
}
.governance__menu-icon {
  width: 16px; height: 16px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.governance__back {
  margin-top: auto;
  display: flex; align-items: center; gap: 6px;
  padding: 8px 10px; border-radius: 8px;
  color: var(--neutral-500); text-decoration: none;
  font-size: 13px; transition: all 0.15s;
}
.governance__back:hover { background: var(--neutral-100); color: var(--neutral-700); }
.governance__content { flex: 1; overflow-y: auto; background: var(--neutral-50); }
</style>
