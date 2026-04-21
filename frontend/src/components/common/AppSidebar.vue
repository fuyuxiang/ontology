<template>
  <aside class="sidebar">
    <div class="sidebar__logo">
      <div class="sidebar__logo-icon">
        <img src="/images/ontology/BONC.png" alt="BONC" class="sidebar__logo-img" />
      </div>
      <div class="sidebar__logo-info">
        <span class="sidebar__logo-text">元枢</span>
        <span class="sidebar__logo-text">Ontology</span>
      </div>
    </div>

    <nav class="sidebar__nav">
      <template v-for="(group, gi) in navGroups" :key="gi">
        <div v-if="gi > 0" class="sidebar__divider"></div>
        <div class="sidebar__section-label">{{ group.label }}</div>
        <RouterLink
          v-for="item in group.items"
          :key="item.path"
          :to="item.path"
          class="sidebar__item"
          :class="{ 'sidebar__item--active': isActive(item.path, item.exact) }"
        >
          <span class="sidebar__item-icon" v-html="item.icon"></span>
          <span class="sidebar__item-label">{{ item.label }}</span>
        </RouterLink>
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
import { ref, computed } from 'vue'
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

const ico = {
  dashboard: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="8" width="3" height="6" rx="1" fill="currentColor" opacity="0.6"/><rect x="6.5" y="5" width="3" height="9" rx="1" fill="currentColor" opacity="0.8"/><rect x="11" y="2" width="3" height="12" rx="1" fill="currentColor"/></svg>`,
  todo: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M5 8l2 2 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  changes: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 3v5l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/></svg>`,
  catalog: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="3" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M8 6v2M8 8L3 10M8 8l5 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  search: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4.5" stroke="currentColor" stroke-width="1.5"/><path d="M10.5 10.5l2.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  graph: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="4" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M6 4h4M5 5.5L7 10.5M11 5.5L9 10.5" stroke="currentColor" stroke-width="1.5"/></svg>`,
  object: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="3" y="3" width="10" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M6 6h4M6 8h4M6 10h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  attr: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 4h8M4 8h6M4 12h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  rule: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 3h10v3H3zM3 10h10v3H3z" stroke="currentColor" stroke-width="1.5" rx="1"/><path d="M8 6v4" stroke="currentColor" stroke-width="1.5"/></svg>`,
  action: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M9 2L4 9h4l-1 5 5-7H8l1-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  importExport: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M5 2v12M11 2v12M2 5h12M2 11h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  knowledge: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 2h7l3 3v9a1 1 0 01-1 1H3a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.5"/><path d="M10 2v3h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M5 7h6M5 9.5h6M5 12h4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>`,
  datasource: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="currentColor" stroke-width="1.5"/><path d="M3 8v4c0 1.1 2.24 2 5 2s5-.9 5-2V8" stroke="currentColor" stroke-width="1.5"/></svg>`,
  mapping: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="4" cy="5" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="11" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M6 5h2l2 6h-2" stroke="currentColor" stroke-width="1.5"/></svg>`,
  resolve: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 8h4l2-4 2 8 2-4h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  sync: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 8a6 6 0 0110-4.5M14 8a6 6 0 01-10 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M12 2v3h-3M4 14v-3h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  lineage: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="3" cy="8" r="1.5" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="4" r="1.5" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="12" r="1.5" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="8" r="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M4.5 7.2L6.5 5M4.5 8.8L6.5 11M9.5 5L11.5 7.2M9.5 11L11.5 8.8" stroke="currentColor" stroke-width="1.5"/></svg>`,
  quality: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.5 3 3.5.5-2.5 2.5.5 3.5L8 10l-3 1.5.5-3.5L3 5.5l3.5-.5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  semantic: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M7 4.5h2.5V9M9 11.5H7V7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  prompt: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M5 6l2 2-2 2M8 10h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  harness: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2L14 5.5v5L8 14l-6-3.5v-5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 6l2.5 1.5v3L8 12l-2.5-1.5v-3L8 6z" fill="currentColor" opacity=".3"/></svg>`,
  model: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="6" width="4" height="4" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="10" y="6" width="4" height="4" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M6 8h4" stroke="currentColor" stroke-width="1.5"/><path d="M8 3v3M8 10v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  copilot: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2a6 6 0 100 12A6 6 0 008 2z" stroke="currentColor" stroke-width="1.5"/><path d="M5.5 9.5s.5 1.5 2.5 1.5 2.5-1.5 2.5-1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="6" cy="7" r="0.75" fill="currentColor"/><circle cx="10" cy="7" r="0.75" fill="currentColor"/></svg>`,
  scene: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/></svg>`,
  alert: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2a4 4 0 00-4 4v3l-1 1.5h10L12 9V6a4 4 0 00-4-4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6.5 13a1.5 1.5 0 003 0" stroke="currentColor" stroke-width="1.5"/></svg>`,
  api: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M5 4L2 8l3 4M11 4l3 4-3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 3L7 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  version: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M8 6v4" stroke="currentColor" stroke-width="1.5"/></svg>`,
  permission: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="4" y="7" width="8" height="6" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M6 7V5a2 2 0 014 0v2" stroke="currentColor" stroke-width="1.5"/></svg>`,
  review: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2C4.5 2 2 5 2 8s2.5 6 6 6 6-3 6-6-2.5-6-6-6z" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v3l2 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  release: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2v8M5 7l3 3 3-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 12h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  audit: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke="currentColor" stroke-width="1.5"/><path d="M6 5h4M6 8h4M6 11h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  glossary: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 2h7a3 3 0 010 6H3V2z" stroke="currentColor" stroke-width="1.5"/><path d="M3 8h8a3 3 0 010 6H3V8z" stroke="currentColor" stroke-width="1.5"/></svg>`,
}

