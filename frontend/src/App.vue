<template>
  <a-config-provider :theme="antdTheme" :locale="antdLocale">
    <div v-if="isLoginPage" class="app-shell--login">
      <RouterView />
    </div>
    <div v-else class="app-shell">
      <AppSidebar />
      <div class="app-main">
        <AppTopbar />
        <main class="app-content">
          <p v-if="restoringSession" role="status">{{ t('shell.restoringSession') }}</p>
          <div v-else-if="restoreError" role="alert"><p>{{ t('shell.restoreError') }}</p><button @click="restoreSession">{{ t('common.retry') }}</button></div>
          <ForbiddenView v-else-if="authStore.user && !canAccessRoute(route.path, permission => authStore.hasPermission(permission))" />
          <RouterView v-else v-slot="{ Component }">
            <Transition name="page" mode="out-in">
              <component :is="Component" :key="authStore.user?.id || 'unauthenticated'" />
            </Transition>
          </RouterView>
        </main>
      </div>
    </div>
    <ToastContainer />
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { useThemeStore } from './store/theme'
import AppSidebar from './components/common/AppSidebar.vue'
import AppTopbar from './components/common/AppTopbar.vue'
import ToastContainer from './components/common/ToastContainer.vue'
import { theme } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import enUS from 'ant-design-vue/es/locale/en_US'
import { usePlatformConfigStore } from './store/platformConfig'
import { platformRouteTitle } from './utils/platformPresentation'
import { useAuthStore } from './store/auth'
import { canAccessRoute } from './utils/access'
import ForbiddenView from './views/auth/ForbiddenView.vue'

const route = useRoute()
const themeStore = useThemeStore()
const authStore = useAuthStore()
const platform = usePlatformConfigStore()
const { t } = useI18n()
const restoringSession = ref(false)
const restoreError = ref(false)
let restoreRequest = 0
const antdLocale = computed(() => platform.language === 'en' ? enUS : zhCN)
watch(() => [route.meta.title, platform.system_name, platform.language], () => { document.title = `${platformRouteTitle(route.meta.title as string | undefined)} — ${platform.system_name}` }, { immediate:true })
const antdTheme = computed(() => ({
  algorithm: themeStore.isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
  token: { colorPrimary: '#4c6ef5', borderRadius: 8, fontSize: 13 },
}))
async function restoreSession() {
  const request = ++restoreRequest
  restoringSession.value = !!authStore.token && !authStore.user
  restoreError.value = false
  if (!restoringSession.value) return
  try { await authStore.fetchUser() }
  catch { /* The recovery panel remains available for transient failures. */ }
  finally {
    if (request === restoreRequest) {
      restoringSession.value = false
      restoreError.value = !!authStore.token && !authStore.user
    }
  }
}
watch(() => authStore.token, () => { void restoreSession() }, { immediate: true })

const isLoginPage = computed(() => route.path === '/login')

onMounted(() => {
  themeStore.init()
  void platform.load()
})
</script>

<style scoped>
.app-shell--login {
  height: 100vh;
}
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--neutral-0);
}
.app-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.app-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: var(--neutral-50);
  padding: 24px 32px;
}
@media (max-width: 768px) {
  .app-content {
    padding: 16px 12px;
  }
}
</style>
