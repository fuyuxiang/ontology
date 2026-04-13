<template>
  <div class="action-button-wrap">
    <!-- 默认态 -->
    <button
      v-if="state === 'default'"
      class="action-button action-button--default"
      :disabled="disabled"
      @click="handleClick"
    >
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M3 2.5l8 4.5-8 4.5V2.5z" fill="currentColor"/>
      </svg>
      {{ label }}
    </button>

    <!-- 确认态 -->
    <div v-else-if="state === 'confirm'" class="action-button action-button--confirm">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M7 2v5M7 9.5v1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.5"/>
      </svg>
      <span>确认执行？影响 {{ affectedCount.toLocaleString() }} 人</span>
      <div class="action-button__confirm-actions">
        <button class="action-button__cancel" @click="cancel">取消</button>
        <button class="action-button__ok" @click="confirm">确认</button>
      </div>
    </div>

    <!-- 执行中 -->
    <button v-else-if="state === 'executing'" class="action-button action-button--executing" disabled>
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" class="spin">
        <circle cx="7" cy="7" r="5" stroke="currentColor" stroke-width="1.5" stroke-dasharray="20 12"/>
      </svg>
      执行中 Step {{ currentStep }}/{{ totalSteps }}...
    </button>

    <!-- 完成态 -->
    <button v-else-if="state === 'done'" class="action-button action-button--done" @click="reset">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M2.5 7l3 3 6-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      执行完成 {{ resultText }}
    </button>

    <!-- 失败态 -->
    <button v-else-if="state === 'failed'" class="action-button action-button--failed" @click="reset">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M4 4l6 6M10 4l-6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      执行失败 · 点击重试
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

type ActionState = 'default' | 'confirm' | 'executing' | 'done' | 'failed'

const props = withDefaults(defineProps<{
  label?: string
  affectedCount?: number
  totalSteps?: number
  resultText?: string
  requireConfirm?: boolean
  disabled?: boolean
}>(), {
  label: '执行策略',
  affectedCount: 0,
  totalSteps: 6,
  resultText: '',
  requireConfirm: true,
  disabled: false,
})

const emit = defineEmits<{
  execute: []
  cancel: []
}>()

const state = ref<ActionState>('default')
const currentStep = ref(0)

function handleClick() {
  if (props.requireConfirm) {
    state.value = 'confirm'
  } else {
    runExecute()
  }
}

function cancel() {
  state.value = 'default'
  emit('cancel')
}

async function confirm() {
  await runExecute()
}

async function runExecute() {
  state.value = 'executing'
  currentStep.value = 0
  emit('execute')
  // 模拟步骤进度（实际使用时由父组件控制）
  for (let i = 1; i <= props.totalSteps; i++) {
    await new Promise(r => setTimeout(r, 600))
    currentStep.value = i
  }
  state.value = 'done'
}

function reset() {
  state.value = 'default'
  currentStep.value = 0
}

// 暴露给父组件控制状态
defineExpose({ state, reset, setFailed: () => { state.value = 'failed' } })
</script>

<style scoped>
.action-button-wrap { display: inline-flex; }

.action-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
  font-family: var(--font-sans);
  white-space: nowrap;
}

.action-button--default {
  background: var(--kinetic-500);
  color: #ffffff;
}
.action-button--default:hover:not(:disabled) {
  background: var(--kinetic-600);
  box-shadow: var(--shadow-md);
}
.action-button--default:disabled {
  background: var(--neutral-100);
  color: var(--neutral-400);
  border: 1px solid var(--neutral-200);
  cursor: not-allowed;
  opacity: 0.7;
}

.action-button--confirm {
  background: var(--status-warning-bg);
  color: var(--kinetic-700);
  border: 1px solid var(--kinetic-400);
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
}
.action-button__confirm-actions {
  display: flex;
  gap: 8px;
  align-self: flex-end;
}
.action-button__cancel {
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--neutral-300);
  background: transparent;
  font-size: 12px;
  color: var(--neutral-600);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.action-button__cancel:hover { background: var(--neutral-100); }
.action-button__ok {
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--kinetic-600);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.action-button__ok:hover { background: var(--kinetic-700); }

.action-button--executing {
  background: var(--semantic-50);
  color: var(--semantic-700);
  border: 1px solid var(--semantic-300);
  cursor: wait;
}

.action-button--done {
  background: var(--dynamic-50);
  color: var(--dynamic-700);
  border: 1px solid var(--dynamic-300);
}
.action-button--done:hover { background: var(--dynamic-100); }

.action-button--failed {
  background: var(--status-error-bg);
  color: var(--status-error);
  border: 1px solid var(--status-error);
}
.action-button--failed:hover { opacity: 0.85; }

.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
