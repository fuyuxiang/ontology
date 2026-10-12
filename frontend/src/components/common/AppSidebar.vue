<template>
  <button v-if="isMobile" ref="mobileToggle" class="sidebar-mobile-toggle" type="button" :aria-expanded="mobileOpen" aria-controls="platform-navigation" :aria-label="mobileOpen ? t('shell.closeNavigation') : t('shell.openNavigation')" @click="toggleMobileNavigation">
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path v-if="mobileOpen" d="M5 5l10 10M15 5L5 15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path v-else d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
  </button>
  <button v-if="isMobile && mobileOpen" class="sidebar-mobile-overlay" :aria-label="t('shell.closeNavigation')" @click="closeMobileNavigation"></button>
  <aside id="platform-navigation" ref="sidebarElement" class="sidebar" :class="{ 'sidebar--mobile-open': mobileOpen }" :inert="isMobile && !mobileOpen ? true : undefined" :aria-hidden="isMobile && !mobileOpen ? true : undefined">
    <div class="sidebar__logo">
      <img src="/images/ontology/logo.png" :alt="platform.system_name" class="sidebar__logo-img" />
      <span class="sidebar__logo-divider"></span>
      <span class="sidebar__logo-text" :title="platform.system_name">{{ platform.system_name }}</span>
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
import { reactive, ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePlatformConfigStore } from '../../store/platformConfig'
import { useAuthStore } from '../../store/auth'
import { canAccessRoute } from '../../utils/access'
const { t } = useI18n()
const platform = usePlatformConfigStore()
const auth = useAuthStore()

const route = useRoute()
const isMobile = ref(window.innerWidth <= 768)
const mobileOpen = ref(false)
const mobileToggle = ref<HTMLButtonElement | null>(null)
const sidebarElement = ref<HTMLElement | null>(null)
function resizeNavigation() { isMobile.value = window.innerWidth <= 768; if (!isMobile.value) mobileOpen.value = false }
function closeMobileNavigation() { mobileOpen.value = false; nextTick(() => mobileToggle.value?.focus()) }
function toggleMobileNavigation() { if (mobileOpen.value) closeMobileNavigation(); else { mobileOpen.value = true; nextTick(() => sidebarElement.value?.querySelector<HTMLAnchorElement>('.sidebar__item')?.focus()) } }
function navigationKey(event: KeyboardEvent) { if (!isMobile.value || !mobileOpen.value) return; if (event.key === 'Escape') { event.preventDefault(); closeMobileNavigation() }; if (event.key === 'Tab') { const links = sidebarElement.value?.querySelectorAll<HTMLAnchorElement>('a.sidebar__item'); if (!links?.length) return; const first = links[0]; const last = links[links.length - 1]; if (event.shiftKey && document.activeElement === first) { event.preventDefault(); mobileToggle.value?.focus() } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); mobileToggle.value?.focus() } else if (document.activeElement === mobileToggle.value) { event.preventDefault(); (event.shiftKey ? last : first)?.focus() } } }
watch(() => route.path, () => { if (isMobile.value) mobileOpen.value = false })
onMounted(() => { window.addEventListener('resize', resizeNavigation); document.addEventListener('keydown', navigationKey) })
onBeforeUnmount(() => { window.removeEventListener('resize', resizeNavigation); document.removeEventListener('keydown', navigationKey) })

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
  mapping: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="1.5" y="4" width="4" height="8" rx="1" stroke="currentColor" stroke-width="1.4"/><rect x="10.5" y="4" width="4" height="8" rx="1" stroke="currentColor" stroke-width="1.4"/><path d="M5.5 6.5h5M5.5 9.5h5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  mcp: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 2v4M8 10v4M2 8h4M10 8h4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="8" cy="8" r="2.5" stroke="currentColor" stroke-width="1.4"/><circle cx="8" cy="2" r="1" fill="currentColor"/><circle cx="8" cy="14" r="1" fill="currentColor"/><circle cx="2" cy="8" r="1" fill="currentColor"/><circle cx="14" cy="8" r="1" fill="currentColor"/></svg>`,
}

const navGroups = computed<NavGroup[]>(() => [
  { label: t('shell.dataIntegration'), items: [
    { path: '/data/connections', label: t('shell.connections'), icon: ico.datasource },
    { path: '/data/assets', label: t('shell.assets'), icon: ico.catalog },
  ]},
  { label: t('shell.ontologyCenter'), items: [
    { path: '/ontology/list', label: t('shell.ontologies'), icon: ico.ontologyMgr },
    { path: '/ontology/publish', label: t('shell.publish'), icon: ico.version },
    { path: '/service/mcp', label: t('shell.services'), icon: ico.mcp },
  ]},
  { label: t('shell.applications'), items: [
    { path: '/agent/manage', label: t('shell.agents'), icon: ico.agent },
    { path: '/skills', label: t('shell.skills'), icon: ico.rule },
  ]},
  { label: t('shell.operations'), items: [
    { path: '/dashboard', label: t('shell.dashboard'), icon: ico.monitor },
    { path: '/ops/config', label: t('shell.config'), icon: ico.config },
  ]},
].map(group => ({ ...group, items: group.items.filter(item => canAccessRoute(item.path, permission => auth.hasPermission(permission))) })).filter(group => group.items.length))
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
  overflow: hidden;
  text-overflow: ellipsis;
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
.sidebar-mobile-toggle { display: none; }
@media (max-width: 768px) {
  .sidebar { position: fixed; inset: 0 auto 0 0; width: 240px; min-width: 240px; height: 100vh; height: 100dvh; z-index: 1100; transform: translateX(-100%); transition: transform 180ms ease; background: var(--sidebar-bg, #fff); box-shadow: 8px 0 32px rgba(15, 23, 42, .14); }
  .sidebar--mobile-open { transform: translateX(0); }
  .sidebar__logo { padding-right: 48px; }
  .sidebar-mobile-toggle { display: flex; align-items: center; justify-content: center; position: fixed; top: 12px; left: 12px; width: 32px; height: 32px; background: #fff; color: #334155; border: 1px solid #e2e8f0; border-radius: 6px; z-index: 1110; cursor: pointer; }
  .sidebar-mobile-overlay { position: fixed; inset: 0; z-index: 1090; background: rgba(15, 23, 42, .3); border: 0; padding: 0; }
  .sidebar--mobile-open .sidebar__logo { padding-top: 58px; }
}
</style>
