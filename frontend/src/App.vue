<template>
  <a-config-provider :theme="antdTheme" :locale="zhCN">
    <div v-if="isLoginPage" class="app-shell--login">
      <RouterView />
    </div>
    <div v-else class="app-shell">
      <AppSidebar />
      <div class="app-main">
        <AppTopbar />
        <main class="app-content">
          <RouterView v-slot="{ Component }">
            <Transition name="page" mode="out-in">
              <component :is="Component" />
            </Transition>
          </RouterView>
        </main>
      </div>
    </div>
    <ToastContainer />
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from './store/theme'
import AppSidebar from './components/common/AppSidebar.vue'
import AppTopbar from './components/common/AppTopbar.vue'
import ToastContainer from './components/common/ToastContainer.vue'
import { theme } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useAuthStore } from './store/auth'

const route = useRoute()
const themeStore = useThemeStore()
const authStore = useAuthStore()
const antdTheme = computed(() => ({
  algorithm: themeStore.isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
  token: { colorPrimary: '#4c6ef5', borderRadius: 8, fontSize: 13 },
}))
watch(
  () => authStore.token,
  (token) => {
    if (token && !authStore.user) void authStore.fetchUser()
  },
  { immediate: true },
)

const isLoginPage = computed(() => route.path === '/login')

onMounted(() => {
  themeStore.init()
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
