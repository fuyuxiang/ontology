<template>
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
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from './store/theme'
import AppSidebar from './components/common/AppSidebar.vue'
import AppTopbar from './components/common/AppTopbar.vue'
import ToastContainer from './components/common/ToastContainer.vue'

const route = useRoute()
const themeStore = useThemeStore()

const isLoginPage = computed(() => route.path === '/login')

onMounted(() => {
  themeStore.init()
})
</script>

<style scoped>
.app-shell--login { height: 100vh; }
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #fff;
}
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.app-content {
  flex: 1;
  overflow-y: auto;
  background: var(--neutral-50);
  padding: 24px 32px;
}
</style>
