<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast"
          :class="`toast--${toast.type}`"
          @click="remove(toast.id)"
        >
          <span class="toast__icon" v-html="icons[toast.type]"></span>
          <span class="toast__message">{{ toast.message }}</span>
          <button class="toast__close" @click.stop="remove(toast.id)">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToast } from '../../composables/useToast'

const { toasts, remove } = useToast()

const icons: Record<string, string> = {
  success: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" fill="var(--status-success)"/><path d="M4 7l2 2 4-4" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  error:   `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" fill="var(--status-error)"/><path d="M4.5 4.5l5 5M9.5 4.5l-5 5" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  warning: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5L13 12H1L7 1.5z" fill="var(--status-warning)"/><path d="M7 5.5v3M7 10v.5" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  info:    `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" fill="var(--status-info)"/><path d="M7 6v4M7 4v.5" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>`,
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  font-size: 13px;
  font-weight: 500;
  min-width: 260px;
  max-width: 400px;
  pointer-events: all;
  cursor: pointer;
  border: 1px solid transparent;
}

.toast--success { background: var(--status-success-bg); color: var(--dynamic-800); border-color: var(--status-success); }
.toast--error   { background: var(--status-error-bg);   color: var(--status-error);   border-color: var(--status-error); }
.toast--warning { background: var(--status-warning-bg); color: var(--kinetic-800);    border-color: var(--status-warning); }
.toast--info    { background: var(--status-info-bg);    color: var(--semantic-800);   border-color: var(--status-info); }

.toast__icon { flex-shrink: 0; display: flex; align-items: center; }
.toast__message { flex: 1; }
.toast__close {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: currentColor;
  opacity: 0.6;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: opacity var(--transition-fast);
}
.toast__close:hover { opacity: 1; }

/* 过渡 */
.toast-enter-active { transition: opacity 300ms ease-out, transform 300ms ease-out; }
.toast-leave-active { transition: opacity 250ms ease-in, transform 250ms ease-in; }
.toast-enter-from   { opacity: 0; transform: translateX(100%); }
.toast-leave-to     { opacity: 0; transform: translateX(100%); }
.toast-move         { transition: transform 300ms ease; }
</style>
