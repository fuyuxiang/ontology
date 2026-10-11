<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
        <div
          ref="panel"
          class="modal-panel"
          :style="{ maxWidth: width }"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
        >
          <div class="modal-header">
            <h3 :id="titleId" class="text-h2">{{ title }}</h3>
            <button type="button" class="modal-close" aria-label="关闭" @click="$emit('close')">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path
                  d="M4 4l8 8M12 4l-8 8"
                  stroke="currentColor"
                  stroke-width="1.5"
                  stroke-linecap="round"
                />
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <slot />
          </div>
          <div v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, useId } from 'vue'
import { useDialogFocus } from '../../composables/useDialogFocus'

const props = defineProps<{
  visible: boolean
  title: string
  width?: string
}>()

const emit = defineEmits<{
  close: []
}>()
const panel = ref<HTMLElement | null>(null)
const titleId = useId()
useDialogFocus(
  () => props.visible,
  panel,
  () => emit('close'),
)
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}
.modal-panel {
  background: var(--neutral-0);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  width: 90%;
  max-width: 560px;
  max-height: calc(100dvh - 48px);
  display: flex;
  flex-direction: column;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
  gap: 16px;
  flex-shrink: 0;
}
.modal-header h3 {
  min-width: 0;
  overflow-wrap: anywhere;
}
.modal-close {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  color: var(--neutral-500);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition-fast);
  flex-shrink: 0;
}
.modal-close:hover {
  background: var(--neutral-100);
  color: var(--neutral-800);
}
.modal-body {
  padding: 16px 24px;
  overflow-y: auto;
  overscroll-behavior: contain;
  min-height: 0;
  flex: 1;
}
.modal-footer {
  padding: 12px 24px 20px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid var(--neutral-100);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.modal-enter-active {
  animation: overlay-in 150ms ease-out;
}
.modal-leave-active {
  animation: overlay-in 100ms ease-in reverse;
}
.modal-enter-active .modal-panel {
  animation: panel-in 200ms ease-out;
}
.modal-leave-active .modal-panel {
  animation: panel-in 150ms ease-in reverse;
}
@keyframes overlay-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
@keyframes panel-in {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(-8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
</style>
