<template>
  <a-card :bordered="false" class="stat-card">
    <div class="stat-icon" style="color: #fa5252;"><ThunderboltOutlined /></div>
    <div class="stat-value">{{ data?.total_rules ?? '-' }}</div>
    <div class="stat-label">业务规则</div>
  </a-card>
</template>

<script setup lang="ts">
import { ThunderboltOutlined } from '@ant-design/icons-vue'
import type { PlatformStatsResponse } from '../../../api/monitor'
defineProps<{ data: PlatformStatsResponse | null }>()
</script>

<style scoped>
.stat-card { text-align: center; padding: 20px; height: 100%; display: flex; flex-direction: column; justify-content: center; }
.stat-icon { font-size: 28px; margin-bottom: 8px; }
.stat-value { font-size: 32px; font-weight: 700; line-height: 1.2; }
.stat-label { font-size: 13px; color: var(--color-text-secondary, #888); margin-top: 4px; }
</style>
