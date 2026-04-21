<template>
  <aside class="sidebar">
    <div class="sidebar__logo">
      <div class="sidebar__logo-icon">
        <img src="/images/ontology/BONC.png" alt="BONC" class="sidebar__logo-img" />
      </div>
      <div class="sidebar__logo-info">
        <span class="sidebar__logo-text">元枢</span>
        <span class="sidebar__logo-subtext">Ontology</span>
      </div>
    </div>

    <nav class="sidebar__nav">
      <template v-for="(group, gi) in navGroups" :key="gi">
        <div v-if="gi > 0" class="sidebar__divider"></div>
        <div class="sidebar__section-label">{{ group.label }}</div>
        <template v-for="item in group.items" :key="item.path">
          <!-- 有子菜单 -->
          <template v-if="item.children">
            <RouterLink
              :to="item.path"
              class="sidebar__item sidebar__item--parent"
              :class="{ 'sidebar__item--active': route.path.startsWith(item.path) }"
              @click.prevent="toggleSubmenu(item.path)"
            >
              <span class="sidebar__item-icon" v-html="item.icon"></span>
              <span class="sidebar__item-label">{{ item.label }}</span>
              <svg class="sidebar__sub-arrow" :class="{ 'sidebar__sub-arrow--open': expandedSubmenus[item.path] }" width="10" height="10" viewBox="0 0 12 12" fill="none">
                <path d="M4 3l4 3-4 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </RouterLink>
            <div v-show="expandedSubmenus[item.path]" class="sidebar__submenu-items">
              <RouterLink
                v-for="child in item.children"
                :key="child.path"
                :to="child.path"
                class="sidebar__item sidebar__item--child"
                :class="{ 'sidebar__item--active': isActive(child.path, child.exact) }"
              >
                <span class="sidebar__item-label">{{ child.label }}</span>
              </RouterLink>
            </div>
          </template>
          <!-- 普通菜单项 -->
          <RouterLink
            v-else
            :to="item.path"
            class="sidebar__item"
            :class="{ 'sidebar__item--active': isActive(item.path, item.exact) }"
          >
            <span class="sidebar__item-icon" v-html="item.icon"></span>
            <span class="sidebar__item-label">{{ item.label }}</span>
          </RouterLink>
        </template>
      </template>
    </nav>

    <div class="sidebar__footer">
      <button class="sidebar__item sidebar__item--footer" @click="showSettings = true">
        <div class="sidebar__avatar">{{ initial }}</div>
        <span class="sidebar__item-label">{{ userName }}</span>
      </button>
    </div>

    <SettingsDialog :visible="showSettings" @close="showSettings = false" />
  </aside>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../store/auth'
import SettingsDialog from './SettingsDialog.vue'

const route = useRoute()
const authStore = useAuthStore()
const showSettings = ref(false)

const userName = computed(() => authStore.user?.name || '用户')
const initial = computed(() => userName.value.charAt(0).toUpperCase())

function isActive(path: string, exact?: boolean) {
  return exact ? route.path === path : route.path.startsWith(path)
}

const expandedSubmenus = reactive<Record<string, boolean>>({})
expandedSubmenus['/browser'] = true

function toggleSubmenu(path: string) {
  expandedSubmenus[path] = !expandedSubmenus[path]
}

const ico = {
  dashboard: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="8" width="3" height="6" rx="1" fill="currentColor" opacity="0.6"/><rect x="6.5" y="5" width="3" height="9" rx="1" fill="currentColor" opacity="0.8"/><rect x="11" y="2" width="3" height="12" rx="1" fill="currentColor"/></svg>`,
  todo: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M5 8l2 2 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  changes: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 3v5l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/></svg>`,
  catalog: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="3" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M8 6v2M8 8L3 10M8 8l5 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  search: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4.5" stroke="currentColor" stroke-width="1.5"/><path d="M10.5 10.5l2.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  graph: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="4" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M6 4h4M5 5.5L7 10.5M11 5.5L9 10.5" stroke="currentColor" stroke-width="1.5"/></svg>`,
  datasource: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="currentColor" stroke-width="1.5"/><path d="M3 8v4c0 1.1 2.24 2 5 2s5-.9 5-2V8" stroke="currentColor" stroke-width="1.5"/></svg>`,
  mapping: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="4" cy="5" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="11" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M6 5h2l2 6h-2" stroke="currentColor" stroke-width="1.5"/></svg>`,
  lineage: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="3" cy="8" r="1.5" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="4" r="1.5" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="12" r="1.5" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="8" r="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M4.5 7.2L6.5 5M4.5 8.8L6.5 11M9.5 5L11.5 7.2M9.5 11L11.5 8.8" stroke="currentColor" stroke-width="1.5"/></svg>`,
  harness: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2L14 5.5v5L8 14l-6-3.5v-5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 6l2.5 1.5v3L8 12l-2.5-1.5v-3L8 6z" fill="currentColor" opacity=".3"/></svg>`,
  model: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="6" width="4" height="4" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="10" y="6" width="4" height="4" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M6 8h4" stroke="currentColor" stroke-width="1.5"/><path d="M8 3v3M8 10v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  copilot: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2a6 6 0 100 12A6 6 0 008 2z" stroke="currentColor" stroke-width="1.5"/><path d="M5.5 9.5s.5 1.5 2.5 1.5 2.5-1.5 2.5-1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="6" cy="7" r="0.75" fill="currentColor"/><circle cx="10" cy="7" r="0.75" fill="currentColor"/></svg>`,
  scene: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/></svg>`,
  api: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M5 4L2 8l3 4M11 4l3 4-3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 3L7 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  audit: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.5"/><path d="M6 5h4M6 8h4M6 11h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  glossary: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 2h7a3 3 0 010 6H3V2z" stroke="currentColor" stroke-width="1.5"/><path d="M3 8h8a3 3 0 010 6H3V8z" stroke="currentColor" stroke-width="1.5"/></svg>`,
  permission: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="4" y="7" width="8" height="6" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M6 7V5a2 2 0 014 0v2" stroke="currentColor" stroke-width="1.5"/></svg>`,
  version: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M8 6v4" stroke="currentColor" stroke-width="1.5"/></svg>`,
}

