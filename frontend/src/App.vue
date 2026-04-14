<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <AppTopbar @search="searchRef?.open()" />
      <main class="app-content">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
      <!-- 底部状态栏 -->
      <footer class="app-statusbar">
        <span>{{ statsText }}</span>
        <span class="app-statusbar__dot app-statusbar__dot--success"></span>
        <span>上次保存 {{ lastSaved }}</span>
      </footer>
    </div>
  </div>

  <!-- 全局组件 -->
  <SearchCommand ref="searchRef" />
  <ToastContainer />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useThemeStore } from './store/theme'
import { get } from './api/client'
import AppSidebar from './components/common/AppSidebar.vue'
import AppTopbar from './components/common/AppTopbar.vue'
import SearchCommand from './components/common/SearchCommand.vue'
import ToastContainer from './components/common/ToastContainer.vue'

const themeStore = useThemeStore()
const searchRef = ref<InstanceType<typeof SearchCommand>>()

const stats = ref<{ entity_count: number; relation_count: number; rule_count: number }>({ entity_count: 0, relation_count: 0, rule_count: 0 })
const statsText = computed(() => `${stats.value.entity_count} 对象类型 · ${stats.value.relation_count} 关系 · ${stats.value.rule_count} 规则`)

async function fetchStats() {
  try {
    stats.value = await get<typeof stats.value>('/dashboard/stats')
  } catch { /* ignore */ }
}

const lastSaved = ref('')
function updateTime() {
  lastSaved.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  themeStore.init()
  updateTime()
  setInterval(updateTime, 60000)
  fetchStats()
})
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--neutral-0);
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
}

/* 底部状态栏 — Layout A 规格：28px */
.app-statusbar {
  height: 28px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  background: var(--neutral-50);
  border-top: 1px solid var(--neutral-200);
  font-size: 11px;
  color: var(--neutral-500);
  flex-shrink: 0;
}
.app-statusbar__dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}
.app-statusbar__dot--success { background: var(--status-success); }
.app-statusbar__dot--warning { background: var(--status-warning); }
.app-statusbar__dot--error   { background: var(--status-error); }
</style>
