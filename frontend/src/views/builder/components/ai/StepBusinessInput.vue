<template>
  <div class="step-input">
    <h2 class="step-input__title">描述你的业务场景</h2>
    <p class="step-input__sub">输入业务描述，下一步从已注册的数据资产中选择数据表</p>
    <textarea
      v-model="desc"
      class="step-input__textarea"
      placeholder="用一两句话描述你想构建本体的业务场景，例如涉及哪些业务对象、要解决什么问题..."
      rows="5"
    ></textarea>
    <button
      class="step-input__btn"
      :disabled="!desc.trim()"
      @click="emit('next', { businessDesc: desc.trim() })"
    >
      下一步：选择数据表
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{ (e: 'next', payload: { businessDesc: string }): void }>()
const desc = ref('')
</script>

<style scoped>
.step-input { max-width: 720px; margin: 0 auto; padding: 32px 24px; }
.step-input__title { font-size: 20px; font-weight: 600; margin-bottom: 8px; color: #1a1a2e; }
.step-input__sub { font-size: 13px; color: #666; margin-bottom: 16px; }
.step-input__textarea { width: 100%; padding: 12px; border: 1px solid #d0d0d0; border-radius: 8px; font-size: 14px; resize: vertical; font-family: inherit; }
.step-input__textarea:focus { outline: none; border-color: #4a6fa5; }
.step-input__btn { margin-top: 12px; padding: 10px 24px; background: #4a6fa5; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.step-input__btn:disabled { opacity: 0.5; cursor: default; }
.step-input__btn:hover:not(:disabled) { background: #3d5f8c; }
</style>