const navGroups = [
  { label: '工作台', items: [
    { path: '/dashboard', label: '平台总览', icon: ico.dashboard, exact: true },
    { path: '/todo', label: '我的待办', icon: ico.todo },
    { path: '/changes', label: '最近变更', icon: ico.changes },
  ]},
  { label: '本体管理', items: [
    { path: '/browser', label: '本体建模', icon: ico.catalog, exact: true },
    { path: '/browser/graph', label: '本体图谱', icon: ico.graph },
  ]},
  { label: '数据接入', items: [
    { path: '/datasource', label: '数据源', icon: ico.datasource },
    { path: '/data/mapping', label: '本体映射', icon: ico.mapping },
    { path: '/data/lineage', label: '血缘分析', icon: ico.lineage },
  ]},
  { label: '智能编排', items: [
    { path: '/harness', label: '智能体编排', icon: ico.harness },
    { path: '/agents', label: '智能体管理', icon: ico.harness },
    { path: '/orchestration/models', label: '模型管理', icon: ico.model },
  ]},
  { label: '智能应用', items: [
    { path: '/copilot', label: '知识问答', icon: ico.copilot },
    { path: '/scene', label: '场景验证', icon: ico.scene, exact: true },
    { path: '/app/api', label: 'API开放平台', icon: ico.api },
  ]},
]
</script>

<style scoped>
.sidebar {
  width: 220px;
  min-width: 220px;
  height: 100vh;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--sidebar-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar__logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 16px 12px;
  flex-shrink: 0;
}
.sidebar__logo-img { width: 72px; height: 28px; border-radius: 4px; object-fit: contain; }
.sidebar__logo-info { display: flex; flex-direction: column; align-items: center; line-height: 1.2; }
.sidebar__logo-text { font-size: 15px; font-weight: 700; color: var(--sidebar-text-active); }
.sidebar__logo-subtext { font-size: 11px; font-weight: 600; color: var(--sidebar-text-muted); letter-spacing: 0.05em; }
.sidebar__nav {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 8px;
}
.sidebar__section-label {
  font-size: var(--text-caption-upper-size);
  font-weight: 600;
  color: var(--sidebar-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 8px 10px 4px;
}
.sidebar__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: var(--radius-md);
  color: var(--sidebar-text);
  text-decoration: none;
  font-size: var(--text-body-size);
  font-weight: 500;
  cursor: pointer;
  border: none;
  background: transparent;
  width: 100%;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.sidebar__item:hover {
  background: var(--sidebar-bg-hover);
  color: var(--sidebar-text-active);
}
.sidebar__item--active {
  background: var(--sidebar-bg-active);
  color: var(--sidebar-text-active);
  border-left: 3px solid var(--semantic-500, #4c6ef5);
  padding-left: 7px;
}
.sidebar__item--active .sidebar__item-icon { color: var(--semantic-500, #4c6ef5); }
.sidebar__item-icon {
  width: 16px; height: 16px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.sidebar__item-label { flex: 1; }
.sidebar__sub-arrow {
  margin-left: auto;
  transition: transform var(--transition-fast);
  flex-shrink: 0;
  color: var(--sidebar-text-muted);
}
.sidebar__sub-arrow--open { transform: rotate(90deg); }
.sidebar__submenu-items { padding-left: 26px; }
.sidebar__item--child {
  font-size: var(--text-caption-size);
  padding: 5px 10px;
  color: var(--sidebar-text-muted);
}
.sidebar__item--child.sidebar__item--active {
  color: var(--sidebar-text-active);
  border-left: 2px solid var(--semantic-400, #748ffc);
  padding-left: 8px;
}
.sidebar__divider {
  height: 1px;
  background: var(--sidebar-border);
  margin: 6px 0;
}
.sidebar__footer {
  padding: 8px;
  border-top: 1px solid var(--sidebar-border);
  flex-shrink: 0;
}
.sidebar__item--footer { color: var(--sidebar-text-muted); }
.sidebar__avatar {
  width: 24px; height: 24px; border-radius: var(--radius-full);
  background: var(--semantic-600); color: var(--neutral-0);
  font-size: var(--text-caption-size); font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
</style>
