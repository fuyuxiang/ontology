<template>
  <div class="placeholder-view">
    <div class="placeholder-view__inner">
      <div class="placeholder-view__icon">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect x="8" y="8" width="32" height="32" rx="8" stroke="var(--neutral-300)" stroke-width="2"/>
          <path d="M16 24h16M16 18h10M16 30h8" stroke="var(--neutral-300)" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <h2 class="text-h2" style="color: var(--neutral-600); margin-top: 16px;">{{ title }} 模块</h2>
      <p class="text-body" style="color: var(--neutral-500); margin-top: 8px; text-align: center; max-width: 320px;">
        该模块正在开发中，设计体系已就绪，后续接入后端接口后即可启用。
      </p>
      <div class="placeholder-view__tags">
        <span class="placeholder-tag placeholder-tag--semantic">前端框架已就绪</span>
        <span class="placeholder-tag placeholder-tag--kinetic">等待后端接口</span>
        <span class="placeholder-tag placeholder-tag--dynamic">设计体系已应用</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => {
  const map: Record<string, string> = {
    '/dataflow': '数据流',
    '/logic': '业务逻辑',
  }
  return map[route.path] ?? '未知'
})
</script>

<style scoped>
.placeholder-view {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
}
.placeholder-view__inner {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.placeholder-view__tags {
  display: flex;
  gap: 8px;
  margin-top: 20px;
  flex-wrap: wrap;
  justify-content: center;
}
.placeholder-tag {
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 500;
}
.placeholder-tag--semantic { background: var(--semantic-50); color: var(--semantic-700); }
.placeholder-tag--kinetic { background: var(--kinetic-50); color: var(--kinetic-700); }
.placeholder-tag--dynamic { background: var(--dynamic-50); color: var(--dynamic-700); }
</style>
