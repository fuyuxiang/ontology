<template>
  <aside class="sidebar">
    <div class="sidebar__logo">
      <img src="/images/ontology/BONC.png" alt="BONC" class="sidebar__logo-img" />
      <span class="sidebar__logo-divider"></span>
      <span class="sidebar__logo-text">元枢 Ontology</span>
    </div>

    <nav class="sidebar__nav">
      <template v-for="(group, gi) in navGroups" :key="gi">
        <div v-if="gi > 0" class="sidebar__divider"></div>
        <div v-if="group.label" class="sidebar__section-label">{{ group.label }}</div>
        <template v-for="item in group.items" :key="item.path">
          <!-- 有子菜单 -->
          <template v-if="item.children">
            <RouterLink
              :to="item.path"
              class="sidebar__item sidebar__item--parent"
              :class="{ 'sidebar__item--active': isParentActive(item) }"
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

  </aside>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

interface NavItem {
  path: string
  label: string
  icon?: string
  exact?: boolean
  children?: NavItem[]
}

interface NavGroup {
  label: string
  items: NavItem[]
}

function isActive(path: string, exact?: boolean) {
  return exact ? route.path === path : route.path.startsWith(path)
}

function isParentActive(item: NavItem) {
  if (item.children?.length) {
    return item.children.some(c => isActive(c.path, c.exact))
  }
  return route.path.startsWith(item.path)
}

const expandedSubmenus = reactive<Record<string, boolean>>({})

function toggleSubmenu(path: string) {
  expandedSubmenus[path] = !expandedSubmenus[path]
}

