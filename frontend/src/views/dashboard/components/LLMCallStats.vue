<template>
  <a-card :bordered="false" class="stat-card">
    <div class="stat-icon" style="color: #7950f2;"><ApiOutlined /></div>
    <div class="stat-value">{{ data?.total_24h ?? '-' }}</div>
    <div class="stat-label">大模型调用 (24h)</div>
    <div class="stat-sub" v-if="topModule">最多: {{ topModule }}</div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ApiOutlined } from '@ant-design/icons-vue'
import type { LLMStatsResponse } from '../../../api/monitor'

const props = defineProps<{ data: LLMStatsResponse | null }>()

const topModule = computed(() => {
  if (!props.data?.by_module) return null
  const entries = Object.entries(props.data.by_module)
  if (!entries.length) return null
  const top = entries.reduce((a, b) => (b[1].count > a[1].count ? b : a))
  return `${top[0]} (${top[1].count}次)`
})
</script>

<style scoped>
.stat-card { text-align: center; padding: 20px; height: 100%; display: flex; flex-direction: column; justify-content: center; }
.stat-icon { font-size: 28px; margin-bottom: 8px; }
.stat-value { font-size: 32px; font-weight: 700; line-height: 1.2; }
.stat-label { font-size: 13px; color: var(--color-text-secondary, #888); margin-top: 4px; }
.stat-sub { font-size: 11px; color: var(--color-text-tertiary, #aaa); margin-top: 2px; }
</style>