const navGroups = [
  { label: '工作台', items: [
    { path: '/dashboard', label: '平台总览', icon: ico.dashboard, exact: true },
    { path: '/todo', label: '我的待办', icon: ico.todo },
    { path: '/changes', label: '最近变更', icon: ico.changes },
  ]},
  { label: '本体资产', items: [
    { path: '/browser', label: '本体目录', icon: ico.catalog, exact: true },
    { path: '/search', label: '对象检索', icon: ico.search },
    { path: '/browser/graph', label: '关系图谱', icon: ico.graph },
  ]},
  { label: '本体建模', items: [
    { path: '/browser', label: '对象', icon: ico.object, exact: true },
    { path: '/modeling/attributes', label: '属性', icon: ico.attr },
    { path: '/browser/graph', label: '关系', icon: ico.graph },
    { path: '/browser/rules', label: '规则', icon: ico.rule },
    { path: '/modeling/actions', label: '动作', icon: ico.action },
    { path: '/modeling/import-export', label: '模型导入导出', icon: ico.importExport },
  ]},
  { label: '数据接入', items: [
    { path: '/datasource', label: '数据源', icon: ico.datasource },
    { path: '/knowledge', label: '多模态知识库', icon: ico.knowledge },
    { path: '/data/mapping', label: '本体映射', icon: ico.mapping },
    { path: '/data/sync', label: '同步任务', icon: ico.sync },
    { path: '/data/lineage', label: '血缘分析', icon: ico.lineage },
    { path: '/data/quality', label: '质量监控', icon: ico.quality },
  ]},
  { label: '智能编排', items: [
    { path: '/harness', label: '智能体编排', icon: ico.harness },
    { path: '/agents', label: '智能体管理', icon: ico.harness },
    { path: '/orchestration/models', label: '模型管理', icon: ico.model },
  ]},
  { label: '智能应用', items: [
    { path: '/copilot', label: '知识问答', icon: ico.copilot },
    { path: '/scene', label: '场景验证', icon: ico.scene, exact: true },
    { path: '/app/api', label: 'API开放', icon: ico.api },
  ]},
  { label: '治理中心', items: [
    { path: '/governance/versions', label: '版本管理', icon: ico.version },
    { path: '/governance/permissions', label: '权限控制', icon: ico.permission },
    { path: '/governance/audit', label: '审计日志', icon: ico.audit },
    { path: '/governance/glossary', label: '帮助文档', icon: ico.glossary },
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
.sidebar__logo-img { width: 80px; height: 28px; border-radius: 6px; object-fit: contain; }
.sidebar__logo-info { display: flex; flex-direction: column; line-height: 1.2; }
.sidebar__logo-text { font-size: var(--text-body-size); font-weight: 700; color: var(--sidebar-text-active); }
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
