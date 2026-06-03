<template>
  <a-card :bordered="false" class="stat-card">
    <div class="stat-icon">🧩</div>
    <div class="stat-value">{{ data?.total_entities ?? '-' }}</div>
    <div class="stat-label">本体对象总数</div>
    <div class="stat-sub" v-if="data?.by_type && Object.keys(data.by_type).length">
      {{ Object.keys(data.by_type).length }} 种类型
    </div>
  </a-card>
</template>

<script setup lang="ts">
import type { OntologyStatsResponse } from '../../../api/monitor'
defineProps<{ data: OntologyStatsResponse | null }>()
</script>

<style scoped>
.stat-card { text-align: center; padding: 20px; }
.stat-icon { font-size: 32px; margin-bottom: 8px; }
.stat-value { font-size: 36px; font-weight: 700; }
.stat-label { font-size: 14px; color: var(--color-text-secondary, #888); margin-top: 4px; }
.stat-sub { font-size: 12px; color: var(--color-text-tertiary, #aaa); margin-top: 2px; }
</style>