const ico = {
  dashboard: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="1.5" y="1.5" width="13" height="13" rx="2.5" stroke="currentColor" stroke-width="1.4"/><path d="M5 5v6M8 7.5v3.5M11 4v7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  sysBoard: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2.5 10.5a6 6 0 1111 0" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><path d="M8 9.5l2.5-4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="8" cy="10" r="1.2" fill="currentColor"/></svg>`,
  datasource: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M6 2v3M10 2v3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><rect x="4" y="5" width="8" height="4" rx="1.5" stroke="currentColor" stroke-width="1.4"/><path d="M6 9v2a2 2 0 004 0V9" stroke="currentColor" stroke-width="1.4"/><path d="M8 11v3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  catalog: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2 4.5A1.5 1.5 0 013.5 3H6l1.5 1.5h5A1.5 1.5 0 0114 6v6.5a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 012 12.5v-8z" stroke="currentColor" stroke-width="1.4"/><path d="M6 9h4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  model: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 1.5l5.5 3v7L8 14.5 2.5 11.5v-7L8 1.5z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M8 7.5v7M2.5 4.5L8 7.5l5.5-3" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>`,
  ontologyMgr: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="8" cy="3" r="1.8" stroke="currentColor" stroke-width="1.4"/><circle cx="4" cy="13" r="1.8" stroke="currentColor" stroke-width="1.4"/><circle cx="12" cy="13" r="1.8" stroke="currentColor" stroke-width="1.4"/><path d="M8 4.8V8M8 8l-4 3.2M8 8l4 3.2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  graph: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.4"/><circle cx="3" cy="3.5" r="1.5" stroke="currentColor" stroke-width="1.4"/><circle cx="13.5" cy="4.5" r="1.5" stroke="currentColor" stroke-width="1.4"/><circle cx="4" cy="13" r="1.5" stroke="currentColor" stroke-width="1.4"/><path d="M4.3 4.8L6.5 6.8M10 7.2l2.2-1.8M5.3 11.8L6.8 9.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  version: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 1.5c0 0-4.5 3-4.5 8h9c0-5-4.5-8-4.5-8z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M6 14.5v-2.5a2 2 0 014 0v2.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="8" cy="7" r="1.2" fill="currentColor"/></svg>`,
  api: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="5" y="2" width="6" height="12" rx="1.5" stroke="currentColor" stroke-width="1.4"/><path d="M7.5 5h1M7.5 7.5h1" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><path d="M2 6h3M2 10h3M11 6h3M11 10h3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  agent: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="5" width="10" height="8" rx="2.5" stroke="currentColor" stroke-width="1.4"/><circle cx="6" cy="9" r="1" fill="currentColor"/><circle cx="10" cy="9" r="1" fill="currentColor"/><path d="M8 2v3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="8" cy="1.5" r="1" stroke="currentColor" stroke-width="1.2"/></svg>`,
  tool: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9 1.5L4 9h4l-1 5.5L12 7H8l1-5.5z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>`,
  orchestrate: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="8" cy="2.5" r="1.8" stroke="currentColor" stroke-width="1.4"/><circle cx="3.5" cy="13" r="1.8" stroke="currentColor" stroke-width="1.4"/><circle cx="12.5" cy="13" r="1.8" stroke="currentColor" stroke-width="1.4"/><rect x="5.5" y="7" width="5" height="3" rx="1" stroke="currentColor" stroke-width="1.4"/><path d="M8 4.3V7M6.5 10l-3 1.2M9.5 10l3 1.2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  monitor: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="1.5" y="2.5" width="13" height="11" rx="2" stroke="currentColor" stroke-width="1.4"/><path d="M4 8.5h2l1-2.5 1.5 5L10 6l1 2.5h2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  audit: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2 3h8M2 6h6M2 9h5M2 12h4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="11.5" cy="10.5" r="3" stroke="currentColor" stroke-width="1.4"/><path d="M11.5 9v1.5l1.2 1" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  permissions: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="5.5" cy="6.5" r="3" stroke="currentColor" stroke-width="1.4"/><path d="M8 8.5l5 5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><path d="M11 11.5l1.5 1.5M12 10.5l1.5 1.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="5.5" cy="6.5" r="1" fill="currentColor"/></svg>`,
  config: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2 4h4M10 4h4M2 8h7M12 8h2M2 12h2M7 12h7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="8" cy="4" r="1.8" stroke="currentColor" stroke-width="1.4"/><circle cx="10.5" cy="8" r="1.8" stroke="currentColor" stroke-width="1.4"/><circle cx="5" cy="12" r="1.8" stroke="currentColor" stroke-width="1.4"/></svg>`,
  rule: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="2.5" y="2" width="11" height="12" rx="2" stroke="currentColor" stroke-width="1.4"/><path d="M5.5 5.5l1 1 1.5-1.5M5.5 9.5l1 1 1.5-1.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.5 6h2M9.5 10h2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  action: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.4"/><path d="M6.5 5.5l4 2.5-4 2.5v-5z" fill="currentColor"/></svg>`,
}

const navGroups: NavGroup[] = [
  { label: '看板', items: [
    { path: '/workspace/business', label: '业务总览', icon: ico.dashboard },
    { path: '/dashboard', label: '系统看板', icon: ico.sysBoard, exact: true },
  ]},
  { label: '数据集成', items: [
    { path: '/data/connections', label: '数据接入', icon: ico.datasource },
    { path: '/data/assets', label: '资产目录', icon: ico.catalog },
  ]},
  { label: '本体中心', items: [
    { path: '/builder', label: '对象建模', icon: ico.model, children: [
      { path: '/builder', label: '手动构建', exact: true },
      { path: '/builder/template', label: '模板构建' },
      { path: '/builder/doc', label: '文档构建' },
      { path: '/builder/ai', label: '资产构建' },
    ]},
    { path: '/logic/functions', label: '逻辑建模', icon: ico.rule, children: [
      { path: '/logic/functions', label: '函数' },
      { path: '/logic/rules', label: '规则' },
    ]},
    { path: '/logic/actions', label: '行动建模', icon: ico.action },
    { path: '/browser', label: '本体管理', icon: ico.ontologyMgr, children: [
      { path: '/browser', label: '对象管理', exact: true },
      { path: '/data/mapping', label: '映射管理' },
    ]},
    { path: '/studio', label: '本体探索', icon: ico.graph },
    { path: '/ontology/publish', label: '本体发布', icon: ico.version },
    { path: '/service/api', label: '本体服务', icon: ico.api },
  ]},
  { label: '本体应用', items: [
    { path: '/agent/manage', label: '智能体管理', icon: ico.agent },
    { path: '/agent/toolbox', label: '技能管理', icon: ico.tool },
    { path: '/aip', label: '流程编排', icon: ico.orchestrate },
  ]},
  { label: '运维与安全中心', items: [
    { path: '/ops/log-audit', label: '日志与审计', icon: ico.audit },
    { path: '/ops/permissions', label: '权限管理', icon: ico.permissions },
    { path: '/ops/config', label: '系统配置', icon: ico.config },
  ]},
]
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width, 240px);
  min-width: var(--sidebar-width, 240px);
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
  gap: 8px;
  padding: 20px 20px 16px;
  flex-shrink: 0;
}
.sidebar__logo-img {
  height: 18px;
  width: auto;
  object-fit: contain;
  flex-shrink: 0;
}
.sidebar__logo-divider {
  width: 1px;
  height: 14px;
  background: var(--sidebar-border);
  flex-shrink: 0;
}
.sidebar__logo-text {
  font-size: 13px;
  font-weight: 700;
  color: var(--sidebar-text-active);
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.sidebar__nav {
  flex: 1;
  overflow-y: auto;
  padding: 4px 12px 12px;
}
.sidebar__section-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--sidebar-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.6px;
  padding: 16px 10px 6px;
}
.sidebar__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  color: var(--sidebar-text);
  text-decoration: none;
  font-size: 13px;
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
  font-weight: 600;
  border-left: none;
  padding-left: 12px;
  position: relative;
}
.sidebar__item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--sidebar-accent, var(--semantic-600));
}
.sidebar__item--active .sidebar__item-icon { color: var(--semantic-600); }
.sidebar__item-icon {
  width: 18px; height: 18px; flex-shrink: 0;
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
.sidebar__submenu-items { padding-left: 30px; }
.sidebar__item--child {
  font-size: 12px;
  padding: 6px 10px;
  color: var(--sidebar-text-muted);
  border-radius: 6px;
}
.sidebar__item--child.sidebar__item--active {
  color: var(--sidebar-text-active);
  background: var(--sidebar-bg-active);
  border-left: none;
  padding-left: 10px;
}
.sidebar__item--child.sidebar__item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 2px;
  border-radius: 0 2px 2px 0;
  background: var(--semantic-400);
}
.sidebar__divider {
  height: 1px;
  background: var(--sidebar-border);
  margin: 8px 12px;
}
</style>
