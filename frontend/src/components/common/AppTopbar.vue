<template>
  <header class="topbar">
    <div class="topbar__left">
      <OntologyBreadcrumb :items="breadcrumbs" />
    </div>
    <div class="topbar__right">
      <button class="topbar__icon-btn" :title="t('shell.pendingFuture')" disabled>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M8 2a4 4 0 00-4 4v3l-1 1.5h10L12 9V6a4 4 0 00-4-4z"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linejoin="round"
          />
          <path d="M6.5 13a1.5 1.5 0 003 0" stroke="currentColor" stroke-width="1.5" />
        </svg>
        <span class="topbar__badge"></span>
      </button>
      <div class="topbar__divider"></div>
      <button
        type="button"
        class="topbar__user"
        :aria-label="t('shell.openSettings')"
        aria-haspopup="dialog"
        @click="showSettings = true"
      >
        <div class="topbar__user-avatar">{{ initial }}</div>
        <span class="topbar__user-name" :title="userName">{{ userName }}</span>
      </button>
    </div>

    <SettingsDialog :visible="showSettings" @close="showSettings = false" />
  </header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { platformRouteTitle } from '../../utils/platformPresentation'
const { t } = useI18n()
import { useAuthStore } from '../../store/auth'
import OntologyBreadcrumb from './OntologyBreadcrumb.vue'
import SettingsDialog from './SettingsDialog.vue'

const route = useRoute()
const authStore = useAuthStore()
const showSettings = ref(false)

const userName = computed(() => authStore.user?.name || t('shell.user'))
const initial = computed(() => userName.value.charAt(0).toUpperCase())

const breadcrumbs = computed(() => {
  const title = platformRouteTitle(route.meta.title as string | undefined)
  if (route.path.startsWith('/skills'))
    return route.name === 'skills-list'
      ? [{ label: t('shell.applications') }, { label: t('shell.skills') }]
      : [
          { label: t('shell.applications') },
          { label: t('shell.skills'), path: '/skills' },
          { label: title || t('shell.skillDetail') },
        ]
  if (route.path.startsWith('/agent/manage'))
    return route.name === 'agent-manage'
      ? [{ label: t('shell.applications') }, { label: t('shell.agents') }]
      : [
          { label: t('shell.applications') },
          { label: t('shell.agents'), path: '/agent/manage' },
          { label: title || t('shell.agentDetail') },
        ]
  if (title) return [{ label: title }]
  return [{ label: t('shell.home') }]
})
</script>

<style scoped>
.topbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--neutral-0);
  border-bottom: 1px solid var(--neutral-200);
  flex-shrink: 0;
  gap: 16px;
}
.topbar__left {
  display: flex;
  align-items: center;
  min-width: 0;
  overflow: hidden;
}
.topbar__right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.topbar__icon-btn {
  position: relative;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--neutral-500);
  cursor: pointer;
  transition:
    background var(--transition-fast),
    color var(--transition-fast);
}
.topbar__icon-btn:hover {
  background: var(--neutral-100);
  color: var(--neutral-700);
}
.topbar__badge {
  position: absolute;
  top: 7px;
  right: 7px;
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--status-error);
  border: 1.5px solid #fff;
}
.topbar__divider {
  width: 1px;
  height: 24px;
  background: var(--neutral-200);
  margin: 0 8px;
}
.topbar__user {
  border: 0;
  background: transparent;
  font: inherit;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.topbar__user:hover {
  background: var(--neutral-100);
}
.topbar__user-avatar {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--semantic-500), var(--semantic-700));
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.topbar__user-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-700);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 768px) {
  .topbar {
    padding: 0 12px 0 52px;
    gap: 8px;
  }
  .topbar__left {
    min-width: 0;
    flex: 1;
    overflow: hidden;
  }
  .topbar__left :deep(.ontology-breadcrumb) {
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    font-size: 11px;
  }
  .topbar__left :deep(.ontology-breadcrumb__item) {
    min-width: 0;
    flex-shrink: 1;
    text-overflow: ellipsis;
    overflow: hidden;
  }
  .topbar__user-name,
  .topbar__icon-btn,
  .topbar__divider {
    display: none;
  }
  .topbar__user {
    padding: 4px;
  }
}
</style>
