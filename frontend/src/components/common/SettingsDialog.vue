<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="settings-overlay" @click.self="emit('close')">
        <div class="settings-dialog">
          <div class="settings-dialog__header">
            <h3 class="settings-dialog__title">系统设置</h3>
            <button class="settings-dialog__close" @click="emit('close')">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
          <div class="settings-dialog__body">
            <div class="settings-dialog__section">
              <div class="settings-dialog__label">用户信息</div>
              <div class="settings-dialog__user">
                <div class="settings-dialog__avatar">{{ initial }}</div>
                <div>
                  <div class="settings-dialog__name">{{ authStore.user?.name || '用户' }}</div>
                  <div class="settings-dialog__role">{{ authStore.user?.role || 'viewer' }}</div>
                </div>
              </div>
            </div>
            <div class="settings-dialog__section">
              <div class="settings-dialog__label">外观</div>
              <div class="settings-dialog__row">
                <span>深色模式</span>
                <button class="settings-dialog__toggle" :class="{ 'settings-dialog__toggle--on': themeStore.isDark }" @click="themeStore.toggle()">
                  <span class="settings-dialog__toggle-dot"></span>
                </button>
              </div>
            </div>
          </div>
          <div class="settings-dialog__footer">
            <button class="settings-dialog__logout" @click="handleLogout">退出登录</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../store/auth'
import { useThemeStore } from '../../store/theme'

defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: [] }>()

const authStore = useAuthStore()
const themeStore = useThemeStore()
const router = useRouter()

const initial = computed(() => (authStore.user?.name || 'U').charAt(0).toUpperCase())

function handleLogout() {
  authStore.logout()
  emit('close')
  router.push('/login')
}
</script>

<style scoped>
.settings-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
}
.settings-dialog {
  width: 360px; background: var(--neutral-0);
  border-radius: 12px; border: 1px solid var(--neutral-200);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}
.settings-dialog__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--neutral-200);
}
.settings-dialog__title { font-size: 15px; font-weight: 600; color: var(--neutral-800); }
.settings-dialog__close {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  border: none; background: transparent; border-radius: 6px;
  color: var(--neutral-500); cursor: pointer;
}
.settings-dialog__close:hover { background: var(--neutral-100); }
.settings-dialog__body { padding: 16px 20px; }
.settings-dialog__section { margin-bottom: 20px; }
.settings-dialog__section:last-child { margin-bottom: 0; }
.settings-dialog__label { font-size: 11px; font-weight: 600; color: var(--neutral-400); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
.settings-dialog__user { display: flex; align-items: center; gap: 12px; }
.settings-dialog__avatar {
  width: 36px; height: 36px; border-radius: 50%;
  background: var(--semantic-600); color: #fff;
  font-size: 14px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.settings-dialog__name { font-size: 14px; font-weight: 600; color: var(--neutral-800); }
.settings-dialog__role { font-size: 12px; color: var(--neutral-500); }
.settings-dialog__row {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 13px; color: var(--neutral-700);
}
.settings-dialog__toggle {
  width: 40px; height: 22px; border-radius: 11px; border: none;
  background: var(--neutral-300); cursor: pointer; position: relative;
  transition: background 0.2s;
}
.settings-dialog__toggle--on { background: var(--semantic-600); }
.settings-dialog__toggle-dot {
  position: absolute; top: 2px; left: 2px;
  width: 18px; height: 18px; border-radius: 50%;
  background: #fff; transition: transform 0.2s;
}
.settings-dialog__toggle--on .settings-dialog__toggle-dot { transform: translateX(18px); }
.settings-dialog__footer {
  padding: 12px 20px; border-top: 1px solid var(--neutral-200);
}
.settings-dialog__logout {
  width: 100%; height: 36px; border-radius: 8px; border: 1px solid var(--neutral-200);
  background: transparent; color: var(--neutral-600);
  font-size: 13px; font-weight: 500; cursor: pointer;
  transition: all 0.15s;
}
.settings-dialog__logout:hover { background: var(--neutral-50); color: #ef4444; border-color: #fca5a5; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
