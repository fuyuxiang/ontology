<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sidebar__logo">
      <div class="sidebar__logo-icon">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M10 2L18 6.5V13.5L10 18L2 13.5V6.5L10 2Z" fill="#4c6ef5" stroke="#4c6ef5" stroke-width="0.5"/>
          <path d="M10 6L14 8.5V13L10 15.5L6 13V8.5L10 6Z" fill="#0f1117" stroke="#748ffc" stroke-width="0.5"/>
        </svg>
      </div>
      <div class="sidebar__logo-info">
        <span class="sidebar__logo-text">Bonc</span>
        <span class="sidebar__logo-text">Agentic Ontology</span>
        <span class="sidebar__logo-sub">Bonc本体智能体平台</span>
      </div>
    </div>

    <!-- 主导航 -->
    <nav class="sidebar__nav">
      <div class="sidebar__section-label">数据基座</div>
      <RouterLink
        v-for="item in dataNav"
        :key="item.path"
        :to="item.path"
        class="sidebar__item"
        :class="{ 'sidebar__item--active': isActive(item.path) }"
      >
        <span class="sidebar__item-icon" v-html="item.icon"></span>
        <span class="sidebar__item-label">{{ item.label }}</span>
      </RouterLink>

      <div class="sidebar__divider"></div>
      <div class="sidebar__section-label">本体中心</div>
      <RouterLink
        v-for="item in mainNav"
        :key="item.path"
        :to="item.path"
        class="sidebar__item"
        :class="{ 'sidebar__item--active': isActive(item.path) }"
      >
        <span class="sidebar__item-icon" v-html="item.icon"></span>
        <span class="sidebar__item-label">{{ item.label }}</span>
        <span v-if="item.badge" class="sidebar__item-badge">{{ item.badge }}</span>
      </RouterLink>

      <div class="sidebar__divider"></div>
      <div class="sidebar__section-label">场景模拟</div>
      <template v-for="item in sceneNav" :key="item.path">
        <RouterLink
          v-if="!item.disabled"
          :to="item.path"
          class="sidebar__item"
          :class="{ 'sidebar__item--active': isActive(item.path) }"
        >
          <span class="sidebar__item-icon" v-html="item.icon"></span>
          <span class="sidebar__item-label">{{ item.label }}</span>
        </RouterLink>
        <div v-else class="sidebar__item sidebar__item--disabled">
          <span class="sidebar__item-icon" v-html="item.icon"></span>
          <span class="sidebar__item-label">{{ item.label }}</span>
        </div>
      </template>

      <div class="sidebar__divider"></div>
      <div class="sidebar__section-label">智能交互</div>
      <RouterLink
        v-for="item in toolNav"
        :key="item.path"
        :to="item.path"
        class="sidebar__item"
        :class="{ 'sidebar__item--active': isActive(item.path) }"
      >
        <span class="sidebar__item-icon" v-html="item.icon"></span>
        <span class="sidebar__item-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <!-- 底部 -->
    <div class="sidebar__footer">
      <button class="sidebar__item sidebar__item--footer" @click="themeStore.toggle()">
        <span class="sidebar__item-icon" v-html="themeStore.isDark ? sunIcon : moonIcon"></span>
        <span class="sidebar__item-label">{{ themeStore.isDark ? '浅色模式' : '深色模式' }}</span>
      </button>
      <div class="sidebar__item sidebar__item--footer">
        <div class="sidebar__avatar">F</div>
        <span class="sidebar__item-label">用户</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useThemeStore } from '../../store/theme'

const route = useRoute()
const themeStore = useThemeStore()

const isActive = (path: string) => route.path.startsWith(path)

