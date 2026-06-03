<template>
  <a-card :bordered="false" class="stat-card">
    <div class="stat-icon">🤖</div>
    <div class="stat-value">{{ data?.published_agents ?? '-' }}</div>
    <div class="stat-label">活跃 Agent</div>
    <div class="stat-sub">共 {{ data?.total_agents ?? '-' }} 个 / {{ data?.total_skills ?? '-' }} 个技能</div>
  </a-card>
</template>

<script setup lang="ts">
import type { AgentActivityResponse } from '../../../api/monitor'
defineProps<{ data: AgentActivityResponse | null }>()
</script>

<style scoped>
.stat-card { text-align: center; padding: 20px; }
.stat-icon { font-size: 32px; margin-bottom: 8px; }
.stat-value { font-size: 36px; font-weight: 700; }
.stat-label { font-size: 14px; color: var(--color-text-secondary, #888); margin-top: 4px; }
.stat-sub { font-size: 12px; color: var(--color-text-tertiary, #aaa); margin-top: 2px; }
</style>
