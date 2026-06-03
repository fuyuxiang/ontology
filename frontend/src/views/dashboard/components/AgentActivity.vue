<template>
  <a-card :bordered="false" class="stat-card">
    <div class="stat-icon" style="color: #20c997;"><RobotOutlined /></div>
    <div class="stat-value">{{ data?.published_agents ?? '-' }}</div>
    <div class="stat-label">活跃 Agent</div>
    <div class="stat-sub">共 {{ data?.total_agents ?? '-' }} 个 / {{ data?.total_skills ?? '-' }} 个技能</div>
  </a-card>
</template>

<script setup lang="ts">
import { RobotOutlined } from '@ant-design/icons-vue'
import type { AgentActivityResponse } from '../../../api/monitor'
defineProps<{ data: AgentActivityResponse | null }>()
</script>

<style scoped>
.stat-card { text-align: center; padding: 20px; height: 100%; display: flex; flex-direction: column; justify-content: center; }
.stat-icon { font-size: 28px; margin-bottom: 8px; }
.stat-value { font-size: 32px; font-weight: 700; line-height: 1.2; }
.stat-label { font-size: 13px; color: var(--color-text-secondary, #888); margin-top: 4px; }
.stat-sub { font-size: 11px; color: var(--color-text-tertiary, #aaa); margin-top: 2px; }
</style>
