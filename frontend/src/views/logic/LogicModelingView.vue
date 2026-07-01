<template>
  <div class="logic-modeling">
    <div class="logic-modeling__header">
      <div>
        <h1 class="text-display">逻辑建模</h1>
        <p class="text-caption" style="margin-top: 4px;">在对象模型之上定义可复用的计算与判定逻辑</p>
      </div>
    </div>

    <div class="logic-modeling__tabs">
      <button
        v-for="t in tabs" :key="t.value"
        class="lm-tab"
        :class="{ 'lm-tab--active': activeTab === t.value }"
        @click="switchTab(t.value)"
      >
        <span class="lm-tab__label">{{ t.label }}</span>
        <span class="lm-tab__hint">{{ t.hint }}</span>
      </button>
    </div>

    <div class="logic-modeling__body">
      <FunctionsView v-if="activeTab === 'function'" embedded />
      <LogicView v-else embedded />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LogicView from './LogicView.vue'
import FunctionsView from './FunctionsView.vue'

type Tab = 'function' | 'rule'

const route = useRoute()
const router = useRouter()

const tabs: { value: Tab; label: string; hint: string }[] = [
  { value: 'function', label: '函数', hint: '计算逻辑 · 有返回值' },
  { value: 'rule', label: '规则', hint: '判定逻辑 · 条件触发' },
]

function tabFromPath(path: string): Tab {
  return path.includes('/functions') ? 'function' : 'rule'
}

const activeTab = ref<Tab>(tabFromPath(route.path))

function switchTab(t: Tab) {
  if (activeTab.value === t) return
  activeTab.value = t
  const path = t === 'function' ? '/logic/functions' : '/logic/rules'
  router.replace({ path, query: route.query })
}

// 外部（如资源选择器）直接跳到 /logic/rules 或 /logic/functions 时同步 Tab
watch(() => route.path, (p) => {
  if (p.startsWith('/logic/')) activeTab.value = tabFromPath(p)
})
</script>

<style scoped>
.logic-modeling { padding: 24px 32px; max-width: 1200px; }
.logic-modeling__header { margin-bottom: 20px; }

.logic-modeling__tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--neutral-200, #e5e5e5);
  margin-bottom: 24px;
}
.lm-tab {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 20px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  text-align: left;
  transition: color 0.15s, border-color 0.15s;
}
.lm-tab__label { font-size: 14px; font-weight: 600; color: var(--neutral-600, #666); }
.lm-tab__hint { font-size: 11px; color: var(--neutral-400, #aaa); }
.lm-tab:hover .lm-tab__label { color: var(--semantic-600, #4c6ef5); }
.lm-tab--active { border-bottom-color: var(--semantic-600, #4c6ef5); }
.lm-tab--active .lm-tab__label { color: var(--semantic-700, #4338ca); }
</style>