const dataNav = [
  {
    path: '/dashboard',
    label: '系统总揽',
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="8" width="3" height="6" rx="1" fill="currentColor" opacity="0.6"/><rect x="6.5" y="5" width="3" height="9" rx="1" fill="currentColor" opacity="0.8"/><rect x="11" y="2" width="3" height="12" rx="1" fill="currentColor"/></svg>`
  },
  {
    path: '/datasource',
    label: '数据工坊',
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M3 4v4c0 1.1 2.24 2 5 2s5-.9 5-2V4" stroke="currentColor" stroke-width="1.5"/><path d="M3 8v4c0 1.1 2.24 2 5 2s5-.9 5-2V8" stroke="currentColor" stroke-width="1.5"/></svg>`
  },
]

const mainNav = [
  {
    path: '/browser',
    label: '本体浏览器',
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="3" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="13" cy="12" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M8 6v2M8 8L3 10M8 8l5 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`
  },
]

const sceneNav = [
  {
    path: '/scene/fttr',
    label: 'FTTR续约策划',
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 13V7l4-4 4 4v6H4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6.5 13v-3h3v3" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
    disabled: true,
  },
  {
    path: '/scene/broadband',
    label: '宽带退单原因稽核',
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 2h7l3 3v9H3V2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M10 2v3h3" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6 8h4M6 10.5h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  },
  {
    path: '/scene/enterprise',
    label: '政企根因分析',
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v3l2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    disabled: true,
  },
  {
    path: '/scene/mnp',
    label: '携号转网预警',
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2l5 3v6l-5 3-5-3V5l5-3z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 5v6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="13" r="0.8" fill="currentColor"/></svg>`,
    disabled: false,
  },
]

const toolNav = [
  {
    path: '/harness',
    label: '智能编排中心',
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2L14 5.5v5L8 14l-6-3.5v-5L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 6l2.5 1.5v3L8 12l-2.5-1.5v-3L8 6z" fill="currentColor" opacity=".3"/></svg>`
  },
  {
    path: '/copilot',
    label: '智能对话',
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2a6 6 0 100 12A6 6 0 008 2z" stroke="currentColor" stroke-width="1.5"/><path d="M5.5 9.5s.5 1.5 2.5 1.5 2.5-1.5 2.5-1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="6" cy="7" r="0.75" fill="currentColor"/><circle cx="10" cy="7" r="0.75" fill="currentColor"/></svg>`
  },
]

const moonIcon = `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M13.5 9.5A5.5 5.5 0 016.5 2.5a5.5 5.5 0 000 11 5.5 5.5 0 007-4z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`
const sunIcon = `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`
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
  padding: 0 16px;
  height: 64px;
  border-bottom: 1px solid var(--sidebar-border);
  flex-shrink: 0;
}

.sidebar__logo-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar__logo-text {
  font-size: 13px;
  font-weight: 700;
  color: var(--sidebar-text-active);
  letter-spacing: 0.02em;
  line-height: 1.2;
}

.sidebar__logo-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.sidebar__logo-sub {
  font-size: 10px;
  color: var(--sidebar-text-muted);
  letter-spacing: 0.02em;
  line-height: 1.3;
}

.sidebar__nav {
  flex: 1;
  padding: 12px 8px;
  overflow-y: auto;
}

.sidebar__section-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--sidebar-text-muted);
  padding: 4px 8px 6px;
}

.sidebar__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
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

.sidebar__item--disabled {
  opacity: 0.4;
  cursor: not-allowed;
  pointer-events: none;
}

.sidebar__item--active {
  background: var(--sidebar-bg-active);
  color: var(--sidebar-text-active);
}

.sidebar__item--active .sidebar__item-icon {
  color: var(--semantic-400);
}

.sidebar__item-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar__item-label {
  flex: 1;
}

.sidebar__item-badge {
  font-size: 10px;
  font-weight: 600;
  background: var(--semantic-600);
  color: #fff;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  min-width: 18px;
  text-align: center;
}

.sidebar__divider {
  height: 1px;
  background: var(--sidebar-border);
  margin: 8px 0;
}

.sidebar__footer {
  padding: 8px;
  border-top: 1px solid var(--sidebar-border);
  flex-shrink: 0;
}

.sidebar__item--footer {
  color: var(--sidebar-text-muted);
}

.sidebar__avatar {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  background: var(--semantic-600);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
</style>
