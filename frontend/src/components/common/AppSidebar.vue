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
        <div v-if="group.label" class="sidebar__section-label">{{ group.label }}</div>
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

  </aside>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

function isActive(path: string, exact?: boolean) {
  return exact ? route.path === path : route.path.startsWith(path)
}

const expandedSubmenus = reactive<Record<string, boolean>>({})

function toggleSubmenu(path: string) {
  expandedSubmenus[path] = !expandedSubmenus[path]
}

const ico = {
  dashboard: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="5" height="5" rx="1.5" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="2" width="5" height="5" rx="1.5" stroke="currentColor" stroke-width="1.5"/><rect x="2" y="9" width="5" height="5" rx="1.5" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="9" width="5" height="5" rx="1.5" stroke="currentColor" stroke-width="1.5"/></svg>`,
  catalog: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="3" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M8 6v2M8 8L3 10M8 8l5 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  graph: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="4" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M6 4h4M5 5.5L7 10.5M11 5.5L9 10.5" stroke="currentColor" stroke-width="1.5"/></svg>`,
  version: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M8 6v4" stroke="currentColor" stroke-width="1.5"/></svg>`,
  datasource: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="currentColor" stroke-width="1.5"/><path d="M3 8v4c0 1.1 2.24 2 5 2s5-.9 5-2V8" stroke="currentColor" stroke-width="1.5"/></svg>`,
  mapping: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="4" cy="5" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="11" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M6 5h2l2 6h-2" stroke="currentColor" stroke-width="1.5"/></svg>`,
  quality: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2v12M4 5l4 3-4 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 5l-4 3 4 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/></svg>`,
  harness: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2L14 5.5v5L8 14l-6-3.5v-5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 6l2.5 1.5v3L8 12l-2.5-1.5v-3L8 6z" fill="currentColor" opacity=".3"/></svg>`,
  model: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="6" width="4" height="4" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="10" y="6" width="4" height="4" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M6 8h4" stroke="currentColor" stroke-width="1.5"/><path d="M8 3v3M8 10v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  rules: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 3h10v2H3V3zM3 7h7v2H3V7zM3 11h10v2H3v-2z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="8" r="2" stroke="currentColor" stroke-width="1.5"/></svg>`,
  workflow: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1" y="3" width="4" height="3" rx="1" stroke="currentColor" stroke-width="1.3"/><rect x="6" y="7" width="4" height="3" rx="1" stroke="currentColor" stroke-width="1.3"/><rect x="11" y="3" width="4" height="3" rx="1" stroke="currentColor" stroke-width="1.3"/><path d="M5 4.5h6M8 5.5v1.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>`,
  sdk: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 4l-2 4 2 4M12 4l2 4-2 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 2L7 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  agent: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 14c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="11" cy="4" r="1.5" fill="currentColor" opacity="0.4"/></svg>`,
  tool: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 2a3 3 0 00-2.83 4L3 10.17V13h2.83L10 8.83A3 3 0 1010 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  settings: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  scene: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="5" cy="4" r="1.5" fill="currentColor"/><circle cx="11" cy="8" r="1.5" fill="currentColor"/><circle cx="7" cy="12" r="1.5" fill="currentColor"/></svg>`,
  sandbox: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 10l6 3 6-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 7l6 3 6-3-6-3-6 3z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  tracking: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 12l3-4 3 2 4-6 2 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="13" cy="7" r="1.5" fill="currentColor"/></svg>`,
  evals: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M5 8l2 2 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  copilot: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2a6 6 0 100 12A6 6 0 008 2z" stroke="currentColor" stroke-width="1.5"/><path d="M5.5 9.5s.5 1.5 2.5 1.5 2.5-1.5 2.5-1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="6" cy="7" r="0.75" fill="currentColor"/><circle cx="10" cy="7" r="0.75" fill="currentColor"/></svg>`,
  bizApp: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M2 6h12" stroke="currentColor" stroke-width="1.5"/><circle cx="4.5" cy="4.5" r="0.5" fill="currentColor"/><circle cx="6.5" cy="4.5" r="0.5" fill="currentColor"/></svg>`,
  api: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M5 4L2 8l3 4M11 4l3 4-3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 3L7 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  audit: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.5"/><path d="M6 5h4M6 8h4M6 11h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
}

const navGroups = [
  { label: '', items: [
    { path: '/dashboard', label: '平台总览', icon: ico.dashboard, exact: true },
  ]},
  { label: '本体中心', items: [
    { path: '/datasource', label: '数据接入', icon: ico.datasource },
    { path: '/browser', label: '本体建模', icon: ico.catalog, exact: true },
    { path: '/studio', label: '本体工作室', icon: ico.graph },
    { path: '/browser/graph', label: '本体图谱', icon: ico.graph },
    { path: '/data/mapping', label: '本体映射', icon: ico.mapping },
    { path: '/ontology/publish', label: '本体发布', icon: ico.version },
  ]},
  { label: '逻辑中心', items: [
    { path: '/logic/actions', label: 'Actions 管理', icon: ico.workflow },
    { path: '/logic/functions', label: 'Functions 管理', icon: ico.sdk },
    { path: '/logic/rules', label: 'Rules 管理', icon: ico.rules },
  ]},
  { label: '本体服务', items: [
    { path: '/service/api', label: 'API 服务', icon: ico.api },
    { path: '/service/osdk', label: 'OSDK 生成', icon: ico.sdk },
    { path: '/service/agent', label: 'Agent 交互', icon: ico.agent },
    { path: '/service/workflow', label: '流程编排', icon: ico.workflow },
  ]},
  { label: '业务场景', items: [
    { path: '/scene', label: '场景总览', icon: ico.scene, exact: true, children: [
      { path: '/scene/fttr', label: 'FTTR续约' },
      { path: '/scene/broadband', label: '宽带退单' },
      { path: '/scene/enterprise', label: '政企根因' },
      { path: '/scene/mnp', label: '携号转网' },
    ]},
  ]},
  { label: '运营观测', items: [
    { path: '/ops/evals', label: 'Agent 评测', icon: ico.evals },
    { path: '/ops/traces', label: '运行追踪', icon: ico.tracking },
  ]},
  { label: '系统设置', items: [
    { path: '/settings/models', label: '模型管理', icon: ico.model },
    { path: '/governance/audit', label: '权限审计', icon: ico.audit },
    { path: '/settings/monitor', label: '运维监控', icon: ico.tracking },
    { path: '/settings/general', label: '系统配置', icon: ico.settings },
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
  gap: 12px;
  padding: 20px 20px 16px;
  flex-shrink: 0;
}
.sidebar__logo-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--semantic-500), var(--semantic-700));
  box-shadow: 0 2px 8px rgba(76, 110, 245, 0.2);
}
.sidebar__logo-img { width: 22px; height: 22px; border-radius: 0; object-fit: contain; filter: brightness(10); }
.sidebar__logo-info { display: flex; flex-direction: column; line-height: 1.2; }
.sidebar__logo-text { font-size: 16px; font-weight: 700; color: var(--sidebar-text-active); letter-spacing: -0.3px; }
.sidebar__logo-subtext { font-size: 11px; font-weight: 500; color: var(--sidebar-text-muted); letter-spacing: 0.02em; }
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
